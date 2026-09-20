"use strict";

(function expose(root, factory) {
  const renderTemplatePreview = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = renderTemplatePreview;
  root.renderTemplatePreview = renderTemplatePreview;
})(typeof globalThis !== "undefined" ? globalThis : this, () => function renderTemplatePreview(
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
    src: previewUrl,
    alt: `Náhľad šablóny ${template.name}`,
  });
  image.addEventListener("error", () => container.replaceChildren(fallback()), { once: true });
  container.replaceChildren(image);
  return "image";
});
