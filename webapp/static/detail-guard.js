"use strict";

(function exposeDetailLoadGuard(root) {
  class DetailLoadGuard {
    constructor() {
      this.current = null;
      this.activeId = null;
    }

    begin(id) {
      this.invalidate();
      const request = { id, controller: new AbortController() };
      request.signal = request.controller.signal;
      this.current = request;
      return request;
    }

    accept(request) {
      if (this.current !== request || request.signal.aborted) return false;
      this.activeId = request.id;
      this.current = null;
      return true;
    }

    fail(request) {
      if (this.current === request) {
        this.current = null;
        this.activeId = null;
      }
    }

    invalidate() {
      if (this.current) this.current.controller.abort();
      this.current = null;
      this.activeId = null;
    }
  }

  root.DetailLoadGuard = DetailLoadGuard;
  if (typeof module === "object" && module.exports) module.exports = DetailLoadGuard;
})(globalThis);