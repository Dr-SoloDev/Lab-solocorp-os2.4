# Multi-Track Parallel Execution

> **ที่มา:** Project Bangkok Phase 1 — SoloCorp POS (21 มิ.ย. 2026)
> 3 parallel Engineering tracks → 34 files, 9,123 บรรทัด → commit `dca3dab`
> Track 1: Foundation Layer (8 files), Track 2: Sale Lots (2 files), Track 3: Core Pages (3 files)

## Overview

Multi-Track Parallel Execution extends the **Parallel Batch** pattern to **large-domain engineering tracks** — each track produces an entire feature module (400-1,400+ lines), not a single small file. Used when a phase has been decomposed into independent domains and the subagents need full project context (schema, existing code, decision rules, design system) to build complete pages/components.

## When to Use

| Use Case | Example |
|:---------|:--------|
| Building multiple dashboard pages | Sale Lots + Purchase Orders + Catalog |
| Foundation layer + feature pages simultaneously | Auth setup + UI pages |
| Backend bridge + frontend consumers | API proxy + client modules + pages |
| Independent modules for the same user audience | Inventory + Reports + Settings |

**Prerequisites:**
- Phase scope is clear (CEO decisions locked)
- Tracks touch **different files entirely** — no shared file modifications
- Each track maps to a single domain or page module
- Project context (schema, design tokens, existing code) is stable and won't change mid-execution

## Track Decomposition

### Step 1: Map Phase Scope → Tracks

```text
Phase: Project Bangkok Phase 1 (Mobile Web PWA)
  ├── Track 1: Foundation Layer
  │   ├── SessionProvider wrapper (layout.tsx)
  │   ├── NextAuth middleware (middleware.ts)
  │   ├── PWA manifest route (manifest.json/route.ts)
  │   ├── Bridge API proxy (api/bridge/[...path]/route.ts)
  │   └── Test users seed (packages/db/src/seed.ts)
  │
  ├── Track 2: Sale Lots Business Logic + Page
  │   ├── Business Rules Doc (SALE_LOTS_BUSINESS_RULES.md)
  │   └── Sale Lots CRUD page (sale-lots/page.tsx)
  │
  └── Track 3: Core Pages
      ├── Purchase Orders page (purchase-orders/page.tsx)
      ├── Catalog page (catalog/page.tsx)
      └── Inventory page (inventory/page.tsx)
```

### Step 2: Build Track Context

Each track gets **complete self-contained context** — never make the subagent read the plan or other tracks' context:

```python
tasks = [
    {
        "goal": "Set up Foundation Layer: SessionProvider, Middleware, PWA manifest, Bridge proxy",
        "context": f"""
        PROJECT: solocorp-pos (pnpm monorepo, Next.js 15)
        
        EXISTING SETUP:
        - NextAuth v5 with PrismaAdapter + Credentials provider (packages/auth/src/index.ts)
        - Login page at apps/web/src/app/auth/login/page.tsx
        - NextAuth route handler at apps/web/src/app/api/auth/[...nextauth]/route.ts
        - Dashboard page with auth guard (apps/web/src/app/dashboard/page.tsx)
        - DashboardLayout at apps/web/src/app/dashboard/layout.tsx (currently wraps TRPCProvider only)
        - Root layout at apps/web/src/app/layout.tsx (calls /manifest.json)
        - PWA Shell component at lib/components/shell/DashboardShell.tsx
        - PWA manifest config at lib/pwa/manifest.ts
        - Service Worker config at lib/pwa/serviceWorker.ts
        - Bridge API client at src/lib/api-bridge/ (14 files)
        
        WHAT TO CREATE/MODIFY:
        1. Modify dashboard/layout.tsx — add SessionProvider + DashboardShell
        2. Create middleware.ts — auth guard (public: /auth/*, /api/*, /manifest.json)
        3. Create manifest.json/route.ts — serve PWA manifest
        4. Create api/bridge/[...path]/route.ts — proxy to PHP backend
        5. Create seed.ts — test users (admin, manager, cashier, viewer)
        """,
        "toolsets": ["terminal", "file", "coding"]
    },
    {
        "goal": "Build Sale Lots Page — understand old PHP logic, create bridge client page",
        "context": f"""
        PROJECT: solocorp-pos (pnpm monorepo)
        
        EXISTING SCHEMA (Prisma, packages/db/prisma/schema.prisma):
        - model Lot (lotCode, productId, branchId, quantity, availableQty, condition, buyPrice, sellPrice)
        - model SaleOrder / SaleItem (with lotId FK)
        - model PurchaseItem (with lotId FK)
        
        OLD PHP: ~/projects/scrap-pos/code/base-pos/api/Controllers/SalesController.php
        BRIDGE CLIENT: src/lib/api-bridge/sale-lots.ts (already exists)
        
        DECISIONS:
        - Sale Lots are IN Phase 1 (CEO override)
        - Auth: NextAuth Option B
        - DB: Dual DB (Bridge → PHP MySQL, NextAuth → PostgreSQL)
        
        WHAT TO CREATE:
        1. SALE_LOTS_BUSINESS_RULES.md — document the old PHP workflow
        2. sale-lots/page.tsx — full CRUD, mobile-first, Industrial Modern design
        """,
        "toolsets": ["terminal", "file", "coding"]
    }
]

results = delegate_task(tasks=tasks)
```

### Step 3: Track Context Checklist

Every track context must include:

| Element | Required? | Example |
|:--------|:---------:|:--------|
| Project root + stack | ✅ | `solocorp-pos (pnpm monorepo, Next.js 15)` |
| Schema / data model | ✅ | `model Lot (lotCode, availableQty, ...)` |
| Existing code paths | ✅ | `Login page at apps/web/src/app/auth/login/page.tsx` |
| CEO decisions / rules | ✅ | `Sale Lots are IN Phase 1` |
| Design system | ✅ | `Industrial Modern (primary #1A56BD, steel grays)` |
| File to create/modify | ✅ | explicit paths for each file |
| Output expectations | ✅ | `mobile-first, touch targets 44px, Thai UI` |
| API modules to use | ✅ | `apiBridge.saleLots.getAll()`, `apiBridge.purchase.*` |

## Cross-Track Integration Validation

After ALL tracks complete, run these checks:

### 1. File Consistency Check

```bash
# Verify all expected files exist
find apps/web/src/app -name "*.tsx" -o -name "*.ts" | sort
git status --short
# Expected: all N files from track decomposition
```

### 2. Cross-Reference Check

| Check | How | Example |
|:------|:----|:--------|
| Layout wraps all pages | Read dashboard/layout.tsx | Does it import SessionProvider? DashboardShell? |
| API modules match pages | Check imports in pages | Does sale-lots/page.tsx import correct apiBridge module? |
| Middleware covers all routes | Read middleware.ts | Are /dashboard/* paths protected? |
| PWA manifest serves correctly | Read manifest.json/route.ts | Does it import the config from lib/pwa/manifest.ts? |
| Seed script has correct imports | Read packages/db/src/seed.ts | Does it import PrismaClient correctly? |

### 3. Build / Type Check

```bash
cd ~/solocorp-pos && pnpm build 2>&1 | tail -30
# Focus on: "Module not found", "Type 'X' is not assignable", "Cannot find name"
```

**Cross-track errors to watch for:**
- Track A created a module, Track B imports it but uses wrong export name
- Track A modified a shared file, Track B's imports now break
- Track C uses a component that Track A renamed
- Two tracks created files with conflicting names

### 4. Functional Integration

If the environment can run:
- Start the dev server
- Visit each page
- Verify auth flow (login → dashboard → pages → logout)
- Check PWA manifest is served

## Checkpoint Pattern

After all tracks complete and pass integration validation:

```bash
# 1. Git commit everything
git add -A && git commit -m "Phase X Complete: [summary]"

# 2. Save durable facts to memory
memory(action="add", content="Phase X delivered: [project] commit HASH, N files, M lines")

# 3. Update task list
todo(todos=[...all tasks completed...], merge=True)

# 4. Report to user
```

**Commit message format:**
```
Phase 1 Complete: Mobile Web PWA — All modules delivered

## What's included

### Foundation
- SessionProvider wrapper (dashboard/layout.tsx)
- NextAuth middleware (middleware.ts)
- PWA manifest JSON route (manifest.json/route.ts)
- Bridge API proxy (api/bridge/[...path]/route.ts)
- Test users seed script (packages/db/src/seed.ts)

### Pages (Mobile-first PWA)
- Sale Lots (sale-lots/) — Full CRUD + Business Rules Doc
- Purchase Orders (purchase-orders/) — Multi-step create form
- Catalog (catalog/) — Product listing with price tiers
- Inventory (inventory/) — Stock levels with alerts

### CEO Decisions Applied
- ✅ Sale Lots kept in Phase 1
- ✅ Auth Option B (NextAuth login, new session)
- ✅ DB Option A (Dual DB: Bridge→MySQL + NextAuth→PostgreSQL)
```

## Common Pitfalls

| Pitfall | Symptom | Prevention |
|:--------|:--------|:----------|
| Tracks touch same file | Merge conflicts, overwritten code | Verify file targets are disjoint before dispatching |
| Missing cross-import | Build fails with "Cannot find module" | Include full module paths in each track's context |
| Inconsistent design | Pages look different | Pass exact design tokens (color hex, spacing) in ALL track contexts |
| Auth gap | Pages don't check auth | Make middleware the FIRST track, verify routes in integration check |
| Subagent self-report is wrong | File says one thing, summary says another | Read/verify files yourself, don't trust the summary alone |

## References

- `subagent-driven-development` main SKILL.md — Phase 2: Implementation workflow
- `references/integration-validation.md` — 5-check post-execution validation pattern
- `references/dev-pipeline.md` — Full lifecycle pipeline with RACI matrix
