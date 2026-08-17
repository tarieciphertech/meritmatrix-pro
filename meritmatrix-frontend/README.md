# MeritMatrix Pro 2.0

A production-ready school administration and academic results management
platform — independent rebuild, first-principles architecture.

> **Status: Milestone 3 complete and hardened (Schools, Academic Structure, Multi-Tenant Isolation).**
> The foundation (Milestone 1), users, roles, permissions, JWT
> authentication, refresh-token rotation, RBAC, schools, academic years,
> terms, classes, subjects, and multi-tenant school isolation are
> implemented and tested. Students, parents, teachers, assessments,
> marks, and results are **not yet** implemented — see [Roadmap](#roadmap).

## Overview

MeritMatrix Pro centralizes school operations for students, parents,
teachers, and administrators: enrollment, subjects, assessments, marks,
configurable grading, result calculation, report cards, notifications,
and audit logging — with strict role-based access control and
server-side authorization on every protected resource.

## Architecture

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL, Alembic,
  Pydantic v2, Uvicorn (dev) / Gunicorn (prod)
- **Frontend**: React, Vite, TypeScript, Tailwind CSS *(scaffolded in Step 6)*
- **Infra**: Docker Compose for local dev; deployable to Render, AWS, or
  Oracle Cloud without hard-coded deployment specifics

```
meritmatrix-pro/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app factory / entrypoint
│   │   ├── config.py          # Environment-driven settings
│   │   ├── database.py        # SQLAlchemy engine/session/Base
│   │   ├── logging_config.py  # Centralized, redacting log setup
│   │   ├── models/            # ORM models: User, Role, Permission, RefreshToken
│   │   ├── schemas/           # Pydantic schemas (auth, user, role, permission)
│   │   ├── routers/           # API route handlers (thin): health, auth, users
│   │   ├── services/          # Business logic: auth_service, user_service,
│   │   │                      #   security (Argon2id), jwt_service
│   │   ├── repositories/      # Data access layer (User/Role/Permission/RefreshToken)
│   │   ├── auth/              # RBAC dependencies: get_current_user, require_permission
│   │   ├── middleware/        # Cross-cutting request middleware
│   │   ├── seed.py            # Dev-only seed: default roles/permissions + demo users
│   │   └── utils/errors.py    # Exceptions + centralized error handlers
│   ├── alembic/                # Migrations
│   ├── tests/                  # pytest suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # React app (scaffolded in Step 6)
├── docs/                       # Architecture docs
├── scripts/
├── docker-compose.yml
├── .env.example
└── .gitignore
```

Business logic lives in `services/`, not in route handlers or React
components. Routers stay thin; the grading/results engine is a backend
service so calculation logic is never duplicated on the frontend.

## Requirements

- Docker & Docker Compose (recommended path)
- Or, for running the backend directly: Python 3.12+, a local PostgreSQL 16 instance

## Installation & environment setup

```bash
git clone <repo-url>
cd meritmatrix-pro
cp .env.example .env
# Edit .env: set SECRET_KEY / JWT_SECRET (e.g. `openssl rand -hex 32`) and DB credentials
```

## Running with Docker Compose (recommended)

```bash
docker compose up --build
```

This starts PostgreSQL and the backend API. Once healthy:

```bash
curl http://localhost:8000/health
# {"status":"ok","app":"MeritMatrix Pro 2.0","environment":"development","database":"connected"}
```

Interactive API docs: http://localhost:8000/api/v1/docs

## Running the backend without Docker

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' ../.env | xargs)   # or otherwise load your .env
uvicorn app.main:app --reload
```

## Database & migrations

```bash
cd backend
alembic upgrade head              # apply migrations
alembic revision --autogenerate -m "describe change"   # create a new migration
```

**Note on the custom `GUID` type:** models use a portable UUID column
type (`app/models/base.py::GUID`) so the same models work against both
PostgreSQL and the SQLite test fallback. Alembic's autogenerate renders
this type by its fully-qualified name but does not add the Python
import for it — after generating a new migration that touches a
UUID-keyed table, add `import app.models.base` near the top of the
generated file if it isn't already there (see the existing migration
in `alembic/versions/` for reference).

## Seed data

```bash
cd backend
python -m app.seed
```

Seeds the default permission set, the five default roles
(`SUPER_ADMIN`, `SCHOOL_ADMIN`, `TEACHER`, `PARENT`, `STUDENT`), their
role→permission mappings, and one demo user per role. Passwords come
from `SEED_<ROLE>_PASSWORD` environment variables if set, otherwise a
random password is generated per run and printed once to stdout — never
persisted in plaintext or logged. The script refuses to run at all when
`ENVIRONMENT=production`.

## Testing

```bash
cd backend
pytest -v
```

The foundation test suite runs against a disposable local SQLite
database (see `tests/conftest.py`) purely so tests are runnable in any
environment without a live PostgreSQL instance; this fallback is
refused outright whenever `ENVIRONMENT=production` (enforced in
`app/database.py`).

## Production deployment

- Set `ENVIRONMENT=production`, a strong `SECRET_KEY`/`JWT_SECRET`, and
  a PostgreSQL `DATABASE_URL` — SQLite is rejected at startup in this mode.
- Build the backend production image: `docker build --target production -t meritmatrix-backend ./backend`
- Run behind Gunicorn + Uvicorn workers (already configured as the
  production `CMD` in `backend/Dockerfile`).
- Terminate TLS and set CORS_ORIGINS/FRONTEND_URL to your real domains.
- Suitable for Render, AWS (e.g. ECS/EC2 + RDS), or Oracle Cloud — no
  deployment-specific values are hard-coded in the application.

## API documentation

FastAPI auto-generates OpenAPI/Swagger docs at `/api/v1/docs` (and
ReDoc at `/api/v1/redoc`) directly from the route/schema definitions,
so they stay in sync with the implementation as endpoints are added.
Protected endpoints use Bearer authentication
(`Authorization: Bearer <access_token>`), documented automatically via
FastAPI's `OAuth2PasswordBearer` security scheme.

### Authentication endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Exchange email/password for an access + refresh token pair |
| POST | `/api/v1/auth/refresh` | Rotate a refresh token for a new access + refresh token pair |
| POST | `/api/v1/auth/logout` | Revoke a refresh token |
| GET | `/api/v1/auth/me` | Current authenticated user |

### User endpoints (RBAC-protected)

| Method | Path | Required permission |
|---|---|---|
| GET | `/api/v1/users/me` | Authenticated only |
| GET | `/api/v1/users` | `users.read` |
| POST | `/api/v1/users` | `users.create` |
| GET | `/api/v1/users/{user_id}` | `users.read` |
| PATCH | `/api/v1/users/{user_id}` | `users.update` |

`system.admin` (held by `SUPER_ADMIN`) satisfies any permission check.

## Security considerations

- Passwords are hashed with **Argon2id** (via passlib) and never stored
  or returned in plaintext; `password_hash` never appears in any API
  response schema.
- Refresh tokens are stored only as a SHA-256 hash (`token_hash`) —
  the raw token is returned to the client once at issuance and never
  persisted.
- Refresh tokens **rotate** on every use; reuse of an already-rotated
  (revoked) token is treated as possible theft and revokes every token
  in that rotation family, not just the one presented.
- Login failures return a single generic `INVALID_CREDENTIALS` error
  and body regardless of whether the email is unknown, the password is
  wrong, or the account is inactive — this is verified by an automated
  test that the two failure modes produce byte-identical responses.
- Every protected endpoint enforces authorization server-side via the
  `require_permission(...)` / `get_current_active_user` dependencies —
  the frontend is never the source of truth for permissions.
- No secrets are committed to source control; all sensitive
  configuration is environment-variable driven (`.env`, gitignored).
- Errors are normalized to a consistent `{"error": {"code", "message"}}`
  shape; raw exceptions/tracebacks are never returned to clients and
  are logged server-side with a request ID for correlation.
- A logging filter redacts log lines that look like they contain
  passwords, tokens, or secrets; an automated test asserts a real login
  password never appears in captured logs.
- SQLite is hard-disallowed once `ENVIRONMENT=production`.
- User deactivation is archival (`is_active=False`), never a hard
  delete — academic/audit history stays intact.

## Roadmap

| Step | Scope | Status |
|------|-------|--------|
| 1 ✅ | Foundation: app bootstrap, DB connectivity, health check, logging, error handling, tests | Complete |
| 2 ✅ | Users, roles, permissions, authentication, RBAC, refresh-token rotation | Complete |
| 3 ✅ | Schools, academic years, terms, classes, subjects, multi-tenant isolation | Complete & Hardened |
| 4 | Students, parents, guardians, staff, enrollment relationships | Not started |
| 5 | Assessments, marks, grading engine, result calculation | Not started |
| 6 | React frontend: auth, layout, admin dashboard, core CRUD screens | Not started |
| 7 | Parent portal, teacher portal, report cards, notifications | Not started |
| 8 | Production hardening: security/authz/DB/performance/accessibility review | Not started |

See `docs/database-architecture.md` for schema conventions and the
planned entity groups.
