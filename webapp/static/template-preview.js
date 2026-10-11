"use strict";

(function expose(root, factory) {
  const renderTemplatePreview = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = renderTemplatePreview;
  root.renderTemplatePreview = renderTemplatePreview;
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  // Native previews share the browser's HTTP/1 connection pool with login/API.
  // The controller serializes slow reads: never occupy every browser connection.
  const queue = [];
  let active = 0;
  const start = (entry) => {
    active += 1;
    entry.started = true;
    entry.image.src = entry.url;
  };
  const drain = () => {
    while (active < 2 && queue.length) {
      const entry = queue.shift();
      if (entry.image.isConnected !== false) start(entry);
    }
  };
  return function renderTemplatePreview(
  container, template, familyLabel, elementFactory,
) {
  const fallback = () => elementFactory("div", {
    className: "template-screen",
    text: familyLabel,
  });
  const previewUrl = template.preview_url;
  if (typeof previewUrl !== "string" || !previewUrl.startsWith("/api/vendor/templates/")) {
    container.replaceChildren(fallback());
    return "fallback";
  }
  const image = elementFactory("img", {
    alt: `Náhľad šablóny ${template.name}`,
    fetchPriority: "low",
  });
  const entry = { image, url: previewUrl, started: false };
  let settled = false;
  const finish = () => {
    if (settled || !entry.started) return;
    settled = true;
    active -= 1;
    drain();
  };
  image.addEventListener("load", finish, { once: true });
  image.addEventListener("error", () => {
    container.replaceChildren(fallback());
    finish();
  }, { once: true });
  container.replaceChildren(image);
  if (active < 2) start(entry);
  else queue.push(entry);
  return "image";
  };
});
