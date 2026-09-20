"use strict";

const assert = require("node:assert/strict");
const DialogFocusManager = require("../static/dialog-focus.js");

const manager = new DialogFocusManager();
const tagDialog = {};
const authDialog = {};
const tagButton = { isConnected: true, focusCalls: 0, focus() { this.focusCalls += 1; } };
const saveButton = { isConnected: true, focusCalls: 0, focus() { this.focusCalls += 1; } };

manager.remember(tagDialog, tagButton);
manager.remember(authDialog, saveButton);
assert.equal(manager.restore(authDialog), true);
assert.equal(saveButton.focusCalls, 1);
assert.equal(tagButton.focusCalls, 0);
assert.equal(manager.restore(tagDialog), true);
assert.equal(tagButton.focusCalls, 1);
assert.equal(manager.restore(tagDialog), false);