"use strict";

const assert = require("node:assert/strict");
const renderTemplatePreview = require("../static/template-preview.js");

function fakeElement(tagName, properties = {}) {
  return {
    tagName,
    ...properties,
    listeners: {},
    addEventListener(type, listener, options) {
      this.listeners[type] = { listener, options };
    },
  };
}

const imageContainer = {
  children: [],
  replaceChildren(...children) { this.children = children; },
};
const result = renderTemplatePreview(
  imageContainer,
  { name: "Cenník", preview_url: "/api/vendor/templates/145/preview?controller_id=legacy" },
  "296 × 128 EPD",
  fakeElement,
);
assert.equal(result, "image");
assert.equal(imageContainer.children[0].tagName, "img");
assert.equal(imageContainer.children[0].src, "/api/vendor/templates/145/preview?controller_id=legacy");
assert.equal(imageContainer.children[0].alt, "Náhľad šablóny Cenník");
assert.deepEqual(imageContainer.children[0].listeners.error.options, { once: true });
imageContainer.children[0].listeners.error.listener();
assert.equal(imageContainer.children[0].tagName, "div");
assert.equal(imageContainer.children[0].className, "template-screen");
assert.equal(imageContainer.children[0].text, "296 × 128 EPD");

const fallbackContainer = {
  children: [],
  replaceChildren(...children) { this.children = children; },
};
assert.equal(renderTemplatePreview(
  fallbackContainer,
  { name: "Lokálna", preview_url: null },
  "296 × 128 EPD",
  fakeElement,
), "fallback");
assert.equal(fallbackContainer.children[0].tagName, "div");
assert.equal(fallbackContainer.children[0].className, "template-screen");
