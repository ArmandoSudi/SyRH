# Roles — requirements

Roadmap phase **0.4 Roles**: one group per profile of section 3 of the spec; permissions exposed
to the frontend; menu filtered by role.

Branch: `feature/roles`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- Phase 0.2 Login is merged. Every API call needs a session; `GET /api/auth/me/` returns `id`,
  `username`, `first_name`, `last_name` and `email`. The payload was designed to receive roles
  and permissions in this phase.
- Section 3 of the [cahier des charges](../../docs/cahier-des-charges-sirh-arptc.md) lists ten
  profiles. "Agent" belongs to the later self-service portal (`missions.md`, out of scope), so
  nine profiles are concerned here.
- Common rules of section 3 that this phase starts to apply:
  - **Least privilege**: a profile sees only what its work needs. Salaries are visible to
    Rémunération and Direction RH only. Care details are visible to Social only (`SOC-M-20`).
  - **Configurable profiles**: the administrator can create profiles and adjust rights without
    development.
  - **Separation of duties**: whoever enters data does not validate it. This is enforced by the
    validation workflow (phase 2.11), not here.
- `NF-02` asks for rights per profile and per scope (module, service, type of data).
- No business table exists yet. The modules in the side menu (Agents, Carrière, Présences, Paie,
  Social, Formation, Référentiels) are placeholders; Système and Design are real pages.
- `tech-stack.md`: authorisation is role-based, built on Django groups and permissions, enforced
  in the API and mirrored, never replaced, in the UI.

## Scope

### In scope

1. **Module access permissions**: one permission per module, giving access to that module.
2. **Thirteen groups**, created in every environment, each with its module access (see the
   matrix below).
3. **Account administration** for the Administrateur système group in Django admin: users and
   groups.
4. **Current user payload** extended with the user's groups and permissions.
5. **API building block**: a DRF permission class that requires a module's access permission,
   for the module endpoints to come.
6. **Menu filtered by role**: modules the user cannot open are not shown.
7. **"Accès refusé" page** for a module opened without access.
8. **No-profile notice** for a signed-in user who belongs to no group.
9. **Role shown in the user menu**, under the user's name.
10. **Demo-users command** for development: one account per group.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Fine-grained permissions (view, add, change per table; see pay amounts; see care details) | Added to the groups as each module's tables arrive |
| Validation and rejection rights, separation of duties | Phase 2.11 Validation workflow |
| Scope by service or site beyond the five "Chef de service" groups (`NF-02`) | When a module needs it |
| A profile and rights screen in SyRH | Django admin covers "configurable profiles" for now |
| Audit of role and permission changes | Phase 0.6 Audit log |
| Two-factor authentication for sensitive profiles (`NF-01`) | Phase 9.4 Hardening |
| Agent self-service profile | Later version |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-17. The others follow
from [`missions.md`](../missions.md), [`tech-stack.md`](../tech-stack.md) and section 3 of the
cahier des charges.

### Profiles and groups

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One "Chef de service" group per HR service**, five in all, rather than one group plus a service field on the user. **(asked)** | A head validates only their own service's entries. Separate groups express that with plain Django groups, and need no model change. |
| D2 | In this phase a role grants **module access only**. Fine-grained permissions are added to the groups by the phase that creates each module's tables. **(asked)** | Nothing else exists to protect yet; permissions declared ahead of their tables would be untested promises. |
| D3 | The groups and their initial permissions are created by a **data migration**, so every environment (development, test, production) has the same roles. | Roles are part of the product, not of one database. |
| D4 | The migration only **adds** missing groups and permissions. It never removes a permission an administrator granted in Django admin. | "Configurable profiles": the administrator's adjustments survive later deployments. |
| D5 | A user may belong to **several groups**; their rights are the union. | Standard Django behaviour; covers a person who holds two roles. |
| D6 | **Group names are in French**, as the profiles of section 3. Permission codenames are in English (`access_paie`), labels in French ("Accès au module Paie"). | `missions.md`, principle 10: French interface, English code. |
| D7 | Module access permissions belong to `apps.accounts`, on a model that has no table (`ModuleAccess`, `managed = False`, no default permissions). | Django permissions need a model; this one exists only to carry them. |
| D8 | **Administrateur système** gets the Django admin permissions to view, add and change users and groups, but **not to delete** them. An account that leaves is deactivated. | `missions.md`, principle 8: nothing is physically deleted. |
| D9 | Group membership does not grant Django admin access by itself: the account also needs "Statut équipe" (`is_staff`), ticked by whoever creates it. | `is_staff` is a per-user flag in Django; keeping it explicit avoids surprise admin access. |
| D10 | **Superuser accounts are for installation only.** A superuser has every permission, pay included, which contradicts the Administrateur système profile. After installation, the first superuser creates named accounts in the right groups. | Section 3: the system administrator has no access to pay amounts. Documented in the README; not enforced in code in this phase. |

### Module access matrix

✓ = the group can open the module. The chef de service groups have the same access as their
service in this phase; their validation rights come with phase 2.11.

| Group | Agents | Carrière | Présences | Paie | Social | Formation | Référentiels | Système |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gestion de carrière | ✓ | ✓ | | | | | ✓ | |
| Administration du personnel | ✓ | | ✓ | | | | ✓ | |
| Rémunération | ✓ | | | ✓ | | | ✓ | |
| Social | ✓ | | | | ✓ | | ✓ | |
| Formation | ✓ | | | | | ✓ | ✓ | |
| Chef de service — Gestion de carrière | ✓ | ✓ | | | | | ✓ | |
| Chef de service — Administration du personnel | ✓ | | ✓ | | | | ✓ | |
| Chef de service — Rémunération | ✓ | | | ✓ | | | ✓ | |
| Chef de service — Social | ✓ | | | | ✓ | | ✓ | |
| Chef de service — Formation | ✓ | | | | | ✓ | ✓ | |
| Direction RH | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | |
| Auditeur | ✓ | ✓ | ✓ | | | ✓ | ✓ | |
| Administrateur système | | | | | | | ✓ | ✓ |

How the matrix was derived:

- **Agents** is open to every HR profile: the agent record is shared by all five services
  (MVP goal). The Administrateur système does not manage HR data.
- **Paie** follows "salaries are visible to Rémunération and Direction RH only".
- **Social** follows `SOC-M-20`: care details are limited to the Social service. Direction RH
  sees medical spend through the dashboard (phase 9.3), not the care detail.
- **Rémunération** reads variable items (absences, overtime) inside Paie, where phase 6.9 brings
  them, so it does not need Présences.
- **Référentiels** is open to everyone who maintains or reads reference data: rules are parameters
  HR maintains (`missions.md`, principle 6). Each table will carry its own write permission.
- **Système** (system status) and the design guide are technical pages for the Administrateur
  système.
- **Tableau de bord** is open to every signed-in user; it shows demonstration data until phase
  9.3.

### API

| # | Decision | Reason |
| --- | --- | --- |
| D11 | `GET /api/auth/me/` (and the login response) add `groups` (names, sorted) and `permissions` (`app_label.codename`, sorted, as `user.get_all_permissions()` returns them). | The frontend mirrors the rules without hard-coding who is in which group. |
| D12 | A DRF permission class, `HasModuleAccess("paie")`, answers `403` to a signed-in user without `accounts.access_paie`, and `401` to an anonymous one. Every module endpoint will use it. | `tech-stack.md`: access is enforced in the API. One class keeps every module consistent. |
| D13 | `/api/health/` stays public. No existing endpoint changes access. | Only the login and health endpoints exist so far. |

### Frontend

| # | Decision | Reason |
| --- | --- | --- |
| D14 | One shared map from module to permission (`agents` → `accounts.access_agents`, ...) is used by both the routes and the menu. | One source of truth for which permission opens which screen. |
| D15 | A route declares the permission it needs in `meta.permission`. The auth store answers `can(permission)`. | Mirrors `HasModuleAccess` on the API side. |
| D16 | The menu hides modules the user cannot open. The "Administration" heading is hidden when none of its entries is visible. | Least privilege; no dead links. |
| D17 | Opening a module without access shows an **"Accès refusé" page inside the shell**, with the URL unchanged and a link back to the dashboard. **(asked)** | The user sees what happened and where they are. |
| D18 | A signed-in user with **no group** sees the dashboard and a notice: "Aucun profil ne vous est attribué. Contactez l'administrateur du système." | Otherwise they would face an empty menu with no explanation. |
| D19 | The user menu shows the user's group names under their name; with several groups, they are listed. | Users and support can tell at a glance which role is active. |
| D20 | The UI never replaces the API check. Hiding a menu entry is a convenience; the endpoint refuses on its own. | `tech-stack.md`, API section. |

### Development tooling

| # | Decision | Reason |
| --- | --- | --- |
| D21 | `manage.py create_demo_users` creates or updates one account per group (`demo.carriere`, `demo.chef-carriere`, ..., `demo.admin`), with a password given on the command line or prompted. **(asked)** | Lets anyone walk through the app as each role, in this phase and every later one. |
| D22 | The command **refuses to run when `DEBUG` is off**. The demo Administrateur système account gets `is_staff`; no demo account is a superuser. | Demo accounts must never reach production. |

## Open points

| Point | MVP choice | To confirm with |
| --- | --- | --- |
| The Auditeur checks operations, but section 3 limits salaries to Rémunération and Direction RH and care details to Social. Should the auditor read Paie and Social? | No: the stricter rule wins until stakeholders decide. Granting it later is one change in Django admin. | Direction RH and internal audit |
| Should Direction RH read care details? | No (`SOC-M-20`). | Direction RH and Social |
