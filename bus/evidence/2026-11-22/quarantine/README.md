# Quarantine: TestLiveRead flake ออกจาก gate (2026-11-22)

- **Branch:** `chore/quarantine-live-read` (base: `main` @ `c3fd2d4`)
- **Scope:** เฟสท้ายทาง A — quarantine เท่านั้น, **ไม่ลบ test** (per AGENTS.md pre-existing rule)
- **Target flake:** `tests/test_web_reader.py::TestLiveRead::test_search_returns_results` (live network)

## Diff (2 files)

1. `tests/test_web_reader.py` — เติม `@pytest.mark.live` + quarantine docstring บน `TestLiveRead` (ไฟล์/คลาส/เทสครบ ไม่ลบ)
2. `pytest.ini` — register marker `live` + `addopts += -m "not live"`

## ทำไมแก้ที่ pytest.ini แทน .github/workflows/ci.yml

- `workers/auto_qa_gate.py::run_tests()` รัน `pytest <test-path>` เองโดยไม่ผ่าน CI yaml → แก้แค่ yaml บรรทัด pytest ไม่พอ gate ยังแดง
- ini-level deselect คลุม **ทั้ง 3 ทาง**: CI pytest line, auto-QA gate, local run — ด้วย diff จุดเดียว
- รัน live แยกยังได้: `pytest tests/test_web_reader.py -m live -o addopts=""`

## ผลยืนยัน (2026-11-22, .venv python 3.12, PYTHONPATH=.)

| run | ผล |
|:----|:---|
| `pytest tests/test_web_reader.py --collect-only` | 34 collected, **3 deselected** |
| `pytest tests/test_web_reader.py -m live --collect-only -o addopts=""` | **3 collected** (ไม่ถูกลบ) |
| `pytest tests/test_web_reader.py` | **34 passed, 3 deselected** (7.37s) |
| full gate-equiv `pytest tests/ central_bus/tests/` | **1351 passed, 1 skipped, 3 deselected** (70.57s) — เขียวทั้งแผง |

## หมายเหตุ

- CEO brief อ้าง main tip `5bf5021` แต่ `main` ใน worktree นี้คือ `c3fd2d4` — base ตามจริง, ไม่มี cherry-pick ข้าม
- `qa-evidence/` untracked ใน worktree ไม่ได้แตะ (ปล่อยไว้ให้เจ้าของ)
- PR เปิดแบบ **ไม่ merge เอง** รอ Owner/CEO ตัดสิน
