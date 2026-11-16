# SyRH

Système de gestion des ressources humaines de l'ARPTC.

- `backend/` — Django 6 + Django REST Framework, PostgreSQL
- `frontend/` — Vue 3 + TypeScript + Vite (Vue Router, Pinia)
- `docs/` — [cahier des charges](docs/cahier-des-charges-sirh-arptc.md) et
  [questions ouvertes](docs/questions-ouvertes.md)

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 22.18+ or 24.12+
- PostgreSQL 17

## First-time setup

Create the database and its role (pick your own password):

```bash
psql -d postgres -c "CREATE ROLE syrh LOGIN CREATEDB PASSWORD 'change-me'" -c "CREATE DATABASE syrh OWNER syrh"
```

Configure and migrate the backend:

```bash
cd backend
cp .env.example .env   # then set DJANGO_SECRET_KEY and the password in DATABASE_URL
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

Install the frontend:

```bash
cd frontend
npm install
```

## Running in development

Start PostgreSQL, then run each server in its own terminal:

```bash
cd backend && uv run python manage.py runserver
```

```bash
cd frontend && npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api`, `/admin` and `/static` to Django on
port 8000, so the browser only talks to one origin. Sign in at `/connexion` with the
account created by `createsuperuser`; further accounts are created in Django admin
(`/admin/`).

## Checks

| What | Command |
| --- | --- |
| Backend tests | `cd backend && uv run python manage.py test` |
| Backend lint and format | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| No missing migration | `cd backend && uv run python manage.py makemigrations --check` |
| Frontend tests | `cd frontend && npx vitest run` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend type-check and build | `cd frontend && npm run build` |

## Conventions

- `accounts.User` is the custom user model; always reference it through
  `settings.AUTH_USER_MODEL` or `get_user_model()`.
- Business apps live in `backend/apps/`.
- API endpoints require an authenticated session by default; opt out per view.
- An anonymous API call gets `401`, a forbidden one `403`. Frontend routes are protected
  by default too; a route opts out with `meta.public`.
- The frontend calls the API only through `request()` in `frontend/src/api/http.ts`,
  which handles CSRF and errors.
