# 🔄 Pipeline — คำสั่ง, handoff, workflow

## Slash Commands

| คำสั่ง | ทำอะไร |
|:------|:-------|
| `/pipeline <feature>` | รัน SoloCorp pipeline: Spec → Plan → Build → QA → Deliver |
| `/handoff <from> <to> <task>` | ทำ structured handoff พร้อม context pack |
| `/status` | ดูสถานะ pipeline + bus + governance health |
| `/audit <scope>` | ตรวจ audit trail + compliance |
| `/deploy` | Build profiles → export agents → validate → commit |
| `/brain <context>` | บันทึก session context ลง brain |
| `/pipeline-bridge <from> <to> <task>` | ส่ง task ข้ามแผนก structured handoff + audit trail |
| `/mirror-check` | ตรวจ decision สะท้อน Owner (L3+) |
| `/route <request>` | Classify request → department + agent |

## Handoff Protocol

```json
{
  "handoff": {
    "from": "Head A",
    "to": "Head B",
    "work_item": "task-id",
    "status": "ready",
    "artifacts": ["path/to/artifacts"],
    "deadline": "YYYY-MM-DD",
    "priority": "high"
  }
}
```

ทุก handoff ต้องมี:
- current state summary
- artifacts (files, decisions, pending)
- context pack
- receiver confirmation

## Pipeline Phases

1. **Spec** — requirements, ยืนยัน scope
2. **Plan** — แตก tasks, ระบุ department
3. **Build** — delegate ไป Engineering/Design
4. **QA** — 3 rounds max (dev ↔ qa)
5. **Deliver** — สรุป + handoff report
