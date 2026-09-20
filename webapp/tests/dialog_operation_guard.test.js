"use strict";

const assert = require("node:assert/strict");
const DialogOperationGuard = require("../static/dialog-operation-guard.js");

const guard = new DialogOperationGuard();
const dialog = {};
guard.open(dialog);
const first = guard.begin(dialog);
assert.ok(first);
assert.equal(guard.isBusy(dialog), true);
assert.equal(guard.canClose(dialog), false);
assert.equal(guard.begin(dialog), null);

guard.invalidate(dialog);
assert.equal(guard.isCurrent(first), false);
assert.equal(guard.finish(first), false);

guard.open(dialog);
const second = guard.begin(dialog);
assert.ok(second);
assert.equal(guard.finish(second), true);
assert.equal(guard.isBusy(dialog), false);
assert.equal(guard.canClose(dialog), true);