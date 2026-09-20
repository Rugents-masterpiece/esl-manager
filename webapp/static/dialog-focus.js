"use strict";

(function exposeDialogFocusManager(root) {
  class DialogFocusManager {
    constructor() { this.openers = new Map(); }

    remember(dialog, opener) {
      this.openers.set(dialog, opener || null);
    }

    restore(dialog) {
      if (!this.openers.has(dialog)) return false;
      const opener = this.openers.get(dialog);
      this.openers.delete(dialog);
      if (opener && opener.isConnected && typeof opener.focus === "function") {
        opener.focus();
        return true;
      }
      return false;
    }
  }

  root.DialogFocusManager = DialogFocusManager;
  if (typeof module === "object" && module.exports) module.exports = DialogFocusManager;
})(globalThis);