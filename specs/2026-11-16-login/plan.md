# Login — plan

Task groups for roadmap phase 0.2, backend first, then frontend. Decision numbers (`D1`...) refer
to [`requirements.md`](requirements.md). Each group ends with its tests passing and can be
committed on its own.

## 1. Backend: authentication plumbing

1. Add a `SessionAuthentication` subclass in `apps/accounts/` that sets `authenticate_header`, so
   anonymous requests get `401` (D8). Make it the default in `REST_FRAMEWORK`.
2. Set cookie options in `config/settings.py`: `SESSION_COOKIE_HTTPONLY`, `SameSite=Lax`,
   `CSRF_COOKIE_HTTPONLY = False`, and `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` when `DEBUG`
   is off (D11).
3. Create `apps/accounts/urls.py` and include it under `/api/auth/` in `config/urls.py`.
4. Test: an anonymous call to a protected endpoint returns `401`; `/api/health/` stays public.

## 2. Backend: login, logout, current user

1. `UserSerializer` with `id`, `username`, `first_name`, `last_name`, `email`.
2. `GET /api/auth/csrf/` — public, sets the CSRF cookie, `204`.
3. `POST /api/auth/login/` — public, CSRF enforced (D9), authenticates, calls `login()`, returns
   the user; generic error on any failure (D4).
4. `POST /api/auth/logout/` — authenticated, `logout()`, `204`.
5. `GET /api/auth/me/` — authenticated, returns the user.
6. Tests, with a CSRF-enforcing client where relevant:
   - login succeeds with valid credentials and the session then authenticates `me`;
   - wrong password, unknown username and inactive account all give the same `400` body;
   - login without a CSRF token is rejected;
   - the session key changes on login (D10);
   - logout ends the session, and `me` then returns `401`;
   - logout and `me` return `401` when anonymous.

## 3. Backend: change own password

1. `POST /api/auth/password/` — checks `old_password`, runs Django's password validators on
   `new_password` against the user, saves, calls `update_session_auth_hash` (D5).
2. Tests:
   - success: the new password works, the old one does not, the current session survives;
   - a second session of the same user is ended;
   - wrong old password gives a field error on `old_password`;
   - a weak new password gives a field error on `new_password`;
   - anonymous gives `401`.

## 4. Frontend: HTTP client

1. `src/api/http.ts`: a small wrapper over `fetch` that reads the `csrftoken` cookie, sends
   `X-CSRFToken` on unsafe methods, handles JSON and `204`, and throws an `ApiError` with
   `status` and field errors (D13).
2. A hook to register one "unauthorised" handler, called on any `401` (D18).
3. Move `fetchHealth` onto the wrapper.
4. `src/api/auth.ts`: `login`, `logout`, `fetchMe`, `changePassword`, with types. The CSRF
   cookie is fetched by the wrapper itself when missing (D24).
5. Tests: CSRF header present on `POST` and absent on `GET`; `ApiError` carries field errors;
   the `401` handler is called.

## 5. Frontend: auth store

1. `src/stores/auth.ts`: `user`, `isAuthenticated`, display name and initials; actions
   `init()` (loads the user once, treats `401` as anonymous), `login()`, `logout()` (D14).
2. Tests: `init` with and without a session; `login` sets the user; `logout` clears it; `init`
   runs the request only once.

## 6. Frontend: login page

1. `src/views/LoginView.vue` at `/connexion`, outside `AppShell`, lazy-loaded, `meta.public`
   (D15, D16).
2. PrimeVue form: "Identifiant", "Mot de passe" (with show/hide), "Se connecter" button with a
   loading state; the generic error shown above the form; focus on the first field; submit on
   Enter; correct `autocomplete` attributes.
3. SyRH branding and theme toggle, using `--sy-*` tokens only (D21).
4. Tests: submits the credentials; shows the error on failure; disables the button while
   loading.

## 7. Frontend: route guard and redirect back

1. `router.beforeEach`: await `auth.init()`; anonymous on a protected route goes to `/connexion`
   with `redirect`; signed-in on `/connexion` goes to the dashboard (D15, D16).
2. A helper that validates the `redirect` value (D17); used after login.
3. Register the `401` handler: clear the store, go to `/connexion` with the current path (D18).
4. Tests: anonymous is redirected with the right query; the redirect target is honoured after
   login; `//evil.example` and absolute URLs fall back to `/`; a signed-in user never sees the
   login page.

## 8. Frontend: user menu and password screen

1. In `AppShell.vue`, replace the static avatar with the user's initials and name, opening a
   PrimeVue menu with "Changer le mot de passe" and "Se déconnecter" (D20).
2. `src/views/PasswordView.vue` at `/compte/mot-de-passe`: old password, new password,
   confirmation; field errors from the API next to each input; success toast (D19).
3. Tests: the menu shows the user's name and signs out; the password form shows API field
   errors and rejects a mismatched confirmation before calling the API.

## 9. Wrap-up

1. Run the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
2. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
3. Update `tech-stack.md`: Authentication status to "In place"; add `/api/auth/csrf/` and
   `/api/auth/login/` to the endpoints that opt out of authentication.
4. Add a line to `README.md` on creating the first user (`createsuperuser`).
5. Tick **0.2 Login** in [`roadmap.md`](../roadmap.md).
