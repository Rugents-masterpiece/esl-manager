"use strict";
const assert = require("node:assert/strict");
const M = require("../static/designer-model.js");
const emoji = "😀";
for (const [property, limit] of [["name",200],["id",64],["text",2000],["prefix",200],["suffix",200]]) {
  const doc = M.add(M.createDocument(), "text");
  doc.elements[0][property] = emoji.repeat(limit);
  assert.deepEqual(M.validate(doc), [], property + " must count Unicode code points");
  doc.elements[0][property] += emoji;
  assert.ok(M.validate(doc).length, property + " must enforce the same backend limit");
}
const doc = M.createDocument(emoji.repeat(200));
doc.sample_data = {name: emoji.repeat(2000)};
assert.deepEqual(M.validate(doc), []);
doc.name += emoji;
assert.ok(M.validate(doc).length);
doc.name = "Draft"; doc.sample_data.name += emoji;
assert.ok(M.validate(doc).length);
console.log("designer Unicode code-point limits: PASS");
