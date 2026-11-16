# Tech stack

What SyRH is built with, and why. Change this file in the same commit as any change of stack.

SyRH is developed in-house by the ARPTC and hosted on ARPTC servers (`NF-04`). It is a web
application reached from a browser on every ARPTC site, with no installation on the workstation
(`NF-10`, `NF-11`).

## Overview

| Layer | Choice | Status |
| --- | --- | --- |
| Database | PostgreSQL 17 | In place |
| Backend language | Python 3.12+ | In place |
| Backend framework | Django 6.1 | In place |
| API | Django REST Framework 3.18 | In place |
| Database driver | psycopg 3 | In place |
| Configuration | django-environ, `.env` file | In place |
| Python tooling | uv (dependencies), Ruff (lint and format) | In place |
| Frontend framework | Vue 3 with `<script setup>` and TypeScript | In place |
| Build tool | Vite 8 | In place |
| Routing and state | Vue Router 5, Pinia 4 | In place |
| UI components | PrimeVue | To add in the first UI phase |
| Frontend tooling | ESLint, Oxlint, Prettier, vue-tsc | In place |
| Tests | Django test runner (backend), Vitest + Vue Test Utils (frontend) | In place |
| Authentication | Django session cookie + CSRF | To build |
| Version control | Git | In place |

## Repository layout

```
backend/            Django project
  config/           settings, root URLs, WSGI/ASGI
  apps/             one Django app per business domain
    accounts/       custom User model
    core/           shared base models, health check
frontend/           Vue application
  src/api/          typed functions that call the API
  src/views/        routed pages
  src/stores/       Pinia stores
docs/               stakeholder input (French)
specs/              this constitution
```

## Backend

- **Django + DRF.** Django gives us the ORM, migrations, admin, auth and permissions that an HR
  back office needs. DRF exposes the JSON API consumed by the Vue app.
- **One app per domain**, under `backend/apps/`: `accounts`, `core`, then `referentiels`,
  `agents`, `carriere`, `personnel`, `paie`, `social`, `formation` as the roadmap reaches them.
  An app owns its tables; other apps reference them by foreign key and never duplicate them.
- **Custom user model** `accounts.User`, referenced through `settings.AUTH_USER_MODEL` or
  `get_user_model()`.
- **Django admin** is a tool for administrators and for early data entry of reference tables. It
  is not the HR user interface.

## Database

PostgreSQL is the only supported database, in development, test and production. We use its
features freely rather than writing for the lowest common denominator.

- **Integrity lives in the database**: foreign keys with explicit `on_delete`, `NOT NULL`,
  `UniqueConstraint`, `CheckConstraint`, and exclusion constraints for non-overlapping date
  ranges where history must not overlap.
- **Deletion**: business rows are never hard-deleted. Use `on_delete=PROTECT` by default and a
  status or end date to retire a row.
- **History**: evolving facts are rows with `date_effet` (and an end date where relevant), not
  columns overwritten in place.
- **Money**: `DecimalField`, never floats. All amounts are in USD.
- **Primary keys**: `BigAutoField`. The agent's matricule is a unique business key, not the
  primary key.
- **Migrations** are committed, reviewed, and never edited once merged.
- **Naming**: tables, columns and domain terms in French, matching the cahier des charges
  (`agent`, `grade`, `date_engagement`). Code structure and comments in English.

## API

- JSON over HTTP under `/api/`.
- **Locked by default**: every endpoint requires an authenticated session. A view opts out
  explicitly (only `/api/health/` does today).
- **Authentication**: Django session cookie with CSRF protection. No tokens stored in the
  browser. The frontend and API are served from the same origin, so no CORS setup is needed.
- **Authorisation**: role-based, built on Django groups and permissions, enforced in the API and
  mirrored (never replaced) in the UI.
- Validation errors are returned per field so forms can display them next to the input.

## Frontend

- **Vue 3 Composition API** with `<script setup lang="ts">`. No Options API.
- **PrimeVue** for tables, forms, date pickers, dialogs and file upload, with the French locale.
  Do not mix in a second component library.
- **Pinia** for state shared across pages (current user, permissions, reference data). Local
  component state stays local.
- **API access** only through typed functions in `src/api/`; components do not call `fetch`
  directly.
- **Vite dev proxy** forwards `/api`, `/admin` and `/static` to Django, so development matches
  the single-origin production setup.
- Interface text in French.

## Files and documents

Scanned supporting documents (PDF and images) are stored on the server filesystem through
Django's storage API, outside the web root, and served only through authenticated views. The
database keeps the metadata and the link to the event the document justifies.

## Security

- Secrets come from the environment; `.env` is never committed.
- `DEBUG` is off unless explicitly enabled.
- HTTPS in production (`NF-03`).
- Passwords are validated by Django's password validators.
- Sensitive data (pay, medical, identity documents) is restricted by role at the API level.
- Every write is recorded in the audit log (`TRA-10`).

## Quality gates

A change is ready to merge when all of these pass:

| Check | Command |
| --- | --- |
| Backend tests | `cd backend && uv run python manage.py test` |
| Backend lint and format | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| No missing migration | `cd backend && uv run python manage.py makemigrations --check` |
| Frontend tests | `cd frontend && npx vitest run` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend type-check and build | `cd frontend && npm run build` |

Every model rule (constraint, computed value, state transition) has a backend test. Tests run
against PostgreSQL.

## Decisions not yet taken

Decide these when the roadmap reaches them, then record the choice above.

| Topic | Needed for |
| --- | --- |
| Audit log implementation (library or custom) | Phase 2 of the roadmap |
| PDF generation for payslips and certificates | Payslip and document phases |
| Excel export library | Bank transfer file, reports |
| Background jobs and scheduled alerts | Alerts phase |
| Production deployment (web server, process manager, backups) | First deployment |
| Time-clock integration (direct interface or file import) | Attendance phase; see `Q14` |
| Two-factor authentication for sensitive roles | `NF-01` |
