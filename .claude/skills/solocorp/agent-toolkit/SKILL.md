---
name: solocorp/agent-toolkit
version: 0.1.0
category: solocorp
platforms: [claude-code]
trigger: "/solocorp"
---

# 🏢 Solocorp Agent Toolkit

> Python module สำหรับ agents ใน SoloCorp OS ใช้สื่อสารระหว่าง departments

## Purpose
Agents ใช้ toolkit นี้สำหรับ:
- ส่ง task ไปยัง department อื่น (route_request)
- ดูข้อมูล department (get_department)
- เช็คสถานะ project (check_status)
- สร้าง dispatch (create_dispatch)
- ดู queue (get_queue)
- เรียก skill ของ department (invoke_skill)
- Mirror check (mirror_check)
- ประกาศแจ้งทุกคน (announce)

## Installation
Module อยู่ที่ `solocorp_skills/` ใน root ของโปรเจกต์

## Usage

### Import
```python
from solocorp_skills import (
    route_request,
    get_department,
    check_status,
    create_dispatch,
    get_queue,
    invoke_skill,
    mirror_check,
    announce,
)
```

### Route Request
```python
result = route_request(
    from_dept="engineering",
    to_dept="design",
    task="Implement new dashboard UI",
    priority="L2",
    deadline="2026-07-30",
    context="Need responsive design for mobile"
)
# Returns: {dispatch_id, status, routed_to}
```

### Get Department
```python
dept = get_department("engineering")
# Returns: {name, name_thai, role, model}

departments = list_departments()
# Returns: list of all departments
```

### Check Status
```python
status = check_status("bangkok-pos")
# Returns: {project, status, progress, blockers}
```

### Create Dispatch
```python
dispatch = create_dispatch(
    task="Fix login bug",
    priority="L2",
    source="engineering",
    target="all"
)
```

### Get Queue
```python
items = get_queue("normal")
# Returns: list of queue items
```

### Invoke Skill
```python
result = invoke_skill("ceo/sprint-plan", params={
    "department": "engineering",
    "sprint": "Sprint 2",
    "action": "plan"
})
```

### Mirror Check
```python
result = mirror_check(
    decision="Migrate to new LLM provider",
    priority="L3"
)
# Returns: {aligned, score, verdict}
```

### Announce
```python
announce(
    message="System maintenance tonight",
    priority="high",
    target="all"
)
```

## Error Handling
```python
from solocorp_skills import SolocorpError

try:
    route_request(...)
except SolocorpError as e:
    print(f"Error: {e.message}")
```

## Notes
- ถ้า Central Bus ไม่ทำงาน จะ fallback เป็น local file-based operations อัตโนมัติ
- ทุก operation มี timeout และ error handling
- ใช้ SOLOCORP_API_KEY environment variable สำหรับ authentication
