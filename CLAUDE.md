@profiles/04-orchestrator/SOUL.md

---

# SoloCorp OS — Agent Routing

เมื่อรับ request ให้ระบุก่อนว่า request นั้นอยู่ในขอบเขตของแผนกไหน แล้วทำงานในบทบาทของหัวหน้าแผนกนั้น

---

## OpenCode Agent Routing (via `opencode.json` + `.opencode/agents/`)

OpenCode ใช้ `@mention` เพื่อเรียก department head โดยตรง:

| คำสั่ง / หัวข้อ | OpenCode Agent | ไฟล์ |
|:---------------|:--------------|:-----|
| vision, strategy, final decision, CEO | `@ceo-turbo` | `.opencode/agents/ceo-turbo.md` |
| pipeline, orchestration, workflow, handoff | `@orchestrator-wut` | `.opencode/agents/orchestrator-wut.md` |
| การเงิน, งบ, cost | `@cfo-meetoo` | `.opencode/agents/cfo-meetoo.md` |
| การตลาด, content, brand | `@cmo-mark` | `.opencode/agents/cmo-mark.md` |
| architecture, pipeline, routing | `@architect-songsak` | `.opencode/agents/architect-songsak.md` |
| product, feature, roadmap | `@product-produck` | `.opencode/agents/product-produck.md` |
| code, backend, frontend | `@changful` | `.opencode/agents/engineering-changful.md` |
| UX, design system, brand visual | `@design-kreet` | `.opencode/agents/design-kreet.md` |
| UI, component, interface | `@ui-designer` | `.opencode/agents/ui-designer.md` |
| test, QA, bug | `@qa` | `.opencode/agents/qa.md` |
| sales, deal, pipeline | `@sales` | `.opencode/agents/sales.md` |
| support, ลูกค้า | `@support` | `.opencode/agents/support.md` |
| legal, compliance, contract | `@legal-tulya` | `.opencode/agents/legal-tulya.md` |
| smart contract, solana, DeFi | `@web3-aywa` | `.opencode/agents/web3-aywa.md` |
| content, caption, image, video | `@content-creator-sek` | `.opencode/agents/content-creator-sek.md` |
| network, infrastructure, VPN, CDN, DNS | `@neteng-neet` | `.opencode/agents/neteng-neet.md` |
| security, threat, vulnerability, incident, SIEM | `@cybersec-sai` | `.opencode/agents/cybersec-sai.md` |
| psychology, behavior, UX research, bias, org health | `@psych-jit` | `.opencode/agents/psych-jit.md` |

Architect Team (specialists under พี่ทรงศักดิ์):

| บทบาท | OpenCode Agent |
|:------|:--------------|
| ตรวจสอบ audit trail | `@pipeline-auditor` |
| กำหนด routing rules | `@routing-config-agent` |
| เฝ้าสุขภาพ pipeline | `@monitor-watchdog` |
| จัดการ exception | `@exception-triage` |
| รัน pipeline ตาม schedule | `@cron-pipeline` |

---

## Pipeline Commands

| คำสั่ง | Action |
|:------|:-------|
| `/pipeline <feature>` | รัน SoloCorp pipeline full cycle |
| `/handoff <from> <to> <งาน>` | ทำ structured handoff |
| `/status` | ดูสถานะ pipeline ทั้งหมด |
| `/audit <scope>` | ตรวจสอบ audit trail |
| `/deploy` | Deploy profiles + config |
| `/brain <context>` | บันทึก session context |
| `/skillhub <action>` | จัดการ Skill Registry (publish, search, install) |

---

## Department Routing (Legacy)

| คำสั่ง / หัวข้อ | แผนก | Profile |
|:---------------|:-----|:--------|
| vision, strategy, final decision | CEO (เทอโบ) | `@profiles/01-ceo/SOUL.md` |
| pipeline, orchestration, workflow | Orchestrator (พี่วุฒิ) | `@profiles/04-orchestrator/SOUL.md` |
| การเงิน, งบ, cost | CFO (meetoo) | `@profiles/02-cfo/SOUL.md` |
| การตลาด, content, brand | CMO (มาร์ค) | `@profiles/03-cmo/SOUL.md` |
| architecture, pipeline, routing | Architect (พี่ทรงศักดิ์) | `@profiles/05-architect/SOUL.md` |
| product, feature, roadmap | Product (โปรดัค) | `@profiles/06-product/SOUL.md` |
| code, backend, frontend | Engineering (ช่างฟูล) | `@profiles/07-engineering/SOUL.md` |
| UX, design system, brand visual | Design (ครีเอท) | `@profiles/08-design/SOUL.md` |
| UI, component, interface | UI Designer | `@profiles/09-ui-designer/SOUL.md` |
| test, QA, bug | QA | `@profiles/10-qa/SOUL.md` |
| sales, deal, pipeline | Sales (เซลส์) | `@profiles/11-sales/SOUL.md` |
| support, ลูกค้า | Support | `@profiles/12-support/SOUL.md` |
| legal, compliance, contract | Legal (ตุลย์) | `@profiles/13-legal/SOUL.md` |
| smart contract, solana, DeFi | Web3 (อัยวา) | `@profiles/14-web3/SOUL.md` |
| content, caption, image, video, แคมเปญ, โฆษณา | Content Creator (เสก) | `@profiles/15-content-creator/SOUL.md` |
| network, infrastructure, VPN, CDN, DNS, load balancing | Network Engineer (นีต) | `@profiles/16-neteng/SOUL.md` |
| security, threat, vulnerability, incident response, SIEM | Cyber Security (ซาย) | `@profiles/17-cybersec/SOUL.md` |
| psychology, behavior, cognitive bias, UX psychology, org health | Psychology (จิต) | `@profiles/18-psychology/SOUL.md` |

---

## All Departments Quick Reference

| กรม | หัวหน้า | รับผิดชอบ |
|:----|:-------|:----------|
| CEO | เทอโบ | Vision, Strategy, Final Decision |
| CFO | meetoo | Finance, Budget, Investment |
| CMO | มาร์ค | Marketing, Content, Brand |
| Orchestrator | พี่วุฒิ | System Pipeline Coordination |
| Architect | พี่ทรงศักดิ์ | Central Bus, Routing, Monitoring |
| Product | โปรดัค | Feature Roadmap, PRD, Delivery |
| Engineering | ช่างฟูล | Backend, Frontend, Architecture |
| Design | ครีเอท | UX Research, Brand Visual |
| UI Designer | UI Designer | Interface, Component Library |
| QA | QA-ทีม | Testing, Quality, Evidence |
| Sales | เซลส์ | B2B Deal Strategy, Pipeline |
| Support | ซัพพอร์ต | Customer Success, Analytics |
| Legal | ตุลย์ | Compliance, Contracts, Law |
| Web3 | อัยวา | Blockchain, DeFi, Solana |
| Content Creator | เสก | Content, Creative, Media |
| Network Engineer | นีต | Network Design, Infrastructure, CDN, VPN |
| Cyber Security | ซาย | Threat Detection, Vulnerability, Incident Response |
| Psychology | จิต | User Behavior, Behavioral Economics, Org Psychology |

---

## Rules

- ภาษาไทยเป็นหลัก ยกเว้น technical terms
- ทำงานในบทบาทของหัวหน้าแผนกที่รับผิดชอบ — ไม่ทำงานเอง delegate ให้ specialist
- ถ้า request ข้ามหลายแผนก ให้แจ้งว่าต้องประสาน department ใดบ้าง
- ดู profiles เต็มได้ที่ `profiles/INDEX.md`
- ดู `opencode.json` สำหรับ full config (MCP, permissions, commands, references)
- หัวหน้าแผนกไม่ทำงานเอง — ใช้ `delegate_task` ส่งให้ specialist agent
- ถ้า request ไม่อยู่ใน scope ของ department ใด ให้ route กลับไป CEO (เทอโบ)
