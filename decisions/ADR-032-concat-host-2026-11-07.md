# ADR-032: Concat Host — Suspend MCP on This Host, Local Pipeline Unchanged

**วันที่:** 2026-11-07
**สถานะ:** Proposed — D1 only, NOT PASSED (D0/NOT PASSED, no config change in this task)
**Owner:** Architect พี่ทรงศักดิ์ (Head of Architect) — maker of decision doc; checker is separate (CEO/QA per `rules/06-certification.md`)
**ที่มา:** `central_bus/content/ceo-phase4-kickoff-20261107_20261107T051623810915Z.md` (Phase 4 Task 1 — Concat host DECISION doc FIRST, before doc cleanup)
**เกี่ยวกับ:** Phase 4 frozen campaigns (Phase1-3: `campaign_synth_phase1_20261107` v5, `campaign_synth_phase2_20261107` v7, `campaign_synth_phase3_20261107` v7 — NO asset changes) · Content Creator Concat workflow (`render_campaign_with_concat`) · local-media path (`render_campaign_media_local`) — **untouched by this ADR**

---

## บริบท

Concat 0.2.8 AppImage ที่ `/home/drsolodev/.opencode/concat/Concat-0.2.8-x86_64.AppImage` (132M, ELF, `--appimage-version` ทำงานได้) ถูกเปิดเป็น MCP ผ่าน `opencode.json` (`mcp.concat`, คำสั่ง `Concat --mcp headless`) — **launch ไม่ผ่าน** บน host/container นี้:

```
/usr/bin/fusermount3 mount failed Operation not permitted   (exit 127, open dir No such file)
```

Host นี้ปฏิเสธ FUSE mount (ไม่มี `SYS_ADMIN` / สิทธิ์ `/dev/fuse`) เลยขยาย AppImage ไม่ได้ตั้งแต่ขั้นตอน mount

Phase 4 เป็น docs/config/decision only — ไม่รัน render ใหม่, ไม่เปลี่ยน code behavior, ไม่ publish อะไร การตัดสินข้อนี้ต้องมาก่อนงาน doc cleanup (kickoff ข้อ 1/5)

---

## Root cause (ที่ตรวจสอบแล้ว, 2026-11-07)

| ประเด็น | ข้อเท็จจริง |
|:--|:--|
| Binary มีจริง | `Concat-0.2.8-x86_64.AppImage` 132M, ELF, `--appimage-version` ทำงาน — ไม่ใช่ "ไม่มีไฟล์" |
| Launch path | `opencode.json` → `mcp.concat.command` = `[Concat-0.2.8-x86_64.AppImage, --mcp, headless]` → AppImage runtime เรียก `fusermount3` เพื่อ mount |
| จุดล้มเหลว | `/usr/bin/fusermount3 mount failed Operation not permitted`, exit 127 — mount ก่อนเปิด dir |
| Host limitation | container/host นี้ไม่มี `SYS_ADMIN` / ไม่ให้ mount FUSE — เป็น **host capability** ไม่ใช่ Concat bug และไม่ใช่ SoloCorp MCP bug |
| `content-creator` env | `opencode.json` ยังส่ง `CONCAT_BIN` ให้ Content MCP (`mcp.content-creator.env.CONCAT_BIN`) — ค่านี้ชี้ไฟล์เดียวกัน |

> คุณภาพ AppImage ไม่ได้ถูกพิสูจน์บน host ที่ mount ได้ (evidence 2026-10-30 ใน `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md:139-168` เคยรัน Concat render สำเร็จ) — ADR นี้ตัดสิน **เฉพาะ host นี้** ไม่ได้ตัดสินคุณภาพ Concat เอง

---

## ผลกระทบ (Impact — วงแคบ)

- **กระทบเฉพาะ** `render_campaign_with_concat` path (ผ่าน `media_service.py` → Concat MCP stdio: `project_create` → `media_import` → `clip_add` → `captions_add` → `export_start`/`export_wait`)
- **ไม่กระทบ** local-media path (`render_campaign_media_local` → FFmpeg CLI ตรง + Piper + Three.js/Playwright) — เป็นเส้นทางที่พิสูจน์แล้วใน Phase 1–3 โดยไม่ต้องใช้ Concat
- **ไม่กระทบ** SoloCorp MCP อื่น (central-bus, content-creator, engineering, qa, github) — `content-creator` MCP ยังโหลดได้ปกติ เพียงเครื่องมือ Concat จะล้มที่ call time
- **Noise:** OpenCode แสดงสถานะ MCP `concat` ล้มเหลวทุก session — เสียงรบกวนที่ไม่เกี่ยวกับงานจริงของ Phase 4

---

## ตัวเลือก (Options matrix)

| # | ตัวเลือก | ความพยายาม (Effort) | ความเสี่ยง (Risk) | ย้อนกลับได้ | OpenCode status noise | ผลต่อผู้ใช้ Concat workflow |
|:--|:--|:--|:--|:--|:--|:--|
| **1** | **Disable `concat` ใน `opencode.json` (`enabled: true → false`) + เอกสาร suspended** | ~5 นาที (1 บรรทัด + อัปเดต runbook โน้ตเดียว) | ต่ำสุด — ไม่แตะ binary, ไม่แตะ Content MCP | **ทำทันที** — เปลี่ยนกลับ `false → true` | **หยุดทันที** (ไม่มี MCP ล้มเหลวให้แสดง) | เปลี่ยนเป็น **local-only mode** ชัดเจน; Concat workflow ถูก suspend แบบเปิดเผย ไม่ใช่ล้มเงียบ |
| **2** | **หลบด้วย `--appimage-extract`** (extract ลง writable dir แล้วยิง AppRun/extracted binary ตรง, ไม่ mount) | ปานกลาง — Engineering ต้องทดสอบ feasibility ใน `/tmp/opencode` (non-destructive), เช็ก disk, บันทึก `CONCAT_BIN` ใหม่, อัปเดต `opencode.json` 2 จุด (`mcp.concat.command` + `mcp.content-creator.env.CONCAT_BIN`) + runbook | ปานกลาง — extract แล้วรันได้ไม่แน่นอนบน host นี้ (ยังอาจขาด runtime libs, permissions, Qt/GUI plugin ขาด); AppImage version/extracted runtime drift; ต้อง restart OpenCode ทดสอบซ้ำ | ย้อนกลับได้ (กลับไป `--mcp` เดิม + binary เดิม) แต่ใช้เวลา | แก้ได้ถ้า extract สำเร็จจริง — ก่อนหน้านั้นยัง noise | ถ้าสำเร็จ = ได้ Concat workflow กลับบน host เดิม; ถ้าล้มเหลว = เสียเวลาหลบทิ้งโดยไม่ได้อะไร |
| **3** | **คง `enabled: true` + เอกสาร known-failed** | 5 นาที (เอกสารอย่างเดียว) | ต่ำทางเทคนิค แต่สูงทาง trust — ทุก session แสดงล้มเหลว, ผู้ใช้อ่านเอกสารแล้วเจอ MCP แตกเป็นสัญญาณ "ระบบพัง" | ทันที | **คงเดิม (noise ทุก session)** | ผู้ใช้ Concat workflow ยังเจอ failure แบบเงียบที่ call time, ต้องอ่าน docs ก่อนถึงจะรู้ |
| **4** | **ย้าย Concat editing ไป host ที่ mount FUSE ได้** | สูง — จัดหา/ยืนยัน host ใหม่, ย้าย binary/project ดูแล `CONCAT_MCP_ROOTS` เดียวกัน, re-verify E2E บน host ใหม่, docs อีกชุด | ปานกลาง-สูง — project path เป็น `/data/projects/Lab-solocorp-os2.4/central_bus/content` ผูกกับ host นี้; ย้ายแล้วต้องดูแล 2 host | กลับ_host เดิมได้ แต่ configuration สองชุดต้องดูแลคู่กัน | noise บน host นี้ถ้ายัง `enabled` อยู่; host ใหม่ไม่มี noise | Concat workflow ยังใช้ได้ — แต่ **ไม่อยู่ในขอบเขต Phase 4** (Phase 4 คือ docs/config/decision เท่านั้น) |

---

## การตัดสินใจ (Recommendation — Ratify CEO leaning (1))

**ตัดสิน: ตัวเลือก (1) — disable `concat` ใน `opencode.json` + document ว่า suspended จนกว่า host จะ mount FUSE ได้**

CEO ไม่ได้ผิด — (1) ตรงกับข้อจำกัดจริงที่สุด: binary มีจริงแต่ host ไม่รองรับ FUSE, local pipeline ไม่ต้องการ Concat, และ Phase 4 ห้ามเปลี่ยน behavior/render ใด ๆ (2) ยังไม่ผ่าน feasibility test, (4) ไม่อยู่ในขอบเขต Phase 4, (3) เก็บ noise ไว้โดยไม่ได้อะไร

เหตุผลหลัก 3 ข้อ:

1. **Reversible & ถูกสุด** — เปลี่ยนกลับภายใน 1 บรรทัดเมื่อ host พร้อม, ไม่ต้อง uninstall/binary ไม่ถูกลบ
2. **Local-first สะอาด** — โฆษณา host นี้เป็น local-only mode (FFmpeg CLI ตรง) ตรงกับ PRD ประเด็น local-first + proven path Phase 1–3
3. **Noise เป็นต้นทุน** — MCP ลงทะเบียนแต่ล้มทุก session ทำลายความน่าเชื่อถือของ status; การปิดแบบเปิดเผย + เอกสาร suspended สะอาดกว่าการเก็บ failure ไว้

---

## สเปกการเปลี่ยนแปลง (exact config diff — ไม่ทำใน task นี้, รอ Owner approval นอก task นี้)

**ก่อน (opencode.json:197-201):**

```json
"concat": {
  "type": "local",
  "command": ["/home/drsolodev/.opencode/concat/Concat-0.2.8-x86_64.AppImage", "--mcp", "headless"],
  "cwd": ".",
  "enabled": true,
```

**หลัง — เปลี่ยนบรรทัดเดียว:**

```json
"concat": {
  "type": "local",
  "command": ["/home/drsolodev/.opencode/concat/Concat-0.2.8-x86_64.AppImage", "--mcp", "headless"],
  "cwd": ".",
  "enabled": false,
```

กฎที่ห้ามแตก:

- **คง `command` / `env` (`CONCAT_MCP_ROOTS`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`) ไว้ครบ** — ไม่ลบ ไม่ comment ไม่ย้าย path — เพื่อ re-enable ทันทีเมื่อ host พร้อม
- **ไม่แตะ `mcp.content-creator.env.CONCAT_BIN`** (ชี้ AppImage เดียวกัน) — Content MCP ยังโหลดได้; เฉพาะ `concat` MCP ถูก suspend
- **ไม่ลบ binary** `/home/drsolodev/.opencode/concat/Concat-0.2.8-x86_64.AppImage` — ติดตั้งอยู่เหมือนเดิม
- อัปเดตโน้ตใน `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md` + `docs/MEDIA-TOOLKIT.md` ว่า Concat MCP is **suspended on this host (FUSE mount denied)** — ไม่ใช่ "ไม่มี Concat"

### OpenCode restart (สำคัญ)

`opencode.json` เปลี่ยนแล้ว **catalog ยังไม่เปลี่ยนทันที** — ต้อง restart OpenCode (หรือ reopen MCP session เทียบเท่าคำสั่ง `/mcp` ของผู้ใช้) หลังแก้ config กว่าจะเห็น `concat = disabled`

> Catalog-drop workaround (kickoff ข้อ 5 QA): ถ้า restart ไม่ได้ทันที ให้ผู้ใช้ reopen MCP เอง; verifier ห้ามอ้างว่า "แก้แล้วแต่ยังเห็น failed" คือยังไม่ restart

### Rollback (เมื่อ host รองรับ FUSE แล้ว)

1. เปลี่ยน `enabled: false → true` ใน `mcp.concat` บรรทัดเดียว
2. restart OpenCode (หรือ reopen MCP)
3. smoke test: `Concat --version` + `Concat --mcp` stdio handshake (`tools/list` ต้องขึ้น) ก่อนคืน Concat workflow ให้ผู้ใช้ — ไม่ต้องแตะ binary, env, หรือ Content MCP

---

## ขอบเขตที่การตัดสินใจนี้ **NOT** ครอบ (สำคัญ — ห้ามอ่านเกิน)

- **ไม่ลบ** Concat binary, config env, project, หรือ Concat project ที่เคย render แล้ว
- **ไม่กระทบ** local pipeline (`render_campaign_media_local` + FFmpeg CLI) — Phase 1–3 proven path เดินต่อได้ปกติ
- **ไม่ publish อะไร** — ไม่มี human approval, ไม่มี publish, ไม่มี asset ใหม่; frozen campaigns Phase 1–3 ไม่ถูกแตะ
- **ไม่เปลี่ยน** Concat workflow ของผู้ใช้นอก host นี้ (เช่น host หนุมาน/Windows ที่ติดตั้ง Concat แบบ .deb/.AppImage/Flatpak ได้) — ADR นี้ผูกเฉพาะ host ที่ mount FUSE ไม่ได้
- **ไม่แทน** Engineering feasibility test ของตัวเลือก (2) `--appimage-extract` — Engineering ทดสอบแยกใน `/tmp/opencode` (non-destructive) ตาม kickoff ข้อ 1 ถ้า Owner สั่ง

---

## งานที่ต้องทำต่อ (นอก task นี้)

- [ ] **Owner (L5) approve** ตัดสิน (1) — Task นี้เป็น D1 only (decision + inventory), ยังไม่แก้ `opencode.json`
- [ ] หลัง approve: เปลี่ยน `enabled` 1 บรรทัด + restart OpenCode → verifier ตรวจ SoloCorp MCP loading ไม่แตก (`content-creator` = connected, จุดนี้เป็น QA gate ตาม kickoff ข้อ 5)
- [ ] Engineering ทดสอบ feasibility ตัวเลือก (2) ใน `/tmp/opencode` ถ้า Owner ต้องการ — ไม่ host change, ไม่ bin move
- [ ] อัปเดตโน้ต suspended ใน `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md` + `docs/MEDIA-TOOLKIT.md` คู่กับ config change (同 commit)

## References

- `central_bus/content/ceo-phase4-kickoff-20261107_20261107T051623810915Z.md` — Phase 4 kickoff (ข้อ 1/5)
- `opencode.json:197-208` — `mcp.concat` ปัจจุบัน (`enabled: true`); `opencode.json:165-182` — `mcp.content-creator` (`CONCAT_BIN`)
- `solocorp_mcp/departments/media_service.py:23, 367-378` — `Concat + Earshot stdio`, `CONCAT_DEFAULT`, `render_campaign_with_concat`
- `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md:41-47, 85-86, 139-168` — Concat path + 2026-10-30 evidence (ใช้เป็น historical proof, ไม่ใช่ current host claim)
- `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md` — local-first direction (host นี้ = local-only mode คือ default)

---

## Amendment 2026-11-07 — Decision changed: Option 1 (disable) → Option 2 (extract)

**Date:** 2026-11-07
**Authority:** CEO decision — EXTRACT is primary path. Disable (Option 1) is fallback only if MCP handshake fails after restart.
**Maker:** @changful (Engineering)

### Feasibility proof (actual test results, permanent location — NOT /tmp)

Extract run from production directory `/home/drsolodev/.opencode/concat/`:

```
./Concat-0.2.8-x86_64.AppImage --appimage-extract   → EXIT 0, creates squashfs-root/ (362M)
./squashfs-root/AppRun --version                     → "concat 0.2.8", EXIT 0
timeout 8 ./squashfs-root/AppRun --mcp headless < /dev/null
  → INFO ... Concat 0.2.8 · linux-x86_64
  → "concat mcp: serving through {"mode":"headless","writesUnder":["/home/drsolodev"]}"
  → EXIT 0
```

Extracted AppRun works headless without FUSE mount or display — the earlier FUSE `fusermount3 Operation not permitted` (exit 127) failure is bypassed by `--appimage-extract`. This supersedes ADR's original "Option 2 unproven" assessment and its disable recommendation.

### Decision change
- **Before:** Option 1 — disable `concat` MCP in `opencode.json` (`enabled: false`).
- **After:** Option 2 — permanent extract. `concat` MCP stays `enabled: true`.
  - `mcp.concat.command[0]`: `/home/drsolodev/.opencode/concat/Concat-0.2.8-x86_64.AppImage` → `/home/drsolodev/.opencode/concat/squashfs-root/AppRun` (args `--mcp headless` unchanged).
  - `mcp.content-creator.env.CONCAT_BIN` (opencode.json line 171): same AppImage path → same `squashfs-root/AppRun`.
  - Nothing else in `opencode.json` touched (verified `git diff` = 2 lines only).
- **Fallback:** If MCP handshake fails after OpenCode restart (QA-verified), use Option 1 disable as fallback.

### Permanent paths
- Source binary (retained, untouched): `/home/drsolodev/.opencode/concat/Concat-0.2.8-x86_64.AppImage`
- Extracted runtime (permanent, NOT /tmp): `/home/drsolodev/.opencode/concat/squashfs-root/` (362M, `AppRun` symlink → `usr/bin/concat`, 128451152 bytes, executable)

### Rollback
1. Revert both `opencode.json` lines back to `Concat-0.2.8-x86_64.AppImage` (or apply Option 1 `enabled: false`).
2. Delete `squashfs-root/` if extracted runtime no longer needed: `rm -rf /home/drsolodev/.opencode/concat/squashfs-root`.
3. Restart OpenCode.

### OpenCode restart required
Config change does NOT take effect in the current session — the MCP catalog stays stale. User must restart OpenCode (or reopen MCP) for the new `squashfs-root/AppRun` command to be picked up. Do not claim verified until QA smoke-tests the MCP handshake after restart. No full Concat render was attempted (needs campaign assets + long run).
