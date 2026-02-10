const API = '/api/v1';
let autoRefreshEnabled = true;
let refreshTimer = null;
let activeMonitorId = null;
let monitorDetailTimer = null;

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
    actions.push(`<button class="action-btn" onclick="incidentAction('${incident.id}', 'investigate')">Investigate</button>`);
    actions.push(`<button class="action-btn" onclick="incidentAction('${incident.id}', 'close')">Close</button>`);
  }
  if (incident.status === 'closed' || incident.status === 'resolved') {
    actions.push(`<button class="action-btn" onclick="incidentAction('${incident.id}', 'reopen')">Reopen</button>`);
  }
  return actions.join(' ');
}

async function incidentAction(incidentId, action) {
  try {
    await apiPost(`/incidents/${incidentId}/${action}`);
    showToast(`Incident ${action === 'close' ? 'closed' : action + 'd'}`);
    refreshIncidents();
    refreshStats();
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
      <div class="px-5 py-3 hover:bg-surface/50 transition">
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
