# Video Script — อย่าเพิ่งเชื่อเรา

> **Campaign:** customer-value-proof-2026-10-26  
> **Duration:** 38 seconds  
> **Format:** Vertical 9:16, Thai  
> **Status:** human-edited draft; not rendered, approved, or published  
> **Objective:** Invite solo builders to give specific feedback on what would make this workflow useful.

## Core Claim

SoloCorp OS is testing whether its Content Creator workflow helps a solo builder turn a brief into a reviewable script artifact. This clip does not claim customer value is proven or that SoloCorp OS matches or beats leading products.

## Scene-by-Scene

| Time | Visual direction | Voiceover | On-screen copy | Audio direction |
|:--|:--|:--|:--|:--|
| 0–4s | Original typography on a plain dark workspace. A cursor pauses, then the question appears. No stock or user footage. | **“คนเดียวจะสร้างซอฟต์แวร์ที่คนใช้จริงได้ไหม?”** | **คนเดียว สร้างของที่คนใช้จริงได้ไหม?** | Start dry. One restrained, original low hit on the question; omit if rights/source cannot be documented. |
| 4–11s | A one-line brief appears on screen; cut to a simple blank project board. Label this as an illustration, not a product UI. | **“เราอยากพิสูจน์คำถามนี้ด้วย SoloCorp OS แต่ตอนนี้ยังไม่มีหลักฐานว่าลูกค้าต้องการมัน”** | **ยังไม่มีคำตอบ** | A quiet, warm instrumental bed may enter. Keep voice clear and close. |
| 11–20s | Show a simple, clearly labeled workflow diagram: Brief → Script draft → Human review. Then show the real artifact status “scaffold” / campaign manifest, with sensitive local details hidden. | **“วันนี้เริ่มจากงานหนึ่งชิ้น: รับ brief สร้างร่างสคริปต์ เก็บไว้เป็นแคมเปญ แล้วเตรียมให้คนตรวจ”** | **Brief → Script draft → Human review**  
Small label: **ร่างที่ตรวจต่อได้ ไม่ใช่งานสำเร็จ** | Soft original click at each step; no sampled SFX. Small pause after “หนึ่งชิ้น”. |
| 20–29s | Hold on “scaffold” and a review checklist. Do not show a finished-render preview or imply that users have tested it. | **“ตอนนี้เราพิสูจน์ได้แค่ว่าระบบสร้างร่างและเก็บ manifest ไว้ตรวจต่อได้ ยังไม่ได้พิสูจน์คุณค่ากับลูกค้า หรือว่าเหนือกว่าเครื่องมือชั้นนำ”** | **Workflow มีให้ตรวจ**  
**คุณค่าต่อลูกค้า: ยังไม่พิสูจน์** | Lower music under the qualification; no dramatic success cue. |
| 29–38s | End card with two numbered questions and a comment prompt. Keep text inside mobile-safe area. | **“ถ้าคุณเป็น solo dev ช่วยตอบสองข้อ: งานไหนเสียเวลาซ้ำที่สุด และต้องเห็นหลักฐานอะไรจึงจะลองใช้?”** | **1. งานไหนเสียเวลาซ้ำที่สุด?**  
**2. ต้องเห็นหลักฐานอะไร ก่อนลองใช้?**  
**ตอบพร้อมเหตุผลใต้โพสต์** | Let the bed resolve gently. Leave a short silence after the final question. |

## Production Notes

- Treat all graphics as original diagrams, not screenshots of a finished SoloCorp product UI.
- Use no user audio, cloned voice, ElevenLabs, external generation provider, stock footage, or unlicensed music/SFX for this draft.
- Narration is text only at this stage. Any later recording or synthesis needs a separate decision.
- Keep Thai subtitles legible and within the vertical safe area. Add no performance statistics or customer testimonials.
- The FFmpeg runtime diagnostic is not clear for production rendering: it reports FFmpeg 7.0.2-static, missing `drawtext`, and an unverified security backport. Use synthetic-only checks until that is resolved.
- Do not publish. Human review and approval remain separate steps.

## Claims and Evidence

**Grounded in the repository**
- The Content MCP exposes tools to create a video-script artifact and store it in the campaign content bus; the script generator labels its initial output `scaffold`.
- Campaign manifests, human-edited artifact versions, and a publish review gate are implemented in the Content service.
- The current pilot brief explicitly treats customer value as a hypothesis and calls for audience feedback.

**Not established by this draft**
- That customers want SoloCorp OS, that the workflow saves time or money, that output quality is competitive with leading products, or that an audience will respond positively.
- No final video render, external audience review, or publication has happened in this task.

## Evaluation

Ask 3–5 Thai-speaking solo developers/builders to review the draft. Score each from 1–5 and retain their comments:
- Clarity: Can they explain what is being tested?
- Relevance: Does the problem match their work?
- Credibility: Does the clip avoid overstating what exists?
- Pacing: Does the message land within 38 seconds?
- Craft: Are visuals, captions, and audio cues coherent?

Record production minutes, human edit minutes, revision rounds, tool failures, and external cash spend separately. After any separately approved publication, track retention/completion, saves, shares, and substantive replies; views or likes alone are not proof of product value.

## Repository Evidence

- `solocorp_mcp/departments/content_mcp.py:1-5, 78-100, 178-221`
- `solocorp_mcp/departments/content_service.py:321-334, 421-475, 1017-1125`
- `docs/plans/CONTENT-CUSTOMER-VALUE-PILOT.md`
- `bus/evidence/2026-10-26/ffmpeg-skill-diagnostic.json`
