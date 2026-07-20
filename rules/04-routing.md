# 🧭 Routing — request นี้ไป department ไหน?

**แหล่งเดียว — ไม่ซ้ำกับที่ไหนอีก**

## Department Routing

| คำสำคัญ | แผนก | Head | Agent |
|:--------|:-----|:-----|:------|
| vision, strategy, decision | CEO | เทอโบ | `@ceo-turbo` |
| การเงิน, งบ, cost, budget | CFO | meetoo | `@cfo-meetoo` |
| การตลาด, brand, content | CMO | มาร์ค | `@cmo-mark` |
| pipeline, orchestration, workflow | Orchestrator | พี่วุฒิ | `@orchestrator-wut` |
| architecture, bus, routing | Architect | พี่ทรงศักดิ์ | `@architect-songsak` |
| product, feature, PRD, roadmap | Product | โปรดัค | `@product-produck` |
| code, backend, frontend, implement | Engineering | ช่างฟูล | `@changful` |
| UX, design system, brand visual | Design | ครีเอท | `@design-kreet` |
| UI, component, interface | UI Designer | UI Designer | `@ui-designer` |
| test, QA, bug, quality | QA | QA-ทีม | `@qa` |
| sales, deal, pipeline | Sales | เซลส์ | `@sales` |
| support, customer | Support | ซัพพอร์ต | `@support` |
| legal, compliance, contract | Legal | ตุลย์ | `@legal-tulya` |
| blockchain, solana, DeFi, smart contract | Web3 | อัยวา | `@web3-aywa` |
| content, caption, video, campaign | Content | เสก | `@content-creator-sek` |
| network, CDN, VPN, DNS, infra | NetEng | นีต | `@neteng-neet` |
| security, threat, incident, IR | CyberSec | ซาย | `@cybersec-sai` |
| psychology, behavior, bias, UX research | Psychology | จิต | `@psych-jit` |
| research, prototype, experiment | R&D Lab | Lead Researcher | `@rd-lab` |

## Architect Team (under พี่ทรงศักดิ์)

| บทบาท | Agent |
|:------|:------|
| ตรวจสอบ audit trail | `@pipeline-auditor` |
| กำหนด routing rules | `@routing-config-agent` |
| เฝ้าสุขภาพ pipeline | `@monitor-watchdog` |
| จัดการ exception | `@exception-triage` |
| รัน pipeline ตาม schedule | `@cron-pipeline` |
| SkillHub Registry | `@skillhub-admin` |

## กฏ

- ถ้า request ไม่อยู่ใน scope ใด → route ไป CEO
- ถ้า request ข้ามหลายแผนก → บอกว่าต้องประสาน department ไหนบ้าง
- ทำงานใน **บทบาทหัวหน้า** ไม่ใช่ specialist
