# Integration Validation Checklist

> **Use after:** All tasks in a plan are complete (sequential or parallel batch)
> **Use before:** Generating the final report
> **Goal:** Catch cross-task inconsistencies that subagents (self-reporting) would miss

## The 5-Check Pattern

### 1. File Existence Check

Verify every file the plan promised to create/modify:

```python
from hermes_tools import terminal

files = [
    "path/to/file1.yaml",
    "path/to/file2.md",
    "path/to/file3.sh",
]
r = terminal("stat " + " ".join(files) + " 2>&1 | grep -c 'No such file' || echo 'ALL_EXIST'")
# Expect: "ALL_EXIST"
```

**Variant — check all files of a type were created:**
```bash
# Check count matches plan spec
ls path/to/dir/*.yaml | wc -l
# Expect: 7 (schema + 6 profile cards)
```

### 2. Syntax / Lint Validation

For every generated structured file:

| Format | Command |
|:-------|:--------|
| YAML | `python3 -c "import yaml; yaml.safe_load(open('file.yaml'))"` |
| JSON | `python3 -c "import json; json.load(open('file.json'))"` |
| Markdown | `python3 -c "import sys; lines=open('file.md').readlines(); print(f'{len(lines)} lines')"` |
| Shell script | Run with `--help` or dry-run flag (if available) |

**Batch check YAML files:**
```bash
for f in /path/to/*.yaml; do
    python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>&1 || echo "FAIL: $f"
done
```

### 3. Cross-Reference Check

Files often reference each other. Verify all references resolve:

```python
from hermes_tools import terminal

# Check: Does file A reference a path in file B that exists?
pairs = [
    ("profile-baselines/ceo-baseline.md", "workflows/surface-assumptions.md"),
    ("profile-baselines/ceo-baseline.md", "workflows/spec-template.md"),
    ("profile-baselines/ceo-baseline.md", "workflows/after-action-review.md"),
    ("profile-baselines/orchestrator-baseline.md", "workflows/after-action-review.md"),
    ("profile-baselines/orchestrator-baseline.md", "workflows/pipeline-trace.md"),
    ("profile-baselines/architect-baseline.md", "architect-routing.yaml"),
    ("lab/agent-cards/ceo.yaml", "lab/agent-cards/agentcard-schema.yaml"),
]

for src, target_ref in pairs:
    r = terminal(f"grep -c '{target_ref}' {src} 2>&1")
    status = "✅" if r['output'].strip() != '0' else "❌"
    print(f"{status} {src} → {target_ref}")
```

**To check all cross-references at once:**
```bash
# Find all path references like `workflows/` or `lab/` in the generated files
# and verify the targets exist
for ref in $(grep -roh 'workflows/[a-z-]*\.md' generated_dir/ | sort -u); do
    [ -f "$ref" ] && echo "✅ $ref" || echo "❌ MISSING: $ref"
done
```

### 4. Functional Test

For scripts or tools, run them with real inputs:

```python
from hermes_tools import terminal

# Run with minimal valid inputs
r = terminal("bash /path/to/script.sh profile action status 'Message' 2>&1")

# Check: exit code 0 AND expected output
assert r['exit_code'] == 0, f"Script failed: {r['output']}"
assert "✅" in r['output'], f"Script did not produce success signal"
```

**For database-backed tools:**
```python
import sqlite3
db = sqlite3.connect('/path/to/database.db')
count = db.execute('SELECT count(*) FROM events').fetchone()[0]
assert count > 0, "No events recorded"
```

### 5. Content Consistency Check

Verify generated content matches plan spec:

```bash
# Count expected items
grep -c '  - id:' routing.yaml
# Expect: 22 (matches plan spec)

# Check structure constraints
wc -l < profile-baseline.md
# Expect: ≤ 60 (thin shell constraint)

# Count required template sections
grep -c '## {{section}}' spec-template.md
# Expect: 5 (Objective, Commands, Structure, Testing, Boundaries)
```

## When to Run This

| Scenario | Must Run? | Notes |
|:---------|:---------:|:------|
| After parallel batch execution | ✅ REQUIRED | Subagents self-report; integration gaps likely |
| After sequential execution | ✅ Recommended | Catches cross-task issues reviews miss |
| After single-task plans | ⚠️ Optional | Skip only if 1 file, 1 task, no cross-refs |
| After infrastructure/tool changes | ✅ Required | Configs, scripts, and schemas must be consistent |

## Sample Output (Pass)

```
=== VALIDATION RESULTS ===
1/ File existence: 14/14 ✅
2/ YAML validation: 9/9 ✅
3/ Cross-references: 8/8 ✅
4/ Functional test: 6 events in DB ✅
5/ Route count: 22 (spec: 22) ✅
=== ALL 5 CHECKS PASSED ===
```

## Sample Output (Fail)

```
=== VALIDATION RESULTS ===
1/ File existence: 13/14 ❌ MISSING: deploy-config.yaml
2/ YAML validation: 8/9 ❌ FAIL: agentcard-ceo.yaml
3/ Cross-references: 6/8 ❌ MISSING: baseline → spec-template
4/ Functional test: ⚠️ exit code 1
5/ Route count: 18 (spec: 22) ❌ MISSING 4
=== 4 ISSUES FOUND — FIX BEFORE REPORT ===
```

## Origin

This pattern was distilled from Sprint 1 Foundation (18 Jun 2026) of SoloCorp OS 2.0 — a ~15h session with 7 tasks, 45 files, 1782 lines, executed via parallel batch delegation. The 5-check pattern caught agentcard schema-reference gaps and ensured all 22 routes, 6 agent cards, and 4 workflow templates formed a consistent integrated system.
