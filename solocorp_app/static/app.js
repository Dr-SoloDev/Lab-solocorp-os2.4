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

// Live dashboard: poll /api/live/status every 3s without a reload.
// Cosmetic only — the server-rendered HTML is the truth at open time, and a
// failed fetch keeps the last rendered state (fail-open, never clears).
// CSP: external file only, no inline script, no eval — textContent everywhere.
// Single-instance: the base layout loads this file on every page, and a
// back-forward revisit must not stack a second interval on the same window.
(function () {
  "use strict";

  if (!document.querySelector("[data-live]")) {
    return;
  }
  if (window.__solocorpLiveStarted) {
    return;
  }
  window.__solocorpLiveStarted = true;

  var POLL_INTERVAL_MS = 3000;

  function text(selector, value) {
    var element = document.querySelector(selector);
    if (!element) {
      return;
    }
    element.textContent = value;
  }

  function shortTimestamp(value) {
    if (!value || typeof value !== "string") {
      return "—";
    }
    return value.slice(0, 19).replace("T", " ");
  }

  function dash(value) {
    if (value === null || value === undefined || value === "") {
      return "—";
    }
    return String(value);
  }

  function applyChips(payload) {
    var modules = payload.modules || {};
    var queues = payload.queues || {};
    text(
      "[data-mod-total]",
      (modules.total === undefined ? "—" : modules.total) + " modules"
    );
    text(
      "[data-mod-connected]",
      (modules.connected === undefined ? "—" : modules.connected) + " connected"
    );
    text(
      "[data-mod-error]",
      (modules.error === undefined ? "—" : modules.error) + " error"
    );
    text("[data-queue-total]", "queue " + (payload.queue_total || 0));
    text("[data-queue-high]", "high " + (queues.high || 0));
    text("[data-queue-normal]", "normal " + (queues.normal || 0));
    text("[data-queue-dead]", "dead " + (queues.dead || 0));
    text("[data-provider-state]", "provider " + dash(payload.provider_state));
    text("[data-session-count]", (payload.session_count || 0) + " sessions");
  }

  function applyMeta(payload) {
    text("[data-live-updated]", shortTimestamp(payload.updated_at));
    text("[data-session-source]", dash(payload.session_source));
    var errorBox = document.querySelector("[data-session-error]");
    if (!errorBox) {
      return;
    }
    if (payload.session_error) {
      errorBox.textContent = payload.session_error;
    } else {
      errorBox.textContent = "";
    }
  }

  function applyQueue(payload) {
    var queues = payload.queues || {};
    text("[data-q-critical]", String(queues.critical || 0));
    text("[data-q-high]", String(queues.high || 0));
    text("[data-q-normal]", String(queues.normal || 0));
    text("[data-q-low]", String(queues.low || 0));
    text("[data-q-dead]", String(queues.dead || 0));
    text("[data-q-total]", String(payload.queue_total || 0));
  }

  function makeCell(row, value, mono) {
    var cell = document.createElement("td");
    if (mono) {
      cell.className = "mono";
    }
    cell.textContent = value;
    row.appendChild(cell);
    return cell;
  }

  function applySessions(payload) {
    var body = document.querySelector("[data-sessions-body]");
    if (!body) {
      return;
    }
    var sessions = payload.sessions || [];
    while (body.firstChild) {
      body.removeChild(body.firstChild);
    }
    var empty = document.querySelector("[data-sessions-empty]");
    var wrap = document.querySelector("[data-sessions-wrap]");
    if (!sessions.length) {
      if (empty) {
        empty.hidden = false;
      }
      if (wrap) {
        wrap.hidden = true;
      }
      return;
    }
    if (empty) {
      empty.hidden = true;
    }
    if (wrap) {
      wrap.hidden = false;
    }
    sessions.forEach(function (session) {
      var row = document.createElement("tr");
      var titleCell = document.createElement("td");
      var title = document.createElement("span");
      title.className = "mono";
      title.textContent = dash(session.title);
      var breakLine = document.createElement("br");
      var idLine = document.createElement("span");
      idLine.className = "muted small mono";
      idLine.textContent = dash(session.id);
      titleCell.appendChild(title);
      titleCell.appendChild(breakLine);
      titleCell.appendChild(idLine);
      row.appendChild(titleCell);
      makeCell(row, dash(session.agent), false);
      makeCell(row, dash(session.model), true);
      makeCell(
        row,
        session.tokens === null || session.tokens === undefined
          ? "—"
          : String(session.tokens),
        true
      );
      var statusCell = document.createElement("td");
      var pill = document.createElement("span");
      pill.className = "status status--" + (session.outcome || "disabled");
      pill.textContent = dash(session.outcome);
      statusCell.appendChild(pill);
      row.appendChild(statusCell);
      makeCell(
        row,
        session.time ? shortTimestamp(session.time) : "—",
        true
      );
      body.appendChild(row);
    });
  }

  function applyModules(payload) {
    var states = payload.module_states || [];
    states.forEach(function (module) {
      var element = document.querySelector(
        '[data-live-module="' + module.id + '"]'
      );
      if (!element) {
        return;
      }
      element.textContent = module.status_text;
      element.className = "status status--" + module.status_text;
    });
  }

  function refresh() {
    fetch("/api/live/status", { headers: { Accept: "application/json" } })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (payload) {
        if (!payload) {
          return;
        }
        applyChips(payload);
        applyMeta(payload);
        applyQueue(payload);
        applySessions(payload);
        applyModules(payload);
      })
      .catch(function () {
        // Fetch failed: keep the last rendered state on screen.
      });
  }

  window.setInterval(refresh, POLL_INTERVAL_MS);
})();
