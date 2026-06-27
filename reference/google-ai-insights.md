# Google AI Insights — Architecture Design (2026-06-26)

> ข้อมูลจาก Google AI (AI Mode) ที่ค้นหาโดย Dr.Solodev
> ใช้ออกแบบ Department Architecture + Central Bus System

---

## Key Insight 1: Two-Tier Architecture

ในองค์กรใหญ่ที่ทำงานเป็นระบบ จะไม่มีแผนกใดแผนกหนึ่งทำหน้าที่ "ส่งต่อข้อมูล" ให้แผนกอื่นโดยเฉพาะ
แต่จะใช้ **ระบบสารสนเทศส่วนกลาง (ERP/Workflow Automation)** และ **PMO** เป็นตัวขับเคลื่อน

**โครงสร้างที่ Google AI แนะนำ:**

```
Data Layer (ชั้นข้อมูล - ไม่ผ่านหัวหน้า):
  → ข้อมูลดิบ, ผลลัพธ์, โค้ด, เอกสาร
  → ส่งผ่าน "ระบบกลาง (Shared State / Database / ERP Agent)" โดยตรง
  → หัวหน้าแผนกไม่ต้องรับรู้รายละเอียดข้างใน

Control Layer (ชั้นสั่งการ - ผ่านหัวหน้า):
  → สถานะของงาน (Status) และผลลัพธ์ระดับสูง (High-level Artifacts) เท่านั้น
```

## Key Insight 2: Central Bus Agent (ERP/PMO Agent)

หัวใจคือการสร้าง "Central Bus Agent" หรือ "Environment State Agent" ตัวเดียว
ทำหน้าที่เหมือนระบบ ERP/Jira ส่วนกลาง

### Data Schema (Shared State)
```json
{
  "project_id": "PRJ-2026-001",
  "global_status": "IN_PROGRESS",
  "current_phase": "DEVELOPMENT",
  "departments_state": {
    "product_management": {
      "status": "COMPLETED",
      "artifacts_summary": "...",
      "raw_data_pointer": "db://product/prd_v1.2.md"
    },
    "engineering_tech": {
      "status": "IN_PROGRESS",
      "artifacts_summary": "...",
      "raw_data_pointer": "db://engineering/repo_branch_01"
    }
  },
  "workflow_routing_rules": {
    "on_product_completed": "trigger engineering_tech",
    "on_engineering_completed": "trigger qa_testing",
    "on_qa_completed": "trigger marketing AND operations"
  }
}
```

### Central Bus Protocol

**Input (จาก Agent ทุกตัว):**
- ส่งการอัปเดตทั้งหมดมาที่ Central Bus
- ห้าม Agent ข้ามแผนกคุยกันเองโดยไม่ผ่าน Bus

**Processing:**
1. Parse sender identity + department + status
2. Update departments_state ใน JSON schema
3. Check workflow_routing_rules
4. Generate notification

**Output (ถึง Department Head):**
- **To:** Head of [Department]
- **Project Context:** 1-sentence summary
- **Current Trigger:** Why are they being pinged?
- **High-level Summary:** Max 3 bullet points
- **Data Access Link:** Pointer to raw data
- **Expected Action:** What to do next

## Key Insight 3: 3 สิ่งที่ใส่ใน Profile หัวหน้าแผนก

1. **Goal Alignment** (แปลงคำสั่ง):
   รับเป้าหมายใหญ่จาก CEO → แตกเป็น Task → แจกจ่ายให้ Agent ลูกน้อง

2. **Internal Orchestration** (ควบคุมภายใน):
   ติดตามสถานะลูกน้องในแผนกตนเอง

3. **Exception Handling** (จัดการเมื่อเกิดปัญหา):
   กระโดดลงมาแก้ไขเฉพาะเมื่อระบบแจ้งเตือนว่างานเลทหรือลูกน้องทำไม่ผ่านซ้ำๆ

## สิ่งที่หัวหน้าแผนก "ไม่ต้องรู้/ไม่ต้องทำ"

- ❌ ไม่ต้องตรวจงานลูกน้องทีละบรรทัด (ให้ QA Agent ตรวจแทน)
- ❌ ไม่ต้องคีย์ข้อมูลข้ามแผนกเอง (ให้ลูกน้องอัปเดตระบบกลาง)

---

## การประยุกต์ใช้กับ Lab-solocorp-os2.4

Google AI ช่วยยืนยันทิศทางที่เราออกแบบไว้:
- ✅ Two-Tier Architecture → ตรงกับ ADR-002
- ✅ Central Bus → ตรงกับที่เรากำลังจะ Design
- ✅ Department Head ไม่รับ Data Layer → สอดคล้องกับ Pillar 1
- ✅ Exception Handling → Ownership Mindset (Pillar 3)

**สิ่งที่ Google AI เพิ่มเติมที่เรายังไม่ได้คิด:**
- 🔥 Data Schema สำหรับ Shared State (JSON)
- 🔥 Protocol สำหรับ Input/Output ของ Central Bus
- 🔥 Workflow Routing Rules (Dependency Chain)
- 🔥 Outbound Notification Template
