# Tech stack

What SyRH is built with, and why. Change this file in the same commit as any change of stack.

SyRH is developed in-house by the ARPTC and hosted on ARPTC servers (`NF-04`). It is a web
application reached from a browser on every ARPTC site, with no installation on the workstation
(`NF-10`, `NF-11`).

It is a **single-page application** built with Vue.js, so that it feels native to the user:
the page loads once, navigation between screens is instant, and only data travels to and from
the server.

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
| Frontend architecture | Single-page application (SPA) | In place |
| Frontend framework | Vue 3 with `<script setup>` and TypeScript | In place |
| Build tool | Vite 8 | In place |
| Routing and state | Vue Router 5, Pinia 4 | In place |
| UI components | PrimeVue 4 (MIT), PrimeIcons, French locale via primelocale | In place |
| Design system | Custom tokens and PrimeVue preset, light and dark themes; see [`design.md`](design.md) | In place |
| Font | Plus Jakarta Sans, self-hosted | In place |
| Charts | Apache ECharts with `vue-echarts` | To add in the dashboard phase |
| Frontend tooling | ESLint, Oxlint, Prettier, vue-tsc | In place |
| Tests | Django test runner (backend), Vitest + Vue Test Utils (frontend) | In place |
| Authentication | Django session cookie + CSRF | In place |
| Version control | Git | In place |

## Repository layout

```
backend/            Django project
  config/           settings, root URLs, WSGI/ASGI
  apps/             one Django app per business domain
    accounts/       custom User model
    core/           shared base models, health check
frontend/           Vue application, organised by feature (see "Frontend folder layout")
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
  explicitly (`/api/health/`, `/api/auth/csrf/` and `/api/auth/login/` do today).
- **Authentication**: Django session cookie with CSRF protection. No tokens stored in the
  browser. The frontend and API are served from the same origin, so no CORS setup is needed.
  The endpoints live under `/api/auth/` (`csrf`, `login`, `logout`, `me`, `password`).
- **401 or 403**: an anonymous request gets `401` ("sign in again"), an authenticated request
  without the right gets `403` ("not allowed"). This comes from
  `apps.accounts.authentication.SessionAuthentication`; do not swap it for DRF's stock class.
- **Messages are in French**, whatever language the browser asks for: there is no
  `LocaleMiddleware`.
- **Authorisation**: role-based, built on Django groups and permissions, enforced in the API and
  mirrored (never replaced) in the UI.
- Validation errors are returned per field so forms can display them next to the input.

## Frontend

- **Single-page application.** Django never renders HR screens; it serves JSON, and Vue renders
  everything in the browser. This is what makes the app feel native:
  - **Client-side routing** with Vue Router in history mode: moving between screens never
    reloads the page, and every screen has its own URL that can be bookmarked or shared.
  - **No full-page form posts**: forms submit through the API and the screen updates in place,
    with field-level errors.
  - **Immediate feedback**: every action shows a loading state, then a success or error
    message; nothing leaves the user waiting on a blank page.
  - **Lazy-loaded routes**: each module's screens are loaded on first visit, so the first load
    stays fast as the application grows.
  - **State survives navigation**: filters, search terms and the current user are kept in
    Pinia while the user moves around.
  - In production the server returns `index.html` for any non-API path, so a refresh or a
    deep link lands on the right screen.
- **Feature-based folders**: code is grouped by business feature, not by technical type. See
  [Frontend folder layout](#frontend-folder-layout) below.
- **Vue 3 Composition API** with `<script setup lang="ts">`. No Options API.
- **PrimeVue 4** for tables, forms, date pickers, dialogs and file upload, with the French
  locale. Do not mix in a second component library.
  - **Stay on version 4.** PrimeVue 5 moved to the commercial PrimeUI licence, whose free tier
    is limited to organisations with fewer than 10 employees; the ARPTC does not qualify.
    Version 4 is MIT-licensed. The version is pinned exactly in `package.json`; do not upgrade
    to 5 without buying licences.
- **Design system**: colours, type, shape and components are defined in
  [`design.md`](design.md). Components read CSS tokens (`--sy-*`) and never hard-code a colour.
  Light and dark themes are both supported; every screen is checked in both.
- **Charts: Apache ECharts** (Apache-2.0) through the `vue-echarts` wrapper (MIT). Chosen
  because rounded bars, rounded donut segments and hatch patterns ("decal") are built in, which
  matches the design system, and because it covers every chart the dashboard and reports need.
  - Import only the chart types and components a screen uses, never the whole library, and keep
    charts in lazy-loaded routes.
  - ECharts draws on a canvas and cannot read CSS variables. Chart colours come from one shared
    helper that reads the `--sy-*` tokens and redraws when the theme changes; no chart
    hard-codes a colour.
  - Wrap charts in components under `src/shared/ui/` so screens never configure ECharts
    directly. The small CSS and SVG charts already there stay until a screen needs axes,
    tooltips or time series.
- **Pinia** for state shared across pages (current user, permissions, reference data). Local
  component state stays local.
- **API access** only through the typed functions in each feature's `api/` folder; components
  do not call `fetch` directly. Those functions all go through `request()` in
  `src/shared/utils/http.ts`, which sends the CSRF token, raises a typed `ApiError` with
  per-field messages, and reports a lost session.
- **Vite dev proxy** forwards `/api`, `/admin` and `/static` to Django, so development matches
  the single-origin production setup. It keeps the browser's `Host` header (object form in
  `vite.config.ts`); Django's CSRF origin check depends on it.
- **Routes are protected by default.** The router guard sends anonymous visitors to
  `/connexion`; a route opts out with `meta.public`. This is a convenience, not a security
  boundary: the API enforces access.
- Interface text in French.

### Frontend folder layout

Code is grouped by **feature**: everything one business area needs (screens, components, state,
API calls) lives in one folder. Code used by several features lives in `shared/`. A feature
folder can be read, changed or removed without searching the whole tree.

```
frontend/src/
├── features/
│   ├── auth/                    # sign-in, sign-out, current user, own password
│   │   ├── api/                 # auth.ts: login(), logout(), fetchMe(), changePassword()
│   │   ├── components/          # UserMenu.vue
│   │   ├── composables/         # useX.ts: reusable logic with no state shared across pages
│   │   ├── stores/              # auth.ts: Pinia store for the current user
│   │   ├── views/               # LoginView.vue, PasswordView.vue
│   │   └── routes.ts            # this feature's routes, lazy-loaded
│   ├── dashboard/
│   ├── systeme/                 # system status (health check)
│   ├── design/                  # design guide page
│   ├── agents/                  # then one folder per module as the roadmap reaches it:
│   └── ...                      # referentiels, carriere, personnel, paie, social, formation
├── shared/
│   ├── ui/                      # generic components: StatCard, DonutChart, ThemeToggle, ...
│   ├── layouts/                 # AppShell.vue: side menu and top bar
│   ├── theme/                   # tokens.css, main.css, preset.ts, store.ts (light/dark)
│   └── utils/                   # http.ts (request(), ApiError), formatters
├── router/                      # index.ts assembles the features' routes; guards.ts;
│                                # PlaceholderView.vue for modules not built yet
├── App.vue                      # root component
└── main.ts                      # application entry point
```

Rules:

- **Feature names follow the backend.** A feature folder matches the Django app or module it
  talks to (`agents`, `carriere`, `paie`, ...), so the same word finds the code on both sides.
  `auth` matches `apps.accounts`.
- **A feature only has the subfolders it needs.** The full set is `api/`, `components/`,
  `composables/`, `stores/` and `views/`, plus a `routes.ts`.
- **`views/` holds routed pages; `components/` holds the pieces they are built from.** A
  component used by one feature stays in that feature, even if it looks generic. It moves to
  `shared/ui/` when a second feature needs it.
- **Imports go one way**: `features/` may import from `shared/`. `shared/` never imports from
  `features/`. The `auth` store is the one exception, read by `shared/layouts/` and
  `router/` because every screen depends on the current user.
- **Features import one another sparingly**, and only through stores, composables or `api/`
  functions, never another feature's components or views. If two features need the same
  component, it belongs in `shared/ui/`.
- **Routes are declared by their feature.** Each `routes.ts` exports its routes with lazy
  `() => import(...)` components; `router/index.ts` only assembles them and installs the guards.
- **Tests sit next to the code** in a `__tests__/` folder (`features/auth/stores/__tests__/`).
- **Import with the `@/` alias** (`@/shared/ui/StatCard.vue`, `@/features/auth/stores/auth`),
  never with long relative paths across folders.

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
