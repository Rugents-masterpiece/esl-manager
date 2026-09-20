"use strict";

(function exposeTemplateFamilies(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.TemplateFamilies = api;
})(typeof globalThis === "undefined" ? this : globalThis, () => {
  const models = Object.freeze({
    "2.13TFT-BW": Object.freeze({ label: "250 × 132 TFT", width: 250, height: 132, screen_type: 1 }),
    "2.13EPD-BWR": Object.freeze({ label: "250 × 122 EPD", width: 250, height: 122, screen_type: 2 }),
    "2.9EPD-BWR": Object.freeze({ label: "296 × 128 EPD", width: 296, height: 128, screen_type: 2 }),
  });
  const families = Object.freeze(Object.values(models));
  const family = (template) => families.find((candidate) => (
    template != null
      && template.width === candidate.width
      && template.height === candidate.height
      && template.screen_type === candidate.screen_type
  )) || null;

  return Object.freeze({
    models,
    family,
    label: (template) => family(template)?.label || null,
    supports: (template) => family(template) !== null,
    matchesModel: (template, model) => model != null && family(template) === model,
  });
});
