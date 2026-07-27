---
name: pipeline
description: รัน SoloCorp pipeline workflow: spec → plan → build → qa → deliver
---

# Pipeline

Run the complete SoloCorp OS pipeline for a feature or task.

## Usage
```
/pipeline <feature description>
```

## Pipeline Stages
1. **Spec** — Write requirement specification
2. **Plan** — Decompose into tasks, assign to departments
3. **Build** — Implement in parallel across departments
4. **QA** — Quality assurance gate
5. **Deliver** — Deploy + report

## Rules
- Architecture review by Architect (song) before build
- Mirror check required for L3+ decisions
- All handoffs must follow 01-receive.md protocol

## Example
```
/pipeline Add API rate limiting to central bus
```
