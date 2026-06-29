# Docker + PHP: Environment Variable Debugging

## Pattern: "Server configuration error" on boot

### Root Cause Class
PHP app exits early in `config.php` when a required env var (e.g. `JWT_SECRET`) is not set. The error surfaced as a generic HTTP error — not a PHP fatal — because the exit happened before any output.

### Diagnostic Steps
1. Hit the raw API endpoint directly: `curl http://localhost:<port>/api/index.php`
2. If response is a generic string (not HTML), read `api/config.php` lines 1–30 — look for `getenv()` + `exit()` guards
3. Check which env vars are guarded and whether they exist in the container: `docker exec <container> printenv | grep JWT`

### Fix Pattern
**Two places must be updated in tandem:**

1. `docker-compose.yml` — under the service's `environment:` block:
   ```yaml
   environment:
     JWT_SECRET: your_secret_here
   ```

2. Apache VirtualHost config (e.g. `docker/apache-config.conf`) — inside `<VirtualHost *:80>`:
   ```apache
   SetEnv JWT_SECRET your_secret_here
   ```
   Apache passes env vars to PHP-FPM/mod_php via `SetEnv`; docker-compose alone is not enough if Apache is the server.

### Inject Without Restart (live container)
```bash
docker cp docker/apache-config.conf <container_name>:/etc/apache2/sites-enabled/000-default.conf
docker exec <container_name> apache2ctl graceful
```
Verify: `curl http://localhost:<port>/api/index.php` should return `"Authentication required"` (not config error).

### Pitfalls
- Setting env var in docker-compose is NOT sufficient when Apache is the web server — Apache does NOT inherit Docker env vars into PHP unless `SetEnv` is added to the VirtualHost block.
- `apache2ctl graceful` reloads config without dropping connections; prefer it over `restart`.
- After full `docker compose down && up`, the fix in docker-compose.yml takes effect permanently.

### Verification Signal
`"Authentication required"` response = JWT_SECRET is now being read. System is functional; proceed to login test.
