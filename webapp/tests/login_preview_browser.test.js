"use strict";
// Real CDP browser traffic, no fetch stubs, injected cookies, or vendor hardware.
const assert = require("node:assert/strict");
const base = process.env.ESL_BROWSER_BASE;
const cdp = process.env.ESL_BROWSER_CDP;
const control = process.env.ESL_PREVIEW_CONTROL;
const view = process.env.ESL_LOGIN_VIEW;
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const fixtureState = async () => (await fetch(control + "/state", {signal: AbortSignal.timeout(2000)})).json();

(async () => {
  const watchdog = setTimeout(() => { console.error("login preview browser watchdog"); process.exit(2); }, 28000);
  let ws;
  try {
    const target = await (await fetch(cdp + "/json/new?about:blank", { method: "PUT" })).json();
    ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    let sequence = 0;
    const pending = new Map();
    const requests = new Map();
    const runtimeErrors = [];
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.id && pending.has(message.id)) {
        const callback = pending.get(message.id); pending.delete(message.id);
        message.error ? callback.reject(new Error(message.error.message)) : callback.resolve(message.result);
      } else if (message.method === "Network.requestWillBeSent") {
        const { requestId, request } = message.params;
        const url = new URL(request.url);
        if (url.origin === base) requests.set(requestId, { path: url.pathname, method: request.method, status: null, failed: null });
      } else if (message.method === "Network.responseReceived") {
        const entry = requests.get(message.params.requestId);
        if (entry) { entry.status = message.params.response.status; entry.protocol = message.params.response.protocol; }
      } else if (message.method === "Network.loadingFailed") {
        const entry = requests.get(message.params.requestId);
        if (entry) entry.failed = message.params.errorText;
      } else if (message.method === "Runtime.exceptionThrown") {
        runtimeErrors.push(message.params.exceptionDetails.text);
      }
    };
    const call = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++sequence; pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async (expression) => {
      const result = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    const waitFor = async (check, label, timeout = 5000) => {
      const end = Date.now() + timeout;
      while (Date.now() < end) {
        if (await check()) return;
        await delay(25);
      }
      throw new Error("Timed out waiting for " + label);
    };
    const click = async (selector) => {
      const result = await call("Runtime.evaluate", {
        expression: `(() => { const node = document.querySelector(${JSON.stringify(selector)}); node.scrollIntoView({block:'center'}); return node; })()`,
      });
      const objectId = result.result.objectId;
      const box = await call("DOM.getBoxModel", { objectId });
      await call("Runtime.releaseObject", { objectId });
      const quad = box.model.content;
      const x = (quad[0] + quad[2] + quad[4] + quad[6]) / 4;
      const y = (quad[1] + quad[3] + quad[5] + quad[7]) / 4;
      await call("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await call("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };
    const rejectedMutation = () => evaluate(`fetch('/api/tags/staged', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:'{}'}).then(async r => { const p = await r.json(); return {status:r.status,code:p.error?.code}; })`);
    await call("Page.enable"); await call("Runtime.enable"); await call("Network.enable");
    await call("Network.setCacheDisabled", { cacheDisabled: true });
    await call("Page.navigate", { url: base + "/#tags" });
    await waitFor(() => evaluate(`document.querySelector('#app-status')?.textContent === 'API pripojené' && typeof byId === 'function'`), "local inventory ready");
    assert.equal((await rejectedMutation()).status, 401, "fresh context must not have an authenticated session");
    // The safe direct probe does not invoke the application's auth helper.
    // Initiate authentication only through the ordinary login button below.
    if (view === "templates") {
      console.log('phase: navigating templates');
      await evaluate("location.hash = '#templates'");
      console.log('phase: waiting blocked native preview');
      await waitFor(async () => (await fixtureState()).active >= 2, "two blocked native image handlers");
      // Old eager loading reaches six handlers here; the shared bounded
      // scheduler retains exactly two. Neither path releases fake previews.
      await delay(200);
      assert.equal(await evaluate("document.querySelectorAll('#templates-grid img').length"), 43,
        "fixture must exercise the eagerly rendered native preview grid");
    }
    console.log('phase: opening auth');
    await click("#auth-button");
    console.log('phase: auth clicked');
    await waitFor(() => evaluate("document.querySelector('#auth-modal').open"), "ordinary login dialog");
    await call("Input.insertText", { text: "A".repeat(64) });
    const started = Date.now();
    await click("#auth-submit");
    let prompt = false;
    const deadline = started + 1500;
    while (Date.now() < deadline) {
      if (await evaluate("!document.querySelector('#auth-modal').open && !document.querySelector('#auth-submit').disabled")) {
        prompt = true; break;
      }
      await delay(25);
    }
    const elapsedMs = Date.now() - started;
    const beforeRelease = await fixtureState();
    const login = [...requests.values()].filter(r => r.path === "/api/session");
    const previews = [...requests.values()].filter(r => /\/preview$/.test(r.path));
    const networkSnapshot = {
      session: login.map(r => ({ method: r.method, status: r.status, failed: r.failed })),
      previewsRequested: previews.length,
      previewsPending: previews.filter(r => r.status === null && !r.failed).length,
      previewsResponded: previews.filter(r => r.status !== null).length,
    };
    // Independent Node socket proves the threaded API is not held by vendor serialization.
    const independentHealth = (await fetch(base + "/api/health")).status;
    console.log(JSON.stringify({ phase: "before-preview-release", view, prompt, elapsedMs,
      authBusy: await evaluate("document.querySelector('#auth-submit').disabled"),
      fixture: beforeRelease, network: networkSnapshot, independentHealth }));
    assert.equal(beforeRelease.released, false, "login deadline must precede fixture release");
    if (view === "templates") assert.ok(beforeRelease.active >= 2, "two native previews must remain outstanding at the login deadline");
    if (prompt) {
      const beforeReleaseMutation = await rejectedMutation();
      assert.equal(beforeReleaseMutation.status, 400, "cookie must be reused while native previews remain blocked");
      assert.equal(beforeReleaseMutation.code, "validation_error");
      assert.equal((await fixtureState()).released, false);
    }
    await fetch(control + "/release", { method: "POST" });
    await waitFor(() => evaluate("!document.querySelector('#auth-modal').open && !document.querySelector('#auth-submit').disabled"), "valid login completion after diagnostic release", 8000);
    assert.equal(await evaluate("document.querySelector('#auth-token').value === ''"), true, "token must be cleared after login");
    const cookies = await call("Network.getCookies", { urls: [base] });
    assert.equal(cookies.cookies.some(c => c.name === "esl_session" && c.httpOnly), true,
      "ordinary form response must store an HttpOnly session cookie");
    const rejected = await rejectedMutation();
    assert.equal(rejected.status, 400, "cookie reuse must pass auth and reach safe empty-body validation");
    assert.equal(rejected.code, "validation_error");
    assert.equal((await fixtureState()).sessions, 1);
    assert.deepEqual(runtimeErrors, [], "no uncaught application exception");
    const sessionResponses = [...requests.values()].filter(r => r.path === "/api/session").map(r => r.status);
    console.log(JSON.stringify({ phase: "after-preview-release", sessionStatuses: sessionResponses,
      cookieStored: true, cookieReuseRejectedMutation: rejected.status, tokenCleared: true }));
    assert.ok(prompt,
      `login must finish within 1500ms BEFORE slow native previews are released; elapsed=${elapsedMs}ms; fixture=${JSON.stringify(beforeRelease)}; network=${JSON.stringify(networkSnapshot)}`);
    if (view === "templates") assert.ok(beforeRelease.peak <= 2, "shared preview scheduler must never occupy more than two connections before release");
  } finally {
    await fetch(control + "/release", { method: "POST" }).catch(() => {});
    if (ws) ws.close();
    clearTimeout(watchdog);
  }
})().then(() => process.exit(0), (error) => { console.error(error.message); process.exit(1); });
