---
name: codebase-exploration
description: Efficiently explore unfamiliar codebases — architecture, philosophy, and implementation patterns
---

# Codebase Exploration

**Trigger:** When investigating a new project, especially open-source repos you want to understand deeply or adapt from.

## Goal

Understand a codebase's **architecture, design philosophy, and key patterns** quickly — not just what it does, but *how* and *why* it's built that way.

## Workflow

### 1. Start with the README
- Clone with `--depth 1` to save bandwidth (full history rarely needed for exploration)
- Read README fully — look for: architecture diagrams, design goals, terminology
- Note: **philosophy matters** — projects like BagIdea Office have design docs that explain *intent*, not just features

### 2. Map the structure
```bash
cd <repo>
ls -lah                    # Top-level layout
find . -name "*.md" | head -20     # Find all docs
wc -l <key-files>          # Get LOC sense of scale
```

Look for:
- `docs/` — especially numbered design docs (01-architecture.md, etc.)
- `REQUIREMENT.md` / `DESIGN.md` — feature ideas, philosophy
- Multi-layer structure (daemon + renderer + UI = separation of concerns)

### 3. Read the manifesto/philosophy FIRST
Before diving into code, read design documents like:
- `docs/10-revolutionary-features.md` — "Why we built it this way"
- `ARCHITECTURE.md`, `DESIGN.md`, `PHILOSOPHY.md`

**Why:** Understanding the *thesis* (e.g., "cockpits make agents usable; this makes them employable") gives you the lens to read the code through. Implementation details make sense once you know the goal.

### 4. Identify the core files
```bash
# Entry points
cat package.json | grep '"main"'
cat Cargo.toml | grep '[[bin]]'

# Key modules (sorted by importance)
ls -lSh <source-dir>/     # Largest files = likely core logic
```

For BagIdea-style projects:
- `daemon/server.js` — event hub, agent adapter, permission broker
- `godot/scripts/` — world rendering, agent choreography
- `shell/src/main.rs` — launcher that ties it all together

### 5. Read the core logic (not exhaustively)
- Read **first 100-200 lines** of main files to see:
  - Architecture comments at the top
  - Core data structures (registries, event types)
  - Key constants (BUILTIN_TOOLS, SKILL_LIBRARY)
- Use `head -200 <file>` or `read_file(limit=200)`

**Don't read everything** — focus on understanding *patterns*, not memorizing code.

### 6. Extract learnable patterns
Ask yourself:
- **Architecture:** How is it layered? (daemon + renderer, event-driven, etc.)
- **Philosophy:** What problem does it solve uniquely? (BagIdea: "ambient trust" via visualization)
- **Patterns:** Event protocols? Plugin systems? Memory management?
- **Adaptability:** What concepts could work for *our* project?

### 7. Capture the learning
- Create skill references for **patterns** (not the whole codebase)
- Note **philosophical insights** in memory or skills
- Save **adaptation ideas** for your own projects

## Pitfalls

- ❌ **Don't read every file** — codebases with 10K+ LOC are too big to absorb. Focus on docs + key files.
- ❌ **Don't start with implementation** — start with *why* (manifesto/design docs), then architecture, then code.
- ❌ **Don't ignore the README** — especially for philosophical projects, the README is the thesis statement.
- ❌ **Don't expect to run it immediately** — exploration ≠ installation. Understand first, run later if needed.
- ❌ **Don't get stuck on missing tools** — `jq not found`? Use `python3 -c "import json, sys; ..."` inline instead.

## When Platform Limitations Block You

**BagIdea Office example:** README says "Windows 11 only", Linux in roadmap but not implemented yet.

Response pattern:
1. ✅ Acknowledge the limitation clearly ("Linux ยังไม่ได้จริงๆ")
2. ✅ Explain *why* it's blocked (technical reason: "WorkerW technique ที่เฉพาะ Windows")
3. ✅ Pivot to **adaptable concepts**: "เอาแนวคิดบางอย่างมาประยุกต์ใช้แทน?"
4. ✅ Validate the user's interest even if tool unavailable: "นี่มันเจ๋งจริงๆ"

**Don't:**
- ❌ Over-sell hope ("มี workaround!", "ลองใช้ WSL?") when it won't actually work
- ❌ Ignore user's emotional response ("แอบเฟล") — acknowledge disappointment, then move forward

## Inline JSON Parsing (when jq missing)

```bash
# Instead of: curl <url> | jq '.field'
curl -s <url> | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['field'])"

# Decode base64 README:
curl -s <github-api-url>/readme | python3 -c "import sys, json, base64; print(base64.b64decode(json.load(sys.stdin)['content']).decode('utf-8'))"

# Pretty-print + filter:
curl -s <url> | python3 -c "import sys, json; items = json.load(sys.stdin); [print(f\"{i['key']} - {i['value']}\") for i in items]"
```

Python stdlib (json, base64) is more portable than jq.

## Example: BagIdea Office Exploration

1. **README** → "living 2.5D office, agents work/learn/propose, event-sourced truth"
2. **docs/10-revolutionary-features.md** → "Cockpits make agents usable; this makes them employable"
3. **daemon/server.js (first 200 lines)** → event hub, BUILTIN_TOOLS, SKILL_LIBRARY, registry pattern
4. **Architecture** → 3 layers (daemon + Godot renderer + web overlay), truth in daemon
5. **Key insight** → "Honest Theater" contract: nothing tagged is fake, all animations = journal replay
6. **Adaptation ideas** → project proposals, ambient awareness, plugin system

Result: Understood the **thesis** and **architecture** without reading 11K lines of code.

## Extending: Improvement Roadmaps

When the goal is not just understanding but **generating an improvement plan**, see `references/improvement-roadmap.md` for the tiered analysis framework (Tier 1–4 by impact).

## Extending: Docker PHP Stack Diagnostics

When the codebase runs **in Docker** and the user asks to verify an end-to-end feature (especially PHP CRUD with auth), see `references/docker-php-stack-diagnostics.md` for a systematic 10-layer diagnostic chain from container health → DB → auth → frontend assets. Covers the common "code looks complete but login is broken" pattern that blocks token-based flows.

## Verification

- Philosophy/thesis is captured from design docs before diving into code
- Core architecture (layers, data flow) is mapped
- Key patterns (event protocol, plugins, registries) are identified
- Adaptation opportunities are noted for your own projects
- Time spent reading code is minimized — focus on *understanding*, not *memorizing*
