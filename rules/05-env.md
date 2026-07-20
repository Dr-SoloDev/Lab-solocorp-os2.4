# 05 — สั่งงาน: services, commands, tests

> **เมื่อต้องเปิด service, รัน test, หรือหา path**

## 1. Basic Prep

```bash
source .venv/bin/activate && export PYTHONPATH=.
```

## 2. Services

| Service | Command | Port |
|:--------|:--------|:-----|
| Central Bus (busd) | `uvicorn central_bus.main:app --host 127.0.0.1 --port 8099` | 8099 |
| govctl API | `python -m govctl_cli api start` | 8765 |
| govctl CLI | `python -m govctl_cli <cmd>` | gov/ artifacts |
| Loop Runner | `python -m loop_runner.main` | cron 30m |
| MCP Server | `python -m solocorp_mcp.server` | — |

## 3. Tests

```bash
pytest tests/ central_bus/tests/ -q
```

⚠️ อย่ารัน bare `pytest` จาก root — profile-embedded tests abort collection

## 4. Key Paths

| Path | อะไร |
|:-----|:-----|
| `central_bus/` | FastAPI busd (30+ modules) |
| `govctl_cli/` | Governance CLI + API |
| `gov/` | ADR / RFC / Guard TOML |
| `bus/` | Queue, dispatch, evidence, governance |
| `loop_runner/` | 4 automation loops |
| `profiles/` | 19 department SOUL.md |
| `workers/` | Agent worker + 20 agents |
| `rules/` | **Behavior rules (คุณอยู่ตรงนี้)** |
| `sop/` | Standard Operating Procedures |
| `brain/` | CEO memory, session log, learnt |
| `skills/` | SoloCorp skills |

## 5. Pipeline Phases

| Phase | อะไร | ใคร |
|:------|:-----|:----|
| 1. **Spec** | requirements, scope | CEO ↔ Product |
| 2. **Plan** | แตก task, ระบุ department | CEO ↔ Architect |
| 3. **Build** | implement | Engineering / Design |
| 4. **QA** | test (3 rounds max) | QA ↔ Dev |
| 5. **Deliver** | สรุป + handoff report | CEO |

## 6. Status Commands

| คำสั่ง | เมื่อไหร่ |
|:------|:---------|
| `/status` | ดูสถานะ pipeline + bus + governance health |
| `/audit <scope>` | ตรวจ audit trail + compliance |
| `/brain <context>` | บันทึก session context ลง brain |
| `/mirror-check` | ตรวจ decision สะท้อน Owner |
