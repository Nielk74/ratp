'use strict';

// lib/browser.js
const { chromium } = require('playwright');

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
const WWW_URL = 'https://www.bonjour-ratp.fr';
const FALLBACK_CONFIG = {
  bffExternalUrl: 'https://bff.bonjour-ratp.fr',
  bffExternalApiKey: 'rHaqHU7laBW3WANbmWUwvrAOoLrdU8pC5aLLkS6e'
};
const CONFIG_TTL = 5 * 60 * 1000;
const MAX_RESTART_ATTEMPTS = 3;

let browser = null;
let browserCtx = null;
let proxyPage = null;
let config = null;
let configAt = 0;
let restartAttempts = 0;
let currentProxyUrl = null;
let restartPromise = null;

async function start(proxyUrl = null) {
  currentProxyUrl = proxyUrl;
  const launchOpts = {
    headless: true,
    args: ['--disable-gpu', '--disable-dev-shm-usage', '--no-first-run', '--no-default-browser-check']
  };
  if (proxyUrl) launchOpts.proxy = { server: proxyUrl };

  browser = await chromium.launch(launchOpts);
  browserCtx = await browser.newContext({
    userAgent: UA,
    locale: 'fr-FR',
    viewport: { width: 1920, height: 1080 }
  });
  proxyPage = await browserCtx.newPage();
  restartAttempts = 0;
  console.log('[browser] Started' + (proxyUrl ? ` via ${proxyUrl}` : ' (direct)'));

  await refreshConfig();
}

async function refreshConfig() {
  let tempPage = null;
  try {
    tempPage = await browserCtx.newPage();
    await tempPage.goto(WWW_URL, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await tempPage.waitForTimeout(800);
    const raw = await tempPage.evaluate(() => window.__CONFIG__ || null);
    if (raw && raw.bffExternalApiKey) {
      config = raw;
      configAt = Date.now();
      console.log('[browser] Config loaded, key:', raw.bffExternalApiKey.substring(0, 8) + '...');
      return;
    }
    console.warn('[browser] window.__CONFIG__ missing, using fallback');
  } catch (e) {
    console.error('[browser] Config refresh failed:', e.message);
  } finally {
    if (tempPage) await tempPage.close().catch(() => {});
  }
  if (!config) {
    config = { ...FALLBACK_CONFIG };
    configAt = Date.now();
  }
}

function getConfig() {
  if (Date.now() - configAt > CONFIG_TTL) {
    refreshConfig().catch(e => console.error('[browser] Background config refresh failed:', e.message));
  }
  return config || FALLBACK_CONFIG;
}

async function evaluate(fn, args) {
  if (!proxyPage) throw new Error('Browser not started — call browser.start() first');

  try {
    return await proxyPage.evaluate(fn, args);
  } catch (err) {
    const alive = browser && browser.isConnected() && !proxyPage.isClosed();
    if (!alive) {
      console.error('[browser] Page/browser died:', err.message);
      await restart();
      return await proxyPage.evaluate(fn, args);
    }
    throw err;
  }
}

async function restart() {
  if (restartPromise) return restartPromise;
  restartPromise = _doRestart().finally(() => { restartPromise = null; });
  return restartPromise;
}

async function _doRestart() {
  if (restartAttempts >= MAX_RESTART_ATTEMPTS) {
    throw new Error(`Browser restart limit (${MAX_RESTART_ATTEMPTS}) reached`);
  }
  restartAttempts++;
  const delay = Math.pow(2, restartAttempts) * 1000;
  console.error(`[browser] Restarting (attempt ${restartAttempts}/${MAX_RESTART_ATTEMPTS}) in ${delay}ms...`);
  await new Promise(r => setTimeout(r, delay));
  try { await browser.close(); } catch (e) { console.error('[browser] Close error during restart:', e.message); }
  browser = null; browserCtx = null; proxyPage = null;
  let nextProxy = currentProxyUrl;
  try {
    const proxy = require('./proxy');
    if (currentProxyUrl) proxy.markDead(currentProxyUrl);
    const next = proxy.getProxy();
    nextProxy = next ? next.url : null;
  } catch {}
  await start(nextProxy);
}

async function stop() {
  if (browser) {
    await browser.close().catch(() => {});
    browser = null;
    browserCtx = null;
    proxyPage = null;
  }
}

function getCurrentProxyUrl() { return currentProxyUrl; }

module.exports = { start, stop, evaluate, getConfig, refreshConfig, getCurrentProxyUrl };
