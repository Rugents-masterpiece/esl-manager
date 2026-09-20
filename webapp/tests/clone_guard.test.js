"use strict";

const assert = require("node:assert/strict");
const CloneSubmissionGuard = require("../static/clone-guard.js");

(async () => {
  const guard = new CloneSubmissionGuard();
  const states = [];
  let posts = 0;
  let release;
  const waiting = new Promise((resolve) => { release = resolve; });
  const first = guard.run(async () => { posts += 1; await waiting; }, (busy) => states.push(busy));

  const editedTargetName = "Zmenený názov počas čakania";
  assert.equal(editedTargetName.length > 0, true);
  const second = await guard.run(async () => { posts += 1; }, (busy) => states.push(busy));

  assert.equal(second, false);
  assert.equal(posts, 1);
  release();
  assert.equal(await first, true);
  assert.deepEqual(states, [true, false]);
  assert.equal(posts, 1);
})().catch((error) => { console.error(error); process.exitCode = 1; });