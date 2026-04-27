// tests/playwright/global-setup.js
// Starts the backend server if it's not already running, then waits for healthcheck.

const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3210;
const PID_FILE = path.join(__dirname, '.server.pid');
const BASE_URL = `http://localhost:${PORT}`;
const HEALTH_ENDPOINT = `${BASE_URL}/api/test`;
const MAX_STARTUP_MS = 120_000;
const POLL_INTERVAL_MS = 5_000;

async function healthCheck() {
  return new Promise((resolve) => {
    const req = http.get(HEALTH_ENDPOINT, { timeout: 5000 }, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => resolve(res.statusCode === 200));
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForHealth() {
  const deadline = Date.now() + MAX_STARTUP_MS;
  while (Date.now() < deadline) {
    const ok = await healthCheck();
    if (ok) return true;
    const remaining = Math.round((deadline - Date.now()) / 1000);
    console.log(`[global-setup] Waiting for server health... (${remaining}s remaining)`);
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
  return false;
}

function startServer() {
  console.log(`[global-setup] Starting backend server on port ${PORT}...`);
  console.log('[global-setup] This may take several minutes (proxy pool testing)...');

  const child = spawn('node', ['server.js'], {
    cwd: path.resolve(__dirname, '../../'),
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PORT: String(PORT) },
    windowsHide: true,
  });

  if (child.pid) {
    fs.writeFileSync(PID_FILE, String(child.pid));
    console.log(`[global-setup] Server PID: ${child.pid}`);
  }

  let stdoutData = '';
  let stderrData = '';

  child.stdout.on('data', (data) => {
    stdoutData += data.toString();
    const lines = data.toString().trim().split('\n');
    for (const line of lines) {
      if (line.trim()) console.log(`[server] ${line.trim()}`);
    }
  });

  child.stderr.on('data', (data) => {
    stderrData += data.toString();
    const lines = data.toString().trim().split('\n');
    for (const line of lines) {
      if (line.trim()) console.error(`[server ERR] ${line.trim()}`);
    }
  });

  child.on('exit', (code, signal) => {
    console.log(`[global-setup] Server process exited (code=${code}, signal=${signal})`);
    if (stdoutData) {
      console.log(`[global-setup] Server stdout:\n${stdoutData.trim()}`);
    }
    if (stderrData) {
      console.error(`[global-setup] Server stderr:\n${stderrData.trim()}`);
    }
    if (fs.existsSync(PID_FILE)) fs.unlinkSync(PID_FILE);
  });

  child.on('error', (err) => {
    console.error(`[global-setup] Spawn error: ${err.message}`);
  });

  return child;
}

/**
 * Global setup: ensure backend is running before tests execute.
 */
module.exports = async function globalSetup() {
  const alreadyRunning = await healthCheck();
  if (alreadyRunning) {
    console.log('[global-setup] Backend is already running — skipping startup.');
    return;
  }

  startServer();

  const healthy = await waitForHealth();
  if (!healthy) {
    const msg = [
      `Backend did not become healthy within ${MAX_STARTUP_MS / 1000}s.`,
      '',
      'The server requires working SOCKS5 proxies to start. Proxy pool testing can take several minutes.',
      '',
      'To speed up testing, start the server manually first:',
      '  node server.js',
      '  npm run test:e2e',
    ].join('\n');
    throw new Error(msg);
  }

  console.log('[global-setup] Backend is healthy and ready.');
};
