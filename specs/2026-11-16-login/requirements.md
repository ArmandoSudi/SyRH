# Login — requirements

Roadmap phase **0.2 Login**: session login, logout and "current user" endpoints with CSRF; login
page; route guard that redirects anonymous users.

Branch: `feature/login`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- The API is already locked by default: DRF uses `SessionAuthentication` and `IsAuthenticated`
  ([`backend/config/settings.py`](../../backend/config/settings.py)). Only `/api/health/` opts out.
  Today nobody can obtain a session outside Django admin, so the SPA cannot call anything else.
- `accounts.User` exists as an empty `AbstractUser` subclass. This phase adds no field to it.
- The app shell (phase 0.3) is in place, with a static "RH" avatar in the top bar and no notion of
  a signed-in user ([`frontend/src/layouts/AppShell.vue`](../../frontend/src/layouts/AppShell.vue)).
- The frontend has one API function, `fetchHealth`, calling `fetch` directly. There is no shared
  HTTP client, no CSRF handling and no auth store yet.
- Frontend and API share one origin (Vite proxy in development), so cookies work without CORS.
- Relevant non-functional requirements: `NF-01` (individual login by identifier and strong
  password), `NF-02` (rights per profile), `NF-03` (HTTPS).
- Phases 0.4 Roles, 0.5 Base models (author) and 0.6 Audit log all depend on knowing the current
  user, which this phase delivers.

## Scope

### In scope

1. **Sign in** with username and password, creating a Django session.
2. **Sign out**, destroying the session.
3. **Current user** endpoint the SPA calls on start-up to learn who is signed in.
4. **CSRF** protection on every unsafe request, including login itself.
5. **Login page** at `/connexion`, in French, in light and dark themes.
6. **Route guard**: an anonymous visitor to any application screen is sent to `/connexion`.
7. **Redirect back**: after signing in, the user lands on the screen they first asked for. A
   session that expires mid-use sends the user to `/connexion` and back the same way.
8. **User menu** in the top bar: the signed-in user's initials and name, with "Changer le mot de
   passe" and "Se déconnecter".
9. **Change own password**: old password, new password, confirmation, checked by Django's
   password validators.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Login throttling, account lockout, two-factor authentication, inactivity timeout | Phase 9.4 Hardening |
| Roles, groups, permissions, menu filtered by role | Phase 0.4 Roles |
| Forgotten-password flow by email | Not planned; an administrator resets the password |
| Account creation and management screens | Django admin, for now |
| Audit of logins and password changes | Phase 0.6 Audit log |
| Link between a user and an agent record | Milestone 2 |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-16. The others are
engineering choices that follow from [`tech-stack.md`](../tech-stack.md) and
[`missions.md`](../missions.md).

### Product

| # | Decision | Reason |
| --- | --- | --- |
| D1 | Users sign in with their **username**, labelled "Identifiant". **(asked)** | Matches `NF-01`; no change to the User model. |
| D2 | Redirect back after login, user menu in the top bar and change-own-password are in this phase. Login throttling is not. **(asked)** | Throttling belongs with lockout in 9.4. |
| D3 | Accounts are created by an administrator in Django admin (or `createsuperuser`). There is no self-registration and no "forgot password" link. | Internal system; system administrators own accounts (`missions.md`). |
| D4 | A failed login returns one generic message, "Identifiant ou mot de passe incorrect.", whether the username is unknown, the password wrong or the account inactive. | Does not reveal which accounts exist. |
| D5 | After a password change the user stays signed in on the current browser; their other sessions are ended. | Django's `update_session_auth_hash` behaviour; the expected outcome of changing a password. |
| D6 | Session lifetime stays at Django's default. No "remember me" checkbox. | Inactivity timeout is decided in 9.4. |
| D7 | Django admin keeps its own login page at `/admin/`. It shares the same session cookie. | Admin is an administrator tool, not the HR interface. |

### API

All endpoints live in `apps.accounts`, under `/api/auth/`.

| Method and path | Access | Behaviour |
| --- | --- | --- |
| `GET /api/auth/csrf/` | Public | Sets the `csrftoken` cookie. Returns `204`. |
| `POST /api/auth/login/` | Public, CSRF enforced | Body `{username, password}`. `200` with the user on success; `400` with a non-field error on failure (D4). |
| `POST /api/auth/logout/` | Authenticated | Ends the session. `204`. |
| `GET /api/auth/me/` | Authenticated | `200` with the user. |
| `POST /api/auth/password/` | Authenticated | Body `{old_password, new_password}`. `204` on success; `400` with per-field errors otherwise. |

User payload: `id`, `username`, `first_name`, `last_name`, `email`. Roles and permissions are
added to it in phase 0.4.

| # | Decision | Reason |
| --- | --- | --- |
| D8 | An anonymous request to a protected endpoint returns **`401`**; an authenticated request without the right returns `403`. This needs a small `SessionAuthentication` subclass that sets `authenticate_header`, because stock DRF answers `403` in both cases. | The frontend must tell "sign in again" from "not allowed", which matters as soon as roles land in 0.4. |
| D9 | The login view enforces CSRF explicitly. | DRF's `SessionAuthentication` only checks CSRF for already-authenticated requests, so login would otherwise be unprotected (login CSRF). |
| D10 | Login rotates the session key (Django's `login()`); logout flushes the session. | Prevents session fixation. |
| D11 | Cookies: session cookie `HttpOnly`, `SameSite=Lax`; CSRF cookie readable by JavaScript so the SPA can send it as `X-CSRFToken`; both `Secure` when `DEBUG` is off. | `tech-stack.md`: session cookie + CSRF, no tokens stored in the browser, HTTPS in production. |
| D12 | Validation errors are returned per field. | `tech-stack.md`, API section. |

### Frontend

| # | Decision | Reason |
| --- | --- | --- |
| D13 | One shared HTTP helper in `src/api/` sends the CSRF header on unsafe methods, parses JSON, and throws a typed error carrying the status and field errors. `fetchHealth` moves onto it. | `tech-stack.md`: API access only through typed functions in `src/api/`. Every later phase reuses it. |
| D14 | A Pinia `auth` store holds the current user. It is loaded once, before the first navigation resolves. | `tech-stack.md`: the current user lives in Pinia. Avoids a flash of the shell before the redirect. |
| D15 | Routes are protected by default; a route opts out with `meta.public`. Only `/connexion` is public. | Mirrors "locked by default" on the API. |
| D16 | The login page is outside `AppShell` (no side menu, no top bar) and is lazy-loaded. A signed-in user who opens `/connexion` is sent to the dashboard. | |
| D17 | The return path travels as `?redirect=/chemin`. Only same-origin paths starting with a single `/` are honoured; anything else falls back to `/`. | Prevents open redirects. |
| D18 | Any `401` from the API clears the store and sends the user to `/connexion` with the current path as `redirect`. | Handles an expired session without a blank or broken screen. |
| D19 | The password screen is at `/compte/mot-de-passe`, inside the shell, reached from the user menu. | |
| D20 | Signing out clears the store and goes to `/connexion`. | |
| D21 | All screens use PrimeVue components and `--sy-*` tokens only, with French text, and show a loading state on submit. | `design.md`, `tech-stack.md`. |

### Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D22 | The Vite dev proxy keeps the browser's `Host` header (object form, not the string shorthand). | The shorthand rewrites `Host`, so Django's CSRF origin check rejected every login from the browser in development. Keeping it matches the single-origin production setup. |
| D23 | `LocaleMiddleware` is removed: the API always answers in French (`LANGUAGE_CODE = "fr"`). | With it, password-validation errors came back in the browser's language. `missions.md`: French first. Django admin is French for everyone as a result. |
| D24 | The HTTP helper fetches the CSRF cookie by itself before the first unsafe request; there is no separate `fetchCsrf` call for screens to remember. | One place to get it right. |

## Open points

None blocking. To revisit in phase 9.4: session lifetime and inactivity timeout (D6), throttling
and lockout (D2).
