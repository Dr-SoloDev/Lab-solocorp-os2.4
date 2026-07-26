# SOP-03: Handoff — Head-to-Head ส่งต่องาน

**Owner:** All Department Heads  
**Version:** v1.1  
**Applies to:** Head → Head, CEO → Head

## Step-by-Step

### 1. Trigger
- งานใน department เสร็จ → ต้องส่งต่อ
- CEO dispatch งานมาให้
- หัวหน้าตรวจพบว่างานต้องข้าม department

### 2. Prepare Handoff Payload

```json
{
  "handoff": {
    "id": "HANDOFF-NNN",
    "from": "department-id",
    "to": "department-id",
    "work_item": "ชื่องาน",
    "status": "ready | blocked | partial",
    "summary": "สรุป current state 3-5 บรรทัด",
    "artifacts": ["path/to/artifact1", "path/to/artifact2"],
    "pending": ["สิ่งที่ receiver ต้องทำ"],
    "decisions": [{"decision": "...", "rationale": "...", "by": "..."}],
    "deadline": "YYYY-MM-DD",
    "priority": "P0 | P1 | P2 | P3",
    "context": "context pack หรือ reference"
  }
}
```

### 3. Mirror Check
- ถ้า L3+ → รัน Mirror Check ก่อนส่ง
- Check: "Dr.solodev จะทำแบบนี้ไหม?"

### 4. Record
- บันทึก handoff ใน `bus/dispatch/` หรือ `bus/queue/`
- Evidence collector บันทึกอัตโนมัติ

### 5. Receiver Confirmation
- Receiver ยืนยัน: "รับทราบ context" + "เข้าใจ pending items" + "รับช่วงต่อ"

### 5a. Confirmation Record (Handoff Confirmation Mechanism)
- **หลังจาก Receiver ยืนยันแล้ว** ให้สร้าง Confirmation Record ทันที
- ใช้ `workers/handoff_confirm.py` สำหรับสร้าง confirmation:

  ```bash
  # Receiver ยืนยันรับงาน
  python3 workers/handoff_confirm.py \
    --handoff HANDOFF-NNN \
    --to department-id \
    --status acknowledged

  # Receiver ขอ clarification (ยังไม่รับช่วง)
  python3 workers/handoff_confirm.py \
    --handoff HANDOFF-NNN \
    --to department-id \
    --status need_clarify \
    --notes "รายละเอียดที่ต้องการเพิ่มเติม"

  # Receiver ปฏิเสธ (ส่งกลับ sender)
  python3 workers/handoff_confirm.py \
    --handoff HANDOFF-NNN \
    --to department-id \
    --status rejected \
    --notes "เหตุผลที่ปฏิเสธ"
  ```

- Confirmation Record จะถูกบันทึกที่: `bus/dispatch/confirmations/{HANDOFF_ID}-{status}-{timestamp}.json`
- Record format:

  ```json
  {
    "handoff_id": "HANDOFF-NNN",
    "from": "dept-id",
    "to": "dept-id",
    "work_item": "ชื่องาน",
    "confirmed_by": "department-id",
    "confirmed_at": "ISO-8601",
    "status": "acknowledged | rejected | need_clarify",
    "acknowledge_context": true,
    "understand_pending": true,
    "take_over": true,
    "notes": "optional notes"
  }
  ```

- Confirmation Checklist (สามสิ่งต้องยืนยัน):
  1. **acknowledge_context** — รับทราบ context และรายละเอียดของงาน
  2. **understand_pending** — เข้าใจ pending items และสิ่งที่ต้องทำต่อ
  3. **take_over** — รับช่วงต่อและรับผิดชอบงาน

- `--dry-run` ใช้ทดสอบก่อนบันทึกจริง

## Confirmation Flow

```
Sender                    Receiver              System
  │                         │                     │
  │─── Handoff Payload ────>│                     │
  │                         │                     │
  │                         │─── handoff_confirm ─>│
  │                         │    --status          │
  │                         │    acknowledged      │
  │                         │                     │──> bus/dispatch/confirmations/
  │                         │                     │    HANDOFF-NNN-acknowledged-ts.json
  │                         │                     │
  │<── confirmation.json ───│                     │
  │                         │                     │
```

## Status Meanings

| Status | Receiver's Intent | Sender Must |
|:-------|:------------------|:------------|
| `acknowledged` | รับทราบ + เข้าใจ + รับช่วงต่อ | รอผลงานจาก receiver |
| `need_clarify` | รับทราบ context แต่ยังไม่เข้าใจพอ | ให้ clarification เพิ่ม |
| `rejected` | ปฏิเสธ ไม่รับช่วง | แก้ไข handoff payload แล้วส่งใหม่ |

## Quality Gate

- ❌ ไม่อนุญาตให้ handoff โดยไม่มี acceptance criteria
- ❌ ไม่อนุญาตให้ handoff โดยไม่มี deadline
- ❌ ไม่อนุญาตให้ department เริ่มทำงานถ้า handoff ยังไม่มี confirmation record
- ✅ ทุก handoff ต้องระบุ priority
- ✅ ทุก handoff ต้องมี confirmation record (acknowledged) ก่อนเริ่ม execution

## Integration Scripts

| Asset | Path | Purpose |
|:------|:-----|:--------|
| Confirmation Script | `workers/handoff_confirm.py` | CLI สำหรับสร้าง confirmation record |
| Confirmations Storage | `bus/dispatch/confirmations/` | Directory สำหรับเก็บ confirmation records |
| Test Suite | `tests/test_handoff_confirm.py` | 24 test cases สำหรับ handoff confirmation |
