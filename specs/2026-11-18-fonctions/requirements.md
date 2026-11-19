# Fonctions — requirements

Roadmap phase **1.3 Fonctions**: the job functions an agent can hold. Third phase of Milestone 1
(reference data).

Branch: `feature/fonctions`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.1: the configurable reference data include "catégories, grades,
  échelons et fonctions". Section 4.2: an agent's position holds a direction, service,
  **fonction**, grade, échelon and supérieur hiérarchique. Positions come in phase 2.4; they will
  point to the rows created here.
- Section 3: Gestion de carrière writes the agent's grade and **fonction**.
- `SOC-02`: the dated history of anything that evolves, fonction included. `SOC-06`: search
  agents by fonction (phase 2.8).
- `CAR-08`: changes of fonction are recorded (phase 3.2). `CAR-09`: an interim covers a post and
  its holder (phase 3.3). Both need to tell a post of responsibility (heading a unit) from an
  execution post.
- Section 7.6: the payslip shows the agent's fonction.
- `missions.md`, principle 3: history is never overwritten. Renaming or retiring a fonction must
  not rewrite past positions. Principle 6: the list is reference data maintained by the ARPTC.
  Principle 8: nothing is physically deleted.
- Phases 1.1 and 1.2 set the pattern this phase follows: the `referentiels` app, dated rows with
  `date_ouverture` and `date_fermeture`, the `closing_after_opening()` and `unique_per_period()`
  constraint helpers, editing in Django admin, a read-only API filtered by date, a read-only tab
  on the "Référentiels" screen, and a `DEBUG`-only demo command.
- A fonction has no parent, unlike a grade or a unit: none of the rules that read other rows
  (`ClassificationRules`) apply.
- `docs/user-guide.md` (added 2026-11-18) describes the "Référentiels" screen tab by tab; a new
  tab must be documented there.
- The ARPTC's real list of fonctions is not in the cahier des charges.

## Scope

### In scope

1. **One table in `apps.referentiels`**: `Fonction`, with a code, a name and a nature
   (responsabilité or exécution).
2. **Dated rows**: an opening date and an optional closing date; renaming or retiring a fonction
   closes the row and opens its successor.
3. **Database constraints** that keep codes unique at any date and the dates consistent.
4. **Editing in Django admin** for the same editors as the organisation and the classification.
5. **Read-only API**: one flat endpoint, rows open at a date (or all).
6. **Read-only tab** "Fonctions" on the "Référentiels" screen.
7. **Demo data** for development: a management command that loads a plausible list.
8. **User guide**: the new tab documented in `docs/user-guide.md`, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Giving an agent a fonction | Phase 2.4 Position history |
| Which unit, or which type of unit, a responsibility heads; one head per unit | Phase 2.4, from the agent's position and its unit |
| A minimum catégorie or grade for a fonction | Not in the cahier des charges; raise with `Q29` if HR needs it |
| Recording a change of fonction | Phase 3.2 Transfers and function changes |
| Interim assignments | Phase 3.3 |
| Pay that depends on the fonction (indemnité de fonction) | Phase 6.1 / 6.2, with `Q7`, `Q10` |
| Creating, correcting and closing rows from the app | Phase 1.9 Reference data screens; Django admin until then |
| Loading the real ARPTC list | Entered by HR in Django admin (open point `Q29`) |
| Filters such as `?nature=` on the API | Added by phase 2.4 if its forms need them |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-18. The others follow
from [`missions.md`](../missions.md), [`tech-stack.md`](../tech-stack.md), the cahier des charges
and the pattern of phases 1.1 and 1.2.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One flat table** `Fonction`: `code` (up to 20 characters, saved in capitals), `nom` (up to 150), `nature`. No parent. **(asked)** | Section 4.1 lists fonctions beside the grid, not inside it; a fonction is held at any grade. |
| D2 | `nature` is a choice: **Responsabilité** (the holder heads a unit or a team: Directeur, Chef de service, Chef de bureau...) or **Exécution**. Required. **(asked)** | Phases 2.4 (supérieur hiérarchique), 3.3 (interims) and the reports need to tell posts of responsibility apart; one field now avoids a migration of every row later. |
| D3 | The code is unique among fonctions open at the same time; the name is not constrained. | The code identifies the fonction on decisions and the payslip; two names may legitimately be close. Same as 1.1 D4. |
| D4 | Fonctions sort by nature (Responsabilité first), then by name. | Puts posts of responsibility at the top of lists and dropdowns, without inventing a rank the cahier des charges does not give. |

### History

| # | Decision | Reason |
| --- | --- | --- |
| D5 | `date_ouverture` (required) and `date_fermeture` (optional). A fonction is **open on day D** when `date_ouverture <= D < date_fermeture`. **(asked)** | Same rule as units and the grid (1.1 D7, 1.2 D9): a successor opens on the day its predecessor closes. |
| D6 | A renamed fonction is closed and a successor opened, with the same code if HR wants; a typing error may be corrected in place. Every change is in the audit log. | Principle 3: a position that points to "Chargé d'études" keeps that label after a rename. Same as 1.2 D11. |
| D7 | Nothing is deleted: no delete permission on the table, and the API is read-only. | Principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D8 | **In the database**: closing date after opening date (`closing_after_opening()`); code unique per period (`unique_per_period()`, exclusion constraint on the code and the date range); `nature` limited to its two values by a check constraint. | Principle 1. Reuses the helpers of phase 1.2 instead of copying them. |
| D9 | **In the model**: the code is saved in capitals, from `clean()` and `save()`, as for catégories and grades. No `ClassificationRules`: a fonction has no parent and no children. | Nothing else reads other rows. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D10 | Every holder of `access_referentiels` **reads** the fonctions, through the API and the screen. | Every service shows the agent's fonction. |
| D11 | **Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière** get view, add and change on `Fonction`. Nobody gets delete. **(asked)** | Gestion de carrière writes the agent's fonction (section 3, `CAR-08`); same editors as 1.1 and 1.2. |
| D12 | The permissions go into `roles.py` as a `FONCTION_EDIT_PERMISSIONS` tuple, added to `REFERENTIELS_EDIT_PERMISSIONS`. The group setup grants them after every `migrate` and only ever adds. | One declaration; administrators' adjustments survive deployments (1.1 D18). |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D13 | One admin class with `BaseModelAdmin`: list columns (code, nom, nature, dates), filters (nature, the shared "ouvert aujourd'hui" filter), search on code and name. | Same as the other reference tables. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D14 | `Fonction` inherits `BaseModel` with `module = "referentiels"`. Row label: `CODE — Nom`. | Captured automatically (phase 0.6); readers who open Référentiels see these entries. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D15 | One endpoint `/api/referentiels/fonctions/`: the rows open on `?date=` (default today), or all with `?toutes=1`, through the existing `PeriodeMixin`. Not paginated. Writes answer `405`. | Mirrors `sites`, `unites` and the grid; a list of fonctions has tens of rows. |
| D16 | Fields: `id`, `code`, `nom`, `nature`, `nature_libelle` (French label), `date_ouverture`, `date_fermeture`, plus the base fields. Ordered by D4. | What the screen and the dropdowns of phase 2.4 need. |
| D17 | `HasModuleAccess("referentiels")`. An invalid `date` answers `400` on that field. | `tech-stack.md`: access enforced in the API, errors per field. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D18 | A fourth tab **"Fonctions"** on the "Référentiels" page, after "Classification". **(asked)** | The page was built with tabs for the next reference tables. |
| D19 | The tab shows a table: code, nom, nature (Tag: Responsabilité, Exécution), opening and closing dates. A date picker "Fonctions au" (default today) and a text filter on code and name; loading, empty and error states. No tree: the list is flat. | Same controls as the other tabs, without the expand buttons a flat list does not need. |
| D20 | The screen is read-only. The tab, its date and its filter stay while the user moves around (Pinia), in their own `fonctions` object of the store, apart from the organisation and classification ones. | Same as 1.2 D30, D40. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D21 | `create_demo_fonctions` loads about a dozen plausible fonctions in development, both natures (Directeur général, Directeur, Chef de département, Chef de service, Chef de bureau; Ingénieur télécoms, Juriste, Comptable, Assistant administratif, Chauffeur...), and one fonction renamed in the past (closed, and a successor with the same code opened on the same date). It refuses to run when `DEBUG` is off, and running it twice changes nothing. | Gives the screen and later phases real-looking data without inventing the ARPTC's real list in production. Same as 1.2 D31. |
| D22 | Its rows have no author; the audit log shows them as written by "Système". | Same as the other demo commands. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D23 | `docs/user-guide.md` gets a "Fonctions" subsection under "Reference data", with screenshots taken by `docs/capture_screenshots.py` (extended for the new tab), and `docs/user-guide.html` is rebuilt. **(asked)** | The guide describes the screen tab by tab; leaving one out would make it wrong on merge. |
| D24 | `tech-stack.md`: the `referentiels` lines of the repository and frontend layouts name the fonctions. | `tech-stack.md` changes with the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q29` — the ARPTC's real list of fonctions: their codes and names, which ones are posts of responsibility, whether a fonction requires a minimum catégorie or grade. | A flat list with two natures (D1, D2); HR enters the real list in Django admin. Added to `docs/questions-ouvertes.md` by this phase; the merge does not wait for the answer. |
| `Q7`, `Q10` — whether a pay item depends on the fonction (indemnité de fonction). | Not needed here; a fonction can be priced later by its id. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D25 | A closing date on or before the opening date is refused by the model rules, on `date_fermeture`, for every dated table (units, catégories, grades, échelons, fonctions), through one shared `check_closing_after_opening()`. The database check stays. | Found while testing the fonction admin: Django checked the exclusion constraints even with reversed dates, and PostgreSQL refused to build the range (`DataError`), so the admin crashed instead of showing the message. The fault dated from phase 1.1. An error on the field makes `full_clean()` skip the constraints that use it, and puts the message next to the field. |
