# Docker PHP Stack Diagnostics

**When:** User asks you to "open" or "check status" of a Docker-based PHP CRUD project — verify what actually works vs what looks complete.

## Core Insight

PHP CRUD apps in Docker often appear "complete" because all code files exist, but the real runtime state differs. The diagnostic chain below catches gaps systematically.

## Diagnostic Chain (top to bottom)

### 1. Container Health
```bash
docker compose -f <path>/docker-compose.yml ps
docker ps --format "{{.Names}}"
```
- All expected containers running? (web, db, pma)
- Check port mappings match memory/config

### 2. Web Endpoints (Host-side)
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>/<path>
```
- `200` — normal
- `401` — auth required (expected for protected endpoints)
- `500` — server error (review PHP error log in container)
- `000` / connection refused — Apache not listening, check container logs

Test in this order:
1. Static HTML page → verifies Apache serves files
2. API endpoint (public route, no auth) → verifies PHP + routing work
3. Protected API endpoint (with/without token) → verifies auth chain

### 3. Database Tables
```bash
docker exec <db-container> mysql -u <user> -p<pass> -e "USE <db>; SHOW TABLES;"
docker exec <db-container> mysql -u <user> -p<pass> -e "USE <db>; DESCRIBE <table>;"
```
- The DB container name is `secondhand-pos-db`, user `posuser`, pass `pospass`, database `pos_system`
- The web PHP container (`secondhand-pos-web`) does NOT have `mysql` CLI — query via the db container instead

### 4. Migrations Applied
```bash
docker exec <db-container> mysql -u <user> -p<pass> -e "USE <db>; SELECT * FROM schema_migrations;"
```
- Compare against `migrations/` directory on disk
- **Common gap:** Code references a table that has NO migration file (e.g., `login_attempts`). This causes login to fail with `1146 Table doesn't exist`.

### 5. Autoloader
Check the autoloader picks up custom controller classes:
```bash
docker exec <web-container> php -r "require '<autoloader-path>'; echo class_exists('<ClassName>') ? 'EXISTS' : 'NOT FOUND';"
```
- PHP CLI inside container may lack environment variables Apache provides (`.env` or Apache `SetEnv`). The autoload path check works, but DB-dependent checks (which need `DB_HOST`, `JWT_SECRET`) fail from CLI.
- Key paths for this project: `PhotoUploadController` lives in `customizations/api/Controllers/`, autoloader scans that directory.

### 6. Router & Routes
- Check `Router.php` for registered routes and auth configuration
- Routes registered as `purchase-orders/photos` (without leading `/`)
- Public routes array in constructor — endpoints NOT in this list require JWT Bearer
- Route dispatching handles both path-based ID (`/purchase-orders/{id}/photos`) and query-based ID (`?id=...`)
- For this project: `purchase-orders/photos` is public (HMAC token auth); `purchase-orders/photo-token` is protected (JWT staff auth)

### 7. Filesystem & Permissions
```bash
docker exec <web-container> ls -la /var/www/html/<path>
```
- Check owner: `www-data` must own writable directories (e.g., `uploads/`)
- Docker volume mounts may map to host paths that don't exist yet
- PHP's `mkdir()` creates subdirectories at runtime (year/month) — verify parent exists and is writable

### 8. Volume Mounts
```yaml
# docker-compose.yml example
volumes:
  - ./base-pos:/var/www/html:rw        # Main app
  - ./uploads:/var/www/html/uploads:rw # Uploads
```
- Relative paths are from `docker-compose.yml` location, not project root
- Check both parent dir and subdirs exist on host

### 9. Frontend Assets
- Check vendor JS libs exist (`qrcode.min.js`, etc.)
- Check HTML elements referenced by JS actually exist in the page
- Check CSS files for mobile vs desktop styling
- Inspect: `browser_navigate + browser_vision` for visual verification

### 10. Trace the Complete Auth Chain (the most common bottleneck)

For HMAC-token-based features (like G1 Photo Upload), trace end-to-end:

```
Login (JWT) → photo-token endpoint (HMAC) → QR code → mobile page → upload (HMAC verify)
```

**Common failure pattern:** Login fails → token can't be generated → QR can't be made → mobile flow dead.

Root causes:
- Missing `login_attempts` migration (brute-force table referenced by code but never created)
- JWT_SECRET inconsistency between `.env` and Apache config
- Auth controller references tables/columns that don't match migration state

## Pitfalls

- ❌ **Don't assume `php -r` inside container works for DB tests** — environment variables from Apache may not be available in CLI
- ❌ **Don't confuse 401 with 500** — 401 means auth chain partially works (it reached the auth check), 500 means execution broke before auth
- ❌ **Don't assume library exists because code references it** — check `vendor/` or `assets/js/vendor/` explicitly
- ❌ **Don't skip schema_migrations** — the table that exists and what migrations say are often different things
- ❌ **Don't assume docker exec `mysql` is available in the web container** — it's only in the db container

## Verdict Template

```
## Feature: {name}

| Layer | Status |
|-------|--------|
| Controller | ✅ complete |
| Routes | ✅ registered |
| Autoloader | ✅ resolves |
| DB table | ✅ exists |
| Migrations | ✅ applied |
| Uploads dir | ✅ writable |
| Frontend HTML | ✅ element exists |
| Frontend JS | ✅ function called |
| Vendor lib | ✅ loaded |
| **Auth chain** | **🔴 broken (root cause: X)** |
| **End-to-end** | **🔴 blocked until auth fixed** |
```
