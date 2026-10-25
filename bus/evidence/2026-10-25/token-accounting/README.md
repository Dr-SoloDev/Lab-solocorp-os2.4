# Evidence — Token / Quota Accounting (2026-10-25)

**งาน:** วัด token/ค่าจริงต่อ LLM call + เพดานรายวัน + quota lock (fail-fast)
**สั่งโดย:** Owner (2026-10-25) — "ทำ token accounting ใน `workers/llm_provider.py` ก่อน"
**สถานะ:** D2-equivalent — โค้ด + เทสต์ + smoke จริงกับ LLM (ล้มตามคาดเพราะโควตาหมด)

---

## ทำไม (incident)

โควตาฟรีของ workspace หมดกลางวันโดยไม่มีใครรู้:
298 requests สำเร็จ → **169 × 429** + **186 × outcome=rejected** (ยิงเข้ากำแพงเปล่า ๆ)
สาเหตุ: ไม่มีการวัดต่อ call และไม่มีความจำว่า "โควตาตายแล้ว"

## ตัวเลขที่แก้ความเข้าใจผิด

Console แสดง `DeepSeek V4.1 Flash | 270 | 779.5k | 15.2M | - | 186.9k | $0.00`
→ **15.2M = cache_read** (ถูกมาก $0.006/M) ไม่ใช่ output
→ output จริง **188,132** tokens · paid-equivalent ทั้งวัน **≈ $0.56**

รายละเอียดเต็ม: [`docs/TOKEN-ACCOUNTING.md`](../../../docs/TOKEN-ACCOUNTING.md)

---

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | อะไร | reproduce |
|:--|:--|:--|
| `smoke.log` | `think()` จริง 2 ครั้ง: ครั้งแรก 0.98s (1 attempt) · ครั้งที่สอง **0.001s / 0 LLM attempt** | `python -c "import asyncio;from workers import llm_provider as l;print(asyncio.run(l.think('hi',agent='smoke-test')))"` |
| `request-logs-summary.json` | สรุป 488 records จาก console export (มี sha256 ของไฟล์ต้นทาง) | `python3` + `/data/Videos/request-logs-2026-10-25.json` |
| `tests.log` | 82 passed — 4 ไฟล์เทสต์ที่เกี่ยวข้อง (ไม่ใช้ LLM) | `python -m pytest tests/test_token_ledger.py tests/test_llm_provider_cmd.py tests/test_llm_fallback.py tests/test_mirror_llm_reliability.py -q --no-cov` |
| `token-report.log` | รายงานจริงระหว่างโควตาล็อก (`🔒 free-limit`) | `python scripts/token-report.py --sessions 5` |

## sha256 ของโค้ดที่วัด (ตอนเขียนหลักฐาน)

```
7549d0bdf99f21846f30d279cfbd3b3c2ae1f849dd8fd319b587623eebb305d3  workers/token_ledger.py
8c10af3fc2306fbb8a114220d018564ca2fc365c56776974b2b286a14c69a28b  workers/llm_provider.py
7c9ae975923b807f1b3e747e66b5abb9e08d742f45f1bcf8bff66d125a5d0fae  workers/agents/base_agent.py
478d1c3f4f92ed89608dfdeb7116ebebb3f57ee6477d2059456a81f513af2ea8  scripts/token-report.py
```

## เกณฑ์ผ่าน (ตรวจเองได้)

| ข้อ | หลักฐาน |
|:--|:--|
| วัด usage จริงต่อ call (ไม่ใช่ประมาณ) | `smoke.log` + `tests.log` (อ่านจาก `opencode.db` → `session_message`) |
| ไม่ยิงซ้ำเมื่อโควตาตาย | `smoke.log`: call ที่ 2 = 0.001s, ledger ไม่เพิ่มบรรทัด |
| ledger เขียนไม่ติดต้องไม่ทำให้ LLM ล้ม | `tests/test_llm_provider_cmd.py::TestCallAccounting::test_accounting_failure_does_not_break_call` |
| เทสต์ไม่ปนเปื้อน runtime state | `tests/conftest.py` (autouse isolate) — ก่อนหน้านี้เทสต์เขียน 35 บรรทัดขยะลง ledger จริง |
| เพดานรายวันหยุดก่อนเผา | `TestBudgetGuard::test_over_daily_ceiling_makes_zero_calls` |
| ไม่มี cherry-pick | `tests.log` = ผลรวมทั้ง 4 ไฟล์ (82 passed, 0 skipped) |
