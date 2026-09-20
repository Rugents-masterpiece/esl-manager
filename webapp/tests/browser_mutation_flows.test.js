"use strict";
const assert = require("node:assert/strict");
const base = process.env.ESL_BROWSER_BASE;
const cdp = process.env.ESL_BROWSER_CDP;
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

(async () => {
  const watchdog = setTimeout(() => { console.error("browser flow watchdog"); process.exit(2); }, 15000);
  console.error("opening target");
  const target = await (await fetch(`${cdp}/json/new?${encodeURIComponent(base)}`, { method: "PUT" })).json();
  assert.ok(target, "browser page target must be available");
  console.error(JSON.stringify(target));
  console.error("target opened");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let sequence = 0;
  const pending = new Map();
  const runtimeErrors = [];
  const executionContexts = new Map();
  let activeContextId = null;
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const callbacks = pending.get(message.id); pending.delete(message.id);
      message.error ? callbacks.reject(message.error) : callbacks.resolve(message.result);
    } else if (message.method === "Runtime.executionContextCreated") {
      executionContexts.set(message.params.context.id, message.params.context);
    } else if (message.method === "Runtime.executionContextDestroyed") {
      executionContexts.delete(message.params.executionContextId);
      if (activeContextId === message.params.executionContextId) activeContextId = null;
    } else if (message.method === "Runtime.executionContextsCleared") {
      executionContexts.clear(); activeContextId = null;
    } else if (message.method === "Runtime.exceptionThrown") {
      runtimeErrors.push(message.params);
    } else if (message.method === "Log.entryAdded") {
      const entry = message.params.entry;
      const expected401 = entry.source === "network" && entry.text.includes("401")
        && ["/api/session", "/api/tags/staged", "/api/tags/tag-001/configuration", "/api/vendor/templates/clone"]
          .includes(new URL(entry.url).pathname);
      const expectedPreviewFallback = entry.source === "network" && entry.text.includes("400")
        && /^\/api\/vendor\/templates\/[0-9]+\/preview$/.test(new URL(entry.url).pathname);
      if (!expected401 && !expectedPreviewFallback) runtimeErrors.push(message.params);
    }
  };
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  console.error("websocket opened");
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence; pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    assert.ok(activeContextId, "loaded page execution context must be selected");
    const response = await call("Runtime.evaluate", { expression, contextId: activeContextId, returnByValue: true, awaitPromise: true });
    if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
    return response.result.value;
  };
  const pointerClick = async (expression, count = 1) => {
    const response = await call("Runtime.evaluate", {
      expression: `(() => { const target = (${expression}); if (target) target.scrollIntoView({ block: "center", inline: "center" }); return target; })()`,
      contextId: activeContextId,
      returnByValue: false,
    });
    if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
    const objectId = response.result.objectId;
    assert.ok(objectId, `pointer target must resolve to an element: ${expression}`);
    const box = await call("DOM.getBoxModel", { objectId });
    await call("Runtime.releaseObject", { objectId });
    const quad = box.model.content;
    const x = (quad[0] + quad[2] + quad[4] + quad[6]) / 4;
    const y = (quad[1] + quad[3] + quad[5] + quad[7]) / 4;
    await call("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    for (let click = 0; click < count; click += 1) {
      await call("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await call("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    }
  };
  const waitFor = async (expression) => {
    for (let attempt = 0; attempt < 80; attempt += 1) {
      try {
        if (await evaluate(expression)) return;
      } catch (_error) {
        // The new document may not have installed application globals yet.
      }
      await delay(25);
    }
    throw new Error(`Timed out waiting for ${expression}; runtime=${JSON.stringify(runtimeErrors)}`);
  };
  const installDelayedMutation = (delayedPath = null) => evaluate(`(() => {
    window.__nativeFetch ||= window.fetch.bind(window);
    window.__mutationCounts ||= {};
    window.__releaseMutation = null;
    window.fetch = (url, options = {}) => {
      const method = (options.method || "GET").toUpperCase();
      const path = typeof url === "string" ? url : url.url;
      const pendingResponse = window.__nativeFetch(url, options);
      const shouldDelay = ${JSON.stringify(delayedPath)}
        ? path === ${JSON.stringify(delayedPath)}
        : method !== "GET" && path !== "/api/session";
      if (shouldDelay) {
        const key = method + " " + path;
        window.__mutationCounts[key] = (window.__mutationCounts[key] || 0) + 1;
        return new Promise((resolve, reject) => {
          window.__releaseMutation = () => pendingResponse.then(resolve, reject);
        });
      }
      return pendingResponse;
    };
  })()`);
  const assertBusyClosePaths = async (dialogId) => {
    const result = await evaluate(`(() => {
      const dialog = byId(${JSON.stringify(dialogId)});
      dialog.querySelector(".dialog-close, .auth-close").click();
      const afterButton = dialog.open;
      dialog.dispatchEvent(new Event("cancel", { cancelable: true }));
      const afterEscape = dialog.open;
      dialog.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      const afterBackdrop = dialog.open;
      const directClose = closeDialog(dialog);
      return { afterButton, afterEscape, afterBackdrop, directClose, afterDirect: dialog.open };
    })()`);
    assert.deepEqual(result, { afterButton: true, afterEscape: true, afterBackdrop: true, directClose: false, afterDirect: true });
  };
  const releaseAndAssertAuthFocus = async (buttonId) => {
    assert.equal(await evaluate(`byId(${JSON.stringify(buttonId)}).disabled`), true);
    console.error(`releasing ${buttonId}`);
    await evaluate(`window.__releaseMutation()`);
    console.error(`released ${buttonId}`);
    await waitFor(`byId("auth-modal").open`);
    console.error(`auth open ${buttonId}`);
    assert.equal(await evaluate(`document.activeElement === byId("auth-token")`), true);
    await waitFor(`!byId(${JSON.stringify(buttonId)}).disabled`);
    await evaluate(`closeAuthModal()`);
    assert.equal(await evaluate(`document.activeElement === byId(${JSON.stringify(buttonId)})`), true);
  };

  console.error("enabling domains");
  await call("Page.enable"); await call("Runtime.enable"); await call("DOM.enable"); await call("Log.enable");
  const expectedOrigin = new URL(base).origin;
  for (let attempt = 0; attempt < 80 && !activeContextId; attempt += 1) {
    const context = [...executionContexts.values()].find((candidate) => (
      candidate.auxData?.isDefault
      && candidate.auxData.frameId === target.id
      && candidate.origin === expectedOrigin
    ));
    if (context) activeContextId = context.id;
    else await delay(25);
  }
  assert.ok(activeContextId, `navigated local page execution context must be available: ${JSON.stringify([...executionContexts.values()])}`);
  console.error("domains enabled");
  console.error(JSON.stringify(await evaluate(`({url:location.href,status:document.getElementById("app-status")?.textContent,ready:typeof byId})`)));
  await waitFor(`typeof byId === "function" && byId("app-status") && byId("app-status").textContent === "API pripojené"`);
  console.error("app ready");

  await installDelayedMutation();
  await pointerClick('byId("add-tag")');
  assert.equal(await evaluate(`document.activeElement === byId("new-controller")`), true);
  await evaluate(`(() => {
    byId("new-router").value = byId("new-router").options[1].value;
    byId("new-template").value = byId("new-template").options[1].value;
    byId("new-mac").value = "AA:BB:CC:DD:EE:99";
  })()`);
  await pointerClick('byId("save-new-tag")');
  console.error("create submitted");
  await waitFor(`typeof window.__releaseMutation === "function"`);
  console.error("create delayed");
  await assertBusyClosePaths("tag-modal");
  console.error("create close paths checked");
  await releaseAndAssertAuthFocus("save-new-tag");
  console.log("create flow ok");
  await evaluate(`closeDialog(byId("tag-modal"))`);
  assert.equal(await evaluate(`document.activeElement === byId("add-tag")`), true);

  await installDelayedMutation();
  await pointerClick('document.querySelector(".tag-row")');
  await waitFor(`byId("detail-id").value !== ""`);
  assert.equal(await evaluate(`byId("tag-drawer").contains(document.activeElement)`), true);
  await pointerClick('byId("save-tag-detail")');
  await waitFor(`typeof window.__releaseMutation === "function"`);
  await assertBusyClosePaths("tag-drawer");
  await releaseAndAssertAuthFocus("save-tag-detail");
  console.log("detail flow ok");
  await evaluate(`closeDialog(byId("tag-drawer"))`);
  assert.equal(await evaluate(`document.activeElement === document.querySelector(".tag-row")`), true);

  await evaluate(`location.hash = "templates"`);
  await waitFor(`!byId("view-templates").hidden && document.querySelector("[data-clone-id]:not(:disabled)")`);
  const familyCards = await evaluate(`[...document.querySelectorAll("#templates-grid .card h2")].map((node) => node.textContent)`);
  assert.equal(familyCards.includes("Základná cenovka"), true);
  assert.equal(familyCards.includes("Wrong 250 EPD"), false);
  assert.equal(familyCards.includes("Wrong 296 TFT"), false);
  await waitFor(`document.querySelector(".template-preview img") || document.querySelector(".template-preview .template-screen")`);
  const previewState = await evaluate(`(() => {
    const image = document.querySelector(".template-preview img");
    const requested = image ? new URL(image.src).pathname : null;
    if (image) image.dispatchEvent(new Event("error"));
    return { requested, fallback: Boolean(document.querySelector(".template-preview .template-screen")), image: Boolean(document.querySelector(".template-preview img")) };
  })()`);
  assert.equal(previewState.requested === null || /^\/api\/vendor\/templates\/[0-9]+\/preview$/.test(previewState.requested), true);
  assert.equal(previewState.fallback, true);
  assert.equal(previewState.image, false);
  await installDelayedMutation();
  await pointerClick('document.querySelector("[data-clone-id]:not(:disabled)")');
  assert.equal(await evaluate(`document.activeElement === byId("clone-target-controller")`), true);
  await evaluate(`(() => {
    byId("clone-target-name").value = "Browser 401 clone";
    byId("clone-confirm").checked = true; updateCloneButton();
  })()`);
  await pointerClick('byId("clone-submit")', 2);
  await waitFor(`typeof window.__releaseMutation === "function"`);
  await assertBusyClosePaths("clone-modal");
  await releaseAndAssertAuthFocus("clone-submit");
  assert.equal(await evaluate(`window.__mutationCounts["POST /api/vendor/templates/clone"]`), 1);
  console.log("clone flow ok");
  await evaluate(`closeDialog(byId("clone-modal"))`);
  assert.equal(await evaluate(`document.activeElement === document.querySelector("[data-clone-id]:not(:disabled)")`), true);

  await installDelayedMutation("/api/session");
  await pointerClick('byId("auth-button")');
  assert.equal(await evaluate(`document.activeElement === byId("auth-token")`), true);
  assert.equal(await evaluate(`focusManager.openers.get(byId("auth-modal")) === byId("auth-button")`), true);
  await evaluate(`(() => {
    byId("auth-token").value = ${JSON.stringify("B".repeat(64))};
  })()`);
  await pointerClick('byId("auth-submit")', 2);
  await waitFor(`typeof window.__releaseMutation === "function"`);
  await assertBusyClosePaths("auth-modal");
  assert.equal(await evaluate(`window.__mutationCounts["POST /api/session"]`), 1);
  await evaluate(`window.__releaseMutation()`);
  await waitFor(`!byId("auth-submit").disabled && !byId("auth-form-error").hidden`);
  assert.equal(await evaluate(`byId("auth-modal").open`), true);
  await evaluate(`closeAuthModal()`);
  assert.equal(await evaluate(`document.activeElement === byId("auth-button")`), true);

  assert.equal(runtimeErrors.length, 0, JSON.stringify(runtimeErrors));
  console.log(JSON.stringify({ create401: "ok", detail401: "ok", clone401: "ok", authPending: "ok", closeRaces: "ok" }));
  clearTimeout(watchdog);
  ws.close();
})().catch((error) => { console.error(error); process.exit(1); });
