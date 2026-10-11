"use strict";
const assert = require("node:assert/strict");
const M = require("../static/designer-model.js");
for (const price of [9007199254740992, -9007199254740992, 1e20]) {
  const doc = M.createDocument(); doc.sample_data = {price};
  assert.ok(M.validate(doc).length, "unsafe JSON numbers must require strings");
}
const safe = M.createDocument(); safe.sample_data = {code: "9007199254740993", price: 9007199254740991};
assert.deepEqual(M.validate(safe), []);
console.log("designer safe sample numbers: PASS");
