'use strict';

const API = 'http://localhost:3210';

// --- Tab routing ---
document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
  });
});

// --- Health check ---
async function checkStatus() {
  const dot = document.getElementById('status-dot');
  const txt = document.getElementById('status-text');
  try {
    const r = await fetch(`${API}/v1/providers`, { signal: AbortSignal.timeout(4000) });
    if (r.ok) {
      dot.className = 'status-dot online';
      txt.textContent = 'En ligne';
    } else {
      dot.className = 'status-dot error';
      txt.textContent = `Erreur ${r.status}`;
    }
  } catch {
    dot.className = 'status-dot error';
    txt.textContent = 'Hors ligne';
  }
}
checkStatus();
setInterval(checkStatus, 30000);

// --- Utilities ---
function loading() {
  return `<div class="loading"><div class="spinner"></div><span>Chargement…</span></div>`;
}
function error(msg) {
  return `<div class="error-msg">${msg}</div>`;
}
function empty(msg = 'Aucun résultat.') {
  return `<div class="empty">${msg}</div>`;
}

// --- Departures ---
document.getElementById('departures-form').addEventListener('submit', async e => {
  e.preventDefault();
  const line = document.getElementById('dep-line').value.trim();
  const stop = document.getElementById('dep-stop').value.trim();
  const dir  = document.getElementById('dep-direction').value.trim();
  const out  = document.getElementById('departures-results');

  if (!line || !stop) { out.innerHTML = error('Veuillez saisir une ligne et un arrêt.'); return; }

  out.innerHTML = loading();
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true;

  try {
    const params = new URLSearchParams({ line, stop });
    if (dir) params.set('direction', dir);
    const res = await fetch(`${API}/v1/departures?${params}`);
    const data = await res.json();
    if (!res.ok) { out.innerHTML = error(data.error || `Erreur ${res.status}`); return; }
    if (!data.length) { out.innerHTML = empty('Aucun départ trouvé pour cet arrêt.'); return; }
    out.innerHTML = data.map(renderDeparture).join('');
  } catch (err) {
    out.innerHTML = error('Impossible de contacter le serveur. Est-il démarré ?');
  } finally {
    btn.disabled = false;
  }
});

function renderDeparture(d) {
  const wait = d.waitMinutes != null ? d.waitMinutes : '—';
  const statusClass = d.status === 'ON_TIME' ? 'on-time' : d.status === 'DELAYED' ? 'delayed' : 'unknown';
  const statusLabel = d.status === 'ON_TIME' ? 'À l\'heure' : d.status === 'DELAYED' ? 'Retard' : d.status || '—';
  const meta = d.scheduledAt ? new Date(d.scheduledAt).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '';
  const pattern = d.servicePattern ? ` · ${d.servicePattern}` : '';
  return `
    <div class="departure-card">
      <div class="wait-badge">
        <div class="wait-num">${wait}</div>
        <div class="wait-unit">min</div>
      </div>
      <div class="departure-info">
        <div class="departure-dest">${esc(d.destination || '—')}</div>
        <div class="departure-meta">${meta}${pattern}</div>
      </div>
      <div class="status-pill ${statusClass}">${statusLabel}</div>
    </div>`;
}

// --- Incidents ---
document.getElementById('incidents-form').addEventListener('submit', async e => {
  e.preventDefault();
  const line = document.getElementById('inc-line').value.trim();
  const out  = document.getElementById('incidents-results');

  out.innerHTML = loading();
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true;

  try {
    const params = new URLSearchParams();
    if (line) params.set('line', line);
    const res = await fetch(`${API}/v1/incidents?${params}`);
    const data = await res.json();
    if (!res.ok) { out.innerHTML = error(data.error || `Erreur ${res.status}`); return; }
    if (!data.length) { out.innerHTML = empty('Aucune perturbation en cours. 🎉'); return; }
    out.innerHTML = data.map(renderIncident).join('');
  } catch {
    out.innerHTML = error('Impossible de contacter le serveur. Est-il démarré ?');
  } finally {
    btn.disabled = false;
  }
});

function renderIncident(inc) {
  const sev = (inc.severity || '').toLowerCase();
  const sevClass = ['critical','major','minor','info'].includes(sev) ? sev : 'info';
  const sevLabel = { critical: 'Critique', major: 'Majeur', minor: 'Mineur', info: 'Info' }[sevClass] || sev;
  const mode = inc.mode ? `<span>${esc(inc.mode)}</span>` : '';
  const status = inc.status ? `<span>${esc(inc.status)}</span>` : '';

  let badgeStyle = '';
  if (inc.color) badgeStyle = `style="background:${esc(inc.color)};color:#fff"`;

  const badgeContent = inc.iconUrl
    ? `<img src="${esc(inc.iconUrl)}" alt="${esc(inc.line)}" style="width:22px;height:22px;object-fit:contain" />`
    : esc(inc.line || '?');

  return `
    <div class="incident-card ${sevClass}">
      <div class="line-badge" ${badgeStyle}>${badgeContent}</div>
      <div class="incident-info">
        <div class="incident-title">
          Ligne ${esc(inc.line || '—')}
          <span class="severity-tag ${sevClass}">${sevLabel}</span>
        </div>
        <div class="incident-meta">${mode}${status}</div>
      </div>
    </div>`;
}

// --- Itinerary ---
document.getElementById('itinerary-form').addEventListener('submit', async e => {
  e.preventDefault();
  const from = document.getElementById('itin-from').value.trim();
  const to   = document.getElementById('itin-to').value.trim();
  const out  = document.getElementById('itinerary-results');

  if (!from || !to) { out.innerHTML = error('Veuillez saisir une adresse de départ et d\'arrivée.'); return; }

  out.innerHTML = loading();
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/v1/itinerary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from, to })
    });
    const data = await res.json();
    if (!res.ok) { out.innerHTML = error(data.error || `Erreur ${res.status}`); return; }
    if (!data.length) { out.innerHTML = empty('Aucun itinéraire trouvé.'); return; }
    out.innerHTML = data.map(renderItinerary).join('');
  } catch {
    out.innerHTML = error('Impossible de contacter le serveur. Est-il démarré ?');
  } finally {
    btn.disabled = false;
  }
});

function renderItinerary(itin) {
  const dur = itin.durationMinutes != null ? `${itin.durationMinutes}<span> min</span>` : '—';
  const steps = (itin.steps || []).map(renderStep).join('');
  return `
    <div class="itin-card">
      <div class="itin-header">
        <div class="itin-duration">${dur}</div>
      </div>
      <div class="itin-steps">${steps}</div>
    </div>`;
}

const STEP_ICONS = {
  WALKING: '🚶',
  TRANSIT: '🚇',
  WAIT: '⏳',
  TRANSFER: '🔄',
};

function renderStep(step) {
  const isTransit = step.stepType === 'TRANSIT';
  const icon = STEP_ICONS[step.stepType] || '•';
  const label = step.transit
    ? `Ligne ${esc(step.transit.lineId || '')}${step.transit.directionId ? ' → ' + esc(step.transit.directionId) : ''}`
    : esc(step.stepType || '');
  const detail = step.durationMinutes != null ? `${step.durationMinutes} min` : '';
  return `
    <div class="itin-step">
      <div class="step-icon ${isTransit ? 'transit' : ''}">${icon}</div>
      <div class="step-content">
        <div class="step-label">${label}</div>
        ${detail ? `<div class="step-detail">${detail}</div>` : ''}
      </div>
    </div>`;
}

// --- Escape helper ---
function esc(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
