// Live dashboard poller (PR2.1) — polls /api/live/status every 3s.
// Loads BEFORE deferred app.js (script tag lives in live.html content, app.js
// is deferred at the end of body), so claiming the single-instance flag here
// makes app.js skip its own live poller — exactly one poller per page.
// Cosmetic only: server-rendered HTML is the truth at open time, a failed
// fetch keeps the last rendered state (fail-open, never clears).
// CSP: external file only, no inline script, no eval — textContent everywhere.
(function () {
  "use strict";

  if (!document.querySelector("[data-live]")) {
    return;
  }
  if (window.__solocorpLiveStarted) {
    return;
  }
  window.__solocorpLiveStarted = true;

  var LIVE_POLL_MS = 3000;
  var FETCH_TIMEOUT_MS = 2500;
  var BACKOFF_MAX_MS = 30000;
  var backoffMs = LIVE_POLL_MS;
  var timer = null;
  var inFlight = null;

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
    var tasks = payload.tasks_summary || {};
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
    text("[data-tasks-total]", "tasks " + (tasks.total || 0));
  }

  function applyMeta(payload) {
    text("[data-live-updated]", shortTimestamp(payload.updated_at));
    text("[data-session-source]", dash(payload.session_source));
    text("[data-session-source-badge]", dash(payload.session_source));
    text("[data-queue-source]", dash(payload.queue_source || "empty"));
    var queueErrorBox = document.querySelector("[data-queue-error]");
    if (queueErrorBox) {
      queueErrorBox.textContent = payload.queue_error || "";
    }
    text("[data-tasks-source]", dash(payload.tasks_source || "app-tasks"));
    text("[data-cache-hit]", payload.cache_hit ? "cache" : "fresh");
    var dot = document.querySelector("[data-live-dot]");
    if (dot) {
      dot.textContent = payload.cache_hit
        ? "● live · 3s · cache"
        : "● live · 3s";
    }
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

  function applyTasks(payload) {
    // Product v1.0: tasks_summary = {total, by_status, updated_at}.
    // Render every status the server reports; zero the known lifecycle
    // slots when absent so a resolved queue clears on screen.
    var summary = payload.tasks_summary || {};
    var byStatus = summary.by_status || {};
    text("[data-t-total]", String(summary.total || 0));
    var known = ["pending", "running", "completed", "failed", "cancelled"];
    known.forEach(function (name) {
      var element = document.querySelector("[data-t-" + name + "]");
      if (element) {
        element.textContent = String(byStatus[name] || 0);
      }
    });
    Object.keys(byStatus).forEach(function (name) {
      if (name === "total" || name === "updated_at") {
        return;
      }
      var element = document.querySelector("[data-t-" + name + "]");
      if (element) {
        element.textContent = String(byStatus[name] || 0);
      }
    });
  }

  function applyDegraded(payload) {
    // Product v1.0 §2.3: UI uses this one field for the yellow/red badge.
    var badge = document.querySelector("[data-degraded]");
    if (badge) {
      badge.textContent = payload.degraded ? "degraded" : "ok";
      badge.className =
        "chip " + (payload.degraded ? "chip--warn" : "chip--ok");
    }
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
    var bodies = document.querySelectorAll("[data-sessions-body]");
    if (!bodies.length) {
      return;
    }
    var sessions = payload.sessions || [];
    var empty = document.querySelector("[data-sessions-empty]");
    var wrap = document.querySelector("[data-sessions-wrap]");
    if (!sessions.length) {
      if (empty) {
        empty.hidden = false;
      }
      if (wrap) {
        wrap.hidden = true;
      }
      bodies.forEach(function (body) {
        while (body.firstChild) {
          body.removeChild(body.firstChild);
        }
      });
      return;
    }
    if (empty) {
      empty.hidden = true;
    }
    if (wrap) {
      wrap.hidden = false;
    }
    bodies.forEach(function (body) {
      while (body.firstChild) {
        body.removeChild(body.firstChild);
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
        makeCell(row, session.time ? shortTimestamp(session.time) : "—", true);
        body.appendChild(row);
      });
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

  function scheduleNext(delayMs) {
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
    timer = window.setTimeout(tick, delayMs);
  }

  function onSuccess() {
    backoffMs = LIVE_POLL_MS;
    scheduleNext(LIVE_POLL_MS);
  }

  function onFailure() {
    // Exponential backoff 3s → 6s → 12s → … → 30s max + jitter ±500ms.
    backoffMs = Math.min(backoffMs * 2, BACKOFF_MAX_MS);
    var jitter = Math.floor(Math.random() * 1000) - 500;
    scheduleNext(Math.max(1000, backoffMs + jitter));
  }

  function tick() {
    if (document.visibilityState === "hidden") {
      // Tab hidden: skip this round, retry on the base interval.
      scheduleNext(LIVE_POLL_MS);
      return;
    }
    if (inFlight) {
      return;
    }
    var controller = null;
    var timeoutId = null;
    try {
      controller = new AbortController();
    } catch (e) {
      controller = null;
    }
    var options = { headers: { Accept: "application/json" } };
    if (controller) {
      options.signal = controller.signal;
      timeoutId = window.setTimeout(function () {
        try {
          controller.abort();
        } catch (e) {
          /* abort is best-effort */
        }
      }, FETCH_TIMEOUT_MS);
    }
    inFlight = true;
    fetch("/api/live/status", options)
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (payload) {
        if (!payload) {
          onFailure();
          return;
        }
        applyChips(payload);
        applyMeta(payload);
        applyQueue(payload);
        applyTasks(payload);
        applyDegraded(payload);
        applySessions(payload);
        applyModules(payload);
        onSuccess();
      })
      .catch(function () {
        // Fetch failed: keep the last rendered state on screen.
        onFailure();
      })
      .then(function () {
        inFlight = false;
        if (timeoutId) {
          window.clearTimeout(timeoutId);
        }
      });
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      backoffMs = LIVE_POLL_MS;
      scheduleNext(0);
    }
  });
  window.addEventListener("pagehide", function () {
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
  });

  scheduleNext(0);
})();
