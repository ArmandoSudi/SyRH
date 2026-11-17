# Organisation — requirements

Roadmap phase **1.1 Organisation**: sites, directions, départements, services, bureaux, as a tree.
First phase of Milestone 1 (reference data).

Branch: `feature/organisation`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.1: the configurable reference data include the "structure
  organisationnelle : directions, départements, services, bureaux, sites".
- Section 4.2: an agent's position holds a direction and a service (and a supérieur
  hiérarchique). Positions come in phase 2.4; they will point to the units created here.
- `NF-11`: SyRH is used on every ARPTC site, the head office and the provincial
  representations. `missions.md`, fixed rules: all ARPTC sites are covered.
- `missions.md`, principle 3: history is never overwritten. A restructuring must not rewrite the
  direction of past positions.
- Principle 6: reference data is maintained by the ARPTC, without development. Principle 8:
  nothing is physically deleted; a unit that disappears is closed.
- Phase 0.4: every service, chef de service, Direction RH, Auditeur and Administrateur système
  open the Référentiels module (`accounts.access_referentiels`). Finer, per-table permissions
  are added by the phase that creates the tables: this one.
- Phase 0.4 D9: Django admin needs "Statut équipe" (`is_staff`) on the account, besides the
  permissions.
- Phases 0.5 and 0.6: every business model inherits `BaseModel`, declares its `module`, and is
  audited automatically.
- Roadmap 1.9 plans one generic list and edit screen for all reference data. Until then,
  reference tables are edited in Django admin (`tech-stack.md`, Backend).
- The ARPTC's real organigramme and list of sites are not in the cahier des charges.

## Scope

### In scope

1. **A new `apps.referentiels` app**, the home of every Milestone 1 table.
2. **Sites**: the head office and the provincial representations.
3. **Organisation units** of four types (direction, département, service, bureau), arranged in a
   tree, each located at a site, each with an opening date and an optional closing date.
4. **Database constraints and model rules** that keep the tree and its dates consistent.
5. **Editing in Django admin** for the Administrateur système and Gestion de carrière.
6. **Read-only API**: units open at a date (or all), and sites.
7. **Read-only screen** "Référentiels", tab "Organisation" (the tree) and tab "Sites".
8. **Demo data** for development: a management command that loads a plausible structure.

### Out of scope

| Item | Where it goes |
| --- | --- |
| The head of a unit, the supérieur hiérarchique | Phase 2.4 Position history, once agents exist |
| Assigning agents to units | Phase 2.4 |
| Creating, renaming and closing units from the app | Phase 1.9 Reference data screens; Django admin until then |
| Loading the real ARPTC organigramme | Entered by HR in Django admin, or with phase 2.15 Data import (open point `Q27`) |
| Restricting data by service or site (`NF-02` "périmètre") | Not planned yet; would come with the agent record |
| Budgeted headcount per unit | Not in the cahier des charges |
| Other reference tables (grades, fonctions, contract types, ...) | Phases 1.2 to 1.8 |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-18. The others follow
from [`missions.md`](../missions.md), [`tech-stack.md`](../tech-stack.md) and the cahier des
charges.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | One table of units, `UniteOrganisationnelle`, with a `type`: `direction`, `departement`, `service`, `bureau`, in that order of level. **(asked)** | Section 4.1 lists the four levels; one table keeps the tree and its queries simple. |
| D2 | A unit's parent must be of a **higher level**; levels may be skipped (a service directly under a direction, a bureau directly under a département). **(asked)** | The real structure is not uniform; skipping is common, inversion never makes sense. |
| D3 | **Directions are the roots**: a direction has no parent, and every other unit has one. The Direction générale and each provincial representation are recorded as directions. | Gives every unit a direction, which positions (2.4) and reports by direction need. The assumption is an open point (`Q27`). |
| D4 | Each unit has a `code` (its sigle, such as `DRH`), stored in capitals, up to 20 characters, and a `nom` (up to 150). | Codes are how the ARPTC names its units in documents and reports. |
| D5 | **Sites are a separate table**, `Site`; every unit is located at one site. **(asked)** | Sites are geographic and the tree is hierarchical; a provincial representation's units all point to its site. |
| D6 | A site has a `code` (unique, never reused), a `nom`, a `ville`, a `siege` flag and an optional `date_fermeture`. At most one open site is the head office. | Enough to place units and, later, agents; the head office is needed by documents (payslip header). |

### History and restructuring

| # | Decision | Reason |
| --- | --- | --- |
| D7 | A unit has a `date_ouverture` (required) and a `date_fermeture` (optional). It is **open on day D** when `date_ouverture <= D < date_fermeture`: the closing date is the first day it no longer exists. | Lets a restructuring close the old unit and open the new one on the same effective date. |
| D8 | **A unit's type, parent and site never change** after creation. A move, a split or a merger closes the unit and opens new ones. Its code, name and dates may be corrected; every change is in the audit log. **(asked)** | Principle 3: past positions keep the direction they had. Corrections of typing errors stay possible. |
| D9 | Two units whose periods overlap cannot share a code; a closed unit's code can be reused by its successor. Enforced by a PostgreSQL **exclusion constraint** on the code and the date range. | The code identifies a unit at a given date; reuse after a restructuring is normal. |
| D10 | A unit's period lies within its parent's: it cannot open before its parent nor stay open after it. A parent cannot be closed while one of its children stays open after that date. | The tree at any date is complete: no open unit hangs under a closed one. |
| D11 | A unit cannot be created at a closed site, and a site cannot be closed while an open unit is located there. | Same reason, for sites. |
| D12 | Nothing is deleted: there is no delete permission on either table, and the API is read-only. | Principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D13 | **In the database**: direction if and only if no parent; a unit is not its own parent; closing date after opening date; the code exclusion constraint (D9); the single open head office (D6); `PROTECT` on every foreign key. | Principle 1: invalid states are unrepresentable where practical. |
| D14 | **In the model**: the level order (D2), the fixed type, parent and site (D8), the periods (D10, D11), checked by one method called from `clean()` (admin, serializers) and from `save()` (scripts). Messages in French, per field. | These rules read other rows, which a check constraint cannot do. Calling them from `save()` means a script cannot bypass them. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D15 | Every holder of `access_referentiels` **reads** units and sites, through the API and the screen. | Every service needs the structure; phase 0.4 already gives them the module. |
| D16 | **Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière** get the Django permissions to view, add and change units and sites. Nobody gets delete. **(asked)** | The administrator keeps the settings; Gestion de carrière assigns agents to units and knows the structure. |
| D17 | Gestion de carrière accounts need "Statut équipe" to open Django admin, as in phase 0.4 D9. `create_demo_users` ticks it for the demo accounts of the editing groups. | Keeps admin access explicit per account. |
| D18 | The group setup grants the per-table permissions after every `migrate`, like the module permissions, and only ever adds. | Phase 0.4 D4: administrators' adjustments survive deployments. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D19 | Both models inherit `BaseModel` with `module = "referentiels"`. Their row label in the log is `CODE — Nom`. | Captured automatically (phase 0.6); readers of the audit log who open Référentiels see these entries, the Administrateur système included. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D20 | `GET /api/referentiels/unites/`: a flat list of the units open on `?date=` (default today), or of all units with `?toutes=1`. Each unit carries its parent id, so the client builds the tree. Not paginated. | A few hundred units at most; the tree needs them all at once. |
| D21 | `GET /api/referentiels/sites/`: open sites, or all with `?toutes=1`. Not paginated. | Same reason. |
| D22 | A unit is returned with `id`, `code`, `nom`, `type`, `type_libelle`, `parent`, `site` (`{id, code, nom}`), `date_ouverture`, `date_fermeture`, and the base fields. Writes answer `405`. | What the screen and later forms need; editing comes with 1.9. |
| D23 | Both endpoints use `HasModuleAccess("referentiels")`. An invalid `date` answers `400` for that field. | `tech-stack.md`: access enforced in the API, errors per field. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D24 | Feature folder `referentiels`; route `/referentiels` replaces the placeholder, with the same permission. The page has two tabs, "Organisation" and "Sites"; phase 1.9 adds the other tables. **(asked)** | One page per module; tabs leave room for the next reference tables. |
| D25 | "Organisation" shows the tree (PrimeVue TreeTable): name, code, type, site, opening and closing dates; a date picker "Organisation au" (default today); a text filter; expand all and collapse all. | Shows the structure as it was or will be on any date (D7). |
| D26 | "Sites" lists the sites: code, name, city, head office, status; closed sites on request. | Simple list; there are few sites. |
| D27 | The screen is read-only. The chosen tab, date and filters stay while the user moves around (Pinia). | Editing is in Django admin until 1.9; `tech-stack.md` keeps filters across navigation. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D28 | `create_demo_organisation` loads a plausible structure in development: the head office and three provincial sites, the Direction générale, the Direction des Ressources humaines with its five services, two other directions with départements, services and bureaux, a provincial representation, and one closed unit with its successor. It refuses to run when `DEBUG` is off, and running it twice changes nothing. **(asked)** | Gives the screen and later phases real-looking data, without inventing the ARPTC's real structure in production. |
| D29 | Its rows have no author; the audit log shows them as written by "Système". | Same as other setup scripts (phase 0.6). |

### Decision recorded in tech-stack

| # | Decision | Reason |
| --- | --- | --- |
| D30 | `tech-stack.md`: `referentiels` moves from the planned apps to the repository layout; the Database section names exclusion constraints on date ranges as the way to keep dated rows from overlapping, with `btree_gist`. | `tech-stack.md` changes in the same commit as the stack. |

### Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D31 | The group setup now runs once per `migrate`, on the signal of the last installed app, instead of after `accounts`. | Django creates each app's permissions on its own signal; after `accounts`, the `referentiels` permissions did not exist yet, and the setup failed on a fresh database. |
| D32 | `django.contrib.postgres` is added to `INSTALLED_APPS`. | Range lookups and the validation of the exclusion constraint in forms come from it. |
| D33 | Database constraint messages (code overlap, direction without parent) appear at the top of the admin form, in French; the rules of D14 appear next to their field. | Django reports constraint violations as form-wide errors; the field-level rules cover the common mistakes. |
| D34 | D11 is one rule in each direction: a unit closes no later than its site, and a site cannot close while a unit stays open after that date. | Covers a unit created at a closed site and a site closed under an open unit with the same check. |
| D35 | Text buttons use the `secondary` severity and the active tab keeps the text colour; the audit screen's "Effacer les filtres" button is fixed the same way. | `design.md`, principle 2: lime is a fill, never text. Found in the walkthrough. |
| D36 | `localDate()` moves from the audit store to `shared/utils/dates.ts`, with `formatDate()`. | Both the audit and Référentiels screens need it; a feature does not import another's store for a helper. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q27` — the ARPTC's real organigramme: list of directions, départements, services and bureaux, their codes, and the list of sites. Is there a level between direction and département (division)? Does the Direction générale sit above the directions? | Four levels; the Direction générale and each provincial representation are directions (D3). HR enters the real structure in Django admin. Added to `docs/questions-ouvertes.md` by this phase. |
