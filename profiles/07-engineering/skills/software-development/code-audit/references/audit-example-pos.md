# Example Audit Output — Secondhand POS

**Source:** Session 2026-06-18, audit by คุณวุฒิ (Architecture) via delegate_task
**Repo:** `/home/drsolodev/projects/secondhand-pos/code/`
**Stack:** PHP 8.x (vanilla) + MySQL 8.0 + Docker

This reference shows a real audit output you can pattern-match when writing your own.

---

## Executive Summary

| Severity | Count | Key Impact |
|----------|-------|-----------|
| 🔴 Critical | 5 | Auth bypass, data leak, arbitrary SQL execution |
| 🟠 High | 8 | Missing role checks, XSS, weak crypto, brute-force exposure |
| 🟡 Medium | 6 | Race conditions, info disclosure, duplicate migrations |
| 🔵 Low | 4 | Logging gaps, cosmetic issues, missing headers |

**Risk Score: 72/100 (High)**

---

## Finding Examples (by severity)

### 🔴 CRITICAL: S-03 — `escapeHtml()` Function Is Completely Broken

**Location:** `common.js:133-135`

```javascript
function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g,"\\// Format currencyamp;")   // ← BROKEN
    .replace(/</g,"\\// Format currencylt;")
    .replace(/>/g,"\\// Format currencygt;")
    .replace(/\\"/g,"\\// Format currencyquot;\"");
}
```

**Impact:** All XSS protection in the frontend is non-functional. Any stored XSS (seller name, notes) will execute in the admin panel. Stored JWT tokens are exfiltratable.

**Recommendation:** Replace with `textContent` approach:
```javascript
function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}
```

---

### 🟠 HIGH: H-03 — JWT Token Stored in localStorage

**Location:** `login.js:37-38`, `common.js:3-7`

```javascript
localStorage.setItem('posToken', data.data.token);
```

**Impact:** Any XSS vulnerability immediately leaks the JWT token. Complete account takeover via XSS.

**Recommendation:** Use `HttpOnly` + `Secure` + `SameSite=Strict` cookies instead. Implement token refresh with short-lived access tokens (15 min) and long-lived refresh tokens (7 days).

---

### 🟡 MEDIUM: M-01 — No Blacklist Seller Check on Purchase Order Creation

**Location:** `PurchaseOrdersController.php:77-141`

**Description:** `createPurchaseOrder()` does not verify if the seller is blacklisted before creating the PO.

**Impact:** Business can continue purchasing from blacklisted sellers, exposing to legal liability.

**Recommendation:** Add `$sellerModel->getById($sellerId)` check. If `is_blacklisted === 1`, reject.

---

### 🔵 LOW: L-03 — Missing HTTP Security Headers

**Location:** `apache-config.conf`

**Description:** No `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`.

**Recommendation:** Add via `Header always set ...` in Apache config.

---

## Quick Wins

| # | Issue | Fix | Time |
|---|-------|-----|------|
| 1 | `escapeHtml()` broken | Replace with proper implementation | 5 min |
| 2 | `createPurchaseOrder()` missing `requireAuth()` | Add `$this->requireAuth(['admin', 'manager'])` | 2 min |
| 3 | Uploads directory no `.htaccess` | Add `Deny from all` | 1 min |
| 4 | Duplicate migrations directory | Remove one directory | 1 min |
| 5 | MySQL root password in docker-compose | Move to `.env` reference | 5 min |

## Priority Fix Order

1. **[Critical] S-03**: Fix `escapeHtml()` — XSS protection zero → fixes ALL frontend XSS
2. **[Critical] S-02**: Add `requireAuth()` to `createPurchaseOrder()` — direct auth bypass
3. **[Critical] S-01**: Add `requireAuth()` to ReportsController — privilege escalation
4. **[Critical] S-04**: Rotate JWT secret — complete auth compromise
5. **[Critical] S-05**: Harden BackupService restore — arbitrary SQL execution
6. **[High] H-01**: Fix PhotoUploadController auth — public upload endpoint
7. **[High] H-02**: Add rate limiting to login — brute-force prevention
8. **[High] H-03**: Move JWT from localStorage to HttpOnly cookies
9. **[High] H-05**: Encrypt seller ID card images at rest — PDPA compliance

## Compliance Checklist

| Requirement | Status | Issue |
|-------------|--------|-------|
| 👤 Identity in reports | ❌ Reports accessible without role check | S-01 |
| 🧾 Audit trail for critical actions | ⚠️ Partial — some actions not logged | M-05 |
| 🔒 PII storage (ID cards) | ❌ No encryption, no access control | H-05 |
| 🚫 Blacklist check in purchase flow | ❌ Missing in createPurchaseOrder | M-01 |
| 📊 Database integrity (FK/Cascade) | ✅ Properly implemented | — |
| 🕒 Migration order integrity | ❌ Duplicate migrations in two dirs | H-06 |
