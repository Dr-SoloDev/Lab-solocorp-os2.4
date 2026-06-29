# Auth Pattern: Zustand Persist + Axios Interceptor

Battle-tested auth flow for a React SPA against a JWT backend. Drop-in template —
swap the endpoint URLs and you're done.

## Files Involved

```
src/
├── lib/api.js            # axios instance + interceptors
├── stores/authStore.js   # zustand + persist + localStorage
├── components/ProtectedRoute.jsx
├── pages/Login.jsx
└── main.jsx              # checkAuth() on mount
```

## 1. Axios Client (`src/lib/api.js`)

```js
import axios from 'axios'

const API_BASE = '/api/index.php'  // adjust per backend

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('app_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('app_token')
      localStorage.removeItem('app_user')
      if (!window.location.pathname.endsWith('/login')) {
        window.location.href = '/admin-v2/login'  // adjust base path
      }
    }
    return Promise.reject(err)
  }
)

export const apiCall = {
  get: (url, params) => api.get(url, { params }).then((r) => r.data),
  post: (url, data) => api.post(url, data).then((r) => r.data),
  put: (url, data) => api.put(url, data).then((r) => r.data),
  delete: (url) => api.delete(url).then((r) => r.data),
}
```

**Why two storage layers (Zustand + localStorage):** Zustand `persist` middleware
already syncs to localStorage, but we ALSO write the token under a separate key
because the Axios interceptor runs before React mounts. The interceptor needs raw
localStorage access; the store needs reactive subscriptions.

## 2. Auth Store (`src/stores/authStore.js`)

```js
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiCall } from '@/lib/api'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (username, password) => {
        const res = await apiCall.post('/auth/login', { username, password })
        if (res.status === 'success') {
          const { token, user } = res.data
          localStorage.setItem('app_token', token)
          localStorage.setItem('app_user', JSON.stringify(user))
          set({ user, token, isAuthenticated: true })
          return { success: true }
        }
        return { success: false, message: res.message }
      },

      logout: () => {
        localStorage.removeItem('app_token')
        localStorage.removeItem('app_user')
        set({ user: null, token: null, isAuthenticated: false })
      },

      checkAuth: () => {
        const token = localStorage.getItem('app_token')
        const userStr = localStorage.getItem('app_user')
        if (token && userStr) {
          try {
            set({
              user: JSON.parse(userStr),
              token,
              isAuthenticated: true,
            })
          } catch {
            get().logout()
          }
        }
      },
    }),
    {
      name: 'app-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
```

## 3. Protected Route (`src/components/ProtectedRoute.jsx`)

```jsx
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export default function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}
```

## 4. Mount Hydration (`src/main.jsx`)

```jsx
function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth)
  useEffect(() => { checkAuth() }, [checkAuth])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/admin-v2">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/dashboard" element={<Dashboard />} />
            {/* ... */}
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

`checkAuth()` on mount rehydrates the store from localStorage so a page refresh
doesn't kick the user back to login.

## 5. Login Form Pattern

```jsx
const { register, handleSubmit, formState: { errors } } = useForm()
const login = useAuthStore((s) => s.login)
const navigate = useNavigate()
const [error, setError] = useState('')
const [loading, setLoading] = useState(false)

const onSubmit = async (data) => {
  setError('')
  setLoading(true)
  try {
    const result = await login(data.username, data.password)
    if (result.success) navigate('/dashboard')
    else setError(result.message || 'Login failed')
  } catch (err) {
    setError(err.response?.data?.message || 'Network error')
  } finally {
    setLoading(false)
  }
}
```

## Edge Cases Covered

| Scenario | Behavior |
|---|---|
| User refreshes page | `checkAuth()` reads localStorage, restores session |
| Token expires (401) | Interceptor clears storage, redirects to /login |
| User clicks logout | Store + localStorage cleared, redirected |
| User opens 2nd tab | Both tabs see the same auth state (localStorage shared) |
| User clears site data | App acts as if never logged in — no error spam |
| Token tampered | Backend returns 401, interceptor handles it |

## Don't Do This

- ❌ Store JWT in `httpOnly` cookies AND localStorage — pick one. localStorage is
  fine for SPAs sharing origin with backend; cookies are necessary for cross-origin.
- ❌ Use `sessionStorage` instead of `localStorage` — breaks "remember me" UX
  and most users expect persistence.
- ❌ Rely on Zustand-only persist without the parallel `localStorage.setItem` — the
  Axios interceptor runs outside React and can't read Zustand directly.
- ❌ Auto-redirect to /login from inside a React effect — do it in the Axios
  interceptor so the redirect fires immediately on 401, not after the next render.

## Backend Response Shape Assumed

```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "token": "eyJ0...",
    "user": { "id": 1, "username": "admin", "full_name": "...", "role": "admin" }
  }
}
```

If your backend uses a different envelope (e.g. raw `{ token, user }` at top level
or `accessToken` field name), adjust `login()` in the store accordingly.
