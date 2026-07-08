# 🔬 R&D Lab — Session Synthesis

## สังเคราะห์วัตถุดิบทั้งหมด สู่แผน R&D Lab

| รายการ | รายละเอียด |
|:-------|:-----------|
| **Session** | 2026-07-08 |
| **สังเคราะห์โดย** | AI Research Scientist + Knowledge Curator |
| **จำนวนแหล่ง** | 5 external repositories |
| **Context** | 71% → จะรีเซ็ท — บันทึกก่อน |

---

## 1. วัตถุดิบที่รวบรวมได้

| # | แหล่ง | ประเภท | ขนาด | เหมาะกับ R&D Lab |
|:-:|:------|:-------|:-----|:-----------------|
| 1 | **[OmniScientist](https://github.com/Dr-SoloDev/OmniScientist)** 🆕 | Research Papers (Tsinghua) | 7 papers | **แกนหลัก** — AI Scientist ecosystem สำหรับ automated research |
| 2 | **[Agency Agents](https://github.com/Dr-SoloDev/agency-agents)** | Agent Personalities | 210 agents | **Personality Design** — ปรับปรุง SOUL.md |
| 3 | **[Antigravity Awesome Skills](https://github.com/sickn33/antigravity-awesome-skills)** | Skill Library | 1,935 skills | **Seed for SkillHub** — คัดเลือก skills |
| 4 | **[Awesome AI Dev Agents](https://github.com/Dr-SoloDev/awesome-ai-software-development-agents)** | Tool Index | 32 tools | **Tool Landscape** — รู้จัก tools ทั้งหมด |
| 5 | **[HackAgent](https://github.com/AISecurityLab/hackagent)** | Security Toolkit | — | **Security Research** — Red Team experiments |
| 6 | **[SkillHub](https://github.com/Dr-SoloDev/skillhub)** | Registry Platform | — | **โครงสร้างพื้นฐาน** — publish research output |

---

## 2. OmniScientist — แกนหลักของ R&D Lab

> จาก Tsinghua University — vision: fully automated scientific discovery

| Paper | ใช้กับ R&D Lab ยังไง |
|:------|:--------------------|
| **OmniScientist** | Blueprint สำหรับ R&D Lab — encoding research infrastructure |
| **MirrorMind** | Infuse expert knowledge into AI agents → เสริม SOUL.md design |
| **Deep Ideation** | AI generate research ideas → R&D Lab ใช้วางแผน research |
| **AgentExpt** | Automate experiment design → Experiment Designer ใช้ |
| **HybridQuestion** | Identify high-impact questions → Lead Researcher ใช้ |
| **Survey** | รู้ landscape ทั้งหมดของ AI Scientist field |
| **Scinetbench** | Benchmark สำหรับ literature retrieval |

---

## 3. Synthesis — R&D Lab Roadmap

### 3.1 Foundation (ทำทันที — session หน้า)

| ลำดับ | โปรเจค | Specialist | แหล่งวัตถุดิบ |
|:-----:|:--------|:-----------|:-------------|
| 1 | **ศึกษา OmniScientist papers** — อ่าน 7 papers, สรุป insight | AI Research Scientist + Knowledge Curator | OmniScientist |
| 2 | **ปรับปรุง SOUL.md Template v2** — เพิ่ม Vibe, Fail Triggers, Tools | Knowledge Curator | Agency Agents |
| 3 | **Seed SkillHub** — เลือก skills จาก Antigravity → publish `@solodev-rd/*` | Tool Smith + SkillHub Admin | Antigravity Skills |

### 3.2 Deep Research (2-4 สัปดาห์)

| ลำดับ | โปรเจค | Specialist | แหล่งวัตถุดิบ |
|:-----:|:--------|:-----------|:-------------|
| 4 | **Deep Ideation Implementation** — สร้าง concept network ของ SoloCorp tech stack | AI Research Scientist + Prototyper | OmniScientist |
| 5 | **AgentExpt Adaptation** — automate experiment design สำหรับ R&D Lab | Experiment Designer + Tool Smith | OmniScientist |
| 6 | **MirrorMind for SOUL.md** — infuse expert tacit knowledge เข้า agent profiles | AI Research Scientist + Knowledge Curator | OmniScientist + Agency Agents |

### 3.3 Experimental (1-2 เดือน)

| ลำดับ | โปรเจค | Specialist |
|:-----:|:--------|:-----------|
| 7 | **MCP Tool from Deep Ideation** — build tool ที่ช่วย generate research ideas | Prototyper + Tool Smith |
| 8 | **HackAgent + Red Team Experiment** — ใช้ HackAgent ทดสอบ agent security | AI Research Scientist (ร่วมกับ Security) |
| 9 | **Cross-Pollination** — เอาสิ่งที่เรียนจาก OmniScientist ไปแชร์ department อื่น | Wild Card + Knowledge Curator |

---

## 4. External Repositories Reference

| ชื่อ | Local Path | GitHub |
|:-----|:-----------|:-------|
| OmniScientist | `reference/omniscientist/` | [Dr-SoloDev/OmniScientist](https://github.com/Dr-SoloDev/OmniScientist) |
| Agency Agents | `reference/agency-agents/` | [Dr-SoloDev/agency-agents](https://github.com/Dr-SoloDev/agency-agents) |
| Antigravity Awesome Skills | `reference/antigravity-awesome-skills/` | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) |
| Awesome AI Dev Agents | `reference/awesome-ai-dev-agents/` | [Dr-SoloDev/awesome-ai-software-development-agents](https://github.com/Dr-SoloDev/awesome-ai-software-development-agents) |
| SkillHub | `reference/skillhub/` | [Dr-SoloDev/skillhub](https://github.com/Dr-SoloDev/skillhub) |
| HackAgent | (pip install) | [AISecurityLab/hackagent](https://github.com/AISecurityLab/hackagent) |

---

## 5. R&D Lab Team

| # | บทบาท | ไฟล์ |
|:-:|:------|:-----|
| 01 | 🔬 Lead Researcher | `team/01-lead-researcher.SOUL.md` |
| 02 | 🤖 AI Research Scientist | `team/02-ai-research-scientist.SOUL.md` |
| 03 | 🏗️ Prototyper / Builder | `team/03-prototyper.SOUL.md` |
| 04 | 📐 Experiment Designer | `team/04-experiment-designer.SOUL.md` |
| 05 | 🔧 Tool Smith | `team/05-tool-smith.SOUL.md` |
| 06 | 📚 Knowledge Curator | `team/06-knowledge-curator.SOUL.md` |
| 07 | 🃏 Wild Card | `team/07-wild-card.SOUL.md` |

---

*SoloCorp OS — System First, Everything Follows*  
*R&D Lab — Session Synthesis 2026-07-08*
