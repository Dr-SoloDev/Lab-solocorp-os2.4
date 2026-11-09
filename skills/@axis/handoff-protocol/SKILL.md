---
name: handoff-protocol
description: ทักษะการส่งมอบงานข้ามแผนกอย่างเป็นระบบ (Cross-Department Handoff Protocol) สำหรับ AXIS Framework
---

# 🔄 AXIS Handoff Protocol — Specialized Workflow Skill

## 🎯 Purpose & Overview
ทักษะนี้เป็นคู่มือปฏิบัติงานมาตรฐาน (SOP) สำหรับการส่งมอบงานข้ามแผนกใน **AXIS Framework** เพื่อให้เอเจนต์ผู้ส่งมอบ (**Sender Agent**) สามารถส่งต่อบริบท ไฟล์ผลงาน (Artifacts) และเกณฑ์การรับมอบงานไปยังเอเจนต์ผู้รับมอบ (**Receiver Agent**) ได้อย่างถูกต้อง ป้องกันปัญหาข้อมูลสูญหาย (Context Loss) และรักษาความปลอดภัยระดับองค์กร

---

## 📥 Required Inputs (ข้อมูลที่ต้องระบุ)

เอเจนต์ที่เรียกใช้ทักษะนี้ ต้องจัดเตรียมข้อมูลให้ครบถ้วน 4 ส่วน:
1. **`from_agent`**: ชื่อเอเจนต์ผู้ส่งมอบ (เช่น `@architect-songsak`, `@cfo-meetoo`)
2. **`to_agent`**: ชื่อเอเจนต์ผู้รับมอบ (เช่น `@orchestrator-wut`, `@content-creator-sek`)
3. **`artifacts`**: รายการไฟล์ หรือ Path ผลงานที่เตรียมไว้ส่งมอบ (เช่น `media/brief-v1.md`)
4. **`acceptance_criteria`**: เงื่อนไขและเป้าหมายที่แผนกรับมอบต้องดำเนินการต่อ

---

## 📋 Step-by-Step Execution Workflow (ขั้นตอนการปฏิบัติงาน)

### Step 1: Pre-Handoff Quality & Security Gate
ก่อนการส่งมอบงาน เอเจนต์ผู้ส่งมอบต้องทำการตรวจสอบดังนี้:
- **Security Check**: ตรวจสอบว่าไม่มีไฟล์ความลับ (เช่น `.env` หรือเอกสารใน `legal_vault/`) ติดไปในรายการส่งมอบ
- **Boundary Check**: ตรวจสอบว่าไฟล์ผลลัพธ์ได้รับการจัดเก็บในโฟลเดอร์ที่ถูกต้องตามสิทธิ์ประจำแผนก
- **Completion Check**: ตรวจสอบว่าเนื้อหาผลงานมีความสมบูรณ์ตามโจทย์ที่ได้รับมอบหมาย

### Step 2: Handoff Document Generation
สร้างไฟล์สรุปการส่งมอบงานในโฟลเดอร์ `docs/handoffs/` โดยใช้รูปแบบชื่อไฟล์:
`docs/handoffs/YYYYMMDD-HHMM-[from]-to-[to].md`

**โครงสร้างภายในไฟล์ Handoff Document:**
```markdown
# 📑 AXIS Handoff Record

- **Timestamp**: [วัน-เวลา]
- **From**: [Sender Agent]
- **To**: [Receiver Agent]
- **Status**: Ready for Review

## 📝 Executive Summary
[สรุปสิ่งที่ได้ดำเนินการเสร็จสิ้นในเฟสนี้]

## 📦 Delivered Artifacts
- `[path/to/file1]` — [คำอธิบายไฟล์]
- `[path/to/file2]` — [คำอธิบายไฟล์]

## 🎯 Next Step Acceptance Criteria
1. [สิ่งที่แผนกรับมอบต้องดำเนินการในขั้นตอนถัดไป]
2. [เกณฑ์การวัดผลสำเร็จ]

```

### Step 3: Notification & Delegation

1. แจ้งเตือน **Orchestrator (`@orchestrator-wut`)** เพื่อทำการอัปเดตสถานะใน AXIS Pipeline
2. ส่งมอบภารกิจไปยัง **Receiver Agent** พร้อมอ้างอิงไฟล์ Handoff Document ที่สร้างขึ้น

---

## 🚨 Error Handling & Rollback Protocol

* **Incomplete Input / Failed Gate**: หากแผนกรับมอบพบว่าไฟล์ผลลัพธ์ไม่ครบถ้วน ให้ตอบกลับด้วยสถานะ `HANDOFF_REJECTED` พร้อมระบุเหตุผล เพื่อให้แผนกผู้ส่งมอบกลับไปแก้ไข
* **Security Breach Detected**: หากพบการละเมิดสิทธิ์การเข้าถึงไฟล์ ให้ระงับ Pipeline ทันที และแจ้งเตือน **Legal (`@legal-tulya`)** เข้ามา Audit
