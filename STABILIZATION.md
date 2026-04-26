# Stabilization Plan — RATP BFF Project

> **Goal**: Make the project reliable, robust, and crash-free under normal operation.

---

## 🔴 Critical Stability Fixes

### 1. Silent Error Swallowing
**Location**: `server.js:181,188`
**Problem**: Empty `catch (e) {}` blocks hide navigation failures and config extraction errors, making the app fail silently with broken state.
**Fix**: Log errors to console and set fallback defaults explicitly.

### 2. No Graceful Shutdown
**Location**: `server.js` (entire file)
**Problem**: No `SIGTERM`/`SIGINT` handlers. Browsers are never closed on exit, leaving orphaned Chrome processes on Windows.
**Fix**: Add shutdown handlers that close both `configBrowser` and `proxyBrowser`, then exit cleanly.

### 3. Race Condition on Startup
**Location**: `server.js:313-321`
**Problem**: Server starts listening before `startup()` completes. First request may hit the proxy before the browser is ready.
**Fix**: Wait for `startup()` to resolve before calling `server.listen()`.

---

## 🟠 Reliability Improvements

### 4. Missing Required Headers on Proxy
**Location**: `server.js:56-69`
**Problem**: Proxy forwards requests without injecting `x-client-platform`, `x-client-version`, etc. — headers the API docs mark as required.
**Fix**: Inject mandatory BFF headers automatically.

### 5. Deprecated `url` Module
**Location**: `server.js:52,227`
**Problem**: Uses `require('url').parse()` — deprecated since Node 11, removed in later versions.
**Fix**: Replace with native `URL` and `URLSearchParams`.

### 6. Open Proxy Vulnerability
**Location**: `server.js:50-125`
**Problem**: Proxy accepts any URL from the query parameter with no validation — can be exploited to proxy arbitrary traffic.
**Fix**: Whitelist allowed domains to `*.bonjour-ratp.fr`.

---

## 🟡 Resource Management

### 7. Duplicate Browser Instances
**Location**: `server.js`
**Problem**: Two separate Chromium browsers (`configBrowser` + `proxyBrowser`) run simultaneously, doubling memory usage.
**Fix**: Reuse a single browser instance for both config extraction and proxying.

### 8. No `.gitignore`
**Problem**: `node_modules/` and `captured-bundles.json` are tracked.
**Fix**: Add `.gitignore` with standard Node.js patterns + project artifacts.

---

## 📋 Execution Order

1. Fix silent errors → graceful shutdown → race condition
2. Add required headers → domain whitelist → replace deprecated API
3. Single browser → `.gitignore`

**Estimated effort**: ~30 min total. No API changes, no breaking changes.
