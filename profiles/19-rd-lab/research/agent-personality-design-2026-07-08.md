# 🔬 R&D Lab — Research Report

## Agent Personality Design: Lessons from Agency Agents

| รายการ | รายละเอียด |
|:-------|:-----------|
| **Research ID** | `R&D-2026-07-08-001` |
| **หัวข้อ** | Agent Personality Design Patterns |
| **แหล่งศึกษา** | [Agency Agents](https://github.com/Dr-SoloDev/agency-agents) (210 agents, 16 divisions) |
| **ทีมวิจัย** | AI Research Scientist + Knowledge Curator |
| **วันที่** | 2026-07-08 |
| **สถานะ** | 🟢 Complete |

---

## 1. Abstract

ศึกษา 210 agent personalities จาก Agency Agents collection เพื่อหา design patterns ที่สามารถนำมาปรับปรุง SoloCorp SOUL.md system — ทั้ง 19 departments และ 55+ specialist profiles

---

## 2. Key Findings

### 2.1 What Agency Agents Does Better (5 Core Patterns)

| # | Pattern | จาก | คำอธิบาย |
|:-:|:--------|:---|:----------|
| 1 | **Vibe One-Liner** | ทุก agent | `vibe:` field — ประโยคเดียวที่ capture ตัวตนทั้ง agent |
| 2 | **Negative-Space Rules** | Testing | `## "AUTOMATIC FAIL" Triggers` — บอกว่าอะไรที่ทำให้ FAIL ทันที |
| 3 | **Invisible Weight** | Chief of Staff | ความรับผิดชอบที่คนอื่นไม่เห็น — constraints ที่ agent แบกอยู่ |
| 4 | **Three-Tier Architecture** | Narrative Designer | Tier 1: surface → Tier 2: engaged → Tier 3: deep |
| 5 | **Named Personas + Backstory** | หลาย agent | มีชื่อ มีประสบการณ์ มีบุคลิก — ไม่ใช่แค่ function |

### 2.2 Unique Patterns Found

**A. The "AUTOMATIC FAIL" Triggers** (Testing Division)
> *"Any agent claiming 'zero issues found'"* — ใช้ negative space สร้าง identity ที่ชัดเจน  
> → SoloCorp เอามาใช้: แต่ละ department ควรมี `## 🚫 สิ่งที่ทำให้ FAIL ทันที`

**B. ADHD-Aware Design** (Chief of Staff)
> *"Present the one thing that matters most right now"*  
> → SoloCorp เอามาใช้: CEO และ department heads มี instruction สำหรับ neurodivergent users

**C. Pattern Recognition Sub-Section** (หลาย agent)
> *"You've seen too many 'A+' certifications for basic websites that weren't ready"*  
> → SoloCorp เอามาใช้: แต่ละ department ควรมี section ที่บอก pattern ที่เคยเจอบ่อย

**D. Vibe Field in Frontmatter**
> รูปแบบ: `vibe: "Screenshot-obsessed QA who won't approve anything without visual proof"`  
> → SoloCorp เอามาใช้: เพิ่ม `Vibe` field ในทุก SOUL.md

### 2.3 What SoloCorp Does Better (Keep These)

| # | Pattern | อย่าเปลี่ยน |
|:-:|:---------|:------------|
| 1 | **Hierarchy & Structure** | CEO → Department → Specialist — รู้ escalation path |
| 2 | **Routing System** | CLAUDE.md, `/handoff`, `/pipeline` |
| 3 | **Decision Framework** | RAPID + Core Mode (Command/Strategic/Review) |
| 4 | **Cross-Department Reference** | "Working With", "Always-Read First" |
| 5 | **KPIs in Org Context** | วัดผลได้จริง ไม่ใช่ abstract |
| 6 | **ภาษาไทย + บุคลิกไทย** | ชื่อเล่น ความเป็นครอบครัว — จุดแข็งที่ไม่ควรเปลี่ยน |

---

## 3. Recommendations

### Priority 1: Improved SOUL.md Template

เพิ่ม 5 fields ใหม่:

| Field | ตัวอย่าง | จาก Pattern |
|:------|:---------|:-----------|
| `Vibe` | "Spec = contract — ไม่เพิ่ม ไม่ลด ไม่เดา" | Vibe One-Liner |
| `Tools` | "Python, FastAPI, Docker, PostgreSQL" | Tools List |
| `When to Use` | "Implement spec, code review, incident" | Activation Trigger |
| `When NOT to Use` | "Architecture → @architect, Strategy → @product" | Negative Space |
| `Fail Triggers` | "Spec เปลี่ยนโดยไม่อัปเดต, merge โดยไม่ review" | Automatic Fail |

### Priority 2: Deepen Specialist Profiles

| ปัจจุบัน (SOUL.md) | เป้าหมาย (ใหม่) |
|:-------------------|:----------------|
| 38-120 บรรทัด | 150-250 บรรทัด |
| Factual / สั้น | มี personality + backstory |
| ไม่มี code examples | มี code snippet จริง |
| ไม่มี tools list | มี capabilities section |

### Priority 3: Add Pattern Recognition

ในทุก department SOUL.md เพิ่ม:
```markdown
### 🔁 Pattern Recognition
อาการที่เจอบ่อย:
- X → มักเกิดจาก Y
- ถ้า Z → ให้ทำ W
```

---

## 4. Next Steps

| ลำดับ | อะไร | ใครทำ |
|:-----:|:-----|:------|
| 1 | ปรับปรุง SOUL.md template ต้นแบบ | Knowledge Curator |
| 2 | ทดลองใช้กับ R&D Lab profiles ก่อน | Lead Researcher |
| 3 | ถ้าใช้ได้ → ขยายไปทุก department | All Dept Heads |
| 4 | Publish improved template สู่ SkillHub | SkillHub Admin |

---

## 5. References

- [Agency Agents](https://github.com/Dr-SoloDev/agency-agents) — 210 agent personalities
- [Antigravity Awesome Skills](https://github.com/sickn33/antigravity-awesome-skills) — 1,935+ skills (SKILL.md format)
- SoloCorp SOUL.md — 19 departments, 55+ specialists

---

*R&D Lab — แล็บของ Dr.solodev*  
*Research Report v1.0 — AI Research Scientist + Knowledge Curator*
