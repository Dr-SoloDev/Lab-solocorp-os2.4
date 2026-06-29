# SoloCorp OS Workflow — Deliverables (2026-06-15)

**สร้างโดย:** คุณวุฒิ (Architect) + พี่ทรงศักดิ์ (Orchestrator) ตามคำสั่ง CEO เทอโบ
**สถานะ:** ✅ Complete
**Files location:** `~/projects/solocorp-os/workflows/`

## Files Created

| File | Lines | Creator | Description |
|------|-------|---------|-------------|
| `workflow-diagram.md` | 378 | คุณวุฒิ (Architect) | Mermaid.js 8 แผนผัง — Vision Pipeline, internal workflow 6 แผนก, Exception Flow, RACI Matrix 16 activities, 10 Golden Rules |
| `pipeline-template.md` | 993 | พี่ทรงศักดิ์ (Orchestrator) | Handoff Card Template (Full + Minimal), Pipeline State Machine 10 states, Sequential Queue Logic, Exception Handling 7 strategies, example Handoff Cards ทุกแผนก, Pipeline Log Format |

## Key Content

### Workflow Diagram (คุณวุฒิ)
- **Vision Pipeline:** Dr.solodev → CEO(เทอโบ) → Architect(คุณวุฒิ) → CFO(meetoo) → Orchestrator(พี่ทรงศักดิ์) → Implementation → Legal(ตุลย์) + CMO(มาร์ค) → CEO รายงาน
- **Internal workflows:** 6 แผนก แต่ละแผนกมีกระบวนการภายในของตัวเอง
- **RACI Matrix:** 16 กิจกรรม × 6 แผนก — ใคร Responsible/Accountable/Consulted/Informed
- **Exception Flow:** CEO escalate path, CFO veto path, emergency/crisis bypass

### Pipeline Template (พี่ทรงศักดิ์)
- **Handoff Card Format:** Standardized task card with FROM/TO/Context/Artifact/Deadline/Verification
- **10 Pipeline States:** Vision → Queued → Assigned → InDesign → InReview → Approved → InExecution → InVerification → Completed → Blocked
- **7 Exception Strategies:** CFO Veto, CEO Override, Timeout Escalate, Emergency Bypass, Quality Gate Failed, Resource Unavailable, Dependency Missing

## Usage

When referencing these in future sessions:
```bash
# Load workflow diagram
read_file ~/projects/solocorp-os/workflows/workflow-diagram.md

# Load pipeline template  
read_file ~/projects/solocorp-os/workflows/pipeline-template.md
```

These are the canonical workflow files for SoloCorp OS 2.0. Any session needing to understand the handoff chain, decision rights, or pipeline states should reference these files.
