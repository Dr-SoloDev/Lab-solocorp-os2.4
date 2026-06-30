---
name: hermes-profile-setup
description: "Set up complete Hermes agent profiles with consistent config, custom providers, and SOUL.md identity files for multi-agent systems"
version: 1.0.0
author: agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, profiles, multi-agent, configuration, solocorp]
    related_skills: [hermes-agent, multi-agent-localization]
---

# Hermes Profile Setup

Set up complete Hermes agent profiles with consistent configuration, custom provider definitions, model aliases, and SOUL.md identity files for multi-agent systems.

## When to Use

- Setting up a new agent profile with full configuration
- Standardizing config across multiple existing profiles
- Fixing incomplete profile configs (missing custom_providers, wrong provider names)
- Building a multi-agent "family" where each agent needs separate identity and config
- **Renaming/deleting existing profiles** while maintaining backward compatibility through symlink aliases
- **Updating the Profile Registry** after any lifecycle change

## Profile Structure

Each profile lives under `~/.hermes/profiles/<name>/`:

```
~/.hermes/profiles/<name>/
├── config.yaml              # Model, agent, terminal settings
├── SOUL.md                  # Profile-level identity/role summary
├── references/              # Team member profiles from agency-agents
│   └── design-ui-designer.md
├── skills/                  # Profile-specific skills
├── memories/                # Profile-specific memory
├── cron/                    # Profile-specific cron jobs
├── logs/                    # Runtime logs (auto-created)
└── sessions/                # Profile-specific session history
```

Agent identity (SOUL.md) lives separately in `~/.hermes/agents/<agent-name>/SOUL.md` and is referenced via `agent.system_prompt_file` in config.yaml. The agent SOUL.md is the **full identity document** — detailed team structure, collaboration flows, and decision authority live here.

## Standard Config Template

Full config with custom provider, model aliases, and sensible defaults:

```yaml
custom_providers:
- name: maxplus
  base_url: https://api.maxplus-ai.cc
  key_env: MAXPLUS_API_KEY
  transport: anthropic_messages
  models:
    claude-opus-4-6:
      context_length: 200000
    claude-sonnet-4-6:
      context_length: 200000
    claude-haiku-4-5-20251001:
      context_length: 200000
model:
  default: claude-sonnet-4-6
  provider: custom:maxplus
model_aliases:
  opus:
    model: aws/claude-opus-4-6
    provider: custom:maxplus
  sonnet:
    model: aws/claude-sonnet-4-6
    provider: custom:maxplus
  haiku:
    model: aws/claude-haiku-4-5
    provider: custom:maxplus
agent:
  max_turns: 60
  reasoning_effort: medium
  system_prompt_file: ~/.hermes/agents/hermes-<role>/SOUL.md
terminal:
  backend: local
  cwd: .
  timeout: 180
onboarding:
  seen:
    openclaw_residue_cleanup: true
    tool_progress_prompt: true
    busy_input_prompt: true
```

### Config Customization by Role

**CEO (Commander):**
- `max_turns: 60` (default)
- Higher autonomy, delegates to specialists

**CFO (Financial Officer):**
- `max_turns: 60`
- finance-companion MCP tools enabled
- Strict, data-driven

**Marketing (CMO):**
- `max_turns: 40`
- Content-focused skills preloaded
- Creative but structured

**Architect:**
- `max_turns: 30`
- Technical design and planning
- No execution, pure architecture

**Orchestrator:**
- `max_turns: 50`
- `timeout: 300` (longer for coordination)
- Delegates to other profiles

## Common Provider Mistakes

❌ **Wrong:** `provider: custom:maxplus-aws`
✅ **Right:** `provider: custom:maxplus`

The provider name must match the `name:` field in `custom_providers` block. Common mistake: adding `-aws` suffix in model aliases but defining provider as just `maxplus`.

## Testing a Profile

```bash
# Quick test — profile runs a single prompt
hermes --profile <name> -z "สวัสดีครับ"

# Health check — validates config, env vars, provider
hermes doctor --profile <name>

# Profile registry — confirms profile is registered
hermes profile list

# View full config
hermes --profile <name> config
```

Expected output from `hermes profile list`: the profile appears in the table with its model provider.

## Monitoring Profile Health

Over time, profiles accumulate skills far beyond what's useful through bulk copy and repeated setups. Periodic audits catch this.

### Skill Overload Detection

Profile skills are independent **copies** from the global pool at `~/.hermes/skills/`. They are NOT symlinks (except `solocorp` which uses internal symlinks). Deleting a skill from one profile does NOT affect the global pool or other profiles.

**Audit commands:**

```bash
# Count SKILL.md files per profile
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  count=$(find "$p" -maxdepth 6 -name "SKILL.md" 2>/dev/null | wc -l)
  echo "$name → $count skills"
done

# List all skill paths per profile (for detailed review)
for p in ~/.hermes/profiles/<name>/skills/*/; do
  find "$p" -name "SKILL.md" -printf "%P\n" 2>/dev/null
done
```

**Red flags:**
- **>20 skill files per profile** — likely overloaded, should be trimmed
- **>50 skill files per profile** — critically overloaded, the profile has become a dump for global pool skills
- **A profile has skills that another profile should own** (e.g., DevOps tools under a Legal profile)

**Skill storage architecture:**
```
Global pool: ~/.hermes/skills/<category>/<skill-name>/SKILL.md
Profile copy: ~/.hermes/profiles/<name>/skills/<category>/<skill-name>/SKILL.md
```
Profile skills are real directories (independent copies). A bulk copy like `cp -r ~/.hermes/skills/* ~/.hermes/profiles/<name>/skills/` is what causes the overload. Instead, copy only specific skills needed for the profile's role.

### Profile Breakdown Detection

Check for empty or broken profiles (missing core files):

```bash
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  config="N"; soul="N"
  [ -f "$p/config.yaml" ] && config="Y"
  [ -f "$p/SOUL.md" ] && soul="Y"
  echo "$name | config=$config | SOUL=$soul"
done
```

A profile with `config=N` or `SOUL=N` is broken — it cannot run. Fix by recreating the missing files (see Recovery section below).

### Recover an Empty Profile

If a profile directory exists but is empty (no config.yaml, no SOUL.md, no skills):

```bash
# 1. Check if the agent SOUL exists separately
ls ~/.hermes/agents/hermes-<role>/SOUL.md

# 2. Create config.yaml — use an existing profile as template
#    CRITICAL: update `system_prompt_file` to point at the correct agent SOUL

# 3. Create profile-level SOUL.md (minimal stub):
#    "You are Hermes Agent, an intelligent AI assistant..."

# 4. Restore skills from global pool:
cp -r ~/.hermes/skills/<category>/<skill-name> ~/.hermes/profiles/<name>/skills/<category>/

# 5. Verify:
hermes doctor --profile <name>
```

**Common causes:**
- Accidental `rm -rf <symlink>/` with trailing slash (see Pitfalls)
- Incomplete profile migration or cleanup script
- Race condition during multi-profile operations

## Profile Lifecycle Management

### Rename a Profile (with backward compatibility)

When renaming a profile (e.g. `mkt` → `cmo`), preserve backward compatibility via symlink alias:

```bash
# 1. Copy old profile to new name
cp -a ~/.hermes/profiles/<old-name> ~/.hermes/profiles/<new-name>

# 2. Update new profile's config.yaml (system_prompt_file, etc.)
#    Use skill_manage(action='patch') on the skill or write_file for the profile

# 3. IMPORTANT: Remove old directory FIRST, then create symlink
rm -rf ~/.hermes/profiles/<old-name>     # always remove directory first
ln -s <new-name> ~/.hermes/profiles/<old-name>

# 4. Update Profile Registry (if one exists for the org)
#    e.g., SoloCorp_Profile_Registry.yaml — change old entry to symlink/alias

# 5. Update Governance Policy directives (if D# tracking exists)

# 6. Verify
ls -la ~/.hermes/profiles/<old-name>    # should show as symlink → <new-name>
hermes doctor --profile <new-name>
```

### Delete a Profile (with safety backup)

```bash
# 1. Backup to trash before permanent deletion
mv ~/.hermes/profiles/<name> ~/.hermes/trash/<name>-$(date +%Y%m%d)-*

# 2. Update Registry: mark status as 'deleted' with backup path in note
# 3. Update Governance Policy directives if tracking exists
# 4. Update any cross-references pointing to the deleted profile
```

### Create a New Profile from Scratch

```bash
# Full minimal structure
mkdir -p ~/.hermes/profiles/<name>/{audio_cache,cache,cron,hooks,image_cache,logs,memories,pairing,references,sandboxes,sessions,skills,sync}
touch ~/.hermes/profiles/<name>/auth.lock
mkdir -p ~/.hermes/agents/hermes-<name>
```

Then create `config.yaml` (copy-paste from an existing profile, update `system_prompt_file`) and agent `SOUL.md` at `~/.hermes/agents/hermes-<name>/SOUL.md`.

### Alias Symlink Pattern

When you need backward compatibility for cron jobs, tools, or scripts referencing the old profile name, use a **directory symlink**:

```
~/.hermes/profiles/old-name → new-name
```

This lets `hermes --profile old-name` resolve to the new profile transparently.
Symlinks are listed by `ls -la` and shown by `hermes profile list` (if your Hermes version supports it).

**Reference:** SoloCorp uses this pattern for `mkt → cmo` and `changful → engineering`.

## Workflow

1. **Check existing profiles:**
   ```bash
   ls -la ~/.hermes/profiles/
   ```

2. **Read existing config to understand pattern:**
   ```bash
   cat ~/.hermes/profiles/cfo/config.yaml
   ```

3. **Fix or create config for each profile:**
   - Use `patch` tool for small fixes (provider name, max_turns)
   - Use `write_file` for new profiles or complete rewrites

4. **Update SOUL.md identity if needed:**
   - Gender, communication style (ครับ vs ค่ะ)
   - Role-specific personality traits
   - Decision frameworks

5. **Add Skill Reference Table to SOUL.md (standard step):**
   After creating/updating SOUL.md, append a `## Available Skills` section that maps Hermes skills the profile can use in daily work:

   ```markdown
   ## Available Skills (Load with `skill_view`)
   สกิลในระบบ Hermes ที่ [profile] และทีมสามารถเรียกใช้ได้:

   ### [Category 1]
   | Skill | When to Load | Who Uses |
   |-------|-------------|----------|
   | `skill-name` | relevant trigger | team member |
   | ... | ... | ... |

   ### [Category 2]
   | Skill | When to Load | Who Uses |
   |-------|-------------|----------|
   | ... | ... | ... |
   ```

   **Rules for good skill tables:**
   - Group skills by category (not alphabetically) — categories mirror the profile's actual work domains
   - "When to Load" column = real trigger phrases, not generic descriptions
   - "Who Uses" column = specific team member name/role, not "the team"
   - Only list skills that actually exist in `skills_list` — verify before adding
   - Keep the table to 10-15 entries max — anything beyond that means the skill library needs class-level umbrella skills, not a profile-level reference

   **Why this matters:** The skill table turns a passive SOUL.md into an actionable tool reference. When the profile loads, it knows exactly which Hermes skills to call via `skill_view()` for each class of task — no more "what skill should I use here?" hesitation.

6. **Test each profile after changes:**
   ```bash
   hermes --profile <name> -z "test message"
   ```

## Adding Team Members (from agency-agents)

When Dr.solodev says "เพิ่ม [Role]" — this means making an agency-agents persona a **permanent team member** under an existing profile head. Not a one-off delegate_task call.

**Workflow:**

1. **Browse agency-agents:** Look in the relevant category under agency-agents repo — design/, engineering/, marketing/, etc.
2. **Read profiles:** Use `read_file` to understand each candidate's role, mission, and deliverables
3. **Recommend:** Based on the profile head's existing mission and Dr.solodev's requirements
4. **On approval:**
   a. Copy the .md file → `~/.hermes/profiles/<head-profile>/references/<filename>.md`
   b. Update the head's agent SOUL.md (`~/.hermes/agents/hermes-<head>/SOUL.md`):
      - Add a dedicated subsection under `## Team Structure`
      - Include: role, mission, deliverable table, collaboration workflow
      - Reference: `references/<filename>.md` (from agency-agents)
5. **Verify:** `hermes profile list` + `hermes doctor --profile <head-profile>`

**Example (adding UI Designer under ครีเอท):**
```bash
# Copy reference
mkdir -p ~/.hermes/profiles/design/references
cp ~/.hermes/skills/agency-agents/design/design-ui-designer.md ~/.hermes/profiles/design/references/
```

**SOUL.md team member entry template:**
```markdown
### 🎨 [emoji] [Name] ([Role])

**บทบาท:** [one-line description]

**ภารกิจหลัก:**
1. **[Key Area]** — description
2. ...

**Deliverable หลัก:**
| Output | รายละเอียด |
|--------|-----------|
| [A] | [description] |

**Working กับ [Profile Head]:** [flow description]

**แหล่งอ้างอิง:** `references/<filename>.md` (จาก agency-agents)
```

**Related skill:** `agency-agents` skill has the full Permanent Team Member Pattern with recommendations workflow.

## Creating a Department Profile (Head + Team at scale)

When Dr.solodev says "เพิ่มแผนก" or "สร้างแผนก [name]" — this goes beyond adding single members. You're creating a **department profile** with a head agent + 10-20+ team members in one shot.

**Workflow:**

1. **Plan the department structure:**
   - Identify 4 logical sub-teams (e.g., Core Dev, DevOps, QA, Support/Tooling)
   - Assign 3-8 members per sub-team based on agency-agents categories
   - Total team should feel "พอเพียงสำหรับงานสร้าง" — enough to build end-to-end

2. **Create profile scaffolding:**
   ```bash
   mkdir -p ~/.hermes/profiles/<name>/references
   mkdir -p ~/.hermes/agents/hermes-<name>
   ```

3. **Create config.yaml** (use an existing profile as template, adjust max_turns)

4. **Create agent SOUL.md (~/.hermes/agents/hermes-<name>/SOUL.md)** with:
   - Identity + why the department exists
   - 4-group team table (see template below)
   - Cross-department handoff matrix
   - Available Skills table (verify skills exist in `skills_list` first)
   - Boundaries (what this department does NOT do)
   - Report template

5. **Batch-copy agency-agents references:**
   ```bash
   cd ~/.hermes/skills/agency-agents
   cp engineering/engineering-frontend-developer.md \
      engineering/engineering-backend-architect.md \
      ... \
      ~/.hermes/profiles/<name>/references/
   ls ~/.hermes/profiles/<name>/references/ | wc -l   # verify count
   ```

6. **Create profile SOUL.md (~/.hermes/profiles/<name>/SOUL.md)** — condensed identity card mapping: department name, head, departments structure, key workflows, cross-dept dependencies

7. **Verify:** `hermes doctor --profile <name>` (core checks: config, SOUL.md, directory structure)

### Team Structure Table Template (for agent SOUL.md)

Use this 4-group layout for Engineering/Dev departments. Adjust groups per domain:

```markdown
## 👥 ทีมในสังกัด — [Department Name] ([N] คน)

### 🏗️ [Core Group] ([X] คน)

| บทบาท | ชื่อ | ภารกิจหลัก | Deliverable |
|-------|------|-----------|-------------|
| **หัวหน้า** | **ชื่อหัวหน้า** | [mission] | [key deliverable] |
| [Role A] | ชื่อเล่น | [description] | [deliverable] |
| [Role B] | ชื่อเล่น | [description] | [deliverable] |

### 🔧 [Second Group] ([X] คน)

| บทบาท | ชื่อ | ภารกิจหลัก | Deliverable |
|-------|------|-----------|-------------|
| ... | ... | ... | ... |
```

**Naming convention for Engineering:** ใช้ "ช่าง" + คำขยาย (ช่างหน้า, ช่างหลัง, ช่างฐาน, ช่างเดพลอย, ช่างปลอดภัย, ช่างเช็ค, ฯลฯ)

### Cross-Department Handoff Matrix Template

```markdown
### Cross-Department Handoff
| จาก | รับอะไร | ส่งให้ |
|-----|--------|-------|
| **แผนก A** | [input] | [output] |
| **แผนก B** | [input] | [output] |
| **หัวหน้า** | [direction] | [status report] |
```

### Key Rules for Department Profiles

- **Agent SOUL.md** (~/.hermes/agents/hermes-<name>/SOUL.md) = full identity document with team tables, handoff matrix, skills
- **Profile SOUL.md** (~/.hermes/profiles/<name>/SOUL.md) = concise identity card (~2KB), one-page summary
- **References** = one .md file per team member, copied from agency-agents
- **Team naming** should feel cohesive — all "ช่าง" for Engineering, all "คุณ" for professional roles, etc.
- **Department boundaries** must be explicit (what they do NOT do) to prevent scope creep
- **Available Skills table** must verify skills exist — don't add imaginary entries

### Pitfalls

- **Config mismatch:** Copy from an existing profile but update `system_prompt_file` to the new agent path — a copy-paste from design profile that points at `hermes-design/SOUL.md` breaks the new profile silently
- **Too many references:** 18 files is fine for a full Engineering team; 40+ is token bloat. Pick the essential agency-agents personas
- **Missing boundaries:** Without a "🚫 ไม่รับผิดชอบ" section, the department head may accept work outside scope
- **Cross-ref stale:** When adding a reference in SOUL.md, always note `แหล่งอ้างอิง: references/<filename>.md` so future agents know where to load the full persona

## User Preference: Profile as Identity

Dr.solodev wants each agent to have a **separate profile** even when it doesn't technically change behavior — it's about **identity and family feeling**:

> "แยกทุกคนให้มีโปรไฟล์แยกด้วย มันไม่ได้ส่งผลอะไรมากหรอก แต่มันดีต่อใจ รู้สึกเหมือนมีครอบครัว"

This is an **emotional design requirement**, not just technical separation. Each agent should feel like they have their own "home" with:
- Complete config (not minimal stub)
- Clear identity in SOUL.md
- Runnable via `hermes --profile <name>`

## Pitfalls

- **Provider mismatch:** `custom:foo` in config but defined as `name: bar` in custom_providers
- **Missing custom_providers block:** Profile can't use custom provider without defining it
- **Absolute paths in system_prompt_file:** Don't use `~`, use full `/home/username/...`
- **Testing without restart:** Config changes don't apply mid-session, need fresh `hermes` run
- **Mixing profile homes:** `get_hermes_home()` returns profile-specific path, don't hardcode `~/.hermes/`
- **`ln -sfn` does NOT replace a directory:** If `old-name` is a directory, `ln -sfn new-name old-name` silently creates a symlink **inside** the directory instead of replacing it. Always `rm -rf old-name` first, then `ln -s new-name old-name`
- **Symlink inside a symlink:** After renaming, check that the old-name is a symlink, not a directory that contains a symlink. `ls -la` shows `lrwxrwxrwx` for symlinks, `drwx------` for directories
- **`rm -rf <symlink>/` follows into target directory:** When a symlink points to a directory, using a trailing slash (`rm -rf ~/.hermes/profiles/old-name/`) instructs the shell to follow the symlink and delete the **target's** CONTENTS, not the symlink itself. This can silently destroy the real profile's data. **Always remove symlinks WITHOUT a trailing slash** (`rm -rf ~/.hermes/profiles/old-name`). Use `ls -la` to confirm the entry is a symlink (`lrwxrwxrwx`), then remove without `/`.

## Related

- **hermes-agent:** Core Hermes documentation and CLI reference
- **multi-agent-localization:** Localize agents to consistent language (ภาษาไทย for SoloCorp)
- **agent-army-design:** Design full multi-agent topology (Commander + Specialists)
