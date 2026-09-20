"use strict";

(function exposeDialogOperationGuard(root) {
  class DialogOperationGuard {
    constructor() {
      this.generations = new Map();
      this.busy = new Set();
    }

    open(dialog) {
      this.invalidate(dialog);
    }

    begin(dialog) {
      if (this.busy.has(dialog)) return null;
      const token = { dialog, generation: this.generations.get(dialog) || 0 };
      this.busy.add(dialog);
      return token;
    }

    isCurrent(token) {
      return Boolean(token) && this.busy.has(token.dialog)
        && (this.generations.get(token.dialog) || 0) === token.generation;
    }

    finish(token) {
      if (!this.isCurrent(token)) return false;
      this.busy.delete(token.dialog);
      return true;
    }

    invalidate(dialog) {
      this.generations.set(dialog, (this.generations.get(dialog) || 0) + 1);
      this.busy.delete(dialog);
    }

    isBusy(dialog) { return this.busy.has(dialog); }
    canClose(dialog) { return !this.isBusy(dialog); }
  }

  root.DialogOperationGuard = DialogOperationGuard;
  if (typeof module === "object" && module.exports) module.exports = DialogOperationGuard;
})(globalThis);