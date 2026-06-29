# QA: T3/Next.js Stack Validation Checklist

> **Use after:** Phase 1 implementation complete (parallel batch or sequential)
> **Use before:** CEO Demo / Delivery
> **Purpose:** Catch framework-specific issues that generic file-level checks miss

## 1. TypeScript Compile Check

Run the TypeScript compiler in strict mode — this catches type errors the IDE might miss:

```bash
cd project-root && pnpm tsc --noEmit 2>&1
```

**Expected:** Zero errors. If errors exist:

| Error Type | Likely Cause | Fix |
|:-----------|:-------------|:----|
| `Property 'X' does not exist on type 'Y'` | React Query v4 vs v5 API diff | Check `gcTime` → `cacheTime`, `keepPreviousData` flag |
| `Cannot find module` | Missing barrel export or wrong relative path | Check barrel exports in `index.ts`, relative paths in `packages/*` |
| `Type 'string \| undefined' not assignable` | Narrowing missed | Use `match?.[2]`, `const x = match?.[2]` pattern |

**Common gotchas:**
- **React Query v4** uses `cacheTime` / **v5** uses `gcTime` — check which version your project uses
- **match()[N] type narrowing** — `match` returns `RegExpMatchArray | null`, but array elements are `string | undefined`. Use `match?.[2]` + intermediate variable
- **Static factory methods** — if code calls `BridgeApiError.fromHttpError()`, the static method must exist on the class

## 2. Lint / ESLint Check

```bash
cd apps/web && pnpm lint 2>&1
```

If unconfigured (interactive prompt), the project needs `eslint.config.*` or `.eslintrc.*`. Check if a shared eslint config already exists under `tooling/eslint/` and extend it.

## 3. Barrel Export Completeness

Monorepos with layered exports (`index.ts` barrel files) often miss modules:

```bash
# List all .ts modules in a directory (exclude index.ts)
ls lib/api-bridge/*.ts | grep -v index.ts

# Compare against the barrel export
grep 'from' lib/api-bridge/index.ts | grep './'
```

**Check:** Every module file should be imported and re-exported through the barrel. Missing exports cause silent import failures.

## 4. Pages Structure Verification

```bash
# List all page routes
find apps/web/src/app -name "page.tsx" | sort
```

**Verify each page:**
- [ ] Has `'use client'` directive (if using hooks, effects, or browser APIs)
- [ ] Wrapped in layout / shell (e.g. `DashboardShell`)
- [ ] Uses auth guard (`getCurrentUser()` or middleware)
- [ ] API calls wrapped in `try/catch` with user-facing error messages
- [ ] Loading/error states handled
- [ ] No placeholder or stub content

## 5. Auth Flow Check

| Check | Pass Criteria |
|:------|:-------------|
| Login page | Calls `signIn("credentials")` |
| Error messages | In user's language (not English `Error: ...`) |
| Middleware | Protects dashboard routes, allows `/auth/login` and `/api/auth` |
| Auth guard | Page-level `getCurrentUser()` or `auth()` redirect |
| Session provider | Wraps the dashboard layout tree |

## 6. Environment Variables

```bash
# Check for required vars
grep 'NEXT_PUBLIC_' apps/web/src/env.mjs
grep -E '^[A-Z_]+\:' apps/web/src/env.mjs | grep -v '^#'
```

**Verify:**
- [ ] All env vars used in code are defined in `env.mjs`
- [ ] Both public (`NEXT_PUBLIC_*`) and server-only vars present
- [ ] `.env.example` or documentation exists for local setup

## 7. Seed Data / DB Check

```bash
# Verify seed exists
ls packages/db/src/seed.ts
```

**For auth seed specifically:**
- [ ] Uses hashed passwords (`bcrypt.hash()` or equivalent)
- [ ] Test users cover all roles (admin, manager, cashier, viewer)
- [ ] Follows Prisma schema exactly (same fields, relation shape)

## 8. Summary Template

```
## QA Results — [Project Name]

### TypeScript Compile: ✅ / ❌
- Errors: [N]
- Gotchas found: [none / list]

### Lint: ✅ / ❌
- Status: [pass / not configured]

### Barrel Export: ✅ / ❌
- Missing: [none / list modules]

### Pages Structure: ✅ / ❌
- Pages found: [N]
- Issues: [none / list]

### Auth Flow: ✅ / ❌
- Issues: [none / list]

### Environment: ✅ / ❌
- Missing vars: [none / list]

### Seed Data: ✅ / ❌
- Issues: [none / list]

### Overall Readiness: ✅ / 🟡 / ❌
- Blockers (must fix before demo): [list 🔴]
- Should fix: [list 🟡]
```

## Origin

Adapted from SoloCorp POS Phase 1 QA (June 2026) — a Next.js 15 + T3 + Prisma + NextAuth 5 project with 13 tasks and 34 files delivered via parallel delegation. The stack-specific checks caught 5 pre-existing TS errors (React Query compat, barrel export, static factory, type narrowing, relative path) that generic file-level validation would have missed.
