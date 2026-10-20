# tools/carbonyl — อ่านเว็บที่ render JavaScript โดยไม่ต้องมี display

> **เหตุผลที่มี:** เครื่องจำกัดทรัพยากร — Chrome กิน ~1.4GB + ต้องมี Xorg
> ตัวนี้ใช้ **47.5MB** และ **0% CPU ตอน idle** และไม่ต้องมี display เลย

## ใช้ยังไง

```bash
tools/carbonyl/web-read <url> [--wait N] [--cols N] [--rows N] [--network MODE] [--json]
```

| Option | Default | ความหมาย |
|:--|:--|:--|
| `--wait` | 12 | วินาทีที่รอให้หน้าโหลด (เว็บหนักใช้ 20-30) |
| `--cols` | 120 | ความกว้างเทอร์มินัล → ยิ่งกว้าง ยิ่งได้ข้อความเยอะ |
| `--rows` | 40 | ความสูงเทอร์มินัล |
| `--network` | (default bridge) | ใช้ `host` เมื่อ URL เป็น localhost |
| `--json` | — | ผลลัพธ์แบบ JSON (สำหรับเครื่องมือ/สคริปต์) |

## 3 ทางเข้าสำหรับ agent

| ทาง | ใครใช้ | เรียกยังไง |
|:--|:--|:--|
| **MCP** | OpenCode / Codex / Grok | `solocorp_web_read(url)` · `solocorp_web_search(query)` |
| **Worker** | python agent | `await agent.web_read(url)` · `await agent.web_search(query)` |
| **Bus** | ทุกอย่าง | `POST /v1/web-read {"url":...}` หรือ `{"query":...}` |

Core client อยู่ที่ `solocorp_skills/web.py` — ใช้ร่วมกันทั้ง 3 ทาง (ไม่มี logic ซ้ำ)
ดูรายละเอียด: `skills/@solocorp/engineering/web-read/SKILL.md` · `decisions/ADR-019-web-capability-v1-integration.md`

## Ladder — เลือกให้ถูกขั้น

| ขั้น | เครื่องมือ | RAM | ใช้เมื่อ |
|:--|:--|:--|:--|
| 1 | `webfetch` (HTTP) | **0** | เว็บส่วนใหญ่ |
| 2 | **web-read (นี่)** | **47.5MB** | เว็บที่ render ด้วย JS เท่านั้น |
| 3 | `stealth-browser` (Chrome) | ~1.4GB + display | ต้อง interact / anti-bot / login |

## สถาปัตยกรรม

```
host                                    container (ไม่มี DISPLAY)
┌────────────────────┐                 ┌──────────────────────────────┐
│ web-read (bash)    │ ──docker run──▶ │ entrypoint.sh                │
│  └ extract.py      │ ◀──raw ANSI─── │  └ script(pty) → carbonyl    │
│     (จำลองเทอร์มินัล│                 │     (Chromium headless_shell)│
│      → ข้อความ)    │                 └──────────────────────────────┘
└────────────────────┘                 docker run --rm → ไม่เหลือ residue
```

**ทำไมต้องมี extract.py:** carbonyl เป็นเบราว์เซอร์ที่ *วาด* ลงเทอร์มินัล (ภาพ + ตัวอักษร)
ไม่มีโหมดดึงข้อความ → ต้องจำลองเทอร์มินัลเพื่อรู้ว่าอักขระอยู่ที่ (row, col)ไหน
แล้วอ่านทีละบรรทัด (ตัด block graphics ทิ้ง)

## Build

```bash
docker build -t solocorp/carbonyl-reader:latest tools/carbonyl/
```

Base = `fathyb/carbonyl:latest` (BSD-3-Clause) — build ไม่ต้องเน็ต เพราะไม่มี apt-get
**ไม่มี binary ใน repo** — เก็บไว้ใน Docker image เท่านั้น

## ข้อจำกัด

- เห็นแค่ **viewport แรก** — เนื้อหานอกจอ/carousel/lazy-load ไม่ออก (ใช้ HTTP แทนดีกว่า)
- **ไม่เก็บ cookie** → เว็บที่ต้อง login ใช้ไม่ได้
- ไม่มี Basic Auth / click / type → ต้องใช้ขั้น 3
- ไม่ผ่าน anti-bot → เว็บที่บล็อก headless ใช้ขั้น 3
- text ที่เป็นรูปภาพ → อ่านไม่ได้

## วัดจริง (2026-10-20)

| ตัวชี้วัด | ค่า |
|:--|:--|
| RAM (cgroup) | 47.5 MB |
| CPU idle | 0.03% |
| display | ไม่ต้อง |
| ภาษาไทย | ✅ |
| JS-only content | ✅ |

## ดูเพิ่ม

- Skill: `skills/@solocorp/engineering/web-read/SKILL.md`
- ADR: `decisions/ADR-018-carbonyl-web-read-tool.md`
