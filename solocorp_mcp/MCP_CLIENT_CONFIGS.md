# SoloCorp MCP Server — Client Configuration

ให้ external coding agents เชื่อมต่อ SoloCorp OS ผ่าน MCP protocol

> **รูปแบบ connection:** OpenCode/Codex หรือ client ภายนอกเป็นผู้จัดการ connection ของ MCP ที่ลงทะเบียนใน client นั้น. ต่อเฉพาะ Department MCP ได้เมื่อใช้แผนกเดียว; Core MCP ไม่ได้เห็นหรือควบคุม connection อื่นของ client. ในเป้าหมาย SoloCorp App, local app runtime จะเป็น host ที่จัดการ registry และ toggle ของตัวเอง. ดู [PRD ปัจจุบัน](../docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md); app runtime ยังไม่ implement.

---

## Department MCP servers (Content Creator pilot)

นอกจาก `solocorp` core server แล้ว โปรเจกต์นี้มี server แบบเสียบแยกตามแผนก:

- `central-bus` — storage primitives สำหรับ payload ของแผนก
- `content-creator` — หัวหน้าเสกและ workflow ของ Content Creator

OpenCode ลงทะเบียนไว้ใน `opencode.json` แล้ว ส่วน Codex ลงทะเบียนไว้ใน
`.codex/config.toml` แล้ว คำสั่งที่ใช้จาก repo นี้คือ:

```bash
.venv/bin/python3 -m solocorp_mcp.bus_mcp
.venv/bin/python3 -m solocorp_mcp.departments.content_mcp
```

ต่อเฉพาะ `content-creator` ได้เมื่อใช้งานงานคอนเทนต์อย่างเดียว ตัว server
ใช้ shared bus store ภายในตัวเอง จึงไม่จำเป็นต้องเปิด Central Bus MCP อีกตัว
เพื่อสร้าง draft; ต่อ `central-bus` เพิ่มเมื่อ client ต้องการอ่าน/ตรวจ payload
โดยตรง

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

## 🔌 Grok Build CLI

Add to project `.grok/config.toml` (already wired in this repo):

```toml
[mcp_servers.solocorp]
command = "/path/to/Lab-solocorp-os2.4/.venv/bin/python"
args = ["-m", "solocorp_mcp.server"]
cwd = "/path/to/Lab-solocorp-os2.4"
startup_timeout_sec = 30
tool_timeout_sec = 60
enabled = true

[mcp_servers.solocorp.env]
PYTHONPATH = "/path/to/Lab-solocorp-os2.4"
SOLOCORP_API_KEY = "${SOLOCORP_API_KEY:-sk-solocorp-admin-local-dev-001}"
```

Verify:

```bash
grok mcp list          # should show solocorp (project)
# In TUI: solocorp_list_departments / solocorp_route_request
```

Also start runtime: `bash scripts/start-services.sh`

---

## 🔌 Codex CLI

Add to `.codex/config.toml` (the repo already includes these entries):

```toml
[mcp_servers.central_bus]
command = "/path/to/Lab-solocorp-os2.4/.venv/bin/python3"
args = ["-m", "solocorp_mcp.bus_mcp"]
cwd = "/path/to/Lab-solocorp-os2.4"
enabled = true

[mcp_servers.content_creator]
command = "/path/to/Lab-solocorp-os2.4/.venv/bin/python3"
args = ["-m", "solocorp_mcp.departments.content_mcp"]
cwd = "/path/to/Lab-solocorp-os2.4"
enabled = true
```

Codex CLI รุ่นใหม่จัดการรายการที่ใช้งานจริงใน `~/.codex/config.toml` ให้ใช้
คำสั่ง `codex mcp add` หรือค่าที่แสดงใน `codex mcp list --json` เป็นแหล่งตรวจสอบ
สุดท้าย

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
