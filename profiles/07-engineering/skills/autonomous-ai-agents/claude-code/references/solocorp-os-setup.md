# SoloCorp OS — Claude Code Setup Reference

## Auth: MaxPlus API (not Anthropic direct)

Claude Code uses `ANTHROPIC_API_KEY` env var regardless of provider. For MaxPlus:

```bash
export ANTHROPIC_API_KEY="<your-maxplus-key>"
export ANTHROPIC_BASE_URL="https://api.maxplus-ai.cc"
```

Set in `~/.claude/settings.json` under `env` block so it applies to all sessions:
```json
{
  "env": {
    "ANTHROPIC_API_KEY": "<maxplus-key>",
    "ANTHROPIC_BASE_URL": "https://api.maxplus-ai.cc"
  }
}
```

Verify: `claude auth status` — should show API key mode, NOT OAuth.

## CLAUDE.md for Multi-Agent Org (~/.claude/CLAUDE.md)

Global CLAUDE.md that loads for ALL projects. For a SoloCorp OS setup with CEO/CFO agents:

```markdown
# SoloCorp OS — Claude Code Context

## Org Structure
- Dr.solodev = Architect & Owner (final decisions)
- เทอโบ (CEO) = Orchestrator, delegates to Claude Code
- meetoo (CFO) = Financial veto authority

## Workflow
Claude Code is invoked by เทอโบ (CEO agent via Hermes).
- Report work done, files changed, and any blockers
- Do NOT make financial decisions — flag to CFO
- Do NOT deploy to production without explicit approval

## Tech Stack
- Primary: Solana DeFi dApps, Rust/TypeScript smart contracts
- Web: Next.js, React, TailwindCSS
- Backend: Node.js, Python FastAPI
- Infra: Linux, Docker

## Coding Conventions
- TypeScript: strict mode, no `any`, ESLint + Prettier
- Python: type hints on all public functions, ruff + mypy
- Rust: clippy clean, no unsafe unless justified
- Tests: co-located, cover happy path + at least one error path
- Commits: conventional commits format

## Safety Rules
- Never commit secrets or API keys
- Never `rm -rf` without listing first
- Never push to main/master directly
- Flag unclear requirements before writing code
```

## Delegation Safety Defaults (from CEO/เทอโบ)

Per task type:

| Task | Flags |
|------|-------|
| Feature | `--allowedTools "Read,Edit,Write,Bash" --max-turns 10` |
| Bug fix | `--allowedTools "Read,Edit,Bash" --max-turns 8` |
| Code review | `git diff | claude -p "review" --max-turns 1` |
| Refactor | `--allowedTools "Read,Edit,Bash" --max-turns 15` |
| UX/UI | `--allowedTools "Read,Edit,Write" --max-turns 10` |

**Hard rules:**
- Never use `--dangerously-skip-permissions` on production
- Always set `--max-turns` in print mode
- `--max-budget-usd 0.50` for large tasks

## File Locations
- Global settings: `~/.claude/settings.json`
- Global memory: `~/.claude/CLAUDE.md`
- Project memory: `./CLAUDE.md` or `.claude/CLAUDE.local.md`
- Claude Code binary: `~/.nvm/versions/node/v24.14.1/bin/claude` (v2.x)
