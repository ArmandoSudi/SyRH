# Roles — plan

Task groups for roadmap phase 0.4, backend first, then frontend. Decision numbers (`D1`...) refer
to [`requirements.md`](requirements.md). Each group ends with its tests passing and can be
committed on its own.

## 1. Backend: module access permissions

1. In `apps/accounts/models.py`, add `ModuleAccess`: `managed = False`,
   `default_permissions = ()`, and one permission per module: `access_agents`,
   `access_carriere`, `access_personnel`, `access_paie`, `access_social`, `access_formation`,
   `access_referentiels`, `access_systeme`, labelled "Accès au module …" (D6, D7).
2. Keep the module list in one constant (`apps/accounts/roles.py`) that the model, the migration
   and the permission class all read.
3. Generate the migration; check that it creates no table.
4. Tests: the eight permissions exist after migrating; `ModuleAccess` has no table.

## 2. Backend: groups

1. In `roles.py`, describe the thirteen groups and their modules as data: the matrix of
   `requirements.md`, nothing else.
2. Data migration: call `create_permissions` for the app first (permissions are otherwise only
   created after all migrations), then `get_or_create` each group and **add** its permissions
   (D3, D4). Reverse migration: no-op.
3. Administrateur système also gets `view`, `add` and `change` on `accounts.user` and
   `auth.group`, and no `delete` (D8).
4. Tests:
   - each group exists with exactly the module permissions of the matrix;
   - Paie is granted only to Rémunération, its chef de service and Direction RH;
   - Social only to Social and its chef de service;
   - Administrateur système has no `access_paie` and no `delete_user`;
   - running the group setup twice changes nothing, and keeps a permission added by hand.

## 3. Backend: API

1. `UserSerializer`: add `groups` and `permissions`, both sorted lists (D11).
2. `apps/accounts/permissions.py`: `HasModuleAccess(module)`, returning a DRF permission class;
   unknown module names fail at import time, not at request time (D12).
3. Tests:
   - `me` returns the groups and permissions of a user in two groups (union, D5);
   - a user with no group gets empty lists;
   - with a test view protected by `HasModuleAccess("paie")`: `401` anonymous, `403` for
     Gestion de carrière, `200` for Rémunération;
   - `/api/health/` stays public (D13).

## 4. Backend: demo users

1. `apps/accounts/management/commands/create_demo_users.py`: one account per group, named
   `demo.<slug>`, with a French first and last name; `--password` or an interactive prompt;
   creates or updates, so it can be re-run (D21).
2. Refuse to run when `DEBUG` is off, with a clear message; `is_staff` only for the demo
   Administrateur système; no superuser (D22).
3. Tests: creates thirteen accounts with the right group; re-running updates rather than
   duplicates; refuses with `DEBUG = False`.

## 5. Frontend: permissions in the auth store

1. `User` type: add `groups: string[]` and `permissions: string[]`.
2. `features/auth/permissions.ts`: the module → permission map (D14).
3. Auth store: `can(permission)`, `hasProfile` (at least one group) and `roleLabel` for the user
   menu (D15, D19).
4. Tests: `can` follows the payload; a user with no group has no profile.

## 6. Frontend: routes and menu

1. Add `meta.permission` to the module routes (the placeholders in `router/index.ts`, Système
   and Design) (D15).
2. `AppShell.vue`: each menu entry carries its permission; hide entries the user cannot open and
   the "Administration" heading when it is empty (D16).
3. User menu: show the role label under the name (D19).
4. Tests: the menu shows exactly the allowed entries for Rémunération, Administrateur système
   and a user with no group.

## 7. Frontend: "Accès refusé" and no-profile notice

1. `shared/layouts/AccessDenied.vue`: title, short explanation, link back to the dashboard.
2. `AppShell.vue` renders it in place of the routed page when the route's permission is missing,
   so the URL stays as typed (D17).
3. Dashboard: notice for a user with no group (D18).
4. Tests: a user without `access_paie` who opens `/paie` sees "Accès refusé" and the URL stays
   `/paie`; a user with it sees the module; the notice shows only without a group.

## 8. Wrap-up

1. Run the manual walkthrough in [`validation.md`](validation.md) with the demo accounts, in
   light and dark themes.
2. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
3. `tech-stack.md`: describe roles and `HasModuleAccess` in the API section, and `meta.permission`
   in the frontend section.
4. `README.md`: the demo-users command, and that superusers are for installation only (D10).
5. Tick **0.4 Roles** in [`roadmap.md`](../roadmap.md).
6. Run `/changelog` before merging.
