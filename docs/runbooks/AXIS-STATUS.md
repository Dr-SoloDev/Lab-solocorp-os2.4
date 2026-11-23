# AXIS STATUS — Runbook (D4)

> **สถานะ:** D4 PASSED (2026-11-23, verifier deepseek-v4.1-flash) — runbook v1.1
> **หมายเหตุ:** การเซ็น registry อย่างเป็นทางการเกิดหลัง revision นี้
> **Branch:** `feat/axis-status-c1` · **Base:** `e5b9d74` (contract v1.1)
> **Tool:** `axis_status(force: bool = False)` · **Schema:** `axis.status/1`
> **อ่านคู่กับ:** `docs/plans/AXIS-STATUS-CONTRACT-v1.1.md`
> **เป้าหมาย:** ให้คน/agent อีกคน reproduce tool นี้ได้จาก repo โดยไม่ต้องเดา

## 1. Purpose + scope

`axis_status` รวมสถานะ 7 แหล่งเป็น payload เดียว: `busd`, `cto`, `content`,
`mcp_freshness`, `git`, `browse`, `codegraph`

- วัดแบบ **read-only**: HTTP GET ไป `127.0.0.1:8099`, อ่าน `/proc`, git read-only,
  SQLite `mode=ro`
- **ไม่ทำ**: write/approve/publish, retry/delete queue, POST/PUT/PATCH,
  external network, แก้ config, kill process
- เป็นข้อมูลประกอบการตัดสินใจ ไม่ใช่ gate อนุมัติ

## 2. Prerequisites

- Python 3.12 + repo `.venv`; ทุกคำสั่งรันจาก repo root
  `/data/projects/Lab-solocorp-os2.4`
- ถ้า `.venv` ยังไม่มี: `python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
  (root requirements -> `mcp>=1.28.1,<2` + pytest; `axis_mcp/requirements.txt` ไม่จำเป็น)
- ต้องมี `PYTHONPATH=.` ทุกคำสั่ง
- `SOLOCORP_API_KEY` **ไม่บังคับ**: ถ้า busd require key แล้วไม่มี/ผิด -> 401/403
  -> `busd=down`; ห้าม echo key ออก output/log
- busd `127.0.0.1:8099` **ไม่บังคับ**: absent -> `busd=down/red` แต่ยังคืน 7 sources
- `browse` relay `127.0.0.1:19988`, `.codegraph/codegraph.db`,
  `central_bus/cto.db` ไม่บังคับ; absent -> degraded/down ตาม source
- ใช้ loopback เท่านั้น; ไม่มี cloud/external call

## 3. Install/verify (4 commands)

```bash
cd /data/projects/Lab-solocorp-os2.4   # path ของ repo คุณ
PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_axis_status.py -q
PYTHONPATH=. .venv/bin/python3 scripts/d2_axis_status_check.py
PYTHONPATH=. .venv/bin/python3 -m axis_mcp.status.server --smoke
PYTHONPATH=. .venv/bin/python3 scripts/d3_axis_status_eval.py
```

| # | Command | Expected | Exit |
|:-:|:--------|:---------|:----:|
| 1 | pytest | `40 passed` (coverage warning ปกติ) | 0 |
| 2 | D2 harness | `11/11 checks passed` (ms varies) | 0 |
| 3 | smoke | valid `axis.status/1` + 7 sources + exit 0; overall ขึ้นกับ environment (snapshot นี้ `down/63`, §6) | 0 |
| 4 | D3 eval | `43 PASS · 0 FAIL · 0 SKIP`; pytest post-check `40 passed` | 0 |

- D2 harness เขียนทับ `bus/evidence/2026-11-23/d2-axis-status/harness.log`
  และ `tool-calls.jsonl`; D3 eval เขียนทับ D3 evidence/docs ที่ tracked
- ถ้าต้องการ worktree สะอาดหลังรัน: รันในสำเนา repo ที่มี `.venv` หรือ restore
  in-place ด้วยคำสั่งนี้ (ห้ามรวม runbook/product code):
  `git checkout -- bus/evidence/2026-11-23/d2-axis-status bus/evidence/2026-11-23/d3-axis-status docs/certification/D3-axis-status-2026-11-23.md`

## 4. MCP client (stdio)

- **ยังไม่เพิ่มใน `opencode.jsonc`** (contract §8; รอ D4 ผ่าน)
- ตัวอย่าง OpenCode-compatible (fragment ใต้ `mcp.servers`; เปลี่ยน path เป็น repo ของคุณ;
  ปรับตาม schema ของ client):

```jsonc
"mcp": {"servers": {"axis-status": {"type": "local", "disabled": false,
  "command": ["<repo>/.venv/bin/python3", "-m", "axis_mcp.status.server"], "cwd": "<repo>"}}}
```

- Clients ที่ใช้ `mcpServers`: ใช้ command/args/env เดียวกัน
  (`<repo>/.venv/bin/python3 -m axis_mcp.status.server`, cwd `<repo>`)
- Tool signature: `axis_status(force: bool = False) -> dict`
- `force=False` ใช้ cache 10s; `force=True` วัดใหม่ทุก source
- Manual stdio: newline-delimited JSON-RPC; ลำดับ 1) `initialize` -> 2)
  `notifications/initialized` -> 3) `tools/call` (bare `tools/call` -> `-32602`;
  ข้อความอาจต่างตาม SDK):

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"axis-status-runbook","version":"1.0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"axis_status","arguments":{"force":true}}}
```

- อ่าน response ของ `initialize` ก่อนส่ง notification; result อยู่ที่
  `result.content[0].text` เป็น JSON string — **ไม่ใช่** `structuredContent`
  (key `structuredContent` ไม่มีใน result; keys ที่มีคือ `content`, `isError`); parse text ก่อนใช้
- รันได้จริงจาก repo root (initialize -> initialized -> tools/call; print schema/sources/isError):

```bash
PYTHONPATH=. .venv/bin/python3 - <<'PY'
import json, subprocess
p = subprocess.Popen([".venv/bin/python3", "-m", "axis_mcp.status.server"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    text=True, bufsize=1)
def send(o):
    p.stdin.write(json.dumps(o, separators=(",", ":")) + "\n"); p.stdin.flush()
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"axis-status-runbook","version":"1.0"}}})
json.loads(p.stdout.readline())  # initialize response
send({"jsonrpc":"2.0","method":"notifications/initialized"})
send({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"axis_status","arguments":{"force":True}}})
r = json.loads(p.stdout.readline())["result"]
d = json.loads(r["content"][0]["text"])
print(d["schema"], len(d["sources"]), r["isError"])
p.stdin.close(); p.wait(timeout=10)
PY
```

- `--smoke` ไม่ใช่ MCP call: print JSON หนึ่งก้อนแล้ว exit 0

## 5. Reading the output

Payload fields: `schema`, `generated_at` (UTC ISO-8601),
`overall{status,score,color}`, `sources[7]` (`id,status,latency_ms,fresh,detail,warning`),
`warnings[]`, `meta{duration_ms,cache,tool_version}`

| Status | Meaning |
|:-------|:--------|
| `ok` | วัดได้ + ตรง contract |
| `degraded` | ทำงานบางส่วน/มี warning; ยังคืนผล |
| `down` | ติดต่อไม่ได้/error |
| `unknown` | ยังวัดไม่ได้/ไม่มี probe; ตัดออกจาก score; **ไม่เคยเป็น ok** |

Weights + critical: `busd 25 (critical)`, `cto 20`, `content 15`,
`mcp_freshness 15 (critical)`, `git 10`, `browse 10`, `codegraph 5`
`score = floor(Σ(weight×value) / Σ(measured weight) × 100 + 0.5)` (ปัดครึ่งขึ้น);
`ok=1`, `degraded=0.5`, `down=0`; `unknown=ตัดออก` + renormalize
Bands: `≥90 healthy/green`, `70–89 degraded/amber`, `<70 down/red`
Critical `down`/`unknown` -> overall `down/red` ทันที (score ยังเป็นค่าที่ renormalize)

- `unknown` เกิดเฉพาะ probe ที่ยังไม่ลงทะเบียน (`DEFAULT_PROBES`); critical unknown
  บังคับ overall down + warning
- `detail` เป็นข้อมูลเฉพาะ source (queue counts, tables/columns, codegraph counts,
  process list); `meta.tool_version=1.0.0`
- `meta.duration_ms` = เวลาภายใน tool (budget 2000ms; per-source 1200ms);
  wall time ของ `--smoke` รวม Python startup (~1.1–1.3s) — อย่าเอา wall ไปเทียบ 2000ms
- `warnings` top-level prefix `<source>: ...`; non-ok ทุกตัวมี warning;
  critical/all-unknown มี warning เพิ่ม
- Cache 10s: `meta.cache=fresh|cached`; `force=True` ข้าม cache; cache per process
- `fresh`: `ok` ต้อง fresh; `ok`+warning หรือ `ok`+`fresh=false` -> `degraded`

## 6. Troubleshooting (symptom -> cause -> action)

| Symptom | Cause | Action |
|:--------|:------|:-------|
| `busd=down`, `SOLOCORP_API_KEY missing` หรือ `HTTP 401/403` | ไม่มี/ผิด key | export key ใน shell (ห้ามพิมพ์) หรือถ้า `/v1/health` allowlist ก็ไม่ต้องใช้; เช็ค `curl -s http://127.0.0.1:8099/v1/health` |
| live `overall` เป็น `down` (snapshot นี้ `63`) | busd 12.5 + content 7.5 + mcp_freshness 7.5 + browse 10 = 37.5 loss → 100−37.5=62.5→63; queue state เปลี่ยนได้ | เป็น contract arithmetic ไม่ใช่ crash; แก้ environment หรือรับค่าตามจริง |
| `mcp_freshness=degraded`, `content restart_required` | MCP generation เก่ากว่า source ใหม่สุด | `bash scripts/restart-mcp.sh` (dry-run) -> `--yes` (หรือ `--yes --stale-only`); caveat: MCP catalog อาจหลุด ต้อง reconnect; host respawn เอง |
| `cto=down`, `missing_tables` | DB ขาด table | ตรวจ/restore `central_bus/cto.db` หรือ migration; อย่าสร้างมือโดยไม่ consult owner |
| `cto=down`, `missing_columns` | table มีแต่ขาด column บังคับ | migrate/repair schema; ผลคือ 80/degraded |
| `codegraph=degraded`, `index is empty`/`index has no edges` | index ว่าง/ไม่มี edges | `codegraph index` (หรือ `codegraph init` ถ้า `.codegraph/` หาย) แล้ว `codegraph status`; ผลคือ 98/healthy |
| `busd` `invalid field(s)` | producer ส่ง null/ชนิดผิด | แก้ payload ของ busd; ผลคือ 88/degraded |
| `unknown` | probe ยังไม่ลงทะเบียน | เพิ่มใน `DEFAULT_PROBES` หรือรับว่ายังไม่ implement; critical unknown -> down |

## 7. Safety / guardrails

- Read-only: HTTP GET เท่านั้น; SQLite `mode=ro`; git read-only; no queue retry/delete
- Secrets: key อยู่ใน `X-API-Key` header เท่านั้น; output/warnings/JSON ถูก scrub;
  ห้าม print key; มี canary test ใน D2/D3
- Loopback only: `127.0.0.1:8099`, `127.0.0.1:19988`; ไม่มี external network
- Never gates approvals/publish; status เป็นข้อมูลเท่านั้น
- Restart MCP เฉพาะ `scripts/restart-mcp.sh` ตามขั้นตอน; อย่า kill เอง

## 8. Known limitations (honest)

- CTO ตรวจชื่อ column เท่านั้น; **ไม่ตรวจ type**
- Codegraph ไม่ตรวจอายุ index ที่มีข้อมูลอยู่แล้ว; `fresh` = อ่าน DB ได้
- `_build_payload` ยังต้องมี `id`/`status` ใน row; ทนเฉพาะ `warning` ที่หาย
- Tracked D3 `eval.log` ถูกจับที่ `172740e` + uncommitted v1.1; HEAD ปัจจุบัน
  `e5b9d74`; counts 43/43/0/0 เป็นของ current (D3 docs อาจยัง stale)
- Evidence helper ของ D2 classification/MCP call อยู่ใน `/tmp/opencode/...`
  (ไม่ commit); pytest/D2 harness/D3 harness ที่ commit แล้ว reproduce counts ได้
- `axis_status` ยังไม่ลงทะเบียนใน `opencode.jsonc` (contract §8)
- live `down` (snapshot นี้ 63) เป็น environment ไม่ใช่ product crash

## 9. D4 verifier checklist

- [ ] เริ่มจาก `feat/axis-status-c1` ที่ `e5b9d74`; `git status --porcelain`
  ไม่มี product changes (pre-existing `brain/learnt.md`/lock และ runbook ใหม่ได้)
- [ ] รัน 4 commands §3 + stdio client §4; บันทึก stdout/stderr/exit code
- [ ] counts: pytest 40, D2 11/11, smoke 7 sources, D3 43/43/0/0; exit 0 ทุกตัว
- [ ] stdio §4: `axis.status/1 7 False`, exit 0
- [ ] `git diff --name-only -- axis_mcp tests` ว่าง (D2/D3 evidence แยกจาก product)
- [ ] evidence: `bus/evidence/2026-11-23/d4-axis-status/verifier-<name>-<UTC>/`
  (เช่น `verifier-axis-checker-20261123T120000Z/`): `pytest.log`, `d2-harness.log`,
  `smoke.json`, `d3-eval.log`, `env.txt`, `git-status.txt`, `verifier-report.md`
- [ ] sign-off นับเฉพาะ `verifier-<name>-<UTC>/verifier-report.md`; `verifier-*`
  ที่ root ถือว่า superseded/ignored; หลายรอบใช้ UTC ล่าสุด
- [ ] `git-status.txt` = full `git status --porcelain` before + after
- [ ] `verifier-report.md`: name/agent, date UTC, HEAD, commands+exit, verdict
  PASS/FAIL, SHA-256 ของ `docs/runbooks/AXIS-STATUS.md`, signature 1 บรรทัด
  (`sha256sum docs/runbooks/AXIS-STATUS.md`; format:
  `name=... | date_utc=... | head=... | commands=... | verdict=PASS/FAIL | runbook_sha256=... | signature=...`)
- [ ] `commands=` syntax: `1:pytest:0;2:d2:0;3:smoke:0;4:d3:0;stdio:0`
- [ ] evidence policy: `bus/evidence/` gitignored; เก็บ local subdir; ถ้า certify
  ให้ `git add -f` เฉพาะ sign-off (report + commands + env + logs) ตาม SOP-06
  หรือบันทึก SHA-256 ใน registry ถ้าไม่ commit; **ห้าม commit secrets**
- [ ] formal registry sign-off หลัง revision นี้; D4 runbook ถือว่า passed เมื่อ
  verifier subdir report ลงนามแล้ว

## 10. Rollback / uninstall

- tool ไม่มี state ถาวร: no DB writes, no on-disk cache, no daemon
- แต่ D2/D3 harness เขียน tracked evidence (`harness.log`/`tool-calls.jsonl`/D3 docs);
  ใช้ restore command §3 ถ้าต้องการ clean tree
- ถ้าลงทะเบียน MCP แล้ว: ลบ entry `axis-status` จาก client config แล้ว reload;
  ไม่ต้องลบโค้ด
- ถ้าเริ่ม busd/browse เอง: stop ตามวิธีของ service; tool ไม่ได้ start ให้
- ไม่ต้องลบ `.codegraph/`, `central_bus/cto.db` หรือ evidence; เป็นข้อมูลของ repo
