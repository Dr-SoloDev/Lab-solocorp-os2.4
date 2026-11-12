# ADR-035 — ตัด `opencode.db` ออกจาก Live Beta (2026-11-12)

> **Status:** Proposed (รอ CEO approve พร้อม checklist v2.0) · **Head:** @architect-songsak · **Scope:** PR2 `/live` Beta เท่านั้น
> **Supersedes:** DoD v1.0 §1-DoD3 (DB เป็น opt-in) → ยกระดับเป็นตัดทิ้ง · **Related:** ADR-034 (แยก /live เป็น PR2), ADR-030 (open-core boundary)

## Decision (5 บรรทัด)

1. ลบ `_sessions_from_db` (`solocorp_app/live.py:213-274`) + `import sqlite3` (`live.py:23`) + `DEFAULT_OPENCODE_DB` (`live.py:35-40`) ออกจาก Beta ทั้งหมด — ไม่ใช่ disable
2. `list_sessions` เหลือ CLI-only (`opencode session list --format json`, timeout 1.5s) → ล้มแล้ว fail-open `source=none`
3. `opencode.json` ห้ามเพิ่ม allowlist เพื่อ PR2 (allowlist `opencode.json:129-136` ยังไม่มี `~/.local/share/opencode` = ถูกแล้ว)
4. เอา DB กลับต้องมี ADR ใหม่เท่านั้น (§4) — ห้าม revert เงียบ
5. Test ที่อ้าง DB ต้องถูกลบ/แก้ใน PR เดียวกัน (เหลือ `source in ("cli","none")`)

## 1. ทำไมตัด (3 เหตุผล — เรียงน้ำหนัก)

| # | เหตุผล | หลักฐาน |
|:-:|:--------|:---------|
| 1 | **นอก allowlist + ผิด Least Privilege** — DB มี session content ทั้งเครื่อง เปิดจาก Desktop agent โดนด่าน `ask` ทุกครั้ง (`opencode.json:129-136` ไม่มี `~/.local/share/**`) ยกเว้นต้องขยาย attack surface เพื่อ dashboard ตัวเดียว | `live.py:35-40`, `opencode.json:129-136` |
| 2 | **WAL + schema เดา = พังเงียบ** — อ่าน WAL ของ process อื่นเสี่ยง `SQLITE_BUSY` (ของเดิม `mode=ro` อย่างเดียว ไม่ copy-to-tmp — `live.py:226`) + เดาชื่อตาราง (`session/sessions/session_v2`) + เดา column `ORDER BY` (`live.py:230-257`) → opencode เปลี่ยน schema เมื่อไร dashboard โกหกเมื่อนั้น (PRD §9) | `live.py:213-274` |
| 3 | **ซ้ำซ้อนโดยไม่จำเป็น** — CLI เป็น source หลักที่ได้ shape ใหม่เสมอ + มี `normalize_session` กัน shape เปลี่ยนอยู่แล้ว (`live.py:105-169`) DB fallback เพิ่ม code path 60+ บรรทัดเพื่อกรณีที่ CLI หายพร้อมกัน ซึ่ง fail-open `source=none` รับได้อยู่แล้ว | `live.py:172-210` vs `213-274` |

## 2. Fail-open `source=none` อย่างไร

- CLI ล้ม (ไม่มี binary / timeout 1.5s / non-JSON / non-list) → คืน `{"sessions": [], "count": 0, "source": "none", "error": "<cli_error>", "updated_at"}` — ไม่ raise, ไม่ cache ความว่าง (poll รอบหน้าลองใหม่ทันที)
- `/live` render ได้เสมอด้วยข้อความเดิม (`live.html:69-71` "ไม่มี session ใน opencode บนเครื่องนี้") + `/api/live/status` ตอบ 200 พร้อม `session_source: "none"`
- ไม่มี exception หลุดจาก `list_sessions` / `live_status` เด็ดขาด (PRD §9)

## 3. สิ่งที่ต้องลบพร้อมกัน (กันซาก)

- `solocorp_app/live.py`: `import sqlite3`, `DEFAULT_OPENCODE_DB`, `_sessions_from_db` ทั้งฟังก์ชัน, `db_path` param ทุก signature
- `tests/test_solocorp_app_live.py`: test/assert ใด ๆ ที่อ้าง `db` / `db_path` / `opencode.db`
- ตรวจ: `grep -rn "opencode.db\|_sessions_from_db\|DEFAULT_OPENCODE_DB" solocorp_app/ tests/` → ว่าง (ยกเว้น ADR/checklist นี้)

## 4. เอากลับต้องมี ADR ใหม่ (4 เงื่อนไขขั้นต่ำ)

1. allowlist entry จำกัดไฟล์เดียว (ไม่ใช่ทั้ง dir) + เอกสาร Least Privilege
2. copy-to-tmp ก่อนอ่าน (ห้ามเปิด WAL ตัวจริง) + `mode=ro` + timeout สั้น
3. test schema-mismatch: ตาราง/column ไม่ตรง → `source=none` ไม่ใช่ 500/ข้อมูลมั่ว
4. วัด hammer: poll 3s + cache 15s แล้ว spawn DB read ไม่เกิน TTL (proof เดียวกับ D2)

---

*— @architect-songsak · ตัดเพื่อ Beta เล็ก + อยู่ใน allowlist + ไม่โกหกเมื่อ schema เปลี่ยน · เอากลับได้แต่ต้องมี ADR ใหม่ครบ 4 เงื่อนไข —*
