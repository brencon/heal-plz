const API = '/api/v1';
let autoRefreshEnabled = true;
let refreshTimer = null;
let activeMonitorId = null;
let monitorDetailTimer = null;
let activeIncidentId = null;
let incidentDetailTimer = null;

const PIPELINE_STAGES_FULL = [
  { key: 'open', label: 'Open' },
  { key: 'investigating', label: 'Investigating' },
  { key: 'root_cause_identified', label: 'RCA' },
  { key: 'fix_in_progress', label: 'Fixing' },
  { key: 'fix_pending_review', label: 'PR Review' },
  { key: 'fix_merged', label: 'Merged' },
  { key: 'verifying', label: 'Verifying' },
  { key: 'resolved', label: 'Resolved' },
];

const PIPELINE_STAGES_FIX_ONLY = [
  { key: 'open', label: 'Open' },
  { key: 'investigating', label: 'Investigating' },
  { key: 'root_cause_identified', label: 'RCA' },
  { key: 'fix_in_progress', label: 'Fixing' },
  { key: 'resolved', label: 'Resolved' },
];

const PIPELINE_STAGES_NO_CODE = [
  { key: 'open', label: 'Open' },
  { key: 'investigating', label: 'Investigating' },
  { key: 'root_cause_identified', label: 'RCA' },
  { key: 'resolved', label: 'Resolved' },
];

// --- API helpers ---

async function api(path, options = {}) {
  const resp = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

async function apiPost(path) {
  return api(path, { method: 'POST' });
}

// --- Toast notifications ---

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// --- Stats ---

async function refreshStats() {
  try {
    const data = await api('/dashboard/overview');
    document.getElementById('stat-repos').textContent = data.total_repositories;
    document.getElementById('stat-total-alerts').textContent = data.total_alerts;
    document.getElementById('stat-active-alerts').textContent = data.active_alerts;
    document.getElementById('stat-open-incidents').textContent = data.open_incidents;
    document.getElementById('stat-resolved').textContent = data.resolved_incidents;
    document.getElementById('stat-heal-rate').textContent =
      data.total_incidents > 0
        ? `${(data.auto_heal_success_rate * 100).toFixed(0)}%`
        : '-';

    const sev = data.active_alerts_by_severity;
    document.getElementById('sev-critical').textContent = `CRIT: ${sev.critical}`;
    document.getElementById('sev-high').textContent = `HIGH: ${sev.high}`;
    document.getElementById('sev-medium').textContent = `MED: ${sev.medium}`;
    document.getElementById('sev-low').textContent = `LOW: ${sev.low}`;
    document.getElementById('sev-info').textContent = `INFO: ${sev.info}`;
  } catch (e) {
    console.error('Failed to refresh stats:', e);
  }
}

// --- Monitors ---

async function refreshMonitors() {
  const container = document.getElementById('monitors-list');
  try {
    const monitors = await api('/monitors/');
    if (monitors.length === 0) {
      container.innerHTML = '<div class="px-5 py-6 text-center text-gray-500 text-sm">No monitors registered</div>';
      return;
    }

    container.innerHTML = monitors.map(m => {
      const typeLabel = m.monitor_type.replace(/_/g, ' ');
      const statusColor = m.status === 'active' ? 'emerald' : 'gray';
      const lastEvent = m.last_event_at ? timeAgo(m.last_event_at) : 'never';
      const isActive = activeMonitorId === m.id;
      return `
        <div class="px-5 py-2.5 flex items-center justify-between hover:bg-surface/50 cursor-pointer transition ${isActive ? 'bg-accent/10 border-l-2 border-accent' : ''}" onclick="showMonitorDetail('${m.id}', '${escapeHtml(m.name)}', '${typeLabel}', '${m.status}', ${m.error_count})">
          <div class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-${statusColor}-400"></div>
            <div>
              <div class="text-sm text-gray-200">${escapeHtml(m.name)}</div>
              <div class="text-xs text-gray-500">${typeLabel}</div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <div class="text-right">
              <div class="text-xs text-gray-400">${m.error_count} errors</div>
              <div class="text-xs text-gray-500">Last event: ${lastEvent}</div>
            </div>
            <div class="text-gray-600 text-xs">&rsaquo;</div>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = '<div class="px-5 py-6 text-center text-red-400 text-sm">Failed to load monitors</div>';
  }
}

// --- Monitor Detail ---

function showMonitorDetail(monitorId, name, type, status, errorCount) {
  activeMonitorId = monitorId;

  const panel = document.getElementById('monitor-detail');
  panel.classList.remove('hidden');

  document.getElementById('monitor-detail-name').textContent = name;
  document.getElementById('monitor-detail-meta').innerHTML = `
    <span>Type: <span class="text-gray-300">${type}</span></span>
    <span>Status: <span class="text-gray-300">${status}</span></span>
    <span>Errors: <span class="text-gray-300">${errorCount}</span></span>
  `;

  refreshMonitorEvents();
  refreshMonitors();

  if (monitorDetailTimer) clearInterval(monitorDetailTimer);
  monitorDetailTimer = setInterval(refreshMonitorEvents, 5000);
}

function closeMonitorDetail() {
  activeMonitorId = null;
  document.getElementById('monitor-detail').classList.add('hidden');
  if (monitorDetailTimer) {
    clearInterval(monitorDetailTimer);
    monitorDetailTimer = null;
  }
  refreshMonitors();
}

async function refreshMonitorEvents() {
  if (!activeMonitorId) return;

  const container = document.getElementById('monitor-detail-events');
  try {
    const events = await api(`/monitors/${activeMonitorId}/events?limit=50`);

    if (events.length === 0) {
      container.innerHTML = '<div class="px-5 py-8 text-center text-gray-500 text-sm">No events recorded yet</div>';
      return;
    }

    container.innerHTML = events.map(e => {
      const sevClass = e.severity === 'critical' || e.severity === 'error' ? 'red' : e.severity === 'warning' ? 'amber' : 'blue';
      const location = e.file_path ? `${e.file_path}${e.line_number ? ':' + e.line_number : ''}` : '';
      const linked = [];
      if (e.alert_id) linked.push('<span class="text-amber-400">Alert</span>');
      if (e.incident_id) linked.push('<span class="text-accent">Incident</span>');
      const linkedStr = linked.length > 0 ? ` &rarr; ${linked.join(' &rarr; ')}` : '';

      return `
        <div class="px-5 py-3 hover:bg-surface/50 transition">
          <div class="flex items-start gap-3">
            <div class="w-2 h-2 rounded-full bg-${sevClass}-400 mt-1.5 flex-shrink-0"></div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 mb-0.5">
                ${severityBadge(e.severity)}
                ${e.error_type ? `<span class="text-xs text-gray-300 font-mono">${escapeHtml(e.error_type)}</span>` : ''}
              </div>
              <div class="text-sm text-gray-200 break-words">${escapeHtml(e.error_message)}</div>
              <div class="text-xs text-gray-500 mt-0.5">
                ${location ? `<span class="font-mono">${escapeHtml(location)}</span> &middot; ` : ''}${timeAgo(e.created_at)}${linkedStr}
                ${e.branch ? ` &middot; <span class="text-gray-400">${escapeHtml(e.branch)}</span>` : ''}
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = '<div class="px-5 py-8 text-center text-red-400 text-sm">Failed to load events</div>';
  }
}

// --- Alerts ---

function severityBadge(severity) {
  return `<span class="badge badge-severity-${severity}">${severity}</span>`;
}

function statusBadge(status) {
  return `<span class="badge badge-status-${status}">${status.replace(/_/g, ' ')}</span>`;
}

function priorityBadge(priority) {
  return `<span class="badge badge-priority-${priority}">${priority.toUpperCase()}</span>`;
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr + 'Z').getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function renderAlertActions(alert) {
  const actions = [];
  if (alert.status === 'active') {
    actions.push(`<button class="action-btn" onclick="alertAction('${alert.id}', 'acknowledge')">Ack</button>`);
    actions.push(`<button class="action-btn" onclick="alertAction('${alert.id}', 'suppress')">Suppress</button>`);
  }
  if (alert.status !== 'resolved') {
    actions.push(`<button class="action-btn" onclick="alertAction('${alert.id}', 'resolve')">Resolve</button>`);
  }
  return actions.join(' ');
}

async function alertAction(alertId, action) {
  try {
    await apiPost(`/alerts/${alertId}/${action}`);
    showToast(`Alert ${action}d`);
    refreshAlerts();
    refreshStats();
  } catch (e) {
    showToast(`Failed to ${action} alert`, 'error');
  }
}

async function refreshAlerts() {
  const container = document.getElementById('alerts-list');
  const filter = document.getElementById('alert-filter').value;
  try {
    let path = '/alerts/?limit=20';
    if (filter) path += `&status_filter=${filter}`;
    const alerts = await api(path);

    if (alerts.length === 0) {
      container.innerHTML = '<div class="px-5 py-8 text-center text-gray-500 text-sm">No alerts found</div>';
      return;
    }

    container.innerHTML = alerts.map(a => `
      <div class="px-5 py-3 hover:bg-surface/50 transition">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 mb-1">
              ${severityBadge(a.severity)}
              ${statusBadge(a.status)}
              <span class="text-xs text-gray-500">${a.occurrence_count}x</span>
            </div>
            <div class="text-sm text-gray-200 truncate">${escapeHtml(a.title)}</div>
            <div class="text-xs text-gray-500 mt-0.5">
              ${a.source} &middot; ${timeAgo(a.last_seen_at)}
              ${a.incident_id ? ' &middot; <span class="text-accent">Incident linked</span>' : ''}
            </div>
          </div>
          <div class="flex gap-1 flex-shrink-0 pt-1">
            ${renderAlertActions(a)}
          </div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div class="px-5 py-8 text-center text-red-400 text-sm">Failed to load alerts</div>';
  }
}

// --- Incidents ---

function renderIncidentActions(incident) {
  const actions = [];
  if (incident.status === 'open') {
    actions.push(`<button class="action-btn" onclick="event.stopPropagation(); incidentAction('${incident.id}', 'investigate')">Investigate</button>`);
  }
  if (incident.status === 'closed' || incident.status === 'resolved') {
    actions.push(`<button class="action-btn" onclick="event.stopPropagation(); incidentAction('${incident.id}', 'reopen')">Reopen</button>`);
  }
  return actions.join(' ');
}

async function incidentAction(incidentId, action) {
  try {
    await apiPost(`/incidents/${incidentId}/${action}`);
    const labels = { close: 'closed', investigate: 'investigation started', heal: 'healing started', reopen: 'reopened' };
    showToast(`Incident ${labels[action] || action + 'd'}`);
    refreshIncidents();
    refreshStats();
    if (activeIncidentId === incidentId) refreshIncidentPipeline();
  } catch (e) {
    showToast(`Failed to ${action} incident`, 'error');
  }
}

async function refreshIncidents() {
  const container = document.getElementById('incidents-list');
  const filter = document.getElementById('incident-filter').value;
  try {
    let path = '/incidents/?limit=20';
    if (filter) path += `&status_filter=${filter}`;
    const incidents = await api(path);

    if (incidents.length === 0) {
      container.innerHTML = '<div class="px-5 py-8 text-center text-gray-500 text-sm">No incidents found</div>';
      return;
    }

    container.innerHTML = incidents.map(inc => `
      <div class="px-5 py-3 hover:bg-surface/50 cursor-pointer transition ${activeIncidentId === inc.id ? 'bg-accent/10 border-l-2 border-accent' : ''}" onclick="showIncidentDetail('${inc.id}')">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs font-mono text-gray-400">#${inc.incident_number}</span>
              ${priorityBadge(inc.priority)}
              ${statusBadge(inc.status)}
            </div>
            <div class="text-sm text-gray-200 truncate">${escapeHtml(inc.title)}</div>
            <div class="text-xs text-gray-500 mt-0.5">
              ${inc.event_count} event${inc.event_count !== 1 ? 's' : ''} &middot; ${timeAgo(inc.last_seen_at)}
            </div>
          </div>
          <div class="flex gap-1 flex-shrink-0 pt-1">
            ${renderIncidentActions(inc)}
          </div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div class="px-5 py-8 text-center text-red-400 text-sm">Failed to load incidents</div>';
  }
}

// --- Incident Detail ---

function showIncidentDetail(incidentId) {
  activeIncidentId = incidentId;
  document.getElementById('incident-detail').classList.remove('hidden');
  refreshIncidentPipeline();
  refreshIncidents();
  if (incidentDetailTimer) clearInterval(incidentDetailTimer);
  incidentDetailTimer = setInterval(refreshIncidentPipeline, 5000);
}

function closeIncidentDetail() {
  activeIncidentId = null;
  document.getElementById('incident-detail').classList.add('hidden');
  if (incidentDetailTimer) {
    clearInterval(incidentDetailTimer);
    incidentDetailTimer = null;
  }
  refreshIncidents();
}

async function refreshIncidentPipeline() {
  if (!activeIncidentId) return;
  try {
    const data = await api(`/incidents/${activeIncidentId}/pipeline`);
    const inc = data.incident;

    document.getElementById('incident-detail-title').textContent =
      `Incident #${inc.incident_number}: ${inc.title}`;

    document.getElementById('incident-detail-meta').innerHTML = `
      ${priorityBadge(inc.priority)}
      ${statusBadge(inc.status)}
      <span>${inc.event_count} event${inc.event_count !== 1 ? 's' : ''}</span>
      <span>First seen: ${timeAgo(inc.first_seen_at)}</span>
      <span>Last seen: ${timeAgo(inc.last_seen_at)}</span>
      ${inc.error_category ? `<span class="font-mono">${escapeHtml(inc.error_category)}</span>` : ''}
    `;

    renderPipelineStepper(inc.status, data.resolutions);
    renderInvestigationSection(data.investigation, data.evidence);
    renderRCASection(data.root_causes);
    renderResolutionSection(data.resolutions);
    renderVerificationSection(data.verifications);
    renderIncidentDetailActions(inc, data.resolutions);
  } catch (e) {
    console.error('Failed to refresh incident pipeline:', e);
  }
}

function renderPipelineStepper(status, resolutions) {
  const container = document.getElementById('incident-pipeline-stepper');
  const terminal = { wont_fix: true, closed: true };

  const hasPR = resolutions && resolutions.some(r => r.pr_url);
  const hasFix = resolutions && resolutions.length > 0;
  const isFixing = status === 'fix_in_progress';
  let stages;
  if (hasPR) stages = PIPELINE_STAGES_FULL;
  else if (hasFix || isFixing) stages = PIPELINE_STAGES_FIX_ONLY;
  else stages = PIPELINE_STAGES_NO_CODE;

  let currentIndex = stages.findIndex(s => s.key === status);
  if (currentIndex === -1) currentIndex = terminal[status] ? stages.length : 0;

  // If a fix was generated (no PR workflow), mark entire pipeline as complete
  const fixingIndex = stages.findIndex(s => s.key === 'fix_in_progress');
  if (fixingIndex !== -1 && hasFix && !hasPR && currentIndex <= fixingIndex) {
    currentIndex = stages.length;
  }

  const steps = stages.map((stage, i) => {
    let state = 'pending';
    let icon = '';
    if (i < currentIndex) { state = 'completed'; icon = '&#10003;'; }
    else if (i === currentIndex && stage.key === status) { state = 'active'; icon = '&#9679;'; }

    return `
      <div class="pipeline-step">
        <div class="pipeline-step-dot ${state}">${icon}</div>
        <div class="pipeline-step-label ${state}">${stage.label}</div>
      </div>
    `;
  }).join('');

  const fillPercent = currentIndex <= 0 ? 0
    : Math.min(100, (currentIndex / (stages.length - 1)) * 100);

  container.innerHTML = `
    <div class="pipeline-stepper">
      <div class="pipeline-connector">
        <div class="pipeline-connector-fill" style="width: ${fillPercent}%"></div>
      </div>
      ${steps}
    </div>
  `;
}

function renderInvestigationSection(investigation, evidence) {
  const container = document.getElementById('incident-investigation');
  if (!investigation) { container.classList.add('hidden'); return; }
  container.classList.remove('hidden');

  const confidenceClass = investigation.confidence_score >= 0.8 ? 'confidence-high'
    : investigation.confidence_score >= 0.5 ? 'confidence-medium' : 'confidence-low';
  const confidencePct = ((investigation.confidence_score || 0) * 100).toFixed(0);

  let evidenceHtml = '';
  if (evidence && evidence.length > 0) {
    evidenceHtml = `
      <div class="mt-3">
        <div class="text-xs text-gray-500 mb-2">Evidence (${evidence.length})</div>
        ${evidence.map(e => `
          <div class="detail-card mb-2">
            <div class="flex items-center gap-2 mb-1">
              <span class="badge-evidence">${e.evidence_type}</span>
              <span class="text-xs text-gray-300">${escapeHtml(e.title)}</span>
              ${e.file_path ? `<span class="text-xs text-gray-500 font-mono">${escapeHtml(e.file_path)}</span>` : ''}
            </div>
            <div class="text-xs text-gray-400 max-h-[80px] overflow-y-auto font-mono whitespace-pre-wrap">${escapeHtml(e.content.substring(0, 500))}${e.content.length > 500 ? '...' : ''}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  let affectedFilesHtml = '';
  if (investigation.affected_files && investigation.affected_files.length > 0) {
    affectedFilesHtml = `
      <div class="mt-2">
        <div class="text-xs text-gray-500 mb-1">Affected Files</div>
        <div class="flex flex-wrap gap-1">
          ${investigation.affected_files.map(f => `<span class="text-xs font-mono bg-surface px-2 py-0.5 rounded text-gray-300">${escapeHtml(f)}</span>`).join('')}
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="detail-section-header">Investigation</div>
    <div class="detail-card">
      <div class="flex items-center gap-3 mb-2">
        ${statusBadge(investigation.status)}
        ${investigation.duration_seconds ? `<span class="text-xs text-gray-500">Completed in ${investigation.duration_seconds.toFixed(1)}s</span>` : ''}
      </div>
      ${investigation.summary ? `<div class="text-sm text-gray-200 mb-2">${escapeHtml(investigation.summary)}</div>` : ''}
      <div class="flex items-center gap-2">
        <span class="text-xs text-gray-500">Confidence:</span>
        <div class="confidence-bar flex-1 max-w-[120px]">
          <div class="confidence-bar-fill ${confidenceClass}" style="width: ${confidencePct}%"></div>
        </div>
        <span class="text-xs text-gray-400">${confidencePct}%</span>
      </div>
      ${affectedFilesHtml}
    </div>
    ${evidenceHtml}
  `;
}

function renderRCASection(rootCauses) {
  const container = document.getElementById('incident-rca');
  if (!rootCauses || rootCauses.length === 0) { container.classList.add('hidden'); return; }
  container.classList.remove('hidden');

  const rc = rootCauses[0];
  const confidenceClass = rc.confidence_score >= 0.8 ? 'confidence-high'
    : rc.confidence_score >= 0.5 ? 'confidence-medium' : 'confidence-low';
  const confidencePct = (rc.confidence_score * 100).toFixed(0);

  container.innerHTML = `
    <div class="detail-section-header">Root Cause Analysis</div>
    <div class="detail-card">
      <div class="flex items-center gap-2 mb-2">
        <span class="badge-category">${rc.category.replace(/_/g, ' ')}</span>
        <div class="flex items-center gap-1">
          <div class="confidence-bar max-w-[80px]">
            <div class="confidence-bar-fill ${confidenceClass}" style="width: ${confidencePct}%"></div>
          </div>
          <span class="text-xs text-gray-400">${confidencePct}%</span>
        </div>
      </div>
      <div class="text-sm text-gray-200 mb-2">${escapeHtml(rc.description)}</div>
      ${rc.file_path ? `
        <div class="text-xs text-gray-500">
          <span class="font-mono text-gray-400">${escapeHtml(rc.file_path)}</span>
          ${rc.line_range_start ? `:${rc.line_range_start}${rc.line_range_end ? '-' + rc.line_range_end : ''}` : ''}
          ${rc.function_name ? ` &middot; <span class="text-gray-400">${escapeHtml(rc.function_name)}</span>` : ''}
        </div>
      ` : ''}
      ${rc.suggested_fix_description ? `
        <div class="mt-2 p-2 bg-emerald-900/20 border border-emerald-800/30 rounded text-xs text-emerald-300">
          <span class="font-semibold">Suggested fix:</span> ${escapeHtml(rc.suggested_fix_description)}
        </div>
      ` : ''}
    </div>
  `;
}

function renderResolutionSection(resolutions) {
  const container = document.getElementById('incident-resolution');
  if (!resolutions || resolutions.length === 0) { container.classList.add('hidden'); return; }
  container.classList.remove('hidden');

  const res = resolutions[0];
  const filesChanged = res.files_changed || [];

  container.innerHTML = `
    <div class="detail-section-header">Resolution</div>
    <div class="detail-card">
      <div class="flex items-center gap-2 mb-2">
        ${statusBadge(res.status)}
        <span class="badge-category">${res.strategy.replace(/_/g, ' ')}</span>
        <span class="text-xs text-gray-500">Attempt ${res.attempt_number} of ${res.max_attempts}</span>
      </div>
      ${res.fix_description ? `<div class="text-sm text-gray-200 mb-2">${escapeHtml(res.fix_description)}</div>` : ''}
      ${res.pr_url ? `
        <div class="mb-2">
          <a href="${res.pr_url}" target="_blank" rel="noopener" class="text-sm text-accent hover:text-accent-dim transition">
            PR #${res.pr_number} &rarr;
          </a>
          ${res.branch_name ? `<span class="text-xs text-gray-500 font-mono ml-2">${escapeHtml(res.branch_name)}</span>` : ''}
        </div>
      ` : ''}
      ${filesChanged.length > 0 ? `
        <div>
          <div class="text-xs text-gray-500 mb-1">Files changed (${filesChanged.length})</div>
          <div class="flex flex-wrap gap-1">
            ${filesChanged.map(f => `<span class="text-xs font-mono bg-surface px-2 py-0.5 rounded text-gray-300">${escapeHtml(typeof f === 'string' ? f : f.path || JSON.stringify(f))}</span>`).join('')}
          </div>
        </div>
      ` : ''}
      ${res.llm_model_used ? `
        <div class="text-xs text-gray-500 mt-2">
          Model: ${escapeHtml(res.llm_model_used)}
          ${res.llm_tokens_used ? ` &middot; ${res.llm_tokens_used} tokens` : ''}
        </div>
      ` : ''}
    </div>
  `;
}

function renderVerificationSection(verifications) {
  const container = document.getElementById('incident-verification');
  if (!verifications || verifications.length === 0) { container.classList.add('hidden'); return; }
  container.classList.remove('hidden');

  container.innerHTML = `
    <div class="detail-section-header">Verification</div>
    ${verifications.map(v => `
      <div class="detail-card mb-2">
        <div class="flex items-center gap-2">
          <span class="badge-verification-${v.result}">${v.result}</span>
          <span class="badge-evidence">${v.verification_type}</span>
          ${v.duration_seconds ? `<span class="text-xs text-gray-500">${v.duration_seconds.toFixed(2)}s</span>` : ''}
        </div>
        ${v.output ? `<div class="text-xs text-gray-400 mt-1 font-mono whitespace-pre-wrap max-h-[100px] overflow-y-auto">${escapeHtml(v.output)}</div>` : ''}
      </div>
    `).join('')}
  `;
}

function renderIncidentDetailActions(incident, resolutions) {
  const container = document.getElementById('incident-detail-actions');
  const hasFix = resolutions && resolutions.length > 0;
  const actions = [];
  if (incident.status === 'open') {
    actions.push(`<button class="action-btn" onclick="incidentAction('${incident.id}', 'investigate')">Investigate</button>`);
  }
  if (incident.status === 'root_cause_identified' && !hasFix) {
    actions.push(`<button class="action-btn" onclick="incidentAction('${incident.id}', 'heal')">Generate Fix</button>`);
  }
  if (incident.status !== 'closed' && incident.status !== 'resolved') {
    actions.push(`<button class="action-btn" onclick="incidentAction('${incident.id}', 'close')">Close</button>`);
  }
  if (incident.status === 'closed' || incident.status === 'resolved') {
    actions.push(`<button class="action-btn" onclick="incidentAction('${incident.id}', 'reopen')">Reopen</button>`);
  }
  container.innerHTML = actions.join('');
}

// --- Activity Feed ---

async function refreshActivity() {
  const container = document.getElementById('activity-feed');
  try {
    const [alerts, incidents] = await Promise.all([
      api('/alerts/?limit=10'),
      api('/incidents/?limit=10'),
    ]);

    const items = [];

    for (const a of alerts) {
      items.push({
        time: a.created_at,
        icon: 'alert',
        severity: a.severity,
        text: `Alert created: ${a.title}`,
        detail: `${a.source} &middot; ${a.severity} severity`,
      });
      if (a.status === 'escalated' && a.incident_id) {
        items.push({
          time: a.last_seen_at,
          icon: 'escalate',
          severity: a.severity,
          text: `Alert escalated to incident`,
          detail: `${a.title}`,
        });
      }
    }

    for (const inc of incidents) {
      items.push({
        time: inc.created_at,
        icon: 'incident',
        severity: null,
        text: `Incident #${inc.incident_number} created`,
        detail: `${inc.title} &middot; ${inc.priority.toUpperCase()}`,
      });
    }

    items.sort((a, b) => new Date(b.time) - new Date(a.time));

    if (items.length === 0) {
      container.innerHTML = '<div class="px-5 py-8 text-center text-gray-500 text-sm">No recent activity</div>';
      return;
    }

    const iconMap = {
      alert: '<div class="w-2 h-2 rounded-full bg-amber-400 mt-1.5"></div>',
      escalate: '<div class="w-2 h-2 rounded-full bg-red-400 mt-1.5"></div>',
      incident: '<div class="w-2 h-2 rounded-full bg-accent mt-1.5"></div>',
    };

    container.innerHTML = items.slice(0, 20).map(item => `
      <div class="px-5 py-2.5 flex items-start gap-3 hover:bg-surface/50 transition">
        ${iconMap[item.icon]}
        <div class="min-w-0 flex-1">
          <div class="text-sm text-gray-300">${escapeHtml(item.text)}</div>
          <div class="text-xs text-gray-500">${item.detail}</div>
        </div>
        <div class="text-xs text-gray-600 flex-shrink-0">${timeAgo(item.time)}</div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div class="px-5 py-8 text-center text-red-400 text-sm">Failed to load activity</div>';
  }
}

// --- Utilities ---

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// --- Refresh Control ---

async function refreshAll() {
  await Promise.all([refreshStats(), refreshMonitors(), refreshAlerts(), refreshIncidents(), refreshActivity()]);
}

function toggleAutoRefresh() {
  autoRefreshEnabled = !autoRefreshEnabled;
  const dot = document.getElementById('refresh-dot');
  if (autoRefreshEnabled) {
    dot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
    startAutoRefresh();
  } else {
    dot.className = 'w-2 h-2 rounded-full bg-gray-600';
    if (refreshTimer) clearInterval(refreshTimer);
  }
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshAll, 10000);
}

// --- Init ---

document.addEventListener('DOMContentLoaded', () => {
  refreshAll();
  startAutoRefresh();
});
