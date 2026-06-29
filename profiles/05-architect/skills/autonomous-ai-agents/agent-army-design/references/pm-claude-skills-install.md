# pm-claude-skills Batch Install Reference

Source repo: `https://github.com/anthropics/pm-claude-skills` (v9.0.0, 106 skills + 4 agent templates, 15 professions)

## Sparse Checkout Pattern (preferred — avoids cloning 500 MB repo)

```bash
# Step 1: Clone root only (no blobs)
git clone --filter=blob:none --no-checkout --depth=1 \
  https://github.com/anthropics/pm-claude-skills.git /tmp/pm-claude-skills

cd /tmp/pm-claude-skills
git checkout --orphan listing
git ls-tree -r --name-only origin/main   # inspect full file tree without checkout
```

## Extracting Individual Skills

Skills live under `plugins/<plugin-name>/skills/<skill-name>/SKILL.md`.

```bash
# Extract a single skill
git show origin/main:plugins/pm-engineering/skills/api-docs-writer/SKILL.md \
  > ~/.hermes/skills/pm/api-docs-writer.md
```

## Batch Install (execute_code pattern)

Use `execute_code` with a loop for bulk installs — one terminal call per skill is too slow:

```python
from hermes_tools import terminal
import os

skill_map = [
    ("pm-engineering", "api-docs-writer"),
    ("pm-engineering", "architecture-decision-record"),
    ("pm-planning", "okr-builder"),
    # ... etc
]

os.makedirs(os.path.expanduser("~/.hermes/skills/pm"), exist_ok=True)
repo = "/tmp/pm-claude-skills"

cmds = []
for plugin, skill in skill_map:
    src = f"plugins/{plugin}/skills/{skill}/SKILL.md"
    dst = os.path.expanduser(f"~/.hermes/skills/pm/{skill}.md")
    cmds.append(f'git -C {repo} show origin/main:{src} > {dst}')

result = terminal(" && ".join(cmds))
print(result["output"])
```

Verify: `ls ~/.hermes/skills/pm/ | wc -l` should equal the number of skills installed.

## Skills Installed (Tier 1+2+3 — All-in, 21 confirmed)

**pm-engineering:** `api-docs-writer`, `architecture-decision-record`, `runbook-writer`, `incident-postmortem`
**pm-planning:** `okr-builder`, `feature-prioritisation`, `roadmap-narrative`
**pm-strategy:** `ambiguity-resolver`
**pm-gtm:** `go-to-market`, `content-calendar`, `competitor-teardown`
**pm-delivery:** `go-to-market-planner`, `product-launch-checklist`
**skills/ root flat:** `competitive-intelligence-monitor`, `competitor-signal-tracker`, `product-health-analysis`
**pm-finance:** `investor-pitch-deck`, `financial-due-diligence`, `financial-model-narrative`, `budget-variance-analysis`
**pm-business:** `board-deck-narrative`, `investor-update`

## Missing from Batch (install separately if needed)

`seo-content-brief`, `media-pitch`, `email-campaign` — all under `plugins/pm-gtm/skills/<skill>/SKILL.md`

## Plugin → Skill Directory Mapping

| Plugin | Path prefix |
|--------|-------------|
| pm-engineering | `plugins/pm-engineering/skills/` |
| pm-planning | `plugins/pm-planning/skills/` |
| pm-strategy | `plugins/pm-strategy/skills/` |
| pm-gtm | `plugins/pm-gtm/skills/` |
| pm-delivery | `plugins/pm-delivery/skills/` |
| pm-finance | `plugins/pm-finance/skills/` |
| pm-business | `plugins/pm-business/skills/` |
| flat skills | `skills/<skill-name>/SKILL.md` |

## Tier Classification Used

**Tier 1 (Core Ops):** engineering + planning
**Tier 2 (Growth):** gtm + delivery + strategy
**Tier 3 (Finance/Business):** finance + business
**Tier 4 (Creative/Niche):** Not installed — narrow use cases, DeFi context doesn't justify

CEO decision: All-in Tier 1+2+3 — cost=zero (text files), DeFi moves fast, treasury needs pitch-readiness.
