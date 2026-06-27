# ADR-002: Two-Tier Architecture — Control vs Data Layer

**วันที่:** 2026-06-26
**สถานะ:** Accepted ✅

## บริบท
การออกแบบ Department Head Architecture มีความเสี่ยงเรื่อง **Orchestration Bottleneck** — เมื่องานทุกชิ้นต้องผ่านหัวหน้าตลอดเวลา จะทำให้หัวหน้างานล้น และระบบช้าตาย

## ปัญหา
- ถ้าหัวหน้าต้องรับรู้ทุกข้อมูลดิบ → Context Window ล้น / ตัดสินใจช้า
- ถ้าทุก handoff ต้องผ่านกลาง → Pipeline กลายเป็น serial ทำงานช้า
- หัวหน้าไม่มีเวลาจัดการ Exception เพราะจมอยู่กับ routine

## ข้อตกลง (Decision)
แยกสถาปัตยกรรมเป็น 2 ชั้น:

### 1. Control Layer (ผ่านหัวหน้า)
หัวหน้าส่งต่อเฉพาะ:
- **Status:** "งาน #XYZ เสร็จ ✓" "งาน #XYZ ติดขัด ❌"
- **Goal/Target:** "งานใหม่: ทำ X ให้ได้ Y ภายใน Z"
- **Exception:** "ขอ escalate" "ขออนุมัติเพิ่ม"
- **High-level Artifact:** "ดูผลลัพธ์ได้ที่ URL/path นี้"

### 2. Data Layer (Auto — ไม่ผ่านหัวหน้า)
ข้อมูลดิบไหลผ่าน Central Bus:
- Code, Design Files, Reports, Outputs
- System กลางเป็นคนแจ้งเตือนหัวหน้าแผนกปลายทาง
- หัวหน้าเห็นแค่ notification + สรุปสั้น

## Flow Diagram

```
🧑‍💼 Head A
    │  สั่ง: "ทำงาน X" (Control)
    ▼
🛠️ Agent A1 ──(write)──→ 📦 CENTRAL BUS (Data Layer)
🛠️ Agent A2 ──(write)──→ 📦 CENTRAL BUS
                            │ (auto-notify)
                            ▼
                     🧑‍💼 Head B
                            │ "งานใหม่จากแผนก A มาแล้ว"
                            ▼
                      🛠️ Agent B1 ──(read from BUS)──→ 📦 CENTRAL BUS
```

## Handoff Hierarchy (แก้ Bottleneck)

| % | สถานการณ์ | Pathway |
|:--|:----------|:--------|
| 80% | งานปกติ ส่งตรง | Head A → Head B |
| 15% | งานติดขัด | Head คุยกันเอง |
| 5% | ปัญหาใหญ่ | Escalate → Orchestrator / CEO |

## ผลกระทบ
- **Positive:** ไม่มี bottleneck, หัวหน้ามีเวลา Exception จริงๆ
- **Positive:** Context Window ของหัวหน้าไม่พัง
- **Need Design:** ต้องออกแบบ Central Bus ให้ทำงานได้อัตโนมัติ
