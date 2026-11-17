# Roles — validation

How to know phase 0.4 is done and `feature/roles` can be merged. All parts must pass: quality
gates, automated tests for every acceptance criterion, the manual walkthrough and the security
checks.

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

This phase adds two migrations in `accounts`: the `ModuleAccess` permissions (no table) and the
groups. Both must apply on an empty database and on the current development database.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test.

### Backend

| # | Criterion | Decision |
| --- | --- | --- |
| B1 | The eight module access permissions exist, labelled in French; `ModuleAccess` creates no table. | D6, D7 |
| B2 | The thirteen groups exist after migrating, each with exactly its module permissions from the matrix. | D1, D3 |
| B3 | `access_paie` belongs only to Rémunération, Chef de service — Rémunération and Direction RH. | Least privilege |
| B4 | `access_social` belongs only to Social and Chef de service — Social. | `SOC-M-20` |
| B5 | Administrateur système can view, add and change users and groups, cannot delete them, and has no access to Paie. | D8 |
| B6 | Setting up the groups again keeps a permission added by an administrator and creates no duplicate. | D4 |
| B7 | `me` and the login response include sorted `groups` and `permissions`; a user in two groups gets the union; a user in none gets empty lists. | D5, D11 |
| B8 | `HasModuleAccess`: `401` anonymous, `403` without the permission, success with it. | D12 |
| B9 | `/api/health/` and the login endpoints keep their current access. | D13 |
| B10 | `create_demo_users` creates one account per group, can be re-run without duplicates, sets `is_staff` only on the Administrateur système account, creates no superuser, and refuses to run with `DEBUG` off. | D21, D22 |

### Frontend

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The auth store's `can()` follows the `permissions` of the payload. | D15 |
| F2 | The menu shows exactly the modules allowed by the user's permissions; "Administration" is hidden when empty. | D16 |
| F3 | Opening a module without its permission shows "Accès refusé" inside the shell; the URL is unchanged; the link leads to the dashboard. | D17 |
| F4 | A user with no group sees the no-profile notice on the dashboard and no module in the menu. | D18 |
| F5 | The user menu shows the user's group names. | D19 |
| F6 | Routes and menu entries take their permission from the one shared map. | D14 |

## 3. Manual walkthrough

Set up the demo accounts first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_users
```

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.remuneration`. The menu shows Tableau de bord, Agents, Paie and
   Référentiels, and nothing else. The user menu shows "Rémunération".
2. Type `/social` in the address bar. "Accès refusé" appears inside the shell, the address stays
   `/social`, and the link goes back to the dashboard.
3. Sign out; sign in as `demo.social`. Paie is absent from the menu; Social is present.
4. Sign in as `demo.direction`. Every module except Social and Système is in the menu.
5. Sign in as `demo.auditeur`. Paie and Social are absent.
6. Sign in as `demo.admin`. The menu shows Tableau de bord, Référentiels, Système and Design.
   Open `/admin/`: users and groups can be viewed and edited; there is no delete action. The
   thirteen groups are listed with their permissions in French.
7. In `/admin/`, still as `demo.admin`, create an account with no group. Sign in with it: the
   dashboard shows the no-profile notice and the menu has no module.
8. As `demo.admin`, add that account to the Formation group. After signing in again, Formation
   appears in its menu.
9. Sign in as `demo.chef-carriere`: same menu as `demo.carriere`; the user menu shows the
   chef de service group.

Also check:

- Text is in French, with correct accents, in the menu, the "Accès refusé" page, the notice and
  the admin permission labels.
- The narrow layout (icon rail, below 1000 px) shows only the allowed icons.
- No JavaScript errors in the browser console.

## 4. Security checks

- The API refuses on its own: the test view protected by `HasModuleAccess` answers `403` to a
  signed-in user without the permission, whatever the frontend shows (D20).
- No demo account is a superuser. `create_demo_users` refuses to run with `DJANGO_DEBUG` off.
- The `permissions` list for `demo.admin` contains no `accounts.access_paie`.
- Nothing about roles or permissions is written to `localStorage` or `sessionStorage`.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope in `requirements.md` slipped in.
- [ ] `tech-stack.md` describes roles, `HasModuleAccess` and `meta.permission`.
- [ ] `README.md` explains the demo-users command and that superusers are for installation only.
- [ ] **0.4 Roles** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
