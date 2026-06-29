---
name: vite-react-spa-setup
description: "Bootstrap a Vite + React SPA — routing, auth, Tailwind, deploy alongside legacy backend"
version: 1.0.0
author: Dr.solodev + เทอโบ
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  commands: [node, npm]
metadata:
  hermes:
    tags: [react, vite, spa, frontend, tailwind, migration, deployment]
    related_skills: [popular-web-designs, php-mvc-crud-feature]
---

# Vite + React SPA Setup

Class-level workflow for spinning up a production-ready React SPA with Vite. Covers the
full path: scaffold → Tailwind → routing → auth → API client → deployment. Designed for
the common case of building a new frontend that lives alongside an existing backend
(PHP/Apache, Node, Django, Rails) and shares the same API.

## When to Use

- Building a new React frontend for an existing app (incremental migration)
- Bootstrapping a fresh React SPA that needs to ship to production
- Rebuilding a UI while keeping the legacy version reachable for fallback
- Setting up the standard React stack: Router + state + API + forms

## The Stack (defaults)

| Concern | Library | Why |
|---|---|---|
| Build | **Vite** | Fastest dev server, HMR, ES modules |
| UI | **React 18** | Default |
| Styling | **Tailwind CSS 3.x** | Utility-first, fast iteration |
| Routing | **react-router-dom 6** | De facto standard |
| State | **Zustand** + `persist` | Light, no boilerplate, localStorage built-in |
| Server state | **@tanstack/react-query** | Caching, retry, loading states |
| API | **Axios** | Interceptors for JWT |
| Forms | **react-hook-form** + **zod** | Validation, no re-renders |
| Icons | **lucide-react** | Modern, tree-shakable |
| cn helper | **clsx** + **tailwind-merge** | Conditional classes |

Pin Tailwind to v3.x — v4 uses different config syntax and breaks `tailwind.config.js`.

## Bootstrap Sequence

```bash
# 1. Scaffold
npm create vite@latest my-app -- --template react
cd my-app

# 2. Install runtime deps
npm install react-router-dom zustand axios @tanstack/react-query \
            react-hook-form zod @hookform/resolvers \
            lucide-react clsx tailwind-merge

# 3. Install Tailwind (PIN to 3.x)
npm install -D tailwindcss@^3.4.0 postcss autoprefixer
npx tailwindcss init -p

# 4. Verify build
npm run build
```

## Critical Pitfalls (learned the hard way)

### 1. `.htaccess` must live in `public/` folder

When deploying SPA to Apache, you need `.htaccess` for client-side routing. **DO NOT**
copy `.htaccess` to the build output manually — Vite's `emptyOutDir: true` wipes the
output folder on every build.

```
my-app/
├── public/
│   ├── .htaccess          ← put it here, Vite copies it as static asset
│   └── favicon.svg
└── vite.config.js
```

`.htaccess` template (SPA fallback + cache headers):

```apache
RewriteEngine On
RewriteBase /admin-v2/

RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^ index.html [L]

<FilesMatch "\.(js|css|png|jpg|svg|woff|woff2)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
</FilesMatch>

<Files "index.html">
    Header set Cache-Control "no-cache, no-store, must-revalidate"
</Files>
```

Adjust `RewriteBase` to match Vite's `base` setting.

### 2. `base` must match `basename` must match `RewriteBase`

Three places must agree when deploying to a sub-path:

```js
// vite.config.js
export default defineConfig({
  base: '/admin-v2/',  // ← must end with /
})
```

```jsx
// main.jsx
<BrowserRouter basename="/admin-v2">  // ← no trailing /
```

```apache
# .htaccess
RewriteBase /admin-v2/
```

If they mismatch, you get blank pages, asset 404s, or routes that flicker to the wrong
URL on hard reload.

### 3. Vite Tailwind v4 trap

`npm install -D tailwindcss` without a version pin installs v4 by default. v4's
`@tailwindcss/postcss` plugin breaks the `tailwind.config.js` you got from
`npx tailwindcss init`. **Always pin v3** until you've explicitly migrated to v4:

```bash
npm install -D tailwindcss@^3.4.0 postcss autoprefixer
```

### 4. Apache `mod_rewrite` and `mod_headers` must be enabled

Inside the container:

```bash
docker compose exec web bash -c "apache2ctl -M | grep -E 'rewrite|headers'"
```

Both must show `(shared)`. If missing, enable in Dockerfile:

```dockerfile
RUN a2enmod rewrite headers
```

And `AllowOverride All` in the VirtualHost so `.htaccess` actually takes effect.

### 5. Don't forget to remove default Vite cruft

After scaffolding, delete these (they are not used and confuse readers):

```bash
rm -f src/App.jsx src/App.css src/assets/react.svg public/vite.svg
```

Replace `src/main.jsx` with your router setup.

## Recommended Project Structure

```
src/
├── main.jsx              # entry: Router + QueryClient + auth init
├── index.css             # Tailwind + global styles + components layer
├── lib/
│   ├── api.js            # axios instance + JWT interceptor
│   └── utils.js          # cn(), formatCurrency, formatDate
├── stores/
│   └── authStore.js      # zustand + persist
├── components/
│   ├── Layout.jsx        # sidebar + header
│   └── ProtectedRoute.jsx
└── pages/
    ├── Login.jsx
    ├── Dashboard.jsx
    └── ...
```

## Vite Config (with backend proxy)

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/admin-v2/',
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',  // legacy backend
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../../base-pos/admin-v2',  // build into legacy app's static folder
    emptyOutDir: true,
  },
})
```

The `outDir` pattern lets you build directly into the legacy app's web root — both
versions are served by the same Apache instance, no extra deployment step.

## Auth Pattern (Zustand persist + Axios interceptor)

See `references/auth-pattern.md` for the full template — includes the JWT login flow,
auto-logout on 401, localStorage hydration, and protected route wrapper. Use this
verbatim and just swap the API endpoint URLs.

## Deployment Pattern: Side-by-Side with Legacy

Run the new SPA at a different path while keeping the old UI live:

| URL | Serves |
|---|---|
| `/admin/` | Legacy UI (untouched) |
| `/admin-v2/` | New React SPA |
| `/api/` | Shared backend |

Benefits:
- Zero risk to existing users — they keep using `/admin/` until ready
- A/B compare during development
- Rollback is just a router rule away
- Both UIs share session/auth/data

## Verification Checklist

After bootstrapping, verify:

```bash
# 1. Build succeeds without warnings
npm run build

# 2. Output goes to the right place
ls dist/  # or whatever your outDir is

# 3. .htaccess made it into the build
ls -la dist/.htaccess

# 4. Asset URLs include the base path
grep -o 'src="[^"]*"' dist/index.html  # should show /admin-v2/assets/...

# 5. Hard-refresh on a non-root route works
curl -I http://localhost:8080/admin-v2/dashboard  # should return 200, not 404
```

If step 5 fails with 404: `.htaccess` isn't being read — check `AllowOverride All`
and `mod_rewrite`.

## Common Workflow

1. **Scaffold + install deps** — one shot via the bootstrap sequence above
2. **Set up Tailwind config + design tokens** — pull from `popular-web-designs` skill
3. **Wire main.jsx** — Router + QueryClient + checkAuth on mount
4. **Build auth flow first** — Login + protected route + Layout
5. **One page at a time** — start with Dashboard, then key feature pages
6. **Build + deploy after each phase** — verify in real Apache, not just `npm run dev`

## Related

- `popular-web-designs` — design systems (Linear, Stripe, Vercel) for picking visual style
- `php-mvc-crud-feature` — when adding new endpoints to a PHP backend
- `claude-design` — for design taste / one-off HTML artifacts (not production SPAs)
