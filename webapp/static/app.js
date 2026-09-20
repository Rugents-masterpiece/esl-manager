"use strict";

const MODELS = TemplateFamilies.models;
const statusLabels = { ready: "Pripravená", updating: "Aktualizuje sa", success: "Úspešná", failed: "Chyba", online: "Online", offline: "Offline" };
const state = { controllers: [], tags: [], templates: [], routers: [], audit: [], activeView: "tags", inventoryLoaded: false };
const cloneGuard = new CloneSubmissionGuard();
const detailGuard = new DetailLoadGuard();
const focusManager = new DialogFocusManager();
const dialogOperationGuard = new DialogOperationGuard();
let cloneBusy = false;

function byId(id) { return document.getElementById(id); }
function element(tag, options = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(options).forEach(([key, value]) => {
    if (key === "className") node.className = value;
    else if (key === "text") node.textContent = value == null || value === "" ? "—" : String(value);
    else if (key === "attrs") Object.entries(value).forEach(([name, attr]) => node.setAttribute(name, String(attr)));
    else if (key === "dataset") Object.entries(value).forEach(([name, item]) => { node.dataset[name] = item; });
    else node[key] = value;
  });
  children.filter(Boolean).forEach((child) => node.append(child));
  return node;
}
function setMessage(id, message, isError = false) {
  const node = byId(id); node.textContent = message; node.classList.toggle("error", isError);
}
function empty(message) { return element("div", { className: "empty", text: message }); }
function safeDate(value) {
  if (!value) return "Neznámy";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("sk-SK", { dateStyle: "short", timeStyle: "short" }).format(date);
}
function statusNode(value, supported = true) {
  const key = supported ? String(value || "unknown") : "unsupported";
  return element("span", { className: `status status-${key.replace(/[^a-z-]/g, "")}`, text: supported ? (statusLabels[value] || value || "Neznámy") : "Nepodporovaná" });
}
function definitionList(items) {
  const list = element("dl");
  items.forEach(([term, value]) => list.append(element("dt", { text: term }), element("dd", { text: value })));
  return list;
}
async function api(path, options = {}) {
  const { authReturnTarget = null, ...requestOptions } = options;
  const config = { credentials: "same-origin", ...requestOptions, headers: { Accept: "application/json", ...(requestOptions.headers || {}) } };
  if (config.body !== undefined) config.headers["Content-Type"] = "application/json";
  const response = await fetch(path, config);
  const type = response.headers.get("content-type") || "";
  const payload = response.status === 204 ? null : (type.includes("application/json") ? await response.json() : await response.text());
  if (!response.ok) {
    const error = new Error(payload && payload.error ? payload.error.message : `Požiadavka zlyhala (${response.status})`);
    error.status = response.status;
    if (response.status === 401 && path !== "/api/session") openAuthModal(authReturnTarget);
    throw error;
  }
  return payload;
}
function notify(message, isError = false) {
  const toast = element("div", { className: `toast${isError ? " error" : ""}`, text: message });
  byId("toast-region").replaceChildren(toast);
  window.setTimeout(() => { if (toast.isConnected) toast.remove(); }, 5000);
}
function selectedController() { return byId("controller-select").value; }
function controllerName(id) { return state.controllers.find((item) => item.id === id)?.name || id || "Neznámy"; }
function scoped(items, controller = selectedController()) { return items.filter((item) => item.controller_id === controller); }

function rememberAndOpen(dialog, focusTarget, openerOverride = null) {
  if (!dialog.open) {
    const opener = openerOverride || (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    focusManager.remember(dialog, opener);
    dialog.showModal();
  }
  if (focusTarget) focusTarget.focus();
}
function closeDialog(dialog, reset = true) {
  if (!dialogOperationGuard.canClose(dialog)) return false;
  dialogOperationGuard.invalidate(dialog);
  if (dialog.id === "tag-drawer") detailGuard.invalidate();
  if (reset) dialog.querySelector("form")?.reset();
  if (dialog.open) dialog.close();
  focusManager.restore(dialog);
  return true;
}
function clearSessionToken() { byId("auth-token").value = ""; }
function openAuthModal(authReturnTarget = null) {
  const dialog = byId("auth-modal");
  if (dialogOperationGuard.isBusy(dialog)) return false;
  if (!dialog.open) dialogOperationGuard.open(dialog);
  clearSessionToken();
  byId("auth-form-error").hidden = true;
  rememberAndOpen(dialog, byId("auth-token"), authReturnTarget);
  return true;
}
function closeAuthModal() {
  if (!closeDialog(byId("auth-modal"))) return false;
  clearSessionToken();
  byId("auth-form-error").hidden = true;
  return true;
}
async function authenticate(event) {
  event.preventDefault();
  if (!event.currentTarget.reportValidity()) return;
  const dialog = byId("auth-modal");
  const operation = dialogOperationGuard.begin(dialog);
  if (!operation) return;
  const button = byId("auth-submit");
  button.disabled = true; button.textContent = "Prihlasujem…";
  try {
    await api("/api/session", { method: "POST", body: JSON.stringify({ token: byId("auth-token").value }) });
    if (!dialogOperationGuard.finish(operation)) return;
    button.disabled = false; button.textContent = "Prihlásiť";
    clearSessionToken();
    closeAuthModal();
    notify("Prihlásenie bolo úspešné. Zopakujte chránenú operáciu.");
  } catch (error) {
    if (!dialogOperationGuard.finish(operation)) return;
    button.disabled = false; button.textContent = "Prihlásiť";
    clearSessionToken();
    setMessage("auth-form-error", `Prihlásenie zlyhalo: ${error.message}`, true);
    byId("auth-form-error").hidden = false;
  }
}

function renderControllerSelect() {
  const select = byId("controller-select");
  const previous = select.value;
  select.replaceChildren(...state.controllers.map((controller) => element("option", {
    value: controller.id, text: `${controller.name}${controller.default ? " — predvolený" : ""}`,
  })));
  const preferred = state.controllers.find((item) => item.id === previous) || state.controllers.find((item) => item.default) || state.controllers[0];
  if (preferred) select.value = preferred.id;
}
function formControllerOptions(selectId, selected) {
  const select = byId(selectId);
  select.replaceChildren(...state.controllers.map((controller) => element("option", { value: controller.id, text: controller.name })));
  if (state.controllers.some((item) => item.id === selected)) select.value = selected;
}
function modelOptions(selectId, selected, allowUnsupported = false) {
  const select = byId(selectId);
  const options = Object.entries(MODELS).map(([id, model]) => element("option", { value: id, text: model.label }));
  if (allowUnsupported && selected && !MODELS[selected]) options.unshift(element("option", { value: "", text: "Nepodporovaný historický model" }));
  select.replaceChildren(...options);
  select.value = MODELS[selected] ? selected : (allowUnsupported ? "" : Object.keys(MODELS)[0]);
}
function dependentOptions(prefix, controllerId, modelId, selectedRouter = "", selectedTemplate = "") {
  const router = byId(`${prefix}-router`);
  const template = byId(`${prefix}-template`);
  const dimensions = MODELS[modelId];
  const routers = state.routers.filter((item) => item.controller_id === controllerId);
  const templates = state.templates.filter((item) => item.controller_id === controllerId && TemplateFamilies.matchesModel(item, dimensions));
  router.replaceChildren(element("option", { value: "", text: routers.length ? "Vyberte RF router" : "Žiadny RF router" }), ...routers.map((item) => element("option", { value: item.id, text: `${item.name} — ${item.address}` })));
  template.replaceChildren(element("option", { value: "", text: templates.length ? "Vyberte šablónu" : "Žiadna kompatibilná šablóna" }), ...templates.map((item) => element("option", { value: item.id, text: item.name })));
  router.value = routers.some((item) => item.id === selectedRouter) ? selectedRouter : "";
  template.value = templates.some((item) => item.id === selectedTemplate) ? selectedTemplate : "";
}

function renderTags() {
  const query = byId("tag-search").value.trim().toLowerCase();
  const wantedStatus = byId("tag-status").value;
  const items = scoped(state.tags).filter((tag) => {
    const matchesText = !query || [tag.mac, tag.label, tag.id].some((value) => String(value || "").toLowerCase().includes(query));
    return matchesText && (!wantedStatus || tag.status === wantedStatus);
  });
  if (!items.length) {
    byId("tags-list").replaceChildren(empty("Pre tento controller a filter nie sú dostupné žiadne cenovky."));
    setMessage("tags-state", "Prázdny výsledok je aktuálny stav inventára.");
    return;
  }
  const header = element("div", { className: "inventory-header", attrs: { "aria-hidden": "true" } }, ["Cenovka", "Model", "RF router", "Telemetria", "Zdroj", ""].map((text) => element("span", { text })));
  const rows = items.map((tag) => {
    const supported = Boolean(tag.management_supported);
    const model = supported && tag.device_model ? `${tag.device_model.width} × ${tag.device_model.height} ${tag.device_model.screen_type === 1 ? "TFT" : "EPD"}` : `${tag.width} × ${tag.height} — nepodporované`;
    const source = tag.staged ? "lokálny staging" : "vendor inventár";
    const support = supported ? "podporovaná správa" : "nepodporovaná historická cenovka";
    const accessibleName = `Otvoriť detail cenovky ${tag.label || tag.id}, MAC ${tag.mac}, model ${model}, ${support}, RF router ${tag.rf_router?.name || "Bez routera"}, batéria ${tag.battery} %, signál ${tag.rssi} dBm, zdroj ${source}`;
    return element("button", { type: "button", className: "tag-row", dataset: { tagId: tag.id }, attrs: { "aria-label": accessibleName } }, [
      element("span", { className: "tag-primary" }, [element("strong", { className: "mono", text: tag.mac }), element("span", { text: tag.label || tag.id })]),
      element("span", { className: "cell-label", text: model, attrs: { "data-label": "Model" } }),
      element("span", { className: "cell-label", text: tag.rf_router?.name || "Bez routera", attrs: { "data-label": "RF router" } }),
      element("span", { className: "cell-label", text: `${tag.battery} % · ${tag.rssi} dBm`, attrs: { "data-label": "Telemetria" } }),
      element("span", {}, [statusNode(supported ? tag.status : "unsupported", supported), element("span", { className: "cell-label", text: tag.staged ? " · lokálne pripravená" : " · vendor inventár" })]),
      element("span", { className: "tag-mobile-meta", text: `${model} · ${tag.rf_router?.name || "Bez routera"} · ${tag.battery} %` }),
      element("span", { className: "row-arrow", text: "›", attrs: { "aria-hidden": "true" } }),
    ]);
  });
  byId("tags-list").replaceChildren(header, ...rows);
  setMessage("tags-state", "");
}
async function openTagDetail(id) {
  dialogOperationGuard.open(byId("tag-drawer"));
  const request = detailGuard.begin(id);
  setMessage("tag-detail-state", ""); byId("tag-detail-state").hidden = true;
  byId("detail-id").value = "";
  [...byId("tag-detail-form").elements].forEach((control) => { if (!control.classList.contains("dialog-close")) control.disabled = true; });
  rememberAndOpen(byId("tag-drawer"), byId("tag-drawer-title"));
  try {
    const tag = await api(`/api/tags/${encodeURIComponent(id)}`, { signal: request.signal });
    if (!detailGuard.accept(request)) return;
    byId("tag-drawer-title").textContent = tag.label || tag.mac;
    byId("detail-id").value = tag.id;
    formControllerOptions("detail-controller", tag.controller_id);
    modelOptions("detail-model", tag.device_model_id, true);
    dependentOptions("detail", tag.controller_id, tag.device_model_id, tag.router_id, tag.template_id);
    byId("detail-mac").value = tag.mac || "";
    byId("detail-label").value = tag.label || "";
    byId("tag-test-data").value = JSON.stringify(tag.test_data || {}, null, 2);
    byId("tag-telemetry").replaceChildren(...definitionList([
      ["Controller", tag.controller?.name || controllerName(tag.controller_id)],
      ["RF router", tag.rf_router ? `${tag.rf_router.name} · ${tag.rf_router.address}` : "Nepriradený"],
      ["Model", tag.device_model ? MODELS[tag.device_model.id]?.label || tag.device_model.name : `${tag.width} × ${tag.height}`],
      ["Šablóna", tag.compatible_template?.name || (tag.template_id ? "Nekompatibilná" : "Nepriradená")],
      ["Zdroj inventára", tag.staged ? "Lokálny staging" : "Vendor read-only"],
      ["Zdroj konfigurácie", tag.configuration_source || "Neznámy"],
      ["Batéria", `${tag.battery} %`], ["Signál", `${tag.rssi} dBm`],
      ["Posledný kontakt", safeDate(tag.last_seen_at)], ["Stav", statusLabels[tag.status] || tag.status],
    ]).children);
    const supported = Boolean(tag.management_supported);
    byId("tag-support-state").textContent = supported ? "Úprava mení iba lokálnu konfiguráciu; fyzický dispatch sa nevykoná." : "Nepodporovaná historická cenovka. Záznam zostáva viditeľný, ale konfiguráciu nemožno upraviť.";
    [...byId("tag-detail-form").elements].forEach((control) => {
      if (["BUTTON", "INPUT", "SELECT", "TEXTAREA"].includes(control.tagName) && control.id !== "detail-controller") control.disabled = !supported;
    });
    document.querySelectorAll("#tag-detail-form .dialog-close").forEach((button) => { button.disabled = false; });
  } catch (error) {
    const currentFailure = detailGuard.current === request;
    detailGuard.fail(request);
    if (currentFailure && error.name !== "AbortError") {
      setMessage("tag-detail-state", `Detail sa nepodarilo načítať: ${error.message}`, true); byId("tag-detail-state").hidden = false;
    }
  }
}
function parseObject(id) {
  let value;
  try { value = JSON.parse(byId(id).value); } catch (_error) { throw new Error("Testovacie dáta musia byť platný JSON objekt."); }
  if (!value || Array.isArray(value) || typeof value !== "object") throw new Error("Testovacie dáta musia byť JSON objekt.");
  return value;
}
function tagPayload(prefix, testId) {
  const modelId = byId(`${prefix}-model`).value;
  const model = MODELS[modelId];
  if (!model) throw new Error("Vyberte jeden z troch podporovaných modelov.");
  return {
    controller_id: byId(`${prefix}-controller`).value,
    router_id: byId(`${prefix}-router`).value,
    device_model_id: modelId,
    width: model.width, height: model.height,
    template_id: byId(`${prefix}-template`).value,
    mac: byId(`${prefix}-mac`).value.trim(), label: byId(`${prefix}-label`).value.trim() || null,
    test_data: parseObject(testId),
  };
}
async function saveTagDetail(event) {
  event.preventDefault(); if (!event.currentTarget.reportValidity()) return;
  if (!detailGuard.activeId || detailGuard.activeId !== byId("detail-id").value) {
    setMessage("tag-detail-state", "Detail už nie je aktívny. Otvorte cenovku znova.", true); byId("tag-detail-state").hidden = false; return;
  }
  const dialog = byId("tag-drawer");
  const operation = dialogOperationGuard.begin(dialog);
  if (!operation) return;
  const button = byId("save-tag-detail"); button.disabled = true; button.textContent = "Ukladám…";
  try {
    const id = byId("detail-id").value;
    await api(`/api/tags/${encodeURIComponent(id)}/configuration`, { method: "PUT", body: JSON.stringify(tagPayload("detail", "tag-test-data")), authReturnTarget: button });
    if (!dialogOperationGuard.isCurrent(operation)) return;
    dialogOperationGuard.finish(operation);
    button.disabled = false; button.textContent = "Uložiť lokálnu konfiguráciu";
    closeDialog(dialog); notify("Lokálna konfigurácia cenovky bola uložená. Bez fyzického odoslania."); await loadInventory();
  } catch (error) {
    if (!dialogOperationGuard.isCurrent(operation)) return;
    dialogOperationGuard.finish(operation);
    button.disabled = false; button.textContent = "Uložiť lokálnu konfiguráciu";
    setMessage("tag-detail-state", `Konfiguráciu sa nepodarilo uložiť: ${error.message}`, true); byId("tag-detail-state").hidden = false;
  }
}
function openNewTag() {
  dialogOperationGuard.open(byId("tag-modal"));
  byId("tag-form").reset(); byId("new-test-data").value = "{}"; byId("tag-form-error").hidden = true;
  formControllerOptions("new-controller", selectedController()); modelOptions("new-model", "2.9EPD-BWR");
  dependentOptions("new", byId("new-controller").value, byId("new-model").value);
  rememberAndOpen(byId("tag-modal"), byId("new-controller"));
}
async function createTag(event) {
  event.preventDefault(); if (!event.currentTarget.reportValidity()) return;
  const dialog = byId("tag-modal");
  const operation = dialogOperationGuard.begin(dialog);
  if (!operation) return;
  const button = byId("save-new-tag"); button.disabled = true; button.textContent = "Pripravujem…";
  try {
    await api("/api/tags/staged", { method: "POST", body: JSON.stringify(tagPayload("new", "new-test-data")), authReturnTarget: button });
    if (!dialogOperationGuard.isCurrent(operation)) return;
    dialogOperationGuard.finish(operation);
    button.disabled = false; button.textContent = "Pripraviť lokálne";
    closeDialog(dialog); notify("Cenovka bola pripravená lokálne. Nebol vykonaný fyzický dispatch."); await loadInventory();
  } catch (error) {
    if (!dialogOperationGuard.isCurrent(operation)) return;
    dialogOperationGuard.finish(operation);
    button.disabled = false; button.textContent = "Pripraviť lokálne";
    setMessage("tag-form-error", `Cenovku sa nepodarilo pripraviť: ${error.message}`, true); byId("tag-form-error").hidden = false;
  }
}

function templateFamily(template) {
  return TemplateFamilies.label(template);
}
function renderTemplates() {
  const items = scoped(state.templates).filter(TemplateFamilies.supports);
  const cards = items.map((template) => {
    const preview = element("div", { className: "template-preview" });
    renderTemplatePreview(preview, template, templateFamily(template), element);
    const numericVendorId = Number(template.vendor_id);
    const clone = element("button", { type: "button", className: "button button-primary", text: "Klonovať šablónu", dataset: { cloneId: template.id }, disabled: !Number.isInteger(numericVendorId) || numericVendorId <= 0 });
    if (clone.disabled) clone.title = "Klonovanie vyžaduje synchronizované číselné serverové ID.";
    return element("article", { className: "card" }, [preview, element("p", { className: "eyebrow", text: controllerName(template.controller_id) }), element("h2", { text: template.name }), definitionList([["Rodina", templateFamily(template)], ["Rozmery", `${template.width} × ${template.height} px`], ["Server ID", template.vendor_id || template.id], ["Controller", controllerName(template.controller_id)]]), clone]);
  });
  byId("templates-grid").replaceChildren(...(cards.length ? cards : [empty("Pre vybraný controller nie sú dostupné šablóny v troch podporovaných rodinách.")]));
  setMessage("templates-state", cards.length ? "" : "Nepodporované rozmery sú zámerne skryté; inventár sa nemení.");
}
function populateCloneSources(controllerId, selectedId = "") {
  const options = state.templates.filter((item) => item.controller_id === controllerId && TemplateFamilies.supports(item) && Number.isInteger(Number(item.vendor_id)) && Number(item.vendor_id) > 0);
  byId("clone-source-template").replaceChildren(element("option", { value: "", text: options.length ? "Vyberte zdroj" : "Žiadna klonovateľná šablóna" }), ...options.map((item) => element("option", { value: String(item.vendor_id), text: `${item.name} · ${templateFamily(item)}` })));
  if (options.some((item) => item.id === selectedId)) byId("clone-source-template").value = String(options.find((item) => item.id === selectedId).vendor_id);
}
function openClone(template) {
  dialogOperationGuard.open(byId("clone-modal"));
  byId("clone-form").reset(); byId("clone-error").hidden = true; byId("clone-result").hidden = true; byId("clone-result").textContent = "";
  formControllerOptions("clone-source-controller", template.controller_id); formControllerOptions("clone-target-controller", selectedController());
  populateCloneSources(template.controller_id, template.id); updateCloneButton();
  rememberAndOpen(byId("clone-modal"), byId("clone-target-controller"));
}
function updateCloneButton() {
  byId("clone-submit").disabled = cloneBusy || !byId("clone-confirm").checked || !byId("clone-source-template").value || !byId("clone-target-name").value.trim();
}
async function cloneTemplate(event) {
  event.preventDefault(); if (!event.currentTarget.reportValidity() || !byId("clone-confirm").checked) return;
  if (cloneBusy) return;
  const dialog = byId("clone-modal");
  const operation = dialogOperationGuard.begin(dialog);
  if (!operation) return;
  const button = byId("clone-submit");
  const payload = {
    source_controller_id: byId("clone-source-controller").value,
    source_template_id: Number(byId("clone-source-template").value),
    target_controller_id: byId("clone-target-controller").value,
    target_name: byId("clone-target-name").value.trim(),
  };
  await cloneGuard.run(async () => {
    try {
      const result = await api("/api/vendor/templates/clone", { method: "POST", body: JSON.stringify(payload), authReturnTarget: button });
      if (!dialogOperationGuard.isCurrent(operation)) return;
      let readback = "Serverový read-back je overený hashmi odpovede.";
      try {
        const checked = await api(`/api/vendor/templates/${encodeURIComponent(result.id)}?controller_id=${encodeURIComponent(payload.target_controller_id)}`, { authReturnTarget: button });
        readback = `Read-back: ${checked.name || result.name} (${checked.width || "?"} × ${checked.height || "?"} px)`;
      } catch (_error) {
        readback = `Read-back API po úspechu nebolo dostupné; server v clone odpovedi overil layout ${result.layout_sha256 || "bez hashu"}.`;
      }
      byId("clone-result").textContent = `Server ID: ${result.id}\n${readback}`;
      byId("clone-result").hidden = false;
      byId("clone-confirm").checked = false;
      notify(`Šablóna bola vytvorená so server ID ${result.id}.`);
    } catch (error) {
      if (!dialogOperationGuard.isCurrent(operation)) return;
      setMessage("clone-error", `Klonovanie zlyhalo: ${error.message}`, true); byId("clone-error").hidden = false;
    }
  }, (busy) => {
    cloneBusy = busy;
    if (!busy) dialogOperationGuard.finish(operation);
    [...byId("clone-form").elements].forEach((control) => { control.disabled = cloneBusy; });
    byId("clone-submit").textContent = cloneBusy ? "Klonujem a overujem…" : "Klonovať a overiť";
    if (!cloneBusy) updateCloneButton();
  });
}

function renderControllers() {
  const cards = state.controllers.map((controller) => {
    const tags = state.tags.filter((item) => item.controller_id === controller.id);
    const supported = tags.filter((item) => item.management_supported).length;
    return element("article", { className: "card" }, [element("p", { className: "eyebrow", text: controller.default ? "PREDVOLENÝ CONTROLLER" : "CONTROLLER" }), element("h2", { text: controller.name }), definitionList([["ID", controller.id], ["Base URL", controller.base_url || "Lokálny / nezverejnený"], ["Cenovky", tags.length], ["Podporované", supported], ["Historické nepodporované", tags.length - supported], ["RF routery", state.routers.filter((item) => item.controller_id === controller.id).length], ["Podporované šablóny", state.templates.filter((item) => item.controller_id === controller.id && TemplateFamilies.supports(item)).length]])]);
  });
  byId("controllers-grid").replaceChildren(...(cards.length ? cards : [empty("Nie je nakonfigurovaný žiadny controller.")]));
  setMessage("controllers-state", cards.length ? "" : "Prázdny zoznam controllerov.");
}
async function loadAudit() {
  setMessage("audit-state", "Načítavam audit…");
  try {
    const result = await api("/api/audit?limit=100"); state.audit = result.items;
    const items = state.audit.map((item) => element("article", { className: "audit-item" }, [element("strong", { text: item.action }), element("p", { text: `${safeDate(item.created_at)} · ${item.entity_type} · ${item.entity_id}` }), element("p", { className: "mono", text: JSON.stringify(item.details) })]));
    byId("audit-list").replaceChildren(...(items.length ? items : [empty("Audit zatiaľ neobsahuje udalosti.")])); setMessage("audit-state", "");
  } catch (error) { setMessage("audit-state", `Audit sa nepodarilo načítať: ${error.message}`, true); }
}
function currentRenderer() {
  if (!state.inventoryLoaded) return;
  if (state.activeView === "tags") renderTags();
  if (state.activeView === "templates") renderTemplates();
  if (state.activeView === "controllers") renderControllers();
  if (state.activeView === "audit") loadAudit();
}
async function loadInventory() {
  try {
    const [controllers, tags, templates, routers, health] = await Promise.all([
      api("/api/controllers"), api("/api/tags?include_unsupported=true"), api("/api/templates"), api("/api/routers"), api("/api/health"),
    ]);
    state.controllers = controllers.items; state.tags = tags.items; state.templates = templates.items; state.routers = routers.items;
    state.inventoryLoaded = true;
    renderControllerSelect();
    const live = health.mode === "live";
    byId("mode-label").textContent = live ? "LIVE" : (health.mode === "read_only" ? "Read-only" : "Lokálny staging");
    byId("mode-title").textContent = live ? "LIVE režim" : "Bezpečná lokálna správa";
    byId("mode-description").textContent = live ? " Fyzické zápisy sú povolené na serveri, ale táto obrazovka konfigurácie ich neodosiela." : " Konfigurácie cenoviek sa ukladajú lokálne bez fyzického odoslania.";
    byId("safety-banner").classList.toggle("live", live);
    byId("app-status").textContent = "API pripojené"; document.querySelector(".status-dot").classList.remove("error");
    currentRenderer();
  } catch (error) {
    byId("app-status").textContent = "API nedostupné"; document.querySelector(".status-dot").classList.add("error");
    const message = `Inventár sa nepodarilo načítať: ${error.message}`;
    setMessage("tags-state", message, true);
    setMessage("templates-state", message, true);
    setMessage("controllers-state", message, true);
  }
}
function navigate() {
  const requested = location.hash.replace(/^#/, "") || "tags";
  const view = ["tags", "templates", "controllers", "audit"].includes(requested) ? requested : "tags";
  state.activeView = view;
  document.querySelectorAll("[data-view-panel]").forEach((panel) => { panel.hidden = panel.dataset.viewPanel !== view; });
  document.querySelectorAll("[data-view]").forEach((link) => { if (link.dataset.view === view) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current"); });
  byId("primary-nav").classList.remove("open"); byId("mobile-nav-toggle").setAttribute("aria-expanded", "false");
  currentRenderer(); window.scrollTo({ top: 0, behavior: "auto" });
}
function bindEvents() {
  window.addEventListener("hashchange", navigate);
  byId("mobile-nav-toggle").addEventListener("click", () => { const open = byId("primary-nav").classList.toggle("open"); byId("mobile-nav-toggle").setAttribute("aria-expanded", String(open)); });
  byId("controller-select").addEventListener("change", currentRenderer);
  byId("tag-filters").addEventListener("submit", (event) => { event.preventDefault(); renderTags(); });
  byId("tags-list").addEventListener("click", (event) => { const target = event.target.closest("[data-tag-id]"); if (target) openTagDetail(target.dataset.tagId); });
  byId("add-tag").addEventListener("click", openNewTag);
  byId("tag-form").addEventListener("submit", createTag); byId("tag-detail-form").addEventListener("submit", saveTagDetail);
  ["new", "detail"].forEach((prefix) => {
    byId(`${prefix}-controller`).addEventListener("change", () => dependentOptions(prefix, byId(`${prefix}-controller`).value, byId(`${prefix}-model`).value));
    byId(`${prefix}-model`).addEventListener("change", () => dependentOptions(prefix, byId(`${prefix}-controller`).value, byId(`${prefix}-model`).value));
  });
  byId("templates-grid").addEventListener("click", (event) => { const target = event.target.closest("[data-clone-id]"); const template = target && state.templates.find((item) => item.id === target.dataset.cloneId); if (template) openClone(template); });
  byId("clone-source-controller").addEventListener("change", () => { populateCloneSources(byId("clone-source-controller").value); updateCloneButton(); });
  ["clone-source-template", "clone-target-name", "clone-confirm"].forEach((id) => byId(id).addEventListener("input", updateCloneButton));
  byId("clone-form").addEventListener("submit", cloneTemplate);
  document.querySelectorAll(".dialog-close").forEach((button) => button.addEventListener("click", () => closeDialog(button.closest("dialog"))));
  [byId("tag-drawer"), byId("tag-modal"), byId("clone-modal")].forEach((dialog) => {
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); closeDialog(dialog); });
    dialog.addEventListener("click", (event) => { if (event.target === dialog) closeDialog(dialog); });
  });
  byId("auth-button").addEventListener("click", (event) => openAuthModal(event.currentTarget)); byId("auth-form").addEventListener("submit", authenticate);
  document.querySelectorAll(".auth-close").forEach((button) => button.addEventListener("click", closeAuthModal));
  byId("auth-modal").addEventListener("cancel", (event) => { event.preventDefault(); closeAuthModal(); });
  byId("auth-modal").addEventListener("click", (event) => { if (event.target === byId("auth-modal")) closeAuthModal(); });
}

bindEvents();
loadInventory();
navigate();
