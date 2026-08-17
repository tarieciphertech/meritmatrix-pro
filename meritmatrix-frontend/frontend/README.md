# MeritMatrix Pro — Frontend

React + Vite + TypeScript + Tailwind CSS v4 single-page application for the
MeritMatrix Pro school administration platform.

## Stack

- React 19, React Router 7 (BrowserRouter, protected routes)
- Vite 6 with `@vitejs/plugin-react` and `@tailwindcss/vite`
- TypeScript 5.8 (strict), types mirror `backend/app/schemas/*.py`
- Tailwind CSS v4 (`@import "tailwindcss"` — no config file needed)

## Getting started

```bash
npm install
npm run dev      # dev server on http://localhost:5173 (proxies /api → :8000)
npm run build    # type-check (tsc -b) + production bundle in dist/
npm run preview  # serve the production bundle
```

The dev server proxies `/api` to `http://localhost:8000` (see
`vite.config.ts`), so run the FastAPI backend on port 8000 for a full
end-to-end session. To point at a different API origin, set `VITE_API_URL`.

## Architecture

```
src/
  main.tsx               # entry: BrowserRouter + App
  App.tsx                # providers + routes + RequireAuth guard
  types/index.ts         # TS types mirroring backend Pydantic schemas
  lib/api.ts             # fetch client: Bearer tokens, 401→refresh→retry, error normalization
  lib/auth.tsx           # AuthProvider: login/logout, GET /auth/me bootstrap, hasRole
  lib/school-context.tsx # SchoolProvider: accessible schools + selected school (persisted)
  components/ui.tsx      # Button, Input, Select, Field, Card, Modal, Badge, Table, etc.
  layouts/AppLayout.tsx  # sidebar nav, header with school selector + user menu
  pages/                 # Login, Dashboard, Schools, Students, Guardians, Staff, Enrollments
```

Key behaviors:

- Tokens (`access_token`, `refresh_token`) are stored in `localStorage`
  under `meritmatrix.tokens`. The API client retries once after a
  refresh-token rotation on 401.
- All school-scoped screens (Students, Guardians, Staff, Enrollments,
  Dashboard counts) require a selected school in the header selector because
  the backend mandates a `school_id` query parameter on those list endpoints.
- Route guard `RequireAuth` redirects unauthenticated users to `/login`,
  preserving the intended destination.
- Schools page create/edit/deactivate actions are only shown to users with
  the `SUPER_ADMIN` role (backend additionally enforces permissions).

## Backend API dependencies

Endpoints consumed by this frontend (all verified against
`backend/app/routers/*`):

| Area         | Endpoints                                                                                             |
| ------------ | ----------------------------------------------------------------------------------------------------- |
| Auth         | `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me` |
| Schools      | `GET/POST /api/v1/schools`, `PATCH/DELETE /api/v1/schools/{id}` (DELETE = deactivate)                 |
| Students     | `GET/POST /api/v1/students?school_id=…`, `PATCH/DELETE /api/v1/students/{id}` (DELETE = archive)      |
| Guardians    | `GET/POST /api/v1/guardians?school_id=…`, `PATCH/DELETE /api/v1/guardians/{id}`                       |
| Staff        | `GET/POST /api/v1/staff?school_id=…`, `PATCH/DELETE /api/v1/staff/{id}`                               |
| Enrollments  | `GET/POST /api/v1/enrollments?school_id=…`, `PATCH /api/v1/enrollments/{id}`, `POST /api/v1/enrollments/{id}/complete\|withdraw\|cancel` |
| Lookups      | `GET /api/v1/academic-years?school_id=…`, `GET /api/v1/classes?school_id=…` (enrollment dropdowns)    |

Contract notes / known constraints (by design in the backend, not bugs):

1. **List endpoints return bare JSON arrays** (no `{items,total}` envelope);
   pages fetch with `limit=200` (backend max), so counts/listings beyond 200
   records are capped. A pagination envelope would be needed for larger
   datasets.
2. **Enrollment PATCH is limited** to `withdrawal_date`, `status`, `notes`.
   Student, academic year, class, enrollment date, and enrollment number are
   immutable; the UI disables those fields in edit mode.
3. **Enrollment creation requires pre-existing academic years and classes.**
   There are no management screens for academic years, classes, subjects,
   terms, users, or student–guardian links yet — those backend routers exist
   (`/api/v1/academic-years`, `/api/v1/classes`, `/api/v1/subjects`,
   `/api/v1/terms`, `/api/v1/users`, `/api/v1/student-guardians`) and are the
   next frontend work items.
4. **Role-based UI gating** uses role names (`SUPER_ADMIN`) from
   `GET /auth/me`; the backend remains the source of truth for permission
   enforcement via `require_permission(...)`.
5. **No backend blocker** was encountered for the implemented MVP screens:
   every endpoint the pages call exists in the backend with matching method,
   path, query parameters, and response shape.

## Runtime prerequisites for a working session

1. Backend running on `http://localhost:8000` (PostgreSQL + migrations + seed
   data per `backend/` README / `scripts/dev_setup.sh`).
2. A seeded user with at least one school membership; school-scoped screens
   show empty states until a school is selected.