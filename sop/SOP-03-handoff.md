# SOP-03: Handoff — Head-to-Head ส่งต่องาน

**Owner:** All Department Heads  
**Version:** v1.0  
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

## Quality Gate

- ❌ ไม่อนุญาตให้ handoff โดยไม่มี acceptance criteria
- ❌ ไม่อนุญาตให้ handoff โดยไม่มี deadline
- ✅ ทุก handoff ต้องระบุ priority
