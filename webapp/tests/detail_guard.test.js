"use strict";

const assert = require("node:assert/strict");
const DetailLoadGuard = require("../static/detail-guard.js");

(async () => {
  const guard = new DetailLoadGuard();
  const requestA = guard.begin("tag-A");
  const pendingA = Promise.resolve().then(() => ({ id: "tag-A" }));
  const requestB = guard.begin("tag-B");

  assert.equal(requestA.signal.aborted, true);
  assert.equal(guard.activeId, null);
  guard.fail(requestB);
  assert.equal(guard.accept(requestA), false);
  await pendingA;
  assert.equal(guard.activeId, null);
  assert.equal(Boolean(guard.activeId), false, "failed B must not permit PUT of stale A");

  const requestC = guard.begin("tag-C");
  assert.equal(guard.accept(requestC), true);
  guard.fail(requestA);
  assert.equal(guard.activeId, "tag-C", "a stale failure must not clear the accepted detail");
})().catch((error) => { console.error(error); process.exitCode = 1; });