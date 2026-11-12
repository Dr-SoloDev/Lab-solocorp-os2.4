# SoloCorp App Shell — Run & Verify

How to run the Phase 1 local app shell, change provider settings, and enable or
disable a department module from the UI.

**Scope:** the shell only. It renders four pages, writes the module registry
intent, and stores one provider configuration. It does not call a model, does
not create tasks, and has no authentication — see "Phase 1 limits".
**Source of truth for scope:** `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md` §7/§8/§11,
`docs/plans/SOLOCORP-APP-LOCAL-RUNTIME-DESIGN-v0.1.md` §3/§4 D1/§6/§7.

---

## 1. Prerequisites

- Python 3.12 (CI version) with the repo venv: `source .venv/bin/activate`
- `export PYTHONPATH=.`
- Jinja2 — installed from the repo root `requirements.txt` (`-r central_bus/requirements.txt`
  plus `jinja2>=3.1.4,<4.0`). If `python -m solocorp_app` fails with
  `ModuleNotFoundError: No module named 'jinja2'`, run `pip install -r requirements.txt`.

## 2. Run

```bash
source .venv/bin/activate && export PYTHONPATH=.
python -m solocorp_app                    # 127.0.0.1:8766
python -m solocorp_app --port 8790        # another port
SOLOCORP_APP_PORT=8790 python -m solocorp_app
```

Expected first line:

```
SoloCorp App on http://127.0.0.1:8766  (loopback only)
```

| Setting | Env var | Flag | Default |
|:--------|:--------|:-----|:--------|
| Host | `SOLOCORP_APP_HOST` | `--host` | `127.0.0.1` (non-loopback is refused) |
| Port | `SOLOCORP_APP_PORT` | `--port` | `8766` |
| Log level | `SOLOCORP_APP_LOG_LEVEL` | — | `info` |

**Binding is loopback-only on purpose.** Any host that is not `127.0.0.1` /
`localhost` / `::1` is rejected before the socket opens: this build has no
authentication and must not be reachable from the network.

Exit codes — fail fast, never "half started":

| Code | Meaning | Message starts with |
|-----:|:--------|:--------------------|
| 0 | server shut down cleanly | — |
| 2 | port already in use | `SoloCorp App cannot start: cannot bind 127.0.0.1:8766 …` |
| 3 | bad configuration (non-loopback host, invalid port, unwritable config dir) | `SoloCorp App cannot start: …` |

Liveness probe: `curl -s http://127.0.0.1:8766/healthz` → `{"status":"ok","app_version":"0.1.0",
"provider_state":"…","registry_valid":true,"modules":{…}}`. `status` becomes `degraded`
when the registry config does not validate — the probe reports the failure instead of
hiding it.

## 3. Files the shell reads and writes

| Path | Tracked in git? | Contents | Who writes |
|:-----|:----------------|:---------|:-----------|
| `config/module-registry.json` | **yes** | module manifests + operator **intent** (`enabled`/`disabled`) | `ModuleRegistry.update()` when you toggle |
| `central_bus/module-registry.state.json` | no (gitignored) | runtime **observations** (`connected`/`connecting`/`error`, response time, last error) | the health poller / `ModuleHost` |
| `config/provider.json` | yes | provider id, model id, base URL, `api_key_ref` — **no secret** | Settings → Save |
| `config/provider.credentials.json` | no (gitignored, mode `0600`) | the API key value | Settings → Save / Remove |

Rules the shell keeps:

- **Intent and observation never mix.** A toggle writes only `status` in the tracked
  config; a heartbeat writes only the state file. The tracked file never carries
  `observation`/`last_checked`/`response_time_ms` (asserted in
  `tests/test_solocorp_app_runtime.py::test_enable_connects_the_module_and_keeps_observation_out_of_config`).
- **No silent fallback.** Missing credential → provider state `unconfigured`; the
  app does not pick another model. `SOLOCORP_PROVIDER_API_KEY` wins over the
  credentials file when both exist (the page shows `credential source: env`).
- **Startup clears stale observations.** A `connected` entry left by a previous
  process is deleted before the first render, because this process owns no live
  connection yet — otherwise the UI would report a success that does not exist
  (PRD §9).

## 4. Pages

| Route | What it is in Phase 1 |
|:------|:----------------------|
| `/` | 303 → `/chat` |
| `/chat` | CEO Chat placeholder: says model calls arrive in Phase 2. No input is sent anywhere. |
| `/modules` | 5 modules with intent, transport, last-checked, response time, capabilities, permission scopes. Toggle + health actions. |
| `/tasks` | Read-only list of task envelopes from `central_bus/content/tasks/` (newest first). The app does not create tasks yet. |
| `/settings` | Provider status + form. Credential is masked to its last 4 characters; the key never appears in HTML, a task record, or a log. |
| `/api/modules` | JSON the poller uses (`modules`, `counts`, `registry`). |

## 5. Verify a module toggle (the Phase 1 gate check)

1. Start the app, open `http://127.0.0.1:8766/modules`.
2. Confirm the summary chips read `5 modules · 5 enabled · 0 connected · 0 error`
   on a fresh process (0 connected is correct: nothing is connected until you ask).
3. **Content Creator → Check health.** Page reloads with
   `notice=module-checked`; within a few seconds the card shows `connected` with a
   response time in milliseconds, and the chips move to `1 connected`.
4. **Content Creator → Disable.** Notice: *"Module disabled — the connection was
   closed and the config updated."* The card shows `disabled`, its Check health
   button is disabled, the chips read `4 enabled`, and in the tracked config:

   ```bash
   python - <<'PY'
   import json; d = json.load(open("config/module-registry.json"))
   print(d["content-creator"]["status"], d["content-creator"].get("updated_at"))
   print(sorted(set(d["content-creator"]) & {"observation","last_checked"}))  # []
   PY
   ```

5. **Content Creator → Enable.** Notice: *"Module enabled — the app is starting its
   process now."* The runtime writes `connecting` to the state file, connects on a
   worker thread, then `connected`. `GET /api/modules` shows
   `"observation": "connected"` and `"response_time_ms"` within ~5 s.
6. Leave the module enabled and restore the config if you tested on a tracked file:
   `git checkout -- config/module-registry.json`.

Server-side trail to expect in the app log:

```
POST /modules/content-creator/toggle HTTP/1.1" 303 See Other
GET /modules?notice=module-disabled&module=content-creator HTTP/1.1" 200 OK
```

## 6. Verify provider settings

1. `/settings` → fill Provider (`opencode`), Model, API key → **Save provider settings**.
2. Expect `notice=provider-saved`, state `configured`, `credential source: file`,
   `credential: …<last 4>`.
3. Check the split on disk:

   ```bash
   ls -l config/provider.json config/provider.credentials.json   # 0644 vs 0600
   grep -c "sk-" config/provider.json                            # 0
   ```

4. **Remove stored credential** → `notice=provider-cleared`; state returns to
   `unconfigured`; the credentials file becomes `{}` (it is not deleted, so the
   directory mode stays as created).

To leave the tree as you found it: `rm -f config/provider.json config/provider.credentials.json`.

## 7. Security model (what is and is not enforced)

| Control | Behaviour |
|:--------|:----------|
| Binding | loopback only; non-loopback host refused at startup |
| Host header | allowlist `127.0.0.1`/`localhost`/`::1` (+ port) — anything else is rejected |
| CSRF | double-submit: `solocorp_csrf` cookie (HttpOnly, SameSite=strict) must equal the `csrf_token` form field or `X-CSRF-Token` header on every POST |
| Origin | `Origin` must match the request host. `Origin: null` is accepted **only** with `Sec-Fetch-Site: same-origin` (the desktop shell's embedded browser sends exactly that) |
| Headers | CSP `default-src 'self'`, no inline script/style (`/static/app.css`, `/static/app.js`), `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options: DENY` |
| Secrets | key only in the 0600 gitignored credentials file; masked in every render |
| Auth | **none** — single user on loopback. Do not expose this port. |

## 8. Troubleshooting

| Symptom | Cause | Fix |
|:--------|:------|:----|
| `cannot bind 127.0.0.1:8766 (Address already in use)`, exit 2 | another process (often a previous app run) holds the port | `ss -ltn \| grep 8766`, stop that PID, or pass `--port` |
| Every POST → `403 CSRF check failed` | missing/mismatched token, or `Origin`/`Host` mismatch (proxy, or a client that sends neither) | reload the page (the cookie + hidden field are issued together); if the client sends `Origin: null`, it must also send `Sec-Fetch-Site: same-origin` |
| Card says `connected` but nothing answers | a stale observation from a killed process | restart the app — startup clears observations; then Check health |
| Provider shows `unconfigured` after Save | env var `SOLOCORP_PROVIDER_API_KEY` is empty/unset and the credentials file was cleared | save a key, or export the env var |
| `/static/app.js` still behaves like the old build | browser cache (`304 Not Modified`) | hard reload; the dev server revalidates by mtime/size |
| Jinja template error on start | templates not shipped with the package copy | run from the repo root (templates resolve relative to `solocorp_app/`) |

### Single instance only (BUG-3 lesson, QA 2026-11-12)

The state file (`central_bus/module-registry.state.json`) is **global** while
connections are **per-process**. Two app processes on different ports share one
state file, so instance B displays instance A's `connected` row as its own —
a connection reported with no connection (PRD §9). `AppRuntime.start()` clears
stale observations at boot, which makes a *restart* honest, but it cannot make
two *concurrent* instances honest. **Run one instance at a time.**

Hand-off cleanup checklist (run before claiming "port free / tree clean"):

```bash
ss -ltn | grep 8766 || echo "port free"
ps aux | grep '[s]olocorp_app' || echo "no leftover app process"
git status --short   # only intended files changed
```

## 9. Phase 1 limits (do not read as done)

- **No model calls.** `/chat` is a placeholder; nothing is sent to a provider.
- **No task creation.** `/tasks` lists what already exists in
  `central_bus/content/tasks/` (unbounded, newest first — no pagination).
- **No auto-connect at startup.** Modules connect on enable or Check health, so a
  start does not spawn five MCP child processes.
- **No auth, no multi-user, no remote access.**
- **Not certified D3/D4.** The shell was built and checked in one session; an
  independent checker still has to reproduce this runbook.

## 10. Verification commands

```bash
source .venv/bin/activate && export PYTHONPATH=.
python -m pytest tests/test_solocorp_app_runtime.py tests/test_solocorp_app_boundary.py \
  tests/test_solocorp_app_provider.py -q          # app shell
python -m pytest tests/ central_bus/tests/ --tb=short -q   # CI suite
```

`python -m pytest` from the repo root with both paths is the CI invocation; bare
`pytest` misses `central_bus/tests/`.

## 11. Phase 2 CEO loop (`POST /chat`)

One synchronous turn: validate brief → route (content-creator only) →
`TaskTracker.create(pending)` → `running` → `host.call_tool` → terminal
`completed`/`failed` + `completed_at`. No worker, no retry, no silent fallback;
`failed` still returns 200 (work finished, result failed). Only tracker `OSError`
returns 500. `GET /chat` renders the same form with `turn=None`.

| Budget | Value |
|:-------|:------|
| Turn deadline (`CEO_TURN_BUDGET_S`) | 180s, counted around `running` → `call_tool` return |
| Per-tool ceiling (`TOOL_TIMEOUTS`) | default 60s · `render_*` 150s · `tools/list` 5s (`timeout=min(ceiling, remaining)`) |
| `request()` deadline (`mcp_stdio.py`) | total `timeout` per request; id-mismatch no longer resets the clock |
| Timeout/exit | `host.disconnect(module_id)` immediately (reuses `close()` terminate→kill) |

| `error.code` | When | Hint points to |
|:-------------|:-----|:---------------|
| `MODULE_DISABLED` | registry intent disabled | Modules → Enable content-creator |
| `MODULE_DISCONNECTED` | enabled but not connected | Modules → Check + `last_error` |
| `MODULE_ERROR` | connect/probe failed | Modules → Check again / send log |
| `TOOL_FAILED` | `call_tool` raised after connect | retry, shorten brief on repeat |
| `BRIEF_INVALID` | brief empty / >2000 (400, no task) | retype 1–2000 chars |
| `INTERNAL` | anything else / provider unconfigured (`/settings`) | retry + send time + task_id |

Task files: `central_bus/content/tasks/task-<12hex>.json` (envelope v2:
`route_reason` non-empty, `artifact_refs[]`, `app_version`, `error{code,message,hint}`
+ legacy mirrors `result_ref==artifact_refs[0]`, `error_detail==error.message`).
Old files (only `result_ref`/`error_detail`) read via normalize-on-read; the
reader never rewrites them on disk.

```bash
source .venv/bin/activate && export PYTHONPATH=.
python -m pytest tests/test_solocorp_app_ceo_loop.py tests/test_solocorp_app_live.py tests/test_solocorp_app_runtime.py -q --tb=short
```
