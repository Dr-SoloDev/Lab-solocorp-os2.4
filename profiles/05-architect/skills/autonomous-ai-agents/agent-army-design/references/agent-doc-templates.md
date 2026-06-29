# Agent Doc Templates

Fill-in-the-blanks templates for the 5-file per-agent documentation set.
Replace `<SLUG>`, `<ROLE>`, `<PORT>`, etc. with actual values.

---

## inventory.md

```markdown
# <SLUG> — Inventory

## Role
**Type:** Commander | Specialist
**Domain:** <e.g. coding, ops, research>
**Reports to:** <hermes-life | user>
**Description:** <one-sentence purpose>

## Ports
| Port | Service |
|------|---------|
| <PORT_API> | Gateway / API |
| <PORT_DASH> | Dashboard |

## Messaging
**Receives from:** <Commander slug or "user via Telegram">
**Sends to:** <target agent or "user">
**Protocol:** <cron / webhook / direct>

## Credentials
| Key | Purpose | Stored |
|-----|---------|--------|
| ANTHROPIC_API_KEY | LLM inference | .env |
| <OTHER_KEY> | <purpose> | <location> |

## Skills
- <skill-name>: <one-line description>
```

---

## docker.md

```markdown
# <SLUG> — Docker / Process Layout

## Status
**Containerized:** No (bare process) | Yes (Docker)
**Process manager:** systemd | cron | manual

## Layout
```
/srv/<SLUG>/
├── config/
├── memories/
├── skills/
└── .env          # gitignored
```

## Compose (if containerized)
```yaml
services:
  <SLUG>:
    image: hermes-agent:latest
    restart: unless-stopped
    env_file: .env
    ports:
      - "<PORT_API>:8642"
      - "<PORT_DASH>:9119"
    volumes:
      - /srv/<SLUG>/config:/app/config
      - /srv/<SLUG>/memories:/app/memories
```

## Common Ops
- Start: `hermes -p <SLUG> start`
- Stop: `hermes -p <SLUG> stop`
- Logs: `hermes -p <SLUG> logs -f`
- Status: `hermes process list`
```

---

## env-map.md

```markdown
# <SLUG> — Environment Variable Map

> This file documents what keys exist and where they live.
> Actual values are in `.env` (gitignored). NEVER commit values here.

| Key | Purpose | Provider | Scope | Stored | Last Rotated |
|-----|---------|----------|-------|--------|--------------|
| ANTHROPIC_API_KEY | LLM inference (Claude) | Anthropic | global | .env | <date> |
| <KEY_NAME> | <purpose> | <provider> | <global/local> | <.env / secret manager> | <date> |

## Rules
- Rotate all keys every 90 days minimum
- If a key is shared across agents, store once in a shared `.env.global` and symlink
- Never log key values — mask in all runbook commands
```

---

## runbook.md

```markdown
# <SLUG> — Runbook

## Talk to this agent
```bash
hermes -p <SLUG> chat
# or via Commander: "hey hermes-life, ask hermes-dev to <task>"
```

## Health check
```bash
hermes process list | grep <SLUG>
hermes -p <SLUG> ping
```

## Restart
```bash
hermes -p <SLUG> stop
hermes -p <SLUG> start
```

## Upgrade
```bash
cd ~/.local/share/maxplus/hermes-agent
git pull
hermes -p <SLUG> restart
```

## Rotate credentials
1. Generate new key at provider dashboard
2. Update `.env`: `ANTHROPIC_API_KEY=<new-value>`
3. Restart agent: `hermes -p <SLUG> restart`
4. Update `env-map.md` Last Rotated date
5. Revoke old key at provider

## Restore from backup
```bash
restic -r <REPO> restore latest --target /srv/<SLUG>/restore
# then diff and merge config/memories/skills
```
```

---

## backup.md

```markdown
# <SLUG> — Backup

## Include
- `SOUL.md` — agent identity and personality
- `config/` — all configuration files
- `memories/` — persistent memory store
- `skills/` — custom skills
- `cron/` — scheduled job definitions

## Exclude (security + size)
- `.env` — contains secrets; back up separately via secret manager
- `auth/` — tokens, OAuth state
- `sessions/` — conversation history (large, regenerable)
- `logs/` — ephemeral, not worth restoring

## Backup repo
```
restic init --repo <REPO_PATH>   # first time only
restic -r <REPO_PATH> backup /srv/<SLUG> --exclude .env --exclude sessions
```

## Schedule (cron)
```
0 3 * * * restic -r <REPO_PATH> backup /srv/<SLUG> --exclude .env --exclude sessions
```

## Restore
```bash
restic -r <REPO_PATH> snapshots          # list
restic -r <REPO_PATH> restore <ID> --target /tmp/restore-<SLUG>
# review diff, then copy needed files back
```
```