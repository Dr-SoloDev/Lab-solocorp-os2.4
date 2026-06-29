# Improvement Roadmap Analysis

**When:** User asks "วิเคราะห์ดูว่าเราจะสามารถพัฒนามันอีกได้ไหม" — analyze an existing project for improvement opportunities.

**Prerequisites:** Full codebase exploration first (see SKILL.md for exploration workflow).

## Methodology

### Step 1: Gather Context
- **README.md** — Understanding positioning, target audience, philosophy
- **package.json / Cargo.toml / setup.py** — Dependencies, version, binary entry points
- **CHANGELOG.md** — What's been done recently, trajectory of development
- **LICENSE** — Licensing constraints

### Step 2: Full Code Survey
Read every source file systematically (not just first 200 lines — improvement analysis needs breadth):
```
wc -l $(find . -name '*.js' -o -name '*.ts' -o -name '*.py' | sort)
```
- **CLI entry points** — bin/, main.py
- **Core pipeline** — The main processing chain
- **Error handling** — Error codes, retry system, checkpointing
- **Schema/validation** — Script/schema definitions
- **Type definitions** — TypeScript/Python type stubs
- **Tests** — Coverage, what's tested vs not
- **CI/CD** — .github/workflows, Dockerfile
- **Documentation** — docs/, examples/

### Step 3: Score Current State
Note existing strengths (maintain these, don't break them) before proposing changes.

### Step 4: Generate Tiered Improvement Roadmap

Organize improvements by impact, not by module. Use the Four-Tier framework:

```
Tier 1 — High Impact / Quick Win (done in hours-days)
  Features already in the repo's roadmap, missing tests, easy wins users actively request.

Tier 2 — Feature Expansion (done in days-weeks)
  New capabilities that open new use cases or markets (e.g., format support, multi-platform).

Tier 3 — Infrastructure / Scale (done in weeks)
  Docker, CI improvements, performance optimization, hardware acceleration.

Tier 4 — Go-To-Market / Ecosystem (ongoing)
  Plugin systems, publishing, cloud upload, analytics, example gallery.
```

Each tier entry should include:
- **Feature name** with emoji
- **Why it matters** (market demand, user request, technical debt)
- **Technical approach** (one-line if obvious)

### Step 5: Propose Sprint Roadmap
Suggest a sequenced plan (e.g., 4 sprints) with the highest-ROI items first.

### Step 6: Let the User Choose
End with an open question asking which area to start with. Don't assume the order.

## Example Output Structure

```
## 🚀 โอกาสพัฒนา (เรียงตาม Impact)

**🥇 Tier 1 — ของใกล้ / Impact สูง**
| Feature | ทำไมถึงสำคัญ |
|---------|-------------|
| 1. Subtitles 🔥 | ไว้ใน roadmap แล้ว, คำขอสูงสุด |

**🥈 Tier 2 — Feature Expansion**
| Feature | ทำไมถึงสำคัญ |
|---------|-------------|
| 5. Vertical Video | TikTok/Reels ตลาดมหาศาล |

**🥉 Tier 3 — Infrastructure**
| 12. Docker Image | สำหรับ CI/cloud rendering |

**🎯 Tier 4 — Go-To-Market**
| 17. Plugin System | Custom actions, TTS engines |

💡 แนะนำ Priority: Sprint 1 → Subtitles + Tests, Sprint 2 → Music + Vertical Video
```

## Pitfalls

- ❌ Don't skip CHANGELOG — it shows trajectory and what the user prioritized before
- ❌ Don't propose features that already exist and work well
- ❌ Don't assume budget/timeline — present tiers and let the user pick
- ❌ Don't forget existing strengths — acknowledge what's good so the user knows you understood the project
- ❌ Don't make it a wall of text — use tables and tier headers for scannability
