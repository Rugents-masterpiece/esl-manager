"use strict";

const assert = require("node:assert/strict");
const TemplateFamilies = require("../static/template-family.js");

const cases = [
  [{ width: 250, height: 132, screen_type: 1 }, "250 × 132 TFT"],
  [{ width: 250, height: 122, screen_type: 2 }, "250 × 122 EPD"],
  [{ width: 296, height: 128, screen_type: 2 }, "296 × 128 EPD"],
  [{ width: 250, height: 132, screen_type: 2 }, null],
  [{ width: 296, height: 128, screen_type: 1 }, null],
  [{ width: 296, height: 128, screen_type: null }, null],
];

for (const [template, expected] of cases) {
  assert.equal(TemplateFamilies.label(template), expected);
  assert.equal(TemplateFamilies.supports(template), expected !== null);
}
