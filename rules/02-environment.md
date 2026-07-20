# 🌍 Environment — เปิด service ไหน? รันอะไร?

## Basics

```bash
source .venv/bin/activate && export PYTHONPATH=.
```

## Services

| Service | Command | Port |
|:--------|:--------|:-----|
| Central Bus (busd) | `uvicorn central_bus.main:app --host 127.0.0.1 --port 8099` | 8099 |
| govctl API | `python -m govctl_cli api start` | 8765 |
| govctl CLI | `python -m govctl_cli <cmd>` | gov/ artifacts |
| Loop Runner | `python -m loop_runner.main` | cron 30m |
| MCP Server | `python -m solocorp_mcp.server` | — |

## Tests

```bash
pytest tests/ central_bus/tests/ -q
```

⚠️ อย่ารัน bare `pytest` จาก root — profile-embedded tests abort collection

## Key Paths

| Path | What |
|:-----|:-----|
| `central_bus/` | FastAPI busd (30+ modules) |
| `govctl_cli/` | Governance CLI + API |
| `gov/` | ADR / RFC / Guard TOML |
| `bus/` | Queue, dispatch, evidence, governance |
| `loop_runner/` | 4 automation loops |
| `profiles/` | 19 department SOUL.md |
| `workers/` | Agent worker + 20 agents |
| `rules/` | **Behavior-Centric rules (คุณอยู่ตรงนี้)** |
| `sop/` | Standard Operating Procedures |
| `brain/` | CEO memory, session log, learnt |
| `skills/` | SoloCorp skills |
| `rules/INDEX.md` | กลับไปหน้าแรก |
