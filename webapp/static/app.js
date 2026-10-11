"use strict";

const MODELS = TemplateFamilies.models;
const statusLabels = { ready: "Pripravená", updating: "Aktualizuje sa", success: "Úspešná", failed: "Chyba", online: "Online", offline: "Offline" };
const state = { controllers: [], tags: [], templates: [], routers: [], audit: [], activeView: "tags", inventoryLoaded: false };
const cloneGuard = new CloneSubmissionGuard();
const detailGuard = new DetailLoadGuard();
const focusManager = new DialogFocusManager();
const dialogOperationGuard = new DialogOperationGuard();
let cloneBusy = false;
const designer = window.EslDesigner.create({ api, notify });

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
  if (dialog.id === "tag-drawer" && byId("template-apply-modal")?.open && !closeTemplateApply()) return false;
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
function templateDisplayName(template) {
  return `${template.name} · ${template.width} × ${template.height} px`;
}
function fixedTagDisplay(tag) {
  const select = byId("detail-model");
  const model = MODELS[tag.device_model_id];
  select.replaceChildren(element("option", { value: model ? tag.device_model_id : "", text: `${tag.width} × ${tag.height} px · ${model ? tag.device_model_id : "Nepodporovaný historický model"}` }));
  select.value = model ? tag.device_model_id : "";
  select.disabled = true;
}
function dependentOptions(prefix, controllerId, modelId, selectedRouter = "", selectedTemplate = "") {
  const router = byId(`${prefix}-router`);
  const template = byId(`${prefix}-template`);
  const dimensions = MODELS[modelId];
  const routers = state.routers.filter((item) => item.controller_id === controllerId);
  const templates = state.templates.filter((item) => item.controller_id === controllerId && TemplateFamilies.matchesModel(item, dimensions));
  router.replaceChildren(element("option", { value: "", text: routers.length ? "Vyberte RF router" : "Žiadny RF router" }), ...routers.map((item) => element("option", { value: item.id, text: `${item.name} — ${item.address}` })));
  template.replaceChildren(element("option", { value: "", text: templates.length ? "Vyberte šablónu" : "Žiadna kompatibilná šablóna" }), ...templates.map((item) => element("option", { value: item.id, text: templateDisplayName(item) })));
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
  if (dialogOperationGuard.isBusy(byId("tag-drawer")) || (byId("template-apply-modal")?.open && !closeTemplateApply())) return;
  state.detailTag = null;
  tagDisplayGeneration += 1;
  byId("tag-display-summary")?.replaceChildren();
  byId("tag-display-preview")?.replaceChildren();
  if (byId("tag-display-state")) setMessage("tag-display-state", "Stav z controllera ešte nebol načítaný.");
  updateTemplateApplyButton();
  dialogOperationGuard.open(byId("tag-drawer"));
  const request = detailGuard.begin(id);
  setMessage("tag-detail-state", ""); byId("tag-detail-state").hidden = true;
  byId("detail-id").value = "";
  [...byId("tag-detail-form").elements].forEach((control) => { if (!control.classList.contains("dialog-close")) control.disabled = true; });
  rememberAndOpen(byId("tag-drawer"), byId("tag-drawer-title"));
  try {
    const [tag] = await Promise.all([api(`/api/tags/${encodeURIComponent(id)}`, { signal: request.signal }), loadInventory({ renderView: false })]);
    if (!detailGuard.accept(request)) return;
    state.detailTag = tag;
    byId("tag-drawer-title").textContent = tag.label || tag.mac;
    byId("detail-id").value = tag.id;
    formControllerOptions("detail-controller", tag.controller_id);
    fixedTagDisplay(tag);
    dependentOptions("detail", tag.controller_id, tag.device_model_id, tag.router_id, tag.template_id);
    byId("detail-mac").value = tag.mac || "";
    byId("detail-label").value = tag.label || "";
    byId("tag-test-data").value = JSON.stringify(tag.test_data || {}, null, 2);
    byId("tag-telemetry").replaceChildren(...definitionList([
      ["Controller", tag.controller?.name || controllerName(tag.controller_id)],
      ["RF router", tag.rf_router ? `${tag.rf_router.name} · ${tag.rf_router.address}` : "Nepriradený"],
      ["Displej (nemenný)", `${tag.width} × ${tag.height} px · ${tag.device_model_id || "Historický model"}`],
      ["Šablóna", tag.compatible_template?.name || (tag.template_id ? "Nekompatibilná" : "Nepriradená")],
      ["Zdroj inventára", tag.staged ? "Lokálny staging" : "Vendor read-only"],
      ["Zdroj konfigurácie", tag.configuration_source || "Neznámy"],
      ["Batéria", `${tag.battery} %`], ["Signál", `${tag.rssi} dBm`],
      ["Posledný kontakt", safeDate(tag.last_seen_at)], ["Stav", statusLabels[tag.status] || tag.status],
    ]).children);
    const supported = Boolean(tag.management_supported);
    byId("tag-support-state").textContent = supported ? "Upravte šablónu a obsah. Uložiť ponechá zmeny v aplikácii; Aktualizovať displej otvorí potvrdenie odoslania tejto cenovke." : "Nepodporovaná historická cenovka. Záznam zostáva viditeľný, ale konfiguráciu nemožno upraviť.";
    renderTagContentFields();
    [...byId("tag-detail-form").elements].forEach((control) => {
      if (["BUTTON", "INPUT", "SELECT", "TEXTAREA"].includes(control.tagName) && !["detail-controller", "detail-model"].includes(control.id)) control.disabled = !supported;
    });
    document.querySelectorAll("#tag-detail-form .dialog-close").forEach((button) => { button.disabled = false; });
    updateTemplateApplyButton();
  } catch (error) {
    const currentFailure = detailGuard.current === request;
    detailGuard.fail(request);
    if (currentFailure && error.name !== "AbortError") {
      setMessage("tag-detail-state", `Detail sa nepodarilo načítať: ${error.message}`, true); byId("tag-detail-state").hidden = false;
    }
  }
}
function templateApplyEligibility(tag, template) {
  if (!tag || !template || !Number.isInteger(Number(template.vendor_id)) || Number(template.vendor_id) <= 0) return { allowed: false, publication: null };
  const publication = (state.publications || []).find((item) => template && item.controller_id === tag?.controller_id && template.controller_id === tag.controller_id && String(item.vendor_id) === String(template.vendor_id) && item.model_id === tag.device_model_id);
  const allowed = state.mode === "live_enabled" && Boolean(tag?.management_supported && !tag.staged && tag.id && tag.mac && template?.id && publication);
  return { allowed, publication };
}
let tagDisplayGeneration = 0;
async function loadTagDisplay() {
  const tag = state.detailTag;
  if (!tag || tag.staged || detailGuard.activeId !== tag.id || dialogOperationGuard.isBusy(byId("tag-drawer"))) return;
  const button = byId("tag-display-load");
  if (button.disabled) return;
  const generation = ++tagDisplayGeneration;
  const current = () => generation === tagDisplayGeneration && detailGuard.activeId === tag.id && byId("detail-id").value === tag.id;
  button.disabled = true;
  setMessage("tag-display-state", "Načítavam iba stav a priradenú šablónu z controllera. Nič neodosielam na cenovku…");
  try {
    const display = await api(`/api/tags/${encodeURIComponent(tag.id)}/display`);
    if (!current()) return;
    const labels = { 0: "Neaktualizovaná", 1: "Čaká na aktualizáciu", 2: "Aktualizuje sa", 3: "Aktualizácia zlyhala", 4: "Aktualizácia dokončená", 5: "Neaktualizovaná" };
    const nativeLabels = { 1: "Pripravená", 2: "Prenos prebieha", 3: "Prenos zlyhal", 4: "Prenos dokončený" };
    byId("tag-display-summary").replaceChildren(definitionList([
      ["MAC z controllera", display.mac],
      ["Natívny prenos", `${nativeLabels[display.native_update_progress] || "Neznámy"} (kód ${display.native_update_progress ?? "?"})`],
      ["Čas natívneho prenosu na controlleri", display.native_updated_at_ms ? safeDate(display.native_updated_at_ms) : "Neznámy"],
      ["Uložený stav (MMS)", `${labels[display.update_progress] || "Neznámy"} (kód ${display.update_progress ?? "?"})`],
      ["Uložené priradenie šablóny (MMS)", display.style_id ?? "Nepriradená"],
      ["Čas aktualizácie evidovaný controllerom", display.updated_at_ms ? safeDate(display.updated_at_ms) : "Neznámy"],
      ["Stav načítaný", safeDate(display.read_at)],
    ]));
    byId("tag-display-preview").replaceChildren();
    setMessage("tag-display-state", "Náhľad uloženého priradenia MMS nie je čítanie fyzického displeja. Priradenie MMS sa pri natívnom prenose nemusí zmeniť. Obrázok preto nemusí zobrazovať posledný natívny obsah ani dokazovať úspech odoslania.");
    if (typeof display.preview_url === "string" && display.preview_url.startsWith("/api/vendor/templates/")) {
      const image = element("img", { src: display.preview_url, alt: "Controllerový náhľad uloženého priradenia MMS — nie aktuálny obraz displeja", attrs: { style: "max-width:100%;height:auto;image-rendering:pixelated" } });
      image.addEventListener("error", () => { if (current()) { byId("tag-display-preview").replaceChildren(); setMessage("tag-display-state", "Stav bol načítaný, ale obrázok priradenej šablóny nie je dostupný. Fyzický displej nie je overený.", true); } });
      byId("tag-display-preview").append(image);
    }
  } catch (error) {
    if (current()) { byId("tag-display-summary").replaceChildren(); byId("tag-display-preview").replaceChildren(); setMessage("tag-display-state", `Stav sa nepodarilo načítať: ${error.message}. Odoslanie nebolo opakované.`, true); }
  } finally { if (current()) button.disabled = false; }
}
const TEMPLATE_APPLY_CONFIRMATION = "I CONFIRM LIVE ESL UPDATE";
function templateApplyValidation(json, phrase, publication) {
  try {
    const data = JSON.parse(json);
    if (!data || Array.isArray(data) || typeof data !== "object") throw new Error("Dáta musia byť JSON objekt.");
    const fields = [...new Set(Object.values(publication?.bindings || {}).map((binding) => binding.field).filter(Boolean))];
    const missing = fields.filter((field) => !Object.hasOwn(data, field) || data[field] == null || (typeof data[field] === "string" && !data[field].trim()));
    if (missing.length) throw new Error(`Chýbajú povinné polia: ${missing.join(", ")}`);
    return { valid: phrase === TEMPLATE_APPLY_CONFIRMATION, data, message: phrase === TEMPLATE_APPLY_CONFIRMATION ? "" : "Zadajte presnú potvrdzovaciu frázu." };
  } catch (error) { return { valid: false, message: error.message }; }
}
function templateApplyOutcome(result) {
  const verified = result?.verified === true && ["success", "updating"].includes(result.status);
  return { verified, message: verified ? (result.status === "success" ? "Overené: cenovka bola úspešne aktualizovaná." : "Overené: cenovka sa aktualizuje; dokončenie ešte nie je potvrdené.") : "Výsledok fyzického odoslania nie je overený. Neopakujte odoslanie; skontrolujte cenovku a audit." };
}
let applyContext = null;
function selectedApplyTemplate() {
  return state.templates.find((item) => String(item.id) === byId("detail-template").value);
}
function renderTagContentFields() {
  const container = byId("tag-content-fields");
  if (!container) return;
  const publication = templateApplyEligibility(state.detailTag, selectedApplyTemplate()).publication;
  const fields = [...new Set(Object.values(publication?.bindings || {}).map((binding) => binding.field).filter(Boolean))];
  let data;
  try { data = parseObject("tag-test-data"); }
  catch (_error) { container.replaceChildren(empty("Opravte JSON v rozšírených nastaveniach, aby bolo možné upraviť obsah.")); return; }
  if (!fields.length) {
    container.replaceChildren(empty("Táto šablóna nemá dostupný formulár obsahu. Dáta môžete upraviť v rozšírených nastaveniach JSON; odoslanie vyžaduje publikovanú kompatibilnú šablónu."));
    return;
  }
  container.replaceChildren(...fields.map((field, index) => {
    const value = data[field];
    const input = element("input", { id: `tag-content-${index}`, type: "text", value: value == null ? "" : String(value), required: true, disabled: !state.detailTag?.management_supported });
    input.addEventListener("input", () => {
      try {
        const current = parseObject("tag-test-data");
        let next = input.value;
        if (typeof value === "number" || typeof value === "boolean") {
          next = JSON.parse(input.value);
          if (typeof next !== typeof value || (typeof next === "number" && (!Number.isFinite(next) || Math.abs(next) > Number.MAX_SAFE_INTEGER))) throw new Error("Zachovajte typ pôvodnej hodnoty.");
        } else if (value != null && typeof value !== "string") throw new Error("Zložené hodnoty upravte v JSON.");
        Object.defineProperty(current, field, { value: next, enumerable: true, configurable: true, writable: true });
        byId("tag-test-data").value = JSON.stringify(current, null, 2);
        input.setCustomValidity?.("");
      } catch (_error) { input.setCustomValidity?.("Neplatná hodnota. Čísla zadávajte s bodkou, logické hodnoty ako true alebo false; prípadne opravte JSON."); }
    });
    return element("div", { className: "field" }, [element("label", { text: field, attrs: { for: input.id } }), input]);
  }));
}
function applySelectionCurrent(context) {
  return context && detailGuard.activeId === context.tag.id && byId("detail-id").value === context.tag.id && byId("detail-template").value === String(context.template.id) && byId("detail-model").value === context.tag.device_model_id;
}
function updateTemplateApplyButton() {
  const button = byId("apply-tag-template");
  if (!button) return;
  const eligible = templateApplyEligibility(state.detailTag, selectedApplyTemplate());
  button.disabled = !eligible.allowed || !detailGuard.activeId || byId("detail-model").value !== state.detailTag?.device_model_id || dialogOperationGuard.isBusy(byId("tag-drawer"));
  button.title = eligible.allowed ? "Samostatné potvrdené fyzické odoslanie jednej cenovke" : "Vyžaduje LIVE povolenie, fyzickú podporovanú cenovku a publikovanú šablónu pre rovnaký model/controller.";
}
function updateTemplateApplySubmit() {
  if (!applyContext) return;
  const validation = templateApplyValidation(byId("template-apply-data").value, byId("template-apply-confirm").value, applyContext.publication);
  byId("template-apply-submit").disabled = applyContext.attempted || dialogOperationGuard.isBusy(byId("template-apply-modal")) || !applySelectionCurrent(applyContext) || !templateApplyEligibility(applyContext.tag, applyContext.template).allowed || !validation.valid;
  if (!applyContext.attempted) setMessage("template-apply-state", validation.message, !validation.valid);
}
function closeTemplateApply() {
  const dialog = byId("template-apply-modal");
  if (!dialogOperationGuard.canClose(dialog)) return false;
  byId("template-apply-confirm").value = "";
  applyContext = null;
  return closeDialog(dialog);
}
function openTemplateApply() {
  if (dialogOperationGuard.isBusy(byId("tag-drawer"))) return;
  const tag = state.detailTag;
  const template = selectedApplyTemplate();
  const eligibility = templateApplyEligibility(tag, template);
  if (!eligibility.allowed || byId("detail-model").value !== tag.device_model_id || detailGuard.activeId !== tag.id) return;
  let content;
  try { content = parseObject("tag-test-data"); }
  catch (error) { setMessage("tag-detail-state", error.message, true); byId("tag-detail-state").hidden = false; return; }
  if (!byId("tag-detail-form").reportValidity()) return;
  const dialog = byId("template-apply-modal");
  if (dialog.open) return;
  applyContext = { tag: {...tag}, template: {...template}, publication: eligibility.publication, attempted: false };
  dialogOperationGuard.open(dialog);
  byId("template-apply-confirm").value = "";
  byId("template-apply-data").value = JSON.stringify(content, null, 2);
  byId("template-apply-summary").replaceChildren(definitionList([
    ["MAC cenovky", tag.mac], ["Lokálne ID cenovky", tag.id], ["Model", MODELS[tag.device_model_id]?.label || tag.device_model_id],
    ["Šablóna", templateDisplayName(template)], ["Lokálne ID šablóny", template.id], ["Native / vendor ID", template.vendor_id],
    ["Controller", `${controllerName(tag.controller_id)} (${tag.controller_id})`],
    ["Povinné polia JSON", [...new Set(Object.values(eligibility.publication.bindings || {}).map((binding) => binding.field).filter(Boolean))].join(", ") || "Žiadne dynamické polia"],
  ]));
  dialog.querySelectorAll("input, textarea, button").forEach((control) => { control.disabled = false; });
  updateTemplateApplySubmit();
  rememberAndOpen(dialog, byId("template-apply-data"), byId("apply-tag-template"));
}
async function submitTemplateApply(event) {
  event.preventDefault();
  const context = applyContext;
  if (!context || context.attempted || !applySelectionCurrent(context) || !templateApplyEligibility(context.tag, context.template).allowed) return;
  const validation = templateApplyValidation(byId("template-apply-data").value, byId("template-apply-confirm").value, context.publication);
  if (!validation.valid) { updateTemplateApplySubmit(); return; }
  const dialog = byId("template-apply-modal");
  const drawer = byId("tag-drawer");
  if (dialogOperationGuard.isBusy(dialog) || dialogOperationGuard.isBusy(drawer)) return;
  const operation = dialogOperationGuard.begin(dialog);
  const drawerOperation = dialogOperationGuard.begin(drawer);
  context.attempted = true;
  const controllerSelect = byId("controller-select");
  const controllerDisabled = controllerSelect.disabled;
  controllerSelect.disabled = true;
  dialog.querySelectorAll("input, textarea, button").forEach((control) => { control.disabled = true; });
  setMessage("template-apply-state", "Odosielam iba tejto cenovke a čakám na overenie. Nezatvárajte okno.");
  try {
    const result = await api(`/api/tags/${encodeURIComponent(context.tag.id)}/apply-template`, {
      method: "POST", body: JSON.stringify({ template_id: context.template.id, data: validation.data, confirmation: TEMPLATE_APPLY_CONFIRMATION }), authReturnTarget: byId("template-apply-submit"),
    });
    if (!dialogOperationGuard.isCurrent(operation)) return;
    const outcome = templateApplyOutcome(result);
    setMessage("template-apply-state", outcome.message, !outcome.verified);
  } catch (error) {
    if (dialogOperationGuard.isCurrent(operation)) setMessage("template-apply-state", `Výsledok fyzického odoslania nie je overený: ${error.message}. Bez automatického opakovania; skontrolujte cenovku a audit.`, true);
  } finally {
    byId("template-apply-confirm").value = "";
    // Keep the pending locks through the local GET refresh. No vendor sync or retry.
    await loadInventory({ renderView: false });
    dialogOperationGuard.finish(operation);
    dialogOperationGuard.finish(drawerOperation);
    controllerSelect.disabled = controllerDisabled;
    dialog.querySelectorAll(".template-apply-close").forEach((control) => { control.disabled = false; });
    byId("template-apply-submit").disabled = true;
    updateTemplateApplyButton();
  }
}
function installTemplateApplyUI() {
  const displayButton = element("button", { id: "tag-display-load", type: "button", className: "button button-secondary", text: "Načítať stav a náhľad z controllera" });
  displayButton.addEventListener("click", loadTagDisplay);
  byId("tag-detail-form").append(element("details", { className: "notice" }, [
    element("summary", { text: "Stav displeja na controlleri" }), displayButton,
    element("p", { id: "tag-display-state", text: "Stav z controllera ešte nebol načítaný.", attrs: { role: "status", "aria-live": "polite" } }),
    element("div", { id: "tag-display-summary", className: "telemetry" }), element("div", { id: "tag-display-preview" }),
  ]));
  const openButton = element("button", { id: "apply-tag-template", type: "button", className: "button button-primary", text: "Aktualizovať displej…", disabled: true });
  openButton.addEventListener("click", openTemplateApply);
  byId("tag-detail-form").append(element("p", { className: "notice", text: "Aktualizovať displej použije práve upravený obsah a vybranú šablónu. Pred odoslaním skontrolujete MAC, model a dáta a potvrdíte operáciu. Samotné uloženie displej nemení." }), element("div", { className: "modal-actions" }, [openButton]));
  const data = element("textarea", { id: "template-apply-data", rows: 8, spellcheck: false });
  const confirm = element("input", { id: "template-apply-confirm", type: "text", autocomplete: "off", spellcheck: false });
  const cancel = element("button", { type: "button", className: "button template-apply-close", text: "Zrušiť / Zavrieť" });
  cancel.addEventListener("click", closeTemplateApply);
  const form = element("form", { id: "template-apply-form" }, [
    element("div", { className: "modal-heading" }, [element("h2", { id: "template-apply-title", text: "Aktualizovať displej cenovky" })]),
    element("p", { className: "notice", text: "Toto fyzicky mení iba uvedenú cenovku. Lokálne uloženie konfigurácie fyzický obsah nemení. Pri neznámom výsledku odoslanie neopakujte." }),
    element("div", { id: "template-apply-summary", className: "telemetry" }),
    element("div", { className: "form-grid" }, [
      element("div", { className: "field field-full" }, [element("label", { text: "Dáta pre fyzické odoslanie (JSON)", attrs: { for: data.id } }), data]),
      element("div", { className: "field field-full" }, [element("label", { text: `Napíšte presne: ${TEMPLATE_APPLY_CONFIRMATION}`, attrs: { for: confirm.id } }), confirm]),
    ]),
    element("p", { id: "template-apply-state", className: "notice", attrs: { role: "status", "aria-live": "polite" } }),
    element("div", { className: "modal-actions" }, [cancel, element("button", { id: "template-apply-submit", type: "submit", className: "button button-primary", text: "Potvrdiť fyzické odoslanie", disabled: true })]),
  ]);
  form.addEventListener("submit", submitTemplateApply);
  [data, confirm].forEach((control) => control.addEventListener("input", updateTemplateApplySubmit));
  const dialog = element("dialog", { id: "template-apply-modal", className: "modal", attrs: { "aria-labelledby": "template-apply-title" } }, [form]);
  dialog.addEventListener("cancel", (event) => { event.preventDefault(); closeTemplateApply(); });
  dialog.addEventListener("click", (event) => { if (event.target === dialog) closeTemplateApply(); });
  dialog.addEventListener("close", () => { byId("template-apply-confirm").value = ""; applyContext = null; });
  document.body.append(dialog);
  ["detail-template", "detail-model"].forEach((id) => byId(id).addEventListener("change", () => { updateTemplateApplyButton(); renderTagContentFields(); }));
  byId("tag-test-data").addEventListener("change", renderTagContentFields);
}
function parseObject(id) {
  let value;
  try { value = JSON.parse(byId(id).value); } catch (_error) { throw new Error("Testovacie dáta musia byť platný JSON objekt."); }
  if (!value || Array.isArray(value) || typeof value !== "object") throw new Error("Testovacie dáta musia byť JSON objekt.");
  return value;
}
function tagPayload(prefix, testId) {
  const modelId = prefix === "detail" ? state.detailTag?.device_model_id : byId(`${prefix}-model`).value;
  const model = MODELS[modelId];
  if (!model) throw new Error("Vyberte jeden z troch podporovaných modelov.");
  return {
    controller_id: byId(`${prefix}-controller`).value,
    router_id: byId(`${prefix}-router`).value,
    device_model_id: modelId,
    width: prefix === "detail" ? state.detailTag.width : model.width,
    height: prefix === "detail" ? state.detailTag.height : model.height,
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
    return element("article", { className: "card" }, [preview, element("p", { className: "eyebrow", text: controllerName(template.controller_id) }), element("h2", { text: templateDisplayName(template) }), definitionList([["Rodina", templateFamily(template)], ["Rozmery", `${template.width} × ${template.height} px`], ["Server ID", template.vendor_id || template.id], ["Controller", controllerName(template.controller_id)]]), clone]);
  });
  byId("templates-grid").replaceChildren(...(cards.length ? cards : [empty("Pre vybraný controller nie sú dostupné šablóny v troch podporovaných rodinách.")]));
  setMessage("templates-state", cards.length ? "" : "Nepodporované rozmery sú zámerne skryté; inventár sa nemení.");
}
function populateCloneSources(controllerId, selectedId = "") {
  const options = state.templates.filter((item) => item.controller_id === controllerId && TemplateFamilies.supports(item) && Number.isInteger(Number(item.vendor_id)) && Number(item.vendor_id) > 0);
  byId("clone-source-template").replaceChildren(element("option", { value: "", text: options.length ? "Vyberte zdroj" : "Žiadna klonovateľná šablóna" }), ...options.map((item) => element("option", { value: String(item.vendor_id), text: `${templateDisplayName(item)} · ${templateFamily(item)}` })));
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
      await loadInventory();
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
  if (state.activeView === "designer") { designer.show(); return; }
  if (!state.inventoryLoaded) return;
  if (state.activeView === "tags") renderTags();
  if (state.activeView === "templates") renderTemplates();
  if (state.activeView === "controllers") renderControllers();
  if (state.activeView === "audit") loadAudit();
}
async function loadInventory({ renderView = true } = {}) {
  state.mode = null;
  state.publications = [];
  updateTemplateApplyButton();
  try {
    const [controllers, tags, templates, routers, health] = await Promise.all([
      api("/api/controllers"), api("/api/tags?include_unsupported=true"), api("/api/templates"), api("/api/routers"), api("/api/health"),
    ]);
    state.controllers = controllers.items; state.tags = tags.items; state.templates = templates.items; state.routers = routers.items;
    try {
      const publications = await Promise.all(state.controllers.map((controller) => api(`/api/template-publications?controller_id=${encodeURIComponent(controller.id)}`)));
      state.publications = publications.flatMap((result) => result.items);
      state.mode = health.mode;
    } catch (_error) { state.publications = []; }
    updateTemplateApplyButton();
    state.inventoryLoaded = true;
    renderControllerSelect();
    const live = health.mode === "live" || health.mode === "live_enabled";
    byId("mode-label").textContent = live ? "LIVE" : (health.mode === "read_only" ? "Read-only" : "Lokálny staging");
    byId("mode-title").textContent = live ? "LIVE režim" : "Bezpečná lokálna správa";
    byId("mode-description").textContent = live ? " Lokálne uloženie konfigurácie nič fyzicky neodosiela. Fyzické odoslanie vyžaduje samostatnú akciu a presné potvrdenie." : " Konfigurácie cenoviek sa ukladajú lokálne bez fyzického odoslania.";
    byId("safety-banner").classList.toggle("live", live);
    byId("app-status").textContent = "API pripojené"; document.querySelector(".status-dot").classList.remove("error");
    // Modal refreshes need current publications without replacing their opener rows.
    if (renderView) currentRenderer();
  } catch (error) {
    byId("app-status").textContent = "API nedostupné"; document.querySelector(".status-dot").classList.add("error");
    const message = `Inventár sa nepodarilo načítať: ${error.message}`;
    setMessage("tags-state", message, true);
    setMessage("templates-state", message, true);
    setMessage("controllers-state", message, true);
  }
}
function navigate() {
  if (byId("template-apply-modal")?.open) {
    if (dialogOperationGuard.isBusy(byId("template-apply-modal"))) {
      history.replaceState(null, "", `#${state.activeView}`);
      return;
    }
    closeTemplateApply();
  }
  const requested = location.hash.replace(/^#/, "") || "tags";
  const view = ["tags", "templates", "designer", "controllers", "audit"].includes(requested) ? requested : "tags";
  if (state.activeView === "designer" && view !== "designer" && !designer.canLeave()) {
    history.replaceState(null, "", "#designer");
    return;
  }
  const leavingDesigner = state.activeView === "designer" && view !== "designer";
  state.activeView = view;
  if (leavingDesigner) loadInventory();
  document.querySelectorAll("[data-view-panel]").forEach((panel) => { panel.hidden = panel.dataset.viewPanel !== view; });
  document.querySelectorAll("[data-view]").forEach((link) => { if (link.dataset.view === view) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current"); });
  byId("primary-nav").classList.remove("open"); byId("mobile-nav-toggle").setAttribute("aria-expanded", "false");
  currentRenderer(); window.scrollTo({ top: 0, behavior: "auto" });
}
function bindEvents() {
  installTemplateApplyUI();
  window.addEventListener("beforeunload", (event) => {
    if (dialogOperationGuard.isBusy(byId("template-apply-modal"))) { event.preventDefault(); event.returnValue = ""; }
  });
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
