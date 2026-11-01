# PRD: SoloCorp OS Local-First MCP App MVP v1.0

| Field | Value |
|:--|:--|
| Product | SoloCorp OS App + Department MCP Platform |
| Status | Owner-approved product direction; MVP scope defined; implementation not started |
| Date | 2026-11-01 |
| Primary user | Solo operator / developer using AI agents |
| Initial module | Content Creator MCP |
| Delivery target | Local-first web app; hosted deployment follows Beta |

> This is the current source of truth for the product direction and the next MVP. Historical plans remain useful as implementation evidence, but do not override this PRD where their future roadmaps conflict.

## 1. Product Vision

SoloCorp OS will provide one understandable home for an AI-enabled organization. A user can connect only the department MCPs they need, or use the SoloCorp App with one CEO agent that can see enabled departments, route work, track tasks, and return results.

Every department MCP must remain independently useful through a compatible MCP client. Connecting the CEO or the SoloCorp App may add organization-wide context, routing, registry, queue, and cross-department coordination; it must not be a prerequisite for using a department's own capabilities.

The product direction is local-first and compatible with a future hosted app. The initial Beta validates the local experience and user value before subscription, marketplace, and hosted multi-user work.

## 2. Problem

- Users currently configure MCP servers and discover department capabilities through client-specific setup.
- A department MCP can expose useful tools, but a user needs an easy way to select modules, see connection status, brief one CEO, and follow assigned work.
- The existing Core MCP exposes SoloCorp information and routing tools, but it is not a first-party application, connection manager, or department MCP host.
- External-client users need to use a single department without installing the rest of SoloCorp OS.

## 3. Users and Jobs

| User | Job to be done |
|:--|:--|
| Local SoloCorp user | Configure a model, enable departments, brief the CEO, and see task status and outputs in one app. |
| External MCP user | Connect one department MCP directly to a compatible client and use that department's capabilities without the CEO MCP. |
| Self-hosting builder | Run the open components locally, inspect configuration, and add or adapt department modules. |
| Beta participant | Try a narrow end-to-end workflow and share feedback with explicit control over submitted data. |

## 4. Product Principles

1. **Local-first:** The first app runs on the user's machine and does not require SoloCorp cloud services.
2. **Department independence:** A department package owns its domain logic and MCP adapter. It must not require a CEO MCP connection for standalone department work.
3. **One CEO experience:** Inside the SoloCorp App, one CEO agent receives the human brief and coordinates the tools and tasks visible to that app session.
4. **Host-owned connections:** The app runtime manages its MCP connections and reports their status. An MCP server does not claim to know which other servers a separate client has connected.
5. **Composable modules:** Department capabilities, requirements, permissions, transport, and commercial tier are declared as module metadata.
6. **Model choice stays explicit:** The user configures the model/provider for the app. Department MCPs do not silently switch models or receive provider credentials unless the user explicitly configures that integration.
7. **Open-core direction:** Keep the interoperability contract and self-host path usable; optional hosted services and premium department capabilities may fund ongoing development. Pricing and licensing boundaries remain to be validated.

## 5. Target Architecture

```text
Compatible external MCP client
  └── one Department MCP
       └── department-scoped capability; no CEO dependency

SoloCorp local app
  ├── Web UI: CEO chat, module controls, task history, settings
  ├── Local runtime / MCP host: model adapter + department connections
  ├── Registry: module metadata, enabled state, health, capabilities
  ├── Central Bus: task queue/state and artifact references
  └── Department MCPs: independently packaged modules

Future hosted app
  ├── Hosted UI and orchestration
  └── Remote MCP connections or an explicitly installed local connector
```

The MCP host in the local app initiates and owns connections to enabled department MCPs. This gives the user a plug-in experience through the registry and UI; it does not require an MCP server to accept server-to-server connections. In external clients, that client's host owns the connection configuration and status.

The CEO is the model-driven agent experience in the app. The Core MCP is a capability provider for organization data and routing. The web app/runtime is the product shell and connection manager. Keep these responsibilities separate.

## 6. Usage Modes

### 6.1 Standalone Department Mode

- The user connects only the selected department MCP to an external MCP client.
- The client supplies the model and agent behavior.
- The module exposes the full supported capability of that department, including its own workflow, tools, resources, and department data path.
- It must not require the Core MCP, CEO App, Central Bus daemon, or another department unless that dependency is declared as optional and the relevant feature is clearly disabled without it.

### 6.2 Integrated SoloCorp App Mode

- The app presents one CEO conversation and a department module catalog.
- The user can enable or disable modules and inspect status and capabilities.
- The CEO can call tools from enabled department MCPs through the app runtime's existing connections in the same user conversation.
- Work that needs tracking is recorded as a task with an ID, target department, lifecycle status, and artifact/error references.
- A missing or disconnected department produces an explicit status and next action; the app does not silently route the work elsewhere.

### 6.3 Hosted Mode (Future)

- The hosted product may connect to remote MCP endpoints or use an opt-in local connector for local-only servers.
- Hosted mode requires separate multi-tenant, identity, secret storage, billing, and deployment design.
- Local `stdio` processes are not assumed to be reachable from a hosted browser or backend.

## 7. MVP Scope

### Must Have

1. A single-user local web app with a simple CEO chat, module screen, task history, and provider settings.
2. A local runtime that can register, enable, disable, connect, disconnect, and health-check MCP modules.
3. A module registry that records stable module ID, name, version, transport/entry point, capabilities, declared dependencies, required permissions, and status.
4. One explicitly configured model/provider adapter using a user-provided credential; no silent provider or model fallback.
5. The Core MCP's organization and routing capabilities available to the CEO app without making them a dependency of standalone department MCPs.
6. Content Creator as the first integrated department module, using the existing department MCP pilot as the starting point.
7. One end-to-end tracked task path: human brief → CEO selects Content Creator → task record is created → app invokes the enabled department MCP workflow → task reaches a terminal status and returns artifact references or a clear error.
8. A visible unavailable state when Content Creator is disabled or disconnected, with instructions to enable or repair the module.
9. A standalone acceptance path that connects Content Creator directly to at least one external compatible MCP client without the Core MCP.
10. Beta feedback controls. Product telemetry is off by default; any shared diagnostic data is opt-in, and prompts/artifacts are not uploaded by default.

### Should Have

- A curated installable module catalog with clear free/premium labels, without billing enforcement in MVP.
- Task cancellation/retry for safe operations and a compact connection diagnostic view.
- A local export of task metadata and feedback for debugging.

### Out of Scope for MVP

- All departments and all specialist agents.
- General-purpose dynamic plugin installation from arbitrary untrusted commands.
- A full autonomous LLM worker team for every department. MVP proves one bounded department workflow; multi-agent background execution expands after the first Beta.
- Hosted multi-user SaaS, subscriptions, payment processing, public marketplace, and usage billing.
- Requiring the user to connect every department MCP when they only need one.
- Replacing or rewriting the existing Central Bus before its queue and API are evaluated for the MVP task contract.
- Making Core MCP a server-side proxy for every department MCP.

### MVP Execution Boundary

For the first vertical slice, the CEO session/runtime prepares the work and calls the connected Content Creator MCP tools. The queue persists task lifecycle and results. A tool call is not represented as an autonomous department-head LLM session. A bounded local task runner may execute the declared workflow, but a general multi-agent worker pool is a later phase.

### Post-MVP Commercial Direction

- Keep the interoperability contract, local runtime, and a useful starter set available for self-hosting; decide which modules are open-source individually.
- Consider subscriptions for hosted operation and premium flagship department MCPs, plus optional enterprise governance/support.
- Keep model-provider costs separate and explicit. Final packaging, licensing, tiers, and prices require later validation and are not MVP deliverables.

## 8. Functional Requirements

| ID | Requirement | MVP acceptance |
|:--|:--|:--|
| FR-01 | Module discovery | App lists installed/known modules and their declared department capabilities. |
| FR-02 | Connection control | User can enable/disable a curated module and sees `disabled`, `connecting`, `connected`, or `error`. |
| FR-03 | CEO routing | CEO selects a suitable enabled department and names the reason/target in the task record. |
| FR-04 | Missing module handling | If a required department is unavailable, the CEO/App explains which module is missing and how to enable it. |
| FR-05 | Task tracking | Each assignment has a stable `task_id`, department, status, timestamps, result references, and error detail when applicable. |
| FR-06 | Direct department capability | CEO can call an enabled department MCP tool within the app session without starting a second user chat. |
| FR-07 | Standalone compatibility | A department MCP can be configured and used from an external client without CEO/Core MCP. |
| FR-08 | Feedback | User can submit feedback with explicit choice to include diagnostics; content sharing is separately opt-in. |

## 9. Non-Functional Requirements

- Local app binds to loopback by default and keeps provider credentials in local configuration, outside task artifacts.
- Connection, tool, and task errors use explicit structured status; no failure is reported as successful completion.
- Module metadata is validated before starting a process or contacting a remote endpoint. MVP installation uses curated/explicitly trusted modules.
- Task and artifact storage reuse existing Central Bus components where the current data model fits; department domain logic remains protocol-neutral where practical.
- The app can be stopped and restarted without losing task history or enabled-module configuration.
- A module can run with a department-scoped data directory and must not read/write unrelated department data by default.

## 10. Beta Learning Plan

### Events to Measure

- App start and model configuration completion.
- Module enable/connect success and failure.
- Time to first completed task.
- Task completion, failure, retry, and cancellation counts by module.
- User feedback rating and free-text response when submitted.

### Beta Data Policy

- Keep diagnostics local by default.
- Ask separately before sharing diagnostics and before sharing prompt/artifact content.
- Provide a way to inspect the exact diagnostic bundle before submission.
- Use Beta findings to prioritize connection UX, module usefulness, task success, and repeated usage before pricing work.

## 11. Delivery Phases and Gates

| Phase | Deliverable | Exit gate |
|:--|:--|:--|
| 0. Product foundation | This PRD, module manifest, task envelope, and local runtime design note | Contracts and MVP boundaries are documented. |
| 1. Local app shell | Local UI, provider settings, registry, and connection status | User can configure one model and enable/disable the Content Creator module. |
| 2. Integrated vertical slice | CEO routing, tracked task lifecycle, Content MCP invocation, and artifact result view | One brief completes through the app; disabling the module yields a clear unavailable result. |
| 3. Standalone verification | Content MCP setup and successful use in an external MCP client | Department works without Core MCP or SoloCorp App. |
| 4. Closed Beta | Local Beta package, feedback flow, opt-in diagnostics, known limitations | Beta users can install, finish the workflow, and return actionable feedback. |
| 5. Product expansion | More departments and background workers | Prioritize from Beta evidence; certify each department independently. |
| 6. Hosted/open-core release | Remote connection or local connector, multi-tenant design, packaging, licensing, and monetization | Complete release-readiness and independent verification before general/paid launch. |

Known audit and production-readiness findings are recorded and handled in Phase 6. They do not redefine the MVP roadmap; Beta materials must accurately state the current limitations and must not present unverified checks as production guarantees.

## 12. Success Metrics

- At least 80% of invited Beta users connect the initial department module successfully.
- At least 70% of connected Beta users complete one end-to-end Content Creator task.
- Connection failures and task failures are distinguishable and diagnosable from local logs.
- Feedback identifies at least the top three usability or capability gaps for the next iteration.
- Standalone department setup succeeds without the Core MCP in the documented external-client path.

Targets are initial Beta thresholds, not public launch guarantees; revise them after the first cohort.

## 13. Current State (2026-11-01)

- `solocorp_mcp.server` is the existing Core MCP for organization/profile/routing capabilities; it is not yet the SoloCorp App, a UI, or a host for other MCP servers.
- `solocorp_mcp.departments.content_mcp` is the first department MCP pilot and the MVP's initial module candidate. Existing pilot verification is historical evidence, not certification of the new app.
- `central_bus/` already provides FastAPI services and a SQLite-backed queue. Reuse is preferred after validating task semantics and local-app boundaries.
- A first-party SoloCorp App/runtime and module registry are not implemented yet.
- Product direction and documentation alignment are recorded; SoloCorp App/runtime implementation is **NOT STARTED**.

## 14. Related Documents

- [Agent Quickstart](../../AGENTS.md) — current session instructions and product-direction pointer.
- [Content Creator MCP Pilot](../plans/MCP-DEPARTMENT-SERVERS-CONTENT-PILOT.md) — implementation and test history for the initial module.
- [Core MCP README](../../solocorp_mcp/README.md) — current Core MCP capabilities and external-client setup.
- [Multi-Platform Compatibility PRD](PRD-Multi-Platform-Compatibility-v1.0.md) — external-client compatibility context; it does not replace this app roadmap.
