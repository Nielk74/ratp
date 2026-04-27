// tests/playwright/global-teardown.js
// Stops the backend server if we started it during global-setup.

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

const PORT = process.env.PORT || 3210;
const PID_FILE = path.join(__dirname, '.server.pid');

/**
 * Check if the server is still running.
 */
function isServerRunning() {
  return new Promise((resolve) => {
    const req = http.get(`http://localhost:${PORT}/api/test`, { timeout: 3000 }, (res) => {
      res.resume();
      res.on('end', () => resolve(res.statusCode === 200));
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Stop the server by sending SIGTERM.
 */
async function stopServer() {
  if (!fs.existsSync(PID_FILE)) {
    console.log('[global-teardown] No PID file — server was not started by us.');
    return;
  }

  const pid = parseInt(fs.readFileSync(PID_FILE, 'utf8').trim(), 10);
  if (!pid || isNaN(pid)) {
    console.log('[global-teardown] Invalid PID in file — skipping teardown.');
    fs.unlinkSync(PID_FILE);
    return;
  }

  console.log(`[global-teardown] Stopping backend server (PID ${pid})...`);
  try {
    process.kill(pid, 'SIGTERM');
  } catch {
    console.log(`[global-teardown] Process ${pid} already exited.`);
  }
  fs.unlinkSync(PID_FILE);
}

/** @type {import('@playwright/test').FullConfig} */
module.exports = async function globalTeardown() {
  await stopServer();
  console.log('[global-teardown] Done.');
};
