# Login — validation

How to know phase 0.2 is done and `feature/login` can be merged. All three parts must pass:
quality gates, automated tests for every acceptance criterion, and the manual walkthrough.

Decision numbers refer to [`requirements.md`](requirements.md).

## 1. Quality gates

All six, from [`tech-stack.md`](../tech-stack.md), green on the branch tip:

| Check | Command |
| --- | --- |
| Backend tests | `cd backend && uv run python manage.py test` |
| Backend lint and format | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| No missing migration | `cd backend && uv run python manage.py makemigrations --check` |
| Frontend tests | `cd frontend && npx vitest run` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend type-check and build | `cd frontend && npm run build` |

This phase is expected to add **no migration**.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test.

### Backend

| # | Criterion | Decision |
| --- | --- | --- |
| B1 | Valid credentials create a session; `GET /api/auth/me/` then returns the user. | |
| B2 | Wrong password, unknown username and inactive account return the same `400` body. | D4 |
| B3 | `POST /api/auth/login/` without a valid CSRF token is rejected. | D9 |
| B4 | The session key changes on login. | D10 |
| B5 | Logout ends the session; `me` then returns `401`. | D10 |
| B6 | Anonymous calls to `me`, `logout` and `password` return `401`, not `403`. | D8 |
| B7 | `/api/health/` and `/api/auth/csrf/` answer without a session; `csrf` sets the cookie. | |
| B8 | The user payload has exactly `id`, `username`, `first_name`, `last_name`, `email`, and never the password hash. | |
| B9 | Password change succeeds with the right old password; the new password works and the old one does not. | |
| B10 | After a password change the current session survives and another session of the same user is ended. | D5 |
| B11 | A wrong old password gives an error on `old_password`; a weak new password gives an error on `new_password`. | D12 |
| B12 | Error messages are in French whatever language the browser asks for. | D23 |

### Frontend

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The HTTP helper sends `X-CSRFToken` on unsafe methods and not on `GET`. | D13 |
| F2 | API errors surface as a typed error with status and field errors. | D13 |
| F3 | The auth store loads the user once; a `401` on start-up means anonymous, not an error. | D14 |
| F4 | An anonymous visitor to a protected route is sent to `/connexion?redirect=<path>`. | D15 |
| F5 | After login the user lands on the `redirect` path, or the dashboard when there is none. | |
| F6 | An external or malformed `redirect` (`//evil.example`, `https://...`) falls back to `/`. | D17 |
| F7 | A signed-in user who opens `/connexion` is sent to the dashboard. | D16 |
| F8 | The login form shows the generic error on failure and a loading state while submitting. | D4, D21 |
| F9 | A `401` during use clears the store and sends the user to `/connexion` with the current path. | D18 |
| F10 | The user menu shows the user's name and initials; "Se déconnecter" signs out and goes to `/connexion`. | D20 |
| F11 | The password form shows API field errors next to their inputs and blocks a mismatched confirmation. | D12, D19 |
| F12 | The HTTP helper fetches the CSRF cookie before the first unsafe request when it is missing. | D24 |

## 3. Manual walkthrough

Run both servers, with one user created through `createsuperuser`. Do the whole list once in
the **light** theme and once in the **dark** theme.

1. In a private window, open `/agents`. You land on `/connexion?redirect=/agents`. The shell
   (side menu, top bar) never flashes.
2. Submit a wrong password. The message "Identifiant ou mot de passe incorrect." appears; the
   form stays filled in except the password; no page reload.
3. Submit the right credentials with the Enter key. You land on `/agents`.
4. Reload the page. You are still signed in, on `/agents`.
5. The top bar shows your initials and name. Open the menu.
6. Go to "Changer le mot de passe". Try a wrong old password, then a weak new one (`12345678`):
   each error appears next to its field, in French.
7. Change the password for real. A success message appears and you stay signed in.
8. Choose "Se déconnecter". You land on `/connexion`. The browser's Back button does not show
   application data.
9. Sign in with the old password: refused. Sign in with the new one: accepted.
10. While signed in, open `/connexion` by hand. You are sent to the dashboard.
11. Open `/connexion?redirect=https://example.com` while signed out and sign in. You land on the
    dashboard, not on the external site.
12. While signed in, delete the `sessionid` cookie in the browser tools. Open "Agents" from
    the side menu, then the password screen from the user menu, and submit the form. You are
    sent to `/connexion` and, after signing in, back to the password screen. (The "Système"
    screen cannot be used for this check: `/api/health/` is public.)
13. `/admin/` still works with the same account, and shares the session.

Also check on the login and password screens:

- Text is in French, with correct accents.
- Keyboard only: Tab order is logical, focus is visible, Enter submits.
- The password manager offers to fill and to save (`autocomplete` attributes are right).
- The layout holds at a narrow width (about 380 px).
- No colour is hard-coded: both themes look intentional, with readable contrast.
- No JavaScript errors in the browser console. The browser's own "Failed to load resource"
  lines for the expected `401` (anonymous start-up) and `400` (rejected form) are fine.

## 4. Security checks

- In the browser tools: `sessionid` is `HttpOnly` and `SameSite=Lax`; `csrftoken` is readable.
- With `DJANGO_DEBUG` off, both cookies are `Secure`.
- Nothing about the session or the user is written to `localStorage` or `sessionStorage`.
- The password never appears in a URL, in the console or in server logs.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope in `requirements.md` slipped in.
- [ ] `tech-stack.md` shows Authentication as "In place".
- [ ] `README.md` says how to create the first user.
- [ ] **0.2 Login** is ticked in `roadmap.md`.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
