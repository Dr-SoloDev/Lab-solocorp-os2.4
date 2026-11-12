// Modules page: refresh live status from the runtime without a reload.
// Cosmetic only — the server-rendered HTML is always correct on its own, and a
// failed fetch leaves the last rendered state in place.
(function () {
  "use strict";

  var cards = document.querySelectorAll("[data-module]");
  if (!cards.length) {
    return;
  }

  var POLL_INTERVAL_MS = 5000;

  function setText(selector, id, value) {
    var element = document.querySelector(selector + '="' + id + '"');
    if (!element) {
      return;
    }
    element.textContent = value;
  }

  function setStatus(id, value) {
    var element = document.querySelector('[data-status="' + id + '"]');
    if (!element) {
      return;
    }
    element.textContent = value;
    element.className = "status status--" + value;
  }

  function shortTimestamp(value) {
    if (!value || typeof value !== "string") {
      return "—";
    }
    return value.slice(0, 19).replace("T", " ");
  }

  function applyModule(module) {
    setStatus(module.id, module.status_text);
    setText("[data-checked", module.id, shortTimestamp(module.last_checked));
    setText(
      "[data-response",
      module.id,
      module.response_time_ms === null || module.response_time_ms === undefined
        ? "—"
        : module.response_time_ms + " ms"
    );
    setText("[data-intent", module.id, module.intent);

    var error = document.querySelector('[data-error="' + module.id + '"]');
    if (module.last_error) {
      if (error) {
        error.textContent = module.last_error;
      }
    } else if (error) {
      error.textContent = "";
      error.hidden = true;
    }
  }

  // The summary chips come from the same payload: leaving them at their
  // first-render value while cards say "connected" is the page contradicting
  // itself, which reads as a status bug.
  function applyCounts(counts) {
    if (!counts) {
      return;
    }
    setText("[data-count", "total", counts.total + " modules");
    setText("[data-count", "enabled", counts.enabled + " enabled");
    setText("[data-count", "connected", counts.connected + " connected");
    setText("[data-count", "error", counts.error + " error");
  }

  function refresh() {
    fetch("/api/modules", { headers: { Accept: "application/json" } })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (payload) {
        if (!payload || !payload.modules) {
          return;
        }
        payload.modules.forEach(applyModule);
        applyCounts(payload.counts);
      })
      .catch(function () {
        // Runtime unavailable: keep showing the last rendered state.
      });
  }

  window.setInterval(refresh, POLL_INTERVAL_MS);
})();
