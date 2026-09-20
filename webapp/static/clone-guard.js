"use strict";

(function exposeCloneSubmissionGuard(root) {
  class CloneSubmissionGuard {
    constructor() { this.busy = false; }

    async run(action, onStateChange = () => {}) {
      if (this.busy) return false;
      this.busy = true;
      onStateChange(true);
      try {
        await action();
        return true;
      } finally {
        this.busy = false;
        onStateChange(false);
      }
    }
  }

  root.CloneSubmissionGuard = CloneSubmissionGuard;
  if (typeof module === "object" && module.exports) module.exports = CloneSubmissionGuard;
})(globalThis);
