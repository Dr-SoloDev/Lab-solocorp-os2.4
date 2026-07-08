# 🔌 SoloCorp MCP Server

> ให้ AI agent ภายนอก (OpenCode, Claude Code, Kimi CLI, Cursor, Codex CLI อะไรก็ได้) **เข้าใจและเรียกใช้ SoloCorp OS ได้** ผ่าน MCP protocol โดยไม่ต้องรู้โครงสร้างภายใน

---

## สารบัญ

- [MCP Server คืออะไร?](#mcp-server-คืออะไร)
- [Quick Start](#quick-start)
- [Tools ทั้งหมด](#tools-ทั้งหมด)
- [Resources ทั้งหมด](#resources-ทั้งหมด)
- [ตัวอย่างการเรียกใช้](#ตัวอย่างการเรียกใช้)
- [การ configure กับแต่ละ client](#การ-configure-กับแต่ละ-client)
- [สำหรับ Agent ที่อ่านเอกสารนี้ — Instructions](#สำหรับ-agent-ที่อ่านเอกสารนี้--instructions)
- [File Structure](#file-structure)

---

## MCP Server คืออะไร?

**MCP (Model Context Protocol)** เป็น protocol มาตรฐานที่ให้ AI agents เชื่อมต่อกับ tools และ data ภายนอก — เหมือน USB-C สำหรับ AI agents

**SoloCorp MCP Server** ตัวนี้คือสะพานที่ให้ **agent ใดๆ ก็ได้** (ไม่ว่าจะเป็น OpenCode CLI, Claude Code, Codex CLI, Kimi CLI, Cursor หรือ AI editor ใดๆ) สามารถ:

- ✅ **ถามว่า SoloCorp มีแผนกอะไรบ้าง** — ได้รายชื่อ 18 departments พร้อมหัวหน้าและสถานะ
- ✅ **อ่าน SOUL.md ของ department ที่สนใจ** — เข้าใจว่าแผนกนั้นทำอะไร มี specialist อะไรบ้าง
- ✅ **ค้นหาความสามารถ** — ค้นหาทั่วทุก SOUL.md profile ในระบบ
- ✅ **รู้ว่าควรส่งเรื่องนี้ไปแผนกไหน** — route request ตาม keyword หรือ semantic match
- ✅ **ดู routing rules** — เข้าใจว่าระบบตัดสินใจส่งงานอย่างไร
- ✅ **ดู pipeline commands** — รู้ว่ามีคำสั่งอะไรให้ใช้บ้าง
- ✅ **ดูทีม specialist ข้างใต้ department** — รู้ว่าแต่ละแผนกมีใครอยู่บ้าง

### ทำไมต้องมี MCP Server?

ก่อนหน้านี้ SoloCorp OS ถูกออกแบบให้ทำงานภายใน OpenCode เป็นหลัก — ใช้ `@mention` เพื่อเรียก department head และใช้ `/pipeline` commands เพื่อรัน workflow

แต่โลกของ AI agents ไม่ได้มีแค่ OpenCode — Claude Code, Cursor, Codex CLI, Kimi CLI ก็เป็น coding agents ที่มี开发者ใช้งานอยู่ เราเลยสร้าง MCP Server นี้ขึ้นมาเพื่อให้ **agent จาก ecosystem ไหนก็ได้** เข้าใจ SoloCorp OS และเรียกใช้ capabilities ของมันได้ โดยไม่ต้อง migrate มาที่ OpenCode

---

## Quick Start

### 1. Install dependencies

```bash
cd Lab-solocorp-os2.4
pip install mcp
# หรือใช้ uv: uv pip install mcp
```

### 2. Start the server (แยก process)

```bash
python3 -m solocorp_mcp.server
```

หรือ connect ผ่าน MCP client (ดู [การ configure กับแต่ละ client](#การ-configure-กับแต่ละ-client))

### 3. เรียกใช้ tools

จาก OpenCode ใน repo นี้ — พร้อมใช้งานทันทีเพราะ register ไว้ใน `opencode.json` แล้ว:

```
MCP tools available: solocorp_list_departments, solocorp_get_department, ...
```

---

## Tools ทั้งหมด

| Tool | ใช้เมื่อไหร่ | ได้อะไร |
|------|------------|---------|
| `solocorp_list_departments(status_filter?)` | อยากรู้ว่า SoloCorp มีแผนกอะไรบ้าง | รายชื่อ 18 departments + หัวหน้า + สถานะ |
| `solocorp_get_department(dept_id_or_name)` | อยากอ่าน SOUL.md ของแผนกนั้นๆ | Identity, Mission, Rules, Team structure เต็มๆ |
| `solocorp_route_request(query)` | มี request มา แต่ไม่รู้จะส่งใคร | ชื่อ department + @mention + priority |
| `solocorp_search_profiles(keyword)` | ค้นหาความสามารถหรือคนที่ใช่ | รายชื่อ profile ที่ match keyword |
| `solocorp_get_routing_rules()` | อยากรู้ routing logic ของระบบ | 16 routing rules + trigger keywords |
| `solocorp_get_commands()` | อยากรู้ว่ามี pipeline commands อะไร | 6 pipeline commands |
| `solocorp_get_team_members(dept_id)` | อยากรู้ว่าแผนกนั้นมี specialist อะไร | รายชื่อ specialist agents ใน department |

---

## Resources ทั้งหมด

| Resource URI | Description |
|-------------|-------------|
| `solocorp://departments` | รายชื่อแผนกทั้งหมด (markdown table) |
| `solocorp://departments/{id}` | SOUL.md profile ของแผนก (เช่น `solocorp://departments/07-engineering`) |
| `solocorp://routing/rules` | Routing rules ในรูปแบบ JSON |
| `solocorp://routing/semantic` | Semantic routing profiles (Thai + English phrases) |
| `solocorp://commands` | Pipeline commands ในรูปแบบ markdown |

---

## ตัวอย่างการเรียกใช้

### จาก Claude Code (หลังจาก configure)

```
> List departments in SoloCorp

[เรียก solocorp_list_departments]
→ returns: 18 departments with IDs, names, heads, and status

> What does the engineering department do?

[เรียก solocorp_get_department("07-engineering")]
→ returns: full SOUL.md of Engineering department

> I have a bug in the payment system, where should I send it?

[เรียก solocorp_route_request("bug in payment system")]
→ returns: Route to @engineering (high priority)
```

### จาก OpenCode ภายใน repo

```json
// opencode.json มี mcp.solocorp อยู่แล้ว — ใช้ได้ทันที
// tools จะขึ้นใน MCP tool list
```

---

## การ configure กับแต่ละ client

ดูรายละเอียดเต็มได้ที่: [`MCP_CLIENT_CONFIGS.md`](./MCP_CLIENT_CONFIGS.md)

| Client | Config file | ตัวอย่าง |
|--------|------------|---------|
| **OpenCode** | `opencode.json` | `"mcp": { "solocorp": { "type": "local", ... } }` |
| **Claude Desktop** | `claude_desktop_config.json` | `"mcpServers": { "solocorp": { "command": "python3", ... } }` |
| **Claude Code CLI** | `claude.json` | `"mcpServers": { "solocorp": { "command": "python3", ... } }` |
| **Codex CLI** | `.codex/config.toml` | `[mcp.solocorp]` section |
| **Kimi CLI** | `~/.kimi/mcp.json` | `"mcpServers": { "solocorp": { ... } }` |
| **Cursor** | Settings → MCP | Add command: `python3 -m solocorp_mcp.server` |

---

## สำหรับ Agent ที่อ่านเอกสารนี้ — Instructions

*(ถ้าคุณเป็น AI agent ที่กำลังอ่านไฟล์นี้ — นี่คือสิ่งที่คุณต้องรู้)*

This MCP server exposes SoloCorp OS — an organizational operating system with 18 departments, 55+ specialist agents, and a Central Bus. Use these tools when you need to:

1. **Discover who does what** — `solocorp_list_departments` gives you the full org structure
2. **Deep-dive into a department** — `solocorp_get_department` returns the complete SOUL.md profile including identity, mission, and team
3. **Route a user request** — `solocorp_route_request` uses keyword + semantic matching to find the right department
4. **Search for specific capabilities** — `solocorp_search_profiles` scans all 70+ SOUL.md files
5. **Understand routing logic** — `solocorp_get_routing_rules` shows the 16 keyword-based rules
6. **Get pipeline commands** — `solocorp_get_commands` lists what can be done within SoloCorp

**Language note:** SoloCorp OS primarily uses Thai for communication. Technical terms stay English. Don't be surprised if descriptions and profiles mix both — that's by design.

**Key facts to remember:**
- Department Heads **do not work themselves** — they delegate to specialist agents
- Use `@mention` to reach a department head directly (e.g., `@changful` for engineering)
- There are 6 pipeline commands: `/pipeline`, `/handoff`, `/status`, `/audit`, `/deploy`, `/brain`
- Central Bus runs on port 8099

---

## File Structure

```
solocorp_mcp/
├── README.md              ← ไฟล์นี้ — คำอธิบายสำหรับคนและ agent
├── MCP_CLIENT_CONFIGS.md  ← วิธี config กับ client ต่างๆ
├── server.py              ← ตัว MCP server (Python)
├── __init__.py             ← Package init
└── requirements.txt       ← Dependencies
```
