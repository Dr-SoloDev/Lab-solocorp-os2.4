/**
 * SoloCorp OS Dashboard — JavaScript
 *
 * Fetches all dashboard data from the FastAPI backend every 10 seconds,
 * renders a dark-themed single-page dashboard with governance, agent,
 * pipeline, and monitoring panels.
 */

/* ═══════════════════════════════════════════════════════════════════════════
   State & Config
   ═══════════════════════════════════════════════════════════════════════════ */

const REFRESH_INTERVAL = 10000; // 10 seconds
const API_BASE = window.location.origin;

let state = {
  health: null,
  adrs: null,
  rfcs: null,
  guards: null,
  agents: null,
  pipeline: null,
  metrics: null,
};

let refreshTimer = null;

/* ═══════════════════════════════════════════════════════════════════════════
   API Helpers
   ═══════════════════════════════════════════════════════════════════════════ */

async function fetchJSON(endpoint) {
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) throw new Error(`GET ${endpoint} → ${res.status}`);
  return res.json();
}

async function postJSON(endpoint, body = {}) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${endpoint} → ${res.status}`);
  return res.json();
}

/* ═══════════════════════════════════════════════════════════════════════════
   Formatting Helpers
   ═══════════════════════════════════════════════════════════════════════════ */

function timeAgo(isoStr) {
  if (!isoStr) return '';
  const then = new Date(isoStr);
  const now = new Date();
  const seconds = Math.floor((now - then) / 1000);
  if (seconds < 5) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return then.toLocaleDateString();
}

function shortTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function eventIcon(eventType) {
  const e = (eventType || '').toLowerCase();
  if (e.includes('adr')) return '📐';
  if (e.includes('rfc')) return '📋';
  if (e.includes('guard')) return '🛡️';
  if (e.includes('ao_agent') || e.includes('ao')) return '🤖';
  if (e.includes('handoff')) return '🔀';
  if (e.includes('artifact')) return '📦';
  if (e.includes('governance')) return '⚖️';
  if (e.includes('agent')) return '🧠';
  return '📌';
}

function eventIconClass(eventType) {
  const e = (eventType || '').toLowerCase();
  if (e.includes('adr')) return 'event-item__icon--adr';
  if (e.includes('rfc')) return 'event-item__icon--rfc';
  if (e.includes('guard')) return 'event-item__icon--guard';
  if (e.includes('ao') || e.includes('agent')) return 'event-item__icon--ao';
  if (e.includes('handoff')) return 'event-item__icon--handoff';
  return 'event-item__icon--default';
}

/* ═══════════════════════════════════════════════════════════════════════════
   Renderers
   ═══════════════════════════════════════════════════════════════════════════ */

function renderHealth() {
  const el = document.getElementById('health-indicator');
  if (!state.health) {
    el.innerHTML = `<span class="status-badge status-badge--error">
      <span class="status-dot status-dot--error"></span> Offline
    </span>`;
    return;
  }
  const isHealthy = state.health.status === 'ok';
  const badgeClass = isHealthy ? 'status-badge--ok' : 'status-badge--error';
  const dotClass = isHealthy ? 'status-dot--ok' : 'status-dot--error';
  el.innerHTML = `<span class="status-badge ${badgeClass}">
    <span class="status-dot ${dotClass}"></span> ${state.health.status}
  </span>`;
}

function renderGovernance() {
  const adrs = state.adrs?.items || [];
  const rfcs = state.rfcs?.items || [];
  const guards = state.guards?.items || [];

  document.getElementById('gov-adr-count').textContent = adrs.length;
  document.getElementById('gov-rfc-count').textContent = rfcs.length;
  document.getElementById('gov-guard-count').textContent = guards.length;

  // Recent artifacts list (mix all types, newest first)
  const allItems = [
    ...adrs.map(a => ({ ...a, type: 'ADR' })),
    ...rfcs.map(a => ({ ...a, type: 'RFC' })),
    ...guards.map(a => ({ ...a, type: 'Guard' })),
  ].slice(0, 8);

  const listEl = document.getElementById('gov-artifact-list');
  if (!allItems.length) {
    listEl.innerHTML = '<div class="event-item" style="color:var(--text-muted)">No governance artifacts found</div>';
    return;
  }

  listEl.innerHTML = allItems.map(a => {
    const iconType = a.type === 'ADR' ? 'event-item__icon--adr' : a.type === 'RFC' ? 'event-item__icon--rfc' : 'event-item__icon--guard';
    // DES-04: emoji wrapped in aria-hidden so screen readers skip it
    const icon = a.type === 'ADR' ? '<span aria-hidden="true">📐</span>' : a.type === 'RFC' ? '<span aria-hidden="true">📋</span>' : '<span aria-hidden="true">🛡️</span>';
    return `
      <div class="event-item">
        <div class="event-item__icon ${iconType}">${icon}</div>
        <div class="event-item__content">
          <div class="event-item__title">${a.title || a.id || a.name || ''}</div>
          <div class="event-item__detail">${a.id || a.name || ''} · ${a.status || 'proposed'}</div>
        </div>
        <div class="event-item__time">${a.date || a.added_at || ''}</div>
      </div>
    `;
  }).join('');
}

function renderAgents() {
  const agents = state.agents?.items || [];
  const gridEl = document.getElementById('agent-grid');
  const countEl = document.getElementById('agent-count');

  countEl.textContent = `${agents.length}/5`;

  if (!agents.length) {
    gridEl.innerHTML = '<div class="loading">No agents available</div>';
    return;
  }

  gridEl.innerHTML = agents.map(a => `
    <div class="agent-card" id="agent-card-${a.agent_id}" tabindex="0" role="article" aria-label="${a.display_name} agent">
      <div class="agent-card__name">${a.display_name}</div>
      <div class="agent-card__desc">${a.description || ''}</div>
      <div class="agent-card__actions">
        <span class="agent-card__badge">${a.agent_id}</span>
        <button class="btn btn--small btn--primary" onclick="runAgent('${a.agent_id}')" id="btn-run-${a.agent_id}" aria-busy="false">
          <span aria-hidden="true">▶</span> Run
        </button>
      </div>
    </div>
  `).join('');
}

async function runAgent(agentId) {
  const btn = document.getElementById(`btn-run-${agentId}`);
  if (!btn) return;

  btn.disabled = true;
  // DES-13: signal busy state to assistive technologies
  btn.setAttribute('aria-busy', 'true');
  btn.textContent = '⏳ Running...';

  try {
    const result = await postJSON(`/api/v1/agents/${agentId}/run`, {
      context: {
        task: `Execute ${agentId} agent — automated dashboard trigger`,
        project_id: 'dashboard',
      },
    });
    // DES-04: emoji in toast wrapped via showToast — kept plain text here, aria-hidden applied in toast role="alert"
    showToast(`Agent '${agentId}' — ${result.status} (trace: ${(result.trace_id || '').slice(0, 8)})`, 'success');
  } catch (err) {
    showToast(`Agent '${agentId}' failed: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    // DES-13: clear busy state once execution completes
    btn.setAttribute('aria-busy', 'false');
    btn.textContent = '▶ Run';
  }
}

function renderPipeline() {
  const projects = state.pipeline || [];
  const totalEl = document.getElementById('pipeline-total');
  const listEl = document.getElementById('pipeline-project-list');

  totalEl.textContent = `${projects.length} total`;

  if (!projects.length) {
    listEl.innerHTML = '<div class="loading">No projects in pipeline</div>';
    return;
  }

  listEl.innerHTML = projects.map(p => {
    const phases = ['spec', 'design', 'arch', 'dev', 'qa', 'deploy'];
    const barsHTML = phases.map(ph => {
      const status = (p.phases && p.phases[ph]?.status) || p.phases?.[ph] || 'pending';
      const cls = status === 'done' ? 'done' : status === 'in_progress' ? 'active' : status === 'failed' ? 'failed' : 'pending';
      return `<div class="pipeline-phase pipeline-phase--${cls}"></div>`;
    }).join('');

    const labelsHTML = phases.map(ph => {
      const status = (p.phases && p.phases[ph]?.status) || p.phases?.[ph] || 'pending';
      const active = status === 'in_progress' ? ' active' : '';
      return `<span class="${active}">${ph}</span>`;
    }).join('');

    return `
      <div class="project-item">
        <div class="project-item__info">
          <div class="project-item__name">${p.name || p.project_id}</div>
          <div class="project-item__meta">${p.status} · Updated ${timeAgo(p.updated_at)}</div>
        </div>
        <div class="project-item__progress" style="flex:1;margin:0 1rem;">
          <div class="pipeline-phase-bar">${barsHTML}</div>
          <div class="pipeline-labels">${labelsHTML}</div>
        </div>
        <div class="project-item__progress">
          <div class="project-item__pct">${p.progress_pct}%</div>
          <div class="project-item__phase">${p.phase}</div>
        </div>
      </div>
    `;
  }).join('');
}

function renderMonitoring() {
  const m = state.metrics;
  if (!m) return;

  document.getElementById('mon-active-projects').textContent = m.active_projects ?? 0;
  document.getElementById('mon-total-queued').textContent = m.queued_messages ?? 0;

  // Queue breakdown by priority
  const q = m.queued_by_priority || {};
  document.getElementById('mon-queue-critical').textContent = q.critical ?? 0;
  document.getElementById('mon-queue-high').textContent = q.high ?? 0;
  document.getElementById('mon-queue-normal').textContent = q.normal ?? 0;
  document.getElementById('mon-queue-low').textContent = q.low ?? 0;

  // Recent events — not available from metrics directly,
  // show health component status instead
  const components = state.health?.components || {};
  const compEl = document.getElementById('event-log-content');

  const compEntries = [];
  for (const [name, comp] of Object.entries(components)) {
    const st = comp.status || 'unknown';
    // DES-04: emoji wrapped in aria-hidden
    const statusIcon = st === 'ok' ? '<span aria-hidden="true">✅</span>' : st === 'not_configured' ? '<span aria-hidden="true">⚠️</span>' : '<span aria-hidden="true">❌</span>';
    let detail = '';
    if (name === 'gov_dir') {
      detail = `${comp.adr_count || 0} ADRs, ${comp.rfc_count || 0} RFCs`;
    } else if (name === 'central_bus') {
      detail = `${comp.message_count || 0} messages`;
    } else if (name === 'ao_cli') {
      detail = comp.path || 'not configured';
    }
    compEntries.push({ name, status: st, icon: statusIcon, detail });
  }

  if (!compEntries.length) {
    compEl.innerHTML = '<div class="event-item" style="color:var(--text-muted)">No data available</div>';
    return;
  }

  compEl.innerHTML = compEntries.map(c => `
    <div class="event-item">
      <div class="event-item__icon event-item__icon--default">${c.icon}</div>
      <div class="event-item__content">
        <div class="event-item__title">${c.name}</div>
        <div class="event-item__detail">${c.detail || c.status}</div>
      </div>
      <div class="event-item__time" style="color:${c.status === 'ok' ? 'var(--success)' : c.status === 'not_configured' ? 'var(--warning)' : 'var(--danger)'}">${c.status}</div>
    </div>
  `).join('');
}

/* ═══════════════════════════════════════════════════════════════════════════
   Toast
   ═══════════════════════════════════════════════════════════════════════════ */

function showToast(message, type = 'info') {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    // DES-08: role="alert" makes screen readers announce the toast immediately
    toast.setAttribute('role', 'alert');
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = `toast toast--${type} toast--visible`;

  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => {
    toast.classList.remove('toast--visible');
  }, 4000);
}

/* ═══════════════════════════════════════════════════════════════════════════
   Refresh
   ═══════════════════════════════════════════════════════════════════════════ */

async function refreshAll() {
  const spinner = document.getElementById('refresh-spinner');
  const statusEl = document.getElementById('refresh-status');
  if (spinner) spinner.style.display = 'inline-block';

  // Fetch all endpoints in parallel
  const results = await Promise.allSettled([
    fetchJSON('/api/v1/health'),
    fetchJSON('/api/v1/gov/adrs'),
    fetchJSON('/api/v1/gov/rfcs'),
    fetchJSON('/api/v1/gov/guards'),
    fetchJSON('/api/v1/agents'),
    fetchJSON('/api/v1/pipeline/status'),
    fetchJSON('/api/v1/metrics'),
  ]);

  const labels = ['health', 'adrs', 'rfcs', 'guards', 'agents', 'pipeline', 'metrics'];
  results.forEach((r, i) => {
    state[labels[i]] = r.status === 'fulfilled' ? r.value : null;
  });

  renderHealth();
  renderGovernance();
  renderAgents();
  renderPipeline();
  renderMonitoring();

  if (statusEl) {
    const failed = results.filter(r => r.status === 'rejected').length;
    statusEl.textContent = failed
      ? `${new Date().toLocaleTimeString()} (${failed} failed)`
      : `Updated ${new Date().toLocaleTimeString()}`;
    statusEl.style.color = failed ? 'var(--warning)' : '';
  }

  if (spinner) spinner.style.display = 'none';
}

/* ═══════════════════════════════════════════════════════════════════════════
   Init
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  refreshAll();
  refreshTimer = setInterval(refreshAll, REFRESH_INTERVAL);
});
