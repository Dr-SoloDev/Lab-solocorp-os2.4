# Claude Code CLI Reference

> Complete command-line reference for Claude Code
> 
> **Version:** Latest (as of 2026-07-07)

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [Interactive vs Print Mode](#interactive-vs-print-mode)
- [Core Options](#core-options)
- [Session Management](#session-management)
- [Model & Agent Configuration](#model--agent-configuration)
- [Tool Configuration](#tool-configuration)
- [Input/Output Control](#inputoutput-control)
- [Security & Permissions](#security--permissions)
- [Advanced Options](#advanced-options)
- [Subcommands](#subcommands)
- [Examples](#examples)

---

## Overview

Claude Code is an AI-powered coding assistant that can be used interactively (REPL mode) or non-interactively (print mode). By default, `claude` starts an interactive session.

```bash
claude                    # Interactive REPL (default)
claude -p "your prompt"   # Print mode (non-interactive)
```

---

## Basic Usage

### Starting Claude

```bash
claude                          # Start interactive session
claude "implement feature X"    # Start with initial prompt
claude -p "explain this code"   # Print mode, single response
```

### Version & Help

```bash
claude --version                # Show version (-v)
claude --help                   # Show help (-h)
```

---

## Interactive vs Print Mode

### Interactive Mode (Default)

Full REPL with persistent conversation, tool execution, and context awareness.

```bash
claude                          # Basic interactive
claude --continue               # Continue last conversation
claude --resume <session-id>    # Resume specific session
```

### Print Mode (`-p`, `--print`)

Single prompt-response cycle, useful for scripts and pipes. Exits after response.

```bash
claude -p "generate test cases"
echo "explain this" | claude -p
```

**Note:** Workspace trust dialog is skipped in print mode. Only use in trusted directories.

---

## Core Options

### Model Selection

```bash
--model <model>                 # Specify model
-m <model>                      # Short form

# Examples:
claude --model fable            # Latest Fable
claude --model opus             # Latest Opus
claude --model sonnet           # Latest Sonnet
claude --model claude-fable-5   # Specific version
```

**Available model aliases:**
- `fable` → Claude Fable 5
- `opus` → Claude Opus 4.8
- `sonnet` → Claude Sonnet 5
- `haiku` → Claude Haiku 4.5

### Effort Level

```bash
--effort <level>                # Reasoning effort

# Levels: low, medium, high, xhigh, max
claude --effort high -p "complex reasoning task"
```

### System Prompts

```bash
--system-prompt <prompt>                # Replace default system prompt
--append-system-prompt <prompt>         # Append to default
--append-system-prompt-file <file>      # Append from file
```

**Example:**
```bash
claude --append-system-prompt "You are a security expert reviewing code"
```

---

## Session Management

### Continue & Resume

```bash
-c, --continue                  # Continue most recent conversation
-r, --resume [search]           # Resume by ID or search term
--resume                        # Open interactive picker

# Examples:
claude --continue
claude --resume abc123
claude --resume "authentication bug"
```

### Session Naming

```bash
-n, --name <name>               # Set display name for session

claude -n "feature-auth" -p "implement OAuth"
```

### Session ID

```bash
--session-id <uuid>             # Use specific UUID

claude --session-id "550e8400-e29b-41d4-a716-446655440000"
```

### Fork Session

```bash
--fork-session                  # Create new session ID when resuming

claude --resume abc123 --fork-session
```

### PR-Linked Sessions

```bash
--from-pr [value]               # Resume session linked to PR

claude --from-pr 42             # Resume by PR number
claude --from-pr                # Open picker
claude --from-pr "auth"         # Search PRs
```

---

## Model & Agent Configuration

### Agent Selection

```bash
--agent <agent>                 # Use specific agent type

claude --agent code-reviewer
```

### Custom Agents

```bash
--agents <json>                 # Define custom agents (JSON)

claude --agents '{"reviewer": {"description": "Code reviewer", "prompt": "Review code"}}'
```

### Fallback Models

```bash
--fallback-model <model>        # Fallback when primary unavailable

claude --fallback-model opus,sonnet -p "task"
```

**Note:** Only works with `--print` mode.

---

## Tool Configuration

### Tool Selection

```bash
--tools <tools>                 # Specify available tools

claude --tools ""               # Disable all tools
claude --tools "default"        # All tools (default)
claude --tools "Bash,Edit,Read" # Specific tools
```

### Tool Allowlist/Denylist

```bash
--allowedTools <tools>          # Allow specific tools
--allowed-tools <tools>         # Alias
--disallowedTools <tools>       # Deny specific tools
--disallowed-tools <tools>      # Alias

# Examples:
claude --allowedTools "Bash(git *) Edit"
claude --disallowedTools "Bash(rm *)"
```

### Tool Execution Control

```bash
--no-tools                      # Disable tool execution completely
```

---

## Input/Output Control

### Output Format (Print Mode)

```bash
--output-format <format>        # text (default), json, stream-json

claude -p "task" --output-format json
claude -p "task" --output-format stream-json
```

### Input Format (Print Mode)

```bash
--input-format <format>         # text (default), stream-json

echo '{"type":"prompt","text":"hello"}' | claude -p --input-format stream-json
```

### Structured Output

```bash
--json-schema <schema>          # JSON Schema for validation

claude -p "extract data" --json-schema '{"type":"object","properties":{"name":{"type":"string"}}}'
```

### Streaming Options

```bash
--include-partial-messages      # Stream partial chunks (--print + stream-json)
--replay-user-messages          # Echo user messages back (stream-json)
--include-hook-events           # Include hook events (stream-json)
```

### Prompt Suggestions

```bash
--prompt-suggestions [value]    # Enable predicted next prompts

claude -p --prompt-suggestions yes
```

**Values:** true, false, 1, 0, yes, no, on, off

---

## Security & Permissions

### Permission Modes

```bash
--permission-mode <mode>        # Set permission behavior

# Modes:
# - manual: Prompt for every action
# - auto: Auto-approve safe actions
# - acceptEdits: Auto-approve file edits
# - bypassPermissions: Skip all prompts (dangerous)
# - dontAsk: Like auto but more permissive
# - plan: Plan before executing

claude --permission-mode auto
```

### Permission Bypass

```bash
--dangerously-skip-permissions  # Skip ALL permission checks
--allow-dangerously-skip-permissions  # Enable skip as option

# ⚠️ WARNING: Only use in isolated sandboxes
```

---

## Advanced Options

### Directory Access

```bash
--add-dir <directories>         # Additional directories for tool access

claude --add-dir /data --add-dir /config
```

### MCP Configuration

```bash
--mcp-config <configs>          # Load MCP servers

claude --mcp-config servers.json
claude --mcp-config '{"server": "config"}'
```

```bash
--strict-mcp-config             # Only use --mcp-config servers
```

### Plugin Management

```bash
--plugin-dir <path>             # Load plugin from directory/zip
--plugin-url <url>              # Fetch plugin from URL

claude --plugin-dir ./my-plugin
claude --plugin-url https://example.com/plugin.zip
```

### File Resources

```bash
--file <specs>                  # Download files at startup

claude --file file_abc:doc.txt file_def:img.png
```

**Format:** `file_id:relative_path`

### Budget Control

```bash
--max-budget-usd <amount>       # Maximum spend (--print only)

claude -p "task" --max-budget-usd 5.00
```

### Beta Features

```bash
--betas <betas>                 # Enable beta headers (API key only)

claude --betas "feature-2026-01" -p "task"
```

---

## Session Modes

### Background Mode

```bash
--bg, --background              # Start as background agent

claude --bg "long-running task"
# Manage with: claude agents
```

### Remote Control

```bash
--remote-control [name]         # Enable Remote Control

claude --remote-control
claude --remote-control "my-session"
```

```bash
--remote-control-session-name-prefix <prefix>  # Set name prefix
```

### Worktree Mode

```bash
-w, --worktree [name]           # Create git worktree

claude --worktree
claude --worktree feature-branch
```

### Tmux Integration

```bash
--tmux                          # Create tmux session (requires --worktree)
--tmux=classic                  # Use traditional tmux

claude --worktree feature-x --tmux
```

### IDE Integration

```bash
--ide                           # Auto-connect to IDE on startup

claude --ide
```

### Chrome Integration

```bash
--chrome                        # Enable Claude in Chrome
--no-chrome                     # Disable Claude in Chrome
```

---

## Configuration Modes

### Bare Mode

Minimal mode: skip hooks, LSP, plugins, auto-memory, CLAUDE.md discovery.

```bash
--bare                          # Minimal startup

# Sets CLAUDE_CODE_SIMPLE=1
# Auth: ANTHROPIC_API_KEY only
# No auto-discovery
```

**When to use:** CI/CD, containers, minimal environments.

### Safe Mode

Disable all customizations for troubleshooting.

```bash
--safe-mode                     # Disable customizations

# Disables: CLAUDE.md, skills, plugins, hooks, MCP,
#           custom commands/agents, workflows, themes
# Keeps: Auth, model selection, built-in tools
# Sets CLAUDE_CODE_SAFE_MODE=1
```

**When to use:** Debugging broken configuration.

### Session Persistence

```bash
--no-session-persistence        # Don't save session to disk (--print only)
```

### Setting Sources

```bash
--setting-sources <sources>     # Comma-separated sources

claude --setting-sources user,project
```

**Sources:** user, project, local

```bash
--settings <file-or-json>       # Load additional settings

claude --settings ./custom.json
claude --settings '{"key": "value"}'
```

---

## Debug & Development

### Debug Mode

```bash
-d, --debug [filter]            # Enable debug logging

claude --debug                  # All categories
claude --debug api,hooks        # Specific categories
claude --debug "!1p,!file"      # Exclude categories
```

### Debug File

```bash
--debug-file <path>             # Write logs to file (enables debug)

claude --debug-file debug.log
```

### Accessibility

```bash
--ax-screen-reader              # Screen-reader friendly output
```

### Verbose Mode

```bash
--verbose                       # Override config verbose setting
```

### System Prompt Optimization

```bash
--exclude-dynamic-system-prompt-sections  # Move dynamic sections to user message

# Improves cross-user prompt-cache reuse
# Only applies with default system prompt
```

---

## Skill Management

### Disable Skills

```bash
--disable-slash-commands        # Disable all skills
```

**Note:** Skills are invoked with `/skill-name` in interactive mode.

---

## Subcommands

### `claude agents`

Manage background agents.

```bash
claude agents                   # List all agents
claude agents stop <id>         # Stop specific agent
claude agents stop --all        # Stop all agents
claude agents logs <id>         # View agent logs
```

---

### `claude auth`

Manage authentication.

```bash
claude auth login               # Browser-based OAuth login
claude auth logout              # Logout current session
claude auth status              # Show current auth status
```

**Auth methods:**
- `ANTHROPIC_API_KEY` — environment variable
- `claude auth login` — browser OAuth
- `claude setup-token` — long-lived token (subscription required)

---

### `claude auto-mode`

Inspect auto mode classifier configuration.

```bash
claude auto-mode                # Show auto mode config
```

---

### `claude doctor`

Health check for installation, updater, MCP servers, and configuration.

```bash
claude doctor                   # Run all diagnostics
```

⚠️ Workspace trust dialog skipped — only run in trusted directories.

---

### `claude mcp`

Configure and manage MCP (Model Context Protocol) servers.

```bash
claude mcp                      # List servers
claude mcp add <name> <config>  # Add server
claude mcp remove <name>        # Remove server
claude mcp edit <name>          # Edit config
claude mcp test <name>          # Test connection
claude mcp logs <name>          # View logs
```

**Example:**
```bash
claude mcp add fs '{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/path"]}'
claude mcp test fs
```

---

### `claude plugin` / `claude plugins`

Manage plugins.

```bash
claude plugins list             # List installed plugins
claude plugins install <url>    # Install from URL or directory
claude plugins uninstall <name> # Uninstall plugin
claude plugins update [name]    # Update plugin(s)
```

---

### `claude project`

Manage project state.

```bash
claude project init             # Initialize project
claude project reset            # Reset project state
```

---

### `claude setup-token`

Set up long-lived auth token (requires subscription).

```bash
claude setup-token              # Interactive setup
```

---

### `claude ultrareview`

Cloud-hosted multi-agent code review.

```bash
claude ultrareview              # Review current branch vs default base
claude ultrareview 42           # Review PR #42
claude ultrareview main         # Review against main branch
```

Multi-agent review covers security, performance, and best practices in parallel.

---

### `claude update` / `claude upgrade`

```bash
claude update                   # Check and install latest
claude install stable           # Install stable channel
claude install latest           # Install latest channel
claude install <version>        # Install specific version
```

---

### `claude gateway`

Enterprise auth/telemetry gateway.

```bash
claude gateway                  # Start gateway server
claude gateway --port <port>    # Custom port
claude gateway --config <file>  # Config file
```

---

## Examples

### Basic Usage Examples

#### Interactive Session
```bash
# Start basic interactive session
claude

# Start with initial prompt
claude "help me refactor this module"

# Continue last conversation
claude --continue

# Resume specific session
claude --resume abc123
```

#### Print Mode (Non-Interactive)
```bash
# Single response
claude -p "explain async/await"

# Pipe input
echo "explain this code" | claude -p

# Structured output
claude -p "extract user data" --json-schema '{"type":"object","properties":{"name":{"type":"string"},"age":{"type":"number"}}}'

# Stream JSON output
claude -p "analyze this file" --output-format stream-json
```

---

### Model Selection Examples

```bash
# Use Claude Fable 5 (most capable)
claude --model fable

# Use Claude Opus 4.8 (balanced)
claude --model opus

# Use specific version
claude --model claude-opus-4-8

# High reasoning effort
claude --model opus --effort high -p "complex problem"
```

---

### Tool Control Examples

```bash
# Only allow specific tools
claude --tools "Bash,Edit,Read"

# Disable all tools
claude --tools ""

# Allow git commands only
claude --allowedTools "Bash(git *)"

# Block dangerous commands
claude --disallowedTools "Bash(rm *,sudo *)"
```

---

### Session Management Examples

```bash
# Named session
claude -n "feature-auth" "implement OAuth flow"

# Fork existing session
claude --resume abc123 --fork-session

# Resume from PR
claude --from-pr 42

# Background agent
claude --bg "long analysis task"
```

---

### MCP Integration Examples

```bash
# Load MCP config
claude --mcp-config servers.json

# Multiple configs
claude --mcp-config ~/.claude/mcp.json --mcp-config ./project-mcp.json

# Strict mode (only specified configs)
claude --strict-mcp-config --mcp-config servers.json
```

---

### Security & Permissions Examples

```bash
# Manual permission mode
claude --permission-mode manual

# Auto-approve safe actions
claude --permission-mode auto

# Auto-approve edits
claude --permission-mode acceptEdits

# Plan before executing
claude --permission-mode plan
```

---

### Advanced Workflow Examples

#### Code Review Workflow
```bash
# Review current changes
claude ultrareview

# With specific model
claude ultrareview --model opus

# Output to file
claude ultrareview --output review.json --json
```

#### CI/CD Integration
```bash
# Bare mode for CI
claude --bare --model opus -p "run tests and report" --output-format json

# With budget limit
claude -p "analyze PR" --max-budget-usd 2.00 --output-format json

# No session persistence
claude -p "task" --no-session-persistence
```

#### Worktree Workflow
```bash
# Create worktree with tmux
claude --worktree feature-x --tmux

# Named worktree
claude -w experimental-refactor
```

---

### Plugin Examples

```bash
# Install plugin
claude plugins install https://github.com/user/plugin

# Load for single session
claude --plugin-dir ./my-plugin

# Multiple plugins
claude --plugin-dir ./plugin1 --plugin-url https://example.com/plugin2.zip
```

---

### Debug & Development Examples

```bash
# Enable debug logging
claude --debug

# Specific debug categories
claude --debug api,hooks

# Exclude categories
claude --debug "!1p,!file"

# Write to file
claude --debug-file debug.log

# Verbose mode
claude --verbose
```

---

### Custom System Prompts

```bash
# Replace system prompt
claude --system-prompt "You are a security auditor"

# Append to default
claude --append-system-prompt "Focus on performance optimization"

# From file
claude --append-system-prompt-file prompts/reviewer.txt
```

---

### Structured Output Examples

```bash
# Extract structured data
claude -p "parse this invoice" --json-schema '{
  "type": "object",
  "properties": {
    "vendor": {"type": "string"},
    "amount": {"type": "number"},
    "date": {"type": "string"}
  },
  "required": ["vendor", "amount"]
}'

# Stream structured responses
claude -p "analyze logs" --output-format stream-json --include-partial-messages
```

---

### Enterprise Examples

```bash
# Gateway mode
claude gateway --port 8080 --config enterprise.json

# With specific settings sources
claude --setting-sources user,project --settings enterprise.json

# Safe mode for troubleshooting
claude --safe-mode
```

---

## Quick Reference Cheat Sheet

### Most Used Commands

```bash
claude                          # Start interactive
claude -p "prompt"              # Non-interactive, print
claude -c                       # Continue last session
claude -r                       # Resume (interactive picker)
claude -v                       # Version
claude -h                       # Help
```

### Model Shortcuts

```bash
claude --model fable            # Claude Fable 5
claude --model opus             # Claude Opus 4.8 (recommended)
claude --model sonnet           # Claude Sonnet 5
claude --model haiku            # Claude Haiku 4.5
```

### Permission Modes

| Mode | Behavior |
|:-----|:---------|
| `manual` | Prompt for every action |
| `auto` | Auto-approve safe actions |
| `acceptEdits` | Auto-approve file edits |
| `plan` | Plan before executing |
| `bypassPermissions` | Skip all prompts |

### Output Formats

| Format | Use Case |
|:-------|:---------|
| `text` | Default, human-readable |
| `json` | Single structured response |
| `stream-json` | Real-time streaming |

### Effort Levels

| Level | Use Case |
|:------|:---------|
| `low` | Fast, simple tasks |
| `medium` | Balanced default |
| `high` | Complex reasoning |
| `xhigh` | Very complex analysis |
| `max` | Maximum capability |

---

## Environment Variables

| Variable | Purpose |
|:---------|:--------|
| `ANTHROPIC_API_KEY` | API key for auth |
| `CLAUDE_CODE_SAFE_MODE` | Set to `1` for safe mode |
| `CLAUDE_CODE_SIMPLE` | Set to `1` for bare mode |

---

## Config Files

| File | Purpose |
|:-----|:--------|
| `~/.claude/settings.json` | Global user settings |
| `.claude/settings.json` | Project settings |
| `.claude/mcp.json` | MCP server configuration |
| `CLAUDE.md` | Project instructions |
| `~/.claude/CLAUDE.md` | Global instructions |

---

*Generated from `claude --help` — Claude Code, July 2026*
