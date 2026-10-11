"use strict";
const assert = require("node:assert/strict");
const renderPreview = require("../static/template-preview.js");
const active = new Set();
const images = [];
function element(tag, properties) {
  const listeners = {};
  const node = { tagName: tag, isConnected: true, ...properties,
    addEventListener(type, callback) { listeners[type] = callback; },
    emit(type) { active.delete(node); listeners[type](); },
  };
  if (tag === "img") {
    let source = node.src;
    Object.defineProperty(node, "src", { get() { return source; }, set(value) { source = value; active.add(node); } });
    if (source) active.add(node);
    images.push(node);
  }
  return node;
}
for (let id = 1; id <= 8; id += 1) {
  renderPreview({ replaceChildren() {} }, { name: `Template ${id}`, preview_url: `/api/vendor/templates/${id}/preview` }, "Model", element);
}
assert.equal(active.size, 2, "native preview downloads must leave browser connections available for login/API");
images[2].isConnected = false;
images[0].emit("load");
assert.equal(images[2].src, undefined, "detached queued cards must not contact controller");
assert.ok(images[3].src, "completed download must start the next connected card");
assert.equal(active.size, 2);
images[1].emit("error");
assert.ok(images[4].src, "failed download must release its slot");
assert.equal(active.size, 2);
console.log("PASS: bounded preview downloads, login connection capacity, detached cards, load/error release");
