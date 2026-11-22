# Codex CLI Subagents

This repo can expose the SoloCorp OS Codex profiles as project-scoped Codex CLI
custom agents.

## Files

- Source prompts: `dist/codex/**/system_prompt.md`
- Project config: `.codex/config.toml`
- Generated agents: `.codex/agents/*.toml`
- Exporter: `scripts/export-codex-agents.py`

## Generate

From the repo root:

```bash
python3 scripts/export-codex-agents.py
```

The exporter reads every `dist/codex/**/system_prompt.md`, creates an ASCII
slugged agent name, writes `.codex/agents/<name>.toml`, and validates all TOML
with Python `tomllib`.

To validate without rewriting files:

```bash
python3 scripts/export-codex-agents.py --validate-only
```

## Use

Start Codex CLI from this repo:

```bash
cd /home/drsolodev/projects/Lab-solocorp-os2.4
codex
```

Project `.codex/` configuration is loaded only when the project is trusted by
Codex. Subagents are spawned only when you explicitly ask for them.

## Browser MCP

This project also configures a local `stealth_browser` MCP server for browser
automation:

- Runtime: `tools/stealth-browser-mcp`
- Codex config: `.codex/config.toml`
- Mode: `--minimal`
- Tool approval: `prompt`
- File uploads are restricted to this repo by `BROWSER_FILE_UPLOAD_ALLOWED_DIRS`

Use it from a new Codex CLI session with an explicit request:

```text
Use the stealth_browser MCP tools to open https://example.com and take a screenshot.
Ask before using browser actions that submit forms, upload files, or interact with accounts.
```

To verify the server can load:

```bash
tools/stealth-browser-mcp/venv/bin/python tools/stealth-browser-mcp/src/server.py --list-sections
```

Example prompt:

```text
Use subagents for this frontend launch review.
Spawn these agents:
- 09-ui-designer-ui-designer
- 09-ui-designer-ux-architect
- 09-ui-designer-ux-researcher

Wait for all subagents.
Summarize findings by agent.
As department head, decide what must be fixed before handoff.
```

Useful groups:

```text
09-ui-designer-head
09-ui-designer-ui-designer
09-ui-designer-ux-architect
09-ui-designer-ux-researcher

10-qa-head
10-qa-api-tester
10-qa-accessibility-auditor
10-qa-test-results-analyzer

07-engineering-head
07-engineering-backend-architect
07-engineering-senior-developer
07-engineering-software-architect
```

List all generated agents:

```bash
ls .codex/agents
```
