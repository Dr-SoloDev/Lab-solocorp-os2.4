# SoloCorp MCP Server — Client Configuration

ให้ external coding agents เชื่อมต่อ SoloCorp OS ผ่าน MCP protocol

---

## 🔌 OpenCode

Add to `opencode.json`:

```json
{
  "mcp": {
    "solocorp": {
      "type": "local",
      "command": ["python3", "-m", "solocorp_mcp.server"],
      "cwd": "/path/to/Lab-solocorp-os2.4",
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

แล้วเรียกใช้ด้วย `@solocorp` หรือใช้ tools โดยตรง

---

## 🔌 Claude Code / Claude Desktop

Add to `~/.claude/settings.json` (Claude Desktop) or `claude.json` (Claude Code CLI):

```json
{
  "mcpServers": {
    "solocorp": {
      "command": "python3",
      "args": ["-m", "solocorp_mcp.server"],
      "cwd": "/path/to/Lab-solocorp-os2.4"
    }
  }
}
```

---

## 🔌 Codex CLI

Add to `.codex/config.toml`:

```toml
[mcp.solocorp]
command = "python3"
args = ["-m", "solocorp_mcp.server"]
cwd = "/path/to/Lab-solocorp-os2.4"
```

---

## 🔌 Kimi CLI / Kimi Desktop

Kimi ใช้ MCP config แบบ Claude format (`~/.kimi/mcp.json`):

```json
{
  "mcpServers": {
    "solocorp": {
      "command": "python3",
      "args": ["-m", "solocorp_mcp.server"],
      "cwd": "/path/to/Lab-solocorp-os2.4"
    }
  }
}
```

---

## 🔌 Cursor

Settings → Features → MCP → Add:

```
Name: solocorp
Type: command
Command: python3 -m solocorp_mcp.server
Working Directory: /path/to/Lab-solocorp-os2.4
```

---

## 🔌 Windsurf / Continue.dev / Any MCP Client

MCP config ทุกรูปแบบใช้ schema เดียวกัน:

```json
{
  "mcpServers": {
    "solocorp": {
      "command": "python3",
      "args": ["-m", "solocorp_mcp.server"],
      "cwd": "/path/to/Lab-solocorp-os2.4"
    }
  }
}
```

---

## Tools Available

| Tool | Description |
|------|-------------|
| `solocorp_list_departments` | List all departments (optionally filter by status) |
| `solocorp_get_department` | Get full SOUL.md profile of a department |
| `solocorp_route_request` | Route a natural language request to the correct department |
| `solocorp_search_profiles` | Search across all SOUL.md profiles |
| `solocorp_get_routing_rules` | View keyword-based routing rules |
| `solocorp_get_commands` | List available pipeline commands |
| `solocorp_get_team_members` | List specialist agents under a department |

## Resources Available

| Resource | Description |
|----------|-------------|
| `solocorp://departments` | All departments listing |
| `solocorp://departments/{id}` | Full SOUL.md profile |
| `solocorp://routing/rules` | Routing rules JSON |
| `solocorp://routing/semantic` | Semantic routing profiles |
| `solocorp://commands` | Pipeline commands |

---

## Requirements

```bash
pip install mcp
```
