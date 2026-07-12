# WP5: Data Collector Tools — Recommendation Report

**Owner:** @content-creator-sek (เสก)
**Source:** teammate-skill research repo
**Date:** 2026-07-12
**Plan ref:** `bus/plans/persona-engineering-upgrade-v1.md`

---

## Summary

| Tool | Benefit | Primary Dept | Priority |
|:-----|:--------|:-------------|:--------:|
| github_collector.py | High | Engineering | **High** |
| project_tracker_parser.py | High | Orchestrator | **High** |
| slack_collector.py | Medium | Psychology | Medium |
| slack_parser.py | Medium | Psychology | Medium |
| email_parser.py | Medium | Support | Medium |
| notion_parser.py | Medium | Content Creator | Medium |
| confluence_parser.py | Medium | Engineering | Medium |
| teams_parser.py | Low | Support | Low |

---

## 1. github_collector.py

**Would SoloCorp benefit?** Yes — strongly. This tool pulls PRs, reviews, and commits from GitHub. SoloCorp's Engineering (dept 07), QA (dept 10), and Architect (dept 05) all need visibility into code activity. Currently there's no automated pipeline to feed GitHub events into the Central Bus.

**Department:** Engineering (ช่างฟูล), QA (QA-ทีม), Architect (พี่ทรงศักดิ์)

**Changes needed:**
- Wrap as a Loop Runner loop (`loops/github_collector.py`) that fires every 15-30 min
- Write collected events as JSONL messages to Central Bus queue (`bus/queue/`)
- Map repo names to SoloCorp pipeline IDs via a config file
- Add `.env` vars: `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPOS`

**Priority: High**

---

## 2. project_tracker_parser.py

**Would SoloCorp benefit?** Yes. This parses JIRA/Linear exports. SoloCorp uses pipeline-based task tracking — importing JIRA/Linear tickets directly into Central Bus project state would unify task tracking across systems.

**Department:** Orchestrator (พี่วุฒิ), Product (โปรดัค), Engineering (ช่างฟูล)

**Changes needed:**
- Convert export records into Central Bus message format (`models.py` schema)
- Feed parsed tickets into `bus/projects/` state dirs
- Map issue statuses (In Progress / Done) to SoloCorp pipeline stages
- Add an import trigger command (`/import-tracker`) in opencode.json

**Priority: High**

---

## 3. slack_collector.py

**Would SoloCorp benefit?** Moderately. Auto-pulling messages from Slack API would help Psychology (dept 18) analyze team communication patterns and Support (dept 12) monitor customer threads. Not critical for MVP but valuable for org analytics.

**Department:** Psychology (จิต), Support (ซัพพอร์ต)

**Changes needed:**
- Integrate with Central Bus as a loop with configurable channel list
- Anonymize/PII-filter via Legal vault (WP6) before storage
- Add `.env`: `SLACK_BOT_TOKEN`, `SLACK_CHANNELS`, `SLACK_HISTORY_DAYS`
- Respect privacy boundaries — only collect public channels and opted-in threads

**Priority: Medium**

---

## 4. slack_parser.py

**Would SoloCorp benefit?** Moderately. Parses Slack export JSON (complement to slack_collector). Useful for batch-importing historical conversations during onboarding or audit.

**Department:** Psychology (จิต), Legal (ตุลย์) for compliance audits

**Changes needed:**
- Add a CLI entry point or `/import-slack-export` pipeline command
- Validate export structure against SoloCorp's privacy rules before ingestion
- Send parsed messages to Central Bus with a `source: slack_export` tag

**Priority: Medium**

---

## 5. email_parser.py

**Would SoloCorp benefit?** Yes for Support workflows. Parses Gmail .mbox/.eml files. Support (dept 12) could use this to ingest customer email threads into Central Bus for triage and response tracking. Legal (dept 13) could use it for compliance review.

**Department:** Support (ซัพพอร์ต), Legal (ตุลย์)

**Changes needed:**
- Route parsed emails through Legal vault PII scanner (WP6) before storage
- Deduplicate by Message-ID + thread ID
- Map email addresses to SoloCorp customer profiles if available
- Add `MAILBOX_PATH` or `/import-mail` command

**Priority: Medium**

---

## 6. notion_parser.py

**Would SoloCorp benefit?** Yes. SoloCorp's Content Creator (dept 15) and Product (dept 06) likely use Notion for documentation and specs. Parsing Notion exports would bring external docs into the Central Bus knowledge graph.

**Department:** Content Creator (เสก), Product (โปรดัค), Design (ครีเอท)

**Changes needed:**
- Parse Markdown output into Central Bus fact format (`facts.py`)
- Support incremental sync (not just one-shot export)
- Map page hierarchy to SoloCorp's brain/ knowledge structure if applicable

**Priority: Medium**

---

## 7. confluence_parser.py

**Would SoloCorp benefit?** Yes. Similar value to Notion parser but for Confluence — relevant if Engineering or Product teams use Atlassian tools. Many enterprise workflows export architecture docs and PRDs from Confluence.

**Department:** Engineering (ช่างฟูล), Product (โปรดัค), Architect (พี่ทรงศักดิ์)

**Changes needed:**
- Same pattern as notion_parser: parse → convert → write to Central Bus
- Handle Confluence's HTML-based export format (different from Notion's Markdown)
- Register as `/import-confluence` command or loop-based periodic sync

**Priority: Medium**

---

## 8. teams_parser.py

**Would SoloCorp benefit?** Low priority. Parses Teams/Outlook exports. SoloCorp currently doesn't use Microsoft Teams as a primary channel. If the user base expands to enterprise clients using Teams, this becomes relevant.

**Department:** Support (ซัพพอร์ต)

**Changes needed:**
- Similar email-parser pattern with PII filtering
- Teams export format is complex (JSON + HTML); parsing logic would need testing with real exports
- No immediate integration — deprioritize until a concrete Teams data source exists

**Priority: Low**

---

## Implementation Recommendation

### Phase 1 (Week 1)
1. **github_collector.py** → Loop Runner loop + Central Bus integration
2. **project_tracker_parser.py** → Import command + project state mapping

### Phase 2 (Week 2)
3. **slack_collector.py** → Psychology analytics loop with privacy guard
4. **email_parser.py** → Support triage pipeline with PII filtering
5. **slack_parser.py** → Historical import utility

### Phase 3 (Later)
6. **notion_parser.py** — When Notion export volume justifies it
7. **confluence_parser.py** — When Confluence sources are identified
8. **teams_parser.py** — When Teams is an active data source

---

## Architecture Note

All adapted scripts should follow the Central Bus integration pattern:

```
Data Source → Collector Script → Central Bus Queue → Agent Worker → Department
```

This keeps the Two-Tier architecture intact: collectors run autonomously (Data Layer), Heads only see summarized results fed through the Control Layer.
