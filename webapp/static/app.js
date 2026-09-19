"use strict";

const state = {
  products: [], tags: [], templates: [], routers: [], jobs: [], alerts: [], audit: [],
  selectedTags: new Set(), activeView: "overview",
};

const viewLoaders = {
  overview: loadOverview,
  tags: loadTags,
  products: loadProducts,
  templates: loadTemplates,
  routers: loadRouters,
  jobs: loadJobs,
  audit: loadAudit,
};

const statusLabels = {
  ready: "Pripravená", updating: "Aktualizuje sa", success: "Úspešná", failed: "Chyba",
  queued: "Čaká", processing: "Spracúva sa", completed: "Dokončená", partial: "Čiastočne úspešná",
  succeeded: "Úspešná", online: "Online", offline: "Offline", critical: "Kritický",
  warning: "Upozornenie", info: "Informácia",
};

function byId(id) { return document.getElementById(id); }

function element(tag, options = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(options).forEach(([key, value]) => {
    if (key === "className") node.className = value;
    else if (key === "text") node.textContent = value == null ? "—" : String(value);
    else if (key === "dataset") Object.entries(value).forEach(([name, data]) => { node.dataset[name] = data; });
    else if (key === "attrs") Object.entries(value).forEach(([name, attr]) => node.setAttribute(name, attr));
    else node[key] = value;
  });
  children.filter(Boolean).forEach((child) => node.append(child));
  return node;
}

function setState(id, message, isError = false) {
  const node = byId(id);
  node.textContent = message;
  node.classList.toggle("error", isError);
}

function emptyMessage(message) { return element("div", { className: "empty", text: message }); }

function status(value) {
  return element("span", {
    className: `status status-${String(value || "unknown").replace(/[^a-z-]/g, "")}`,
    text: statusLabels[value] || value || "Neznámy",
  });
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("sk-SK", { dateStyle: "short", timeStyle: "short" }).format(date);
}

function formatPrice(value, currency = "EUR") {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  try { return new Intl.NumberFormat("sk-SK", { style: "currency", currency: currency || "EUR" }).format(number); }
  catch (_error) { return `${number.toFixed(2)} ${currency || "EUR"}`; }
}

async function api(path, options = {}) {
  const config = { ...options, headers: { Accept: "application/json", ...(options.headers || {}) } };
  if (config.body !== undefined) config.headers["Content-Type"] = "application/json";
  const response = await fetch(path, config);
  let payload = null;
  if (response.status !== 204) {
    const type = response.headers.get("content-type") || "";
    payload = type.includes("application/json") ? await response.json() : await response.text();
  }
  if (!response.ok) {
    const error = new Error(payload && payload.error ? payload.error.message : `Požiadavka zlyhala (${response.status})`);
    error.payload = payload;
    error.status = response.status;
    if (response.status === 401 && path !== "/api/session") openAuthModal();
    throw error;
  }
  return payload;
}

function notify(message, isError = false) {
  const region = byId("toast-region");
  const toast = element("div", { className: `toast${isError ? " error" : ""}`, text: message });
  region.replaceChildren(toast);
  window.setTimeout(() => { if (toast.isConnected) toast.remove(); }, 5000);
}

function openAuthModal() {
  byId("auth-form").reset();
  byId("auth-form-error").hidden = true;
  if (!byId("auth-modal").open) byId("auth-modal").showModal();
  byId("auth-token").focus();
}

function closeAuthModal() {
  byId("auth-form").reset();
  byId("auth-form-error").hidden = true;
  if (byId("auth-modal").open) byId("auth-modal").close();
}

async function authenticateForWrites(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const submit = byId("auth-submit");
  const token = byId("auth-token");
  submit.disabled = true;
  submit.textContent = "Prihlasujem…";
  byId("auth-form-error").hidden = true;
  try {
    await api("/api/session", { method: "POST", body: JSON.stringify({ token: token.value }) });
    closeAuthModal();
    byId("auth-button").textContent = "Zápis prihlásený";
    notify("Prihlásenie pre write operácie bolo úspešné.");
  } catch (error) {
    const errorBox = byId("auth-form-error");
    errorBox.textContent = `Prihlásenie zlyhalo: ${error.message}`;
    errorBox.hidden = false;
  } finally {
    token.value = "";
    submit.disabled = false;
    submit.textContent = "Prihlásiť";
  }
}

function renderTable(targetId, headers, rows) {
  const target = byId(targetId);
  if (!rows.length) { target.replaceChildren(emptyMessage("Žiadne záznamy nezodpovedajú výberu.")); return; }
  const table = element("table");
  const headRow = element("tr");
  headers.forEach((label) => headRow.append(element("th", { text: label, attrs: { scope: "col" } })));
  table.append(element("thead", {}, [headRow]), element("tbody", {}, rows));
  target.replaceChildren(table);
}

function makeCell(content, className = "") {
  const cell = element("td", { className });
  if (content instanceof Node) cell.append(content);
  else cell.textContent = content == null || content === "" ? "—" : String(content);
  return cell;
}

function actionButton(label, action, itemId, className = "") {
  return element("button", { type: "button", text: label, className, dataset: { action, id: itemId } });
}

function setConnection(ok) {
  byId("app-status").textContent = ok ? "API pripojené" : "API nedostupné";
  document.querySelector(".status-dot").classList.toggle("error", !ok);
}

function setOperatingMode(health) {
  const live = health.mode === "live";
  const readOnly = health.mode === "read_only";
  byId("auth-button").hidden = !(live || readOnly);
  byId("mode-label").textContent = live ? "LIVE" : (readOnly ? "Read-only" : "Simulácia");
  byId("mode-title").textContent = live ? "LIVE režim" : (readOnly ? "Reálny server — iba na čítanie" : "Simulačný režim");
  byId("mode-description").textContent = live
    ? " Fyzické zápisy sú povolené iba s explicitným potvrdením každej požiadavky."
    : (readOnly ? " Inventár pochádza z reálneho ESL servera. Fyzické zápisy sú vypnuté."
      : " Zmeny sú lokálne. Žiadny zápis sa neposiela na fyzické ESL zariadenia.");
  byId("safety-banner").classList.toggle("live", live);
}

async function loadOverview() {
  setState("overview-state", "Načítavam prehľad…");
  byId("kpi-grid").replaceChildren();
  try {
    const [health, dashboard, alertsResult, jobsResult, tagsResult] = await Promise.all([
      api("/api/health"), api("/api/dashboard"), api("/api/alerts?active=true"), api("/api/jobs"), api("/api/tags"),
    ]);
    setOperatingMode(health);
    const lowBattery = tagsResult.items.filter((tag) => Number(tag.battery) <= 20).length;
    const metrics = [
      ["Cenovky", dashboard.tags, `${dashboard.bound_tags} priradených`],
      ["Online / bez chyby", dashboard.tags - dashboard.failed_tags, `${dashboard.failed_tags} s chybou`],
      ["Nízka batéria", lowBattery, "20 % alebo menej"],
      ["Produkty", dashboard.products, "v lokálnom katalógu"],
      ["Otvorené alerty", dashboard.active_alerts, "vyžadujú pozornosť"],
      ["Čakajúce úlohy", dashboard.queued_jobs, "vo fronte alebo v behu"],
      ["Stanice", dashboard.routers, `${dashboard.offline_routers} offline`],
      ["Režim", health.mode === "live" ? "LIVE" : (health.mode === "read_only" ? "READ" : "SIM"), health.mode === "live" ? "zápis vyžaduje potvrdenie" : "bez fyzických zápisov"],
    ];
    byId("kpi-grid").replaceChildren(...metrics.map(([label, value, meta]) => element("article", { className: "kpi" }, [
      element("span", { className: "kpi-label", text: label }), element("strong", { className: "kpi-value", text: value }), element("span", { className: "kpi-meta", text: meta }),
    ])));
    renderOverviewRows("overview-alerts", alertsResult.items.filter((item) => item.severity === "critical" || item.severity === "warning").slice(0, 5), "Bez aktívnych kritických alertov.", (item) => [item.message, `${statusLabels[item.severity] || item.severity} · ${item.entity_id}`]);
    renderOverviewRows("overview-jobs", jobsResult.items.slice(0, 5), "Zatiaľ neboli vytvorené žiadne úlohy.", (item) => [item.id, `${statusLabels[item.status] || item.status} · ${item.succeeded_items}/${item.total_items} úspešných`]);
    setState("overview-state", "");
    setConnection(true);
  } catch (error) {
    setState("overview-state", `Prehľad sa nepodarilo načítať: ${error.message}`, true);
    setConnection(false);
  }
}

function renderOverviewRows(id, items, emptyText, describe) {
  const target = byId(id);
  if (!items.length) { target.replaceChildren(emptyMessage(emptyText)); return; }
  target.replaceChildren(...items.map((item) => {
    const [title, detail] = describe(item);
    return element("div", { className: "list-row" }, [element("div", {}, [element("strong", { text: title }), element("p", { text: detail })]), status(item.status || item.severity)]);
  }));
}

async function loadTags() {
  setState("tags-state", "Načítavam cenovky…");
  try {
    const params = new URLSearchParams();
    const searchTerm = byId("tag-search").value.trim().toLowerCase();
    const selectedStatus = byId("tag-status").value;
    const router = byId("tag-router").value;
    if (selectedStatus) params.set("status", selectedStatus);
    if (router) params.set("router_id", router);
    const query = params.toString();
    const [tagsResult, productsResult, routersResult] = await Promise.all([
      api(`/api/tags${query ? `?${query}` : ""}`), api("/api/products"), api("/api/routers"),
    ]);
    state.products = productsResult.items;
    state.routers = routersResult.items;
    let items = tagsResult.items;
    if (searchTerm) {
      const productMatches = new Set(state.products.filter((product) => [product.name, product.sku, product.ean].some((value) => String(value || "").toLowerCase().includes(searchTerm))).map((product) => product.id));
      items = items.filter((tag) => [tag.mac, tag.label].some((value) => String(value || "").toLowerCase().includes(searchTerm)) || productMatches.has(tag.product_id));
    }
    const battery = byId("tag-battery").value;
    if (battery === "low") items = items.filter((tag) => Number(tag.battery) <= 20);
    if (battery === "ok") items = items.filter((tag) => Number(tag.battery) > 20);
    const signal = byId("tag-signal").value;
    if (signal === "strong") items = items.filter((tag) => Number(tag.rssi) >= -65);
    if (signal === "medium") items = items.filter((tag) => Number(tag.rssi) >= -80 && Number(tag.rssi) < -65);
    if (signal === "weak") items = items.filter((tag) => Number(tag.rssi) < -80);
    state.tags = items;
    populateRouterFilter();
    renderTags(items);
    setState("tags-state", items.length ? "" : "Nenašli sa žiadne cenovky.");
  } catch (error) {
    setState("tags-state", `Cenovky sa nepodarilo načítať: ${error.message}`, true);
    byId("tags-table").replaceChildren();
  }
}

function populateRouterFilter() {
  const select = byId("tag-router");
  const current = select.value;
  const first = element("option", { value: "", text: "Všetky" });
  select.replaceChildren(first, ...state.routers.map((router) => element("option", { value: router.id, text: `${router.name} (${router.address})` })));
  if ([...select.options].some((option) => option.value === current)) select.value = current;
}

function renderTags(items) {
  const productNames = new Map(state.products.map((product) => [product.id, product.name]));
  const rows = items.map((tag) => {
    const checkbox = element("input", { type: "checkbox", checked: state.selectedTags.has(tag.id), value: tag.id, attrs: { "aria-label": `Vybrať cenovku ${tag.mac}` }, dataset: { tagSelect: tag.id } });
    const batteryValue = Math.max(0, Math.min(100, Number(tag.battery) || 0));
    const meter = element("span", { className: `battery${batteryValue <= 20 ? " low" : ""}`, attrs: { "aria-hidden": "true" } }, [element("span")]);
    meter.firstChild.style.width = `${batteryValue}%`;
    const batteryCell = element("span", {}, [meter, document.createTextNode(`${batteryValue} %`)]);
    const row = element("tr");
    row.append(makeCell(checkbox, "checkbox-cell"), makeCell(tag.mac, "mono"), makeCell(tag.label), makeCell(status(tag.status)), makeCell(batteryCell), makeCell(`${tag.rssi} dBm`), makeCell(tag.router_id), makeCell(tag.product_id ? productNames.get(tag.product_id) || tag.product_id : "Nepriradená"));
    return row;
  });
  renderTable("tags-table", ["", "MAC", "Označenie", "Stav", "Batéria", "Signál", "Stanica", "Produkt"], rows);
  updateSelection();
}

function updateSelection() {
  byId("selected-count").textContent = `Vybrané: ${state.selectedTags.size}`;
  byId("create-job-button").disabled = state.selectedTags.size === 0;
}

async function createBulkJob() {
  const selected = state.tags.filter((tag) => state.selectedTags.has(tag.id));
  const productIds = [...new Set(selected.map((tag) => tag.product_id).filter(Boolean))];
  if (!productIds.length) { notify("Vybrané cenovky nemajú priradený produkt.", true); return; }
  if (selected.some((tag) => !tag.product_id)) notify("Nepriradené cenovky boli z výberu vynechané.", true);
  const button = byId("create-job-button");
  button.disabled = true;
  button.textContent = "Vytváram…";
  try {
    const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({ product_ids: productIds }) });
    state.selectedTags.clear();
    updateSelection();
    notify(`Úloha ${job.id} bola vytvorená v simulačnom režime.`);
    location.hash = "jobs";
  } catch (error) { notify(`Úlohu sa nepodarilo vytvoriť: ${error.message}`, true); }
  finally { button.textContent = "Vytvoriť update job"; button.disabled = state.selectedTags.size === 0; }
}

async function loadProducts() {
  setState("products-state", "Načítavam produkty…");
  try {
    const params = new URLSearchParams();
    const searchTerm = byId("product-search").value.trim();
    if (searchTerm) params.set("search", searchTerm);
    const query = params.toString();
    const [productsResult, templatesResult] = await Promise.all([api(`/api/products${query ? `?${query}` : ""}`), api("/api/templates")]);
    state.products = productsResult.items;
    state.templates = templatesResult.items;
    populateTemplateSelect();
    renderProducts();
    setState("products-state", state.products.length ? "" : "Nenašli sa žiadne produkty.");
  } catch (error) {
    setState("products-state", `Produkty sa nepodarilo načítať: ${error.message}`, true);
    byId("products-table").replaceChildren();
  }
}

function renderProducts() {
  const rows = state.products.map((product) => {
    const actions = element("div", { className: "table-actions" }, [
      actionButton("Upraviť", "edit-product", product.id),
      actionButton(product.tag_id ? "Odpojiť cenovku" : "Priradiť cenovku", product.tag_id ? "unbind" : "bind", product.id),
      actionButton("Vymazať produkt", "delete-product", product.id, "danger"),
    ]);
    const row = element("tr");
    row.append(makeCell(product.sku, "mono"), makeCell(product.ean), makeCell(product.name), makeCell(formatPrice(product.price, product.currency)), makeCell(product.currency || "EUR"), makeCell(formatDate(product.updated_at)), makeCell(product.tag_id || "Nepriradená", product.tag_id ? "mono" : "muted"), makeCell(actions));
    return row;
  });
  renderTable("products-table", ["SKU", "EAN", "Názov", "Cena", "Jednotka", "Aktualizované", "Cenovka", "Akcie"], rows);
}

function populateTemplateSelect() {
  const select = byId("product-template");
  select.replaceChildren(element("option", { value: "", text: "Bez šablóny" }), ...state.templates.map((template) => element("option", { value: template.id, text: `${template.name} (${template.width} × ${template.height})` })));
}

function openProductModal(product = null) {
  byId("product-form").reset();
  byId("product-form-error").hidden = true;
  byId("product-id").value = product ? product.id : "";
  byId("product-modal-title").textContent = product ? "Upraviť produkt" : "Pridať produkt";
  byId("product-sku").value = product ? product.sku : "";
  byId("product-ean").value = product && product.ean ? product.ean : "";
  byId("product-name").value = product ? product.name : "";
  byId("product-price").value = product ? product.price : "";
  byId("product-template").value = product && product.template_id ? product.template_id : "";
  byId("product-modal").showModal();
  byId("product-sku").focus();
}

async function saveProduct(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const id = byId("product-id").value;
  const payload = {
    sku: byId("product-sku").value.trim(), ean: byId("product-ean").value.trim() || null,
    name: byId("product-name").value.trim(), price: Number(byId("product-price").value),
    template_id: byId("product-template").value || null,
  };
  const save = byId("save-product");
  save.disabled = true;
  save.textContent = "Ukladám…";
  try {
    if (id) {
      await api(`/api/products/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) });
    } else {
      await api("/api/products", { method: "POST", body: JSON.stringify(payload) });
    }
    byId("product-modal").close();
    notify(id ? "Produkt bol aktualizovaný." : "Produkt bol vytvorený.");
    await loadProducts();
  } catch (error) {
    const errorBox = byId("product-form-error");
    errorBox.textContent = `Produkt sa nepodarilo uložiť: ${error.message}`;
    errorBox.hidden = false;
  } finally { save.disabled = false; save.textContent = "Uložiť produkt"; }
}

async function deleteProduct(id) {
  const product = state.products.find((item) => item.id === id);
  if (!product || !window.confirm(`Vymazať lokálny produkt „${product.name}“? Táto akcia nevymaže fyzickú cenovku.`)) return;
  try {
    await api(`/api/products/${encodeURIComponent(id)}`, { method: "DELETE" });
    notify("Lokálny produkt bol vymazaný.");
    await loadProducts();
  } catch (error) { notify(`Produkt sa nepodarilo vymazať: ${error.message}`, true); }
}

async function openBinding(id) {
  byId("binding-product-id").value = id;
  const select = byId("binding-tag");
  select.replaceChildren(element("option", { value: "", text: "Načítavam…" }));
  byId("binding-modal").showModal();
  try {
    const result = await api("/api/tags?bound=false");
    select.replaceChildren(element("option", { value: "", text: "Vyberte cenovku" }), ...result.items.map((tag) => element("option", { value: tag.id, text: `${tag.mac} — ${tag.label || tag.id}` })));
  } catch (error) { byId("binding-modal").close(); notify(`Voľné cenovky sa nepodarilo načítať: ${error.message}`, true); }
}

async function saveBinding(event) {
  event.preventDefault();
  const productId = byId("binding-product-id").value;
  const tagId = byId("binding-tag").value;
  if (!tagId) return;
  try {
    await api("/api/bindings", { method: "POST", body: JSON.stringify({ product_id: productId, tag_id: tagId }) });
    byId("binding-modal").close(); notify("Cenovka bola priradená k produktu."); await loadProducts();
  } catch (error) { notify(`Cenovku sa nepodarilo priradiť: ${error.message}`, true); }
}

async function unbindProduct(product) {
  if (!product.tag_id || !window.confirm(`Odpojiť cenovku ${product.tag_id} od produktu „${product.name}“?`)) return;
  try {
    await api(`/api/bindings/${encodeURIComponent(product.id)}/${encodeURIComponent(product.tag_id)}`, { method: "DELETE" });
    notify("Cenovka bola od produktu odpojená."); await loadProducts();
  } catch (error) { notify(`Väzbu sa nepodarilo odstrániť: ${error.message}`, true); }
}

async function loadTemplates() {
  setState("templates-state", "Načítavam šablóny…");
  try {
    const [templatesResult, tagsResult] = await Promise.all([api("/api/templates"), api("/api/tags")]);
    state.templates = templatesResult.items;
    const counts = new Map();
    tagsResult.items.forEach((tag) => counts.set(tag.template_id, (counts.get(tag.template_id) || 0) + 1));
    const cards = state.templates.map((template) => element("article", { className: "card" }, [
      element("p", { className: "eyebrow", text: template.id }), element("h2", { text: template.name }),
      definitionList([["Rozmery", `${template.width} × ${template.height} px`], ["Typ", "ESL displej"], ["Mapping typ", template.mapping_type], ["Dynamické polia", "Produkt, cena, EAN"], ["Priradené cenovky", counts.get(template.id) || 0]]),
    ]));
    byId("templates-grid").replaceChildren(...(cards.length ? cards : [emptyMessage("Nie sú dostupné žiadne šablóny.")]));
    setState("templates-state", "");
  } catch (error) { setState("templates-state", `Šablóny sa nepodarilo načítať: ${error.message}`, true); byId("templates-grid").replaceChildren(); }
}

function definitionList(items) {
  const list = element("dl");
  items.forEach(([term, value]) => list.append(element("dt", { text: term }), element("dd", { text: value })));
  return list;
}

async function loadRouters() {
  setState("routers-state", "Načítavam stanice…");
  try {
    const [routersResult, tagsResult] = await Promise.all([api("/api/routers"), api("/api/tags")]);
    state.routers = routersResult.items;
    const cards = state.routers.map((router) => {
      const attached = tagsResult.items.filter((tag) => tag.router_id === router.id).length;
      return element("article", { className: "card" }, [element("p", { className: "eyebrow", text: router.id }), element("h2", { text: router.name }), status(router.status), definitionList([["IP adresa", router.address], ["Heartbeat", formatDate(router.last_seen_at)], ["Frekvencia", "2,4 GHz"], ["Verzia", router.version || router.firmware_version || "Neznáma"], ["Počet cenoviek", attached]])]);
    });
    byId("routers-grid").replaceChildren(...(cards.length ? cards : [emptyMessage("Nie sú dostupné žiadne stanice.")]));
    setState("routers-state", "");
  } catch (error) { setState("routers-state", `Stanice sa nepodarilo načítať: ${error.message}`, true); byId("routers-grid").replaceChildren(); }
}

async function loadJobs() {
  setState("jobs-state", "Načítavam úlohy…");
  try {
    const result = await api("/api/jobs");
    state.jobs = await Promise.all(result.items.map((job) => api(`/api/jobs/${encodeURIComponent(job.id)}`)));
    byId("jobs-list").replaceChildren(...(state.jobs.length ? state.jobs.map(renderJob) : [emptyMessage("Zatiaľ neboli vytvorené žiadne úlohy.")]));
    setState("jobs-state", "");
  } catch (error) { setState("jobs-state", `Úlohy sa nepodarilo načítať: ${error.message}`, true); byId("jobs-list").replaceChildren(); }
}

function renderJob(job) {
  const successRate = job.total_items ? Math.round((Number(job.succeeded_items) / Number(job.total_items)) * 100) : 0;
  const progressFill = element("span");
  progressFill.style.width = `${successRate}%`;
  const actions = element("div", { className: "job-actions" });
  if (["queued", "partial", "failed"].includes(job.status) && job.items.some((item) => item.status === "queued")) {
    actions.append(actionButton("Simulovať úspech", "simulate", job.id), actionButton("Simulovať chybu", "simulate-failure", job.id));
  }
  if (Number(job.failed_items) > 0) actions.append(actionButton("Opakovať chybné", "retry", job.id));
  const itemRows = job.items.map((item) => {
    const row = element("tr");
    row.append(makeCell(item.tag_id, "mono"), makeCell(item.product_id, "mono"), makeCell(status(item.status)), makeCell(item.attempts), makeCell(item.error));
    return row;
  });
  const itemTable = element("div", { className: "table-wrap" });
  if (itemRows.length) {
    const table = element("table"); const header = element("tr");
    ["Cenovka", "Produkt", "Stav", "Pokusy", "Chyba"].forEach((label) => header.append(element("th", { text: label, attrs: { scope: "col" } })));
    table.append(element("thead", {}, [header]), element("tbody", {}, itemRows)); itemTable.append(table);
  }
  return element("article", { className: "job" }, [
    element("div", { className: "job-header" }, [element("div", {}, [element("p", { className: "eyebrow", text: formatDate(job.requested_at) }), element("h2", { className: "mono", text: job.id }), status(job.status)]), actions]),
    element("div", { className: "job-summary" }, [["Položky", job.total_items], ["Úspešné", job.succeeded_items], ["Chybné", job.failed_items], ["Úspešnosť", `${successRate} %`]].map(([label, value]) => element("div", { className: "job-metric" }, [element("span", { text: label }), element("strong", { text: value })]))),
    element("div", { className: "progress", attrs: { role: "progressbar", "aria-label": `Úspešnosť úlohy ${job.id}`, "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(successRate) } }, [progressFill]),
    element("div", { className: "job-items" }, [itemTable]),
  ]);
}

async function processJob(id, withFailure) {
  const job = state.jobs.find((item) => item.id === id);
  const queued = job ? job.items.filter((item) => item.status === "queued") : [];
  const failIds = withFailure && queued.length ? [queued[0].tag_id] : [];
  try {
    await api(`/api/jobs/${encodeURIComponent(id)}/simulate`, { method: "POST", body: JSON.stringify({ fail_tag_ids: failIds }) });
    notify(withFailure ? "Simulácia skončila s označenou chybnou položkou." : "Simulácia bola úspešne dokončená."); await loadJobs();
  } catch (error) { notify(`Simuláciu sa nepodarilo spustiť: ${error.message}`, true); }
}

async function retryJob(id) {
  try {
    await api(`/api/jobs/${encodeURIComponent(id)}/retry`, { method: "POST", body: JSON.stringify({}) });
    notify("Chybné položky sú opäť vo fronte."); await loadJobs();
  } catch (error) { notify(`Opakovanie sa nepodarilo: ${error.message}`, true); }
}

async function loadAudit() {
  setState("audit-state", "Načítavam audit…");
  try {
    const [alertsResult, auditResult] = await Promise.all([api("/api/alerts?active=true"), api("/api/audit?limit=100")]);
    state.alerts = alertsResult.items; state.audit = auditResult.items;
    byId("alerts-list").replaceChildren(...(state.alerts.length ? state.alerts.map((item) => element("div", { className: "alert-item" }, [status(item.severity), element("strong", { text: item.message }), element("p", { text: `${item.entity_type} · ${item.entity_id} · ${formatDate(item.created_at)}` })])) : [emptyMessage("Nie sú evidované aktívne alerty.")]));
    byId("audit-list").replaceChildren(...(state.audit.length ? state.audit.map((item) => element("div", { className: "alert-item" }, [element("strong", { text: item.action }), element("p", { text: `${formatDate(item.created_at)} · ${item.entity_type} · ${item.entity_id}` }), element("div", { className: "audit-details mono", text: JSON.stringify(item.details) })])) : [emptyMessage("Audit zatiaľ neobsahuje udalosti.")]));
    setState("audit-state", "");
  } catch (error) { setState("audit-state", `Audit sa nepodarilo načítať: ${error.message}`, true); byId("alerts-list").replaceChildren(); byId("audit-list").replaceChildren(); }
}

async function readOnlySync() {
  const button = byId("sync-button"); button.disabled = true; button.textContent = "Synchronizujem…";
  try {
    const result = await api("/api/sync/read-only", { method: "POST", body: JSON.stringify({}) });
    const synced = result.synced || {};
    notify(`Synchronizácia iba na čítanie dokončená: ${synced.routers || 0} staníc, ${synced.tags || 0} cenoviek.`);
    await viewLoaders[state.activeView]();
  } catch (error) { notify(`Read-only synchronizácia nie je dostupná: ${error.message}`, true); }
  finally { button.disabled = false; button.textContent = "Synchronizovať iba na čítanie"; }
}

function navigate() {
  const requested = location.hash.replace(/^#/, "") || "overview";
  const view = viewLoaders[requested] ? requested : "overview";
  state.activeView = view;
  document.querySelectorAll("[data-view-panel]").forEach((panel) => { panel.hidden = panel.dataset.viewPanel !== view; });
  document.querySelectorAll("[data-view]").forEach((link) => {
    if (link.dataset.view === view) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
  });
  byId("primary-nav").classList.remove("open");
  byId("mobile-nav-toggle").setAttribute("aria-expanded", "false");
  viewLoaders[view]();
  window.scrollTo({ top: 0, behavior: "auto" });
}

function bindEvents() {
  window.addEventListener("hashchange", navigate);
  byId("mobile-nav-toggle").addEventListener("click", () => {
    const open = byId("primary-nav").classList.toggle("open");
    byId("mobile-nav-toggle").setAttribute("aria-expanded", String(open));
  });
  byId("sync-button").addEventListener("click", readOnlySync);
  byId("auth-button").addEventListener("click", openAuthModal);
  byId("auth-form").addEventListener("submit", authenticateForWrites);
  document.querySelectorAll(".auth-close").forEach((button) => button.addEventListener("click", closeAuthModal));
  byId("auth-modal").addEventListener("cancel", () => byId("auth-form").reset());
  document.querySelectorAll(".refresh-view").forEach((button) => button.addEventListener("click", () => viewLoaders[state.activeView]()));
  byId("tag-filters").addEventListener("submit", (event) => { event.preventDefault(); loadTags(); });
  byId("tags-table").addEventListener("change", (event) => {
    const input = event.target.closest("[data-tag-select]"); if (!input) return;
    if (input.checked) state.selectedTags.add(input.dataset.tagSelect); else state.selectedTags.delete(input.dataset.tagSelect); updateSelection();
  });
  byId("clear-selection").addEventListener("click", () => { state.selectedTags.clear(); renderTags(state.tags); });
  byId("create-job-button").addEventListener("click", createBulkJob);
  byId("product-search-form").addEventListener("submit", (event) => { event.preventDefault(); loadProducts(); });
  byId("add-product").addEventListener("click", () => openProductModal());
  byId("product-form").addEventListener("submit", saveProduct);
  document.querySelectorAll(".modal-close").forEach((button) => button.addEventListener("click", () => byId("product-modal").close()));
  document.querySelectorAll(".binding-close").forEach((button) => button.addEventListener("click", () => byId("binding-modal").close()));
  byId("binding-form").addEventListener("submit", saveBinding);
  byId("products-table").addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]"); if (!button) return;
    const product = state.products.find((item) => item.id === button.dataset.id); if (!product) return;
    if (button.dataset.action === "edit-product") openProductModal(product);
    if (button.dataset.action === "delete-product") deleteProduct(product.id);
    if (button.dataset.action === "bind") openBinding(product.id);
    if (button.dataset.action === "unbind") unbindProduct(product);
  });
  byId("jobs-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]"); if (!button) return;
    if (button.dataset.action === "simulate") processJob(button.dataset.id, false);
    if (button.dataset.action === "simulate-failure") processJob(button.dataset.id, true);
    if (button.dataset.action === "retry") retryJob(button.dataset.id);
  });
  byId("auth-modal").addEventListener("click", (event) => { if (event.target === byId("auth-modal")) closeAuthModal(); });
  [byId("product-modal"), byId("binding-modal")].forEach((dialog) => dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); }));
}

bindEvents();
navigate();
