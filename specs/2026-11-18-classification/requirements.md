# Classification — requirements

Roadmap phase **1.2 Classification**: catégories, grades, échelons. Second phase of Milestone 1
(reference data).

Branch: `feature/classification`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.1: the configurable reference data include "catégories, grades,
  échelons et fonctions, avec la grille salariale associée".
- Section 4.2: an agent's position holds a grade and an échelon. Positions come in phase 2.4;
  they will point to the rows created here.
- `CAR-06`: a promotion records the old and new grade, an effective date and the decision. Phase
  3.1 will need to tell a higher grade from a lower one.
- `REM-24`: a pay component may depend on the grade; the pay grid holds an amount per grade, with
  an effective date. The grid itself is phase 6.2 (`Q7`, `Q11`). Section 7.6: the payslip shows
  the agent's "classification".
- `TRA-08`, `FOR-10`: the dashboard and training statistics break figures down by grade and by
  catégorie.
- `missions.md`, principle 3: history is never overwritten. A reform of the grid must not rewrite
  the grade of past positions. Principle 6: the grid is reference data maintained by the ARPTC.
  Principle 8: nothing is physically deleted.
- Phase 1.1 set the pattern this phase follows: the `referentiels` app, dated rows with
  `date_ouverture` and `date_fermeture`, exclusion constraints with `btree_gist`, one rules method
  called from `clean()` and `save()`, editing in Django admin, a read-only API filtered by date,
  a read-only tab on the "Référentiels" screen, and a `DEBUG`-only demo command.
- Roadmap 1.9 plans one generic edit screen for all reference data. Until then, reference tables
  are edited in Django admin.
- The ARPTC's real grid (catégories, grades, number of échelons) is not in the cahier des charges.

## Scope

### In scope

1. **Three tables in `apps.referentiels`**: `Categorie`, `Grade`, `Echelon`, nested: a grade
   belongs to one catégorie, an échelon to one grade.
2. **Dated rows**: each row has an opening date and an optional closing date; a reform closes
   rows and opens new ones.
3. **Ranks**: catégories and grades are ordered, so the grid sorts correctly and phase 3.1 can
   compare two grades.
4. **Database constraints and model rules** that keep the grid and its dates consistent.
5. **Editing in Django admin** for the Administrateur système and Gestion de carrière.
6. **Read-only API**: three flat endpoints, rows open at a date (or all).
7. **Read-only tab** "Classification" on the "Référentiels" screen, as a tree.
8. **Demo data** for development: a management command that loads a plausible grid.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Pay grid: amounts per grade or per grade and échelon | Phase 6.2 Pay scales (`Q7`, `Q11`) |
| Job functions | Phase 1.3 Fonctions |
| Giving an agent a grade and an échelon | Phase 2.4 Position history |
| Checking that a promotion moves to a higher grade | Phase 3.1 Promotions, using the ranks of D7 |
| Moving up an échelon with seniority, échelon duration | Not in the cahier des charges; to settle with `Q6` and phase 3.5 |
| Creating, correcting and closing rows from the app | Phase 1.9 Reference data screens; Django admin until then |
| Loading the real ARPTC grid | Entered by HR in Django admin (open point `Q28`) |
| Filters such as `?categorie=` or `?grade=` on the API | Added by phase 2.4 if its forms need them |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-18. The others follow
from [`missions.md`](../missions.md), [`tech-stack.md`](../tech-stack.md), the cahier des charges
and the pattern of phase 1.1.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **Three nested tables**: `Categorie`, `Grade` (foreign key to its catégorie), `Echelon` (foreign key to its grade). Each grade has its own échelons, and may have more or fewer than another grade. **(asked)** | Matches section 4.1. Phase 6.2 can then price a grade, or a grade and échelon pair, without restructuring. |
| D2 | A catégorie and a grade each have a `code` (up to 20 characters, saved in capitals) and a `nom` (up to 150). | Same as organisation units (1.1 D4); codes are how the grid is written on decisions and payslips. |
| D3 | A grade's code is unique across the whole grid at any date, not only within its catégorie. | The payslip shows the grade by its code alone; two grades with the same code would be ambiguous. |
| D4 | An échelon has a `numero` (positive integer) and no code or name of its own. Its label is `GRADE — Échelon N`. | An échelon is a step within its grade; its number is all it needs. |
| D5 | Gaps in échelon numbers are not refused (a grade may have échelons 1, 2 and 4). | Refusing gaps would make closing a single échelon impossible; HR keeps the numbering tidy. |

### Order

| # | Decision | Reason |
| --- | --- | --- |
| D6 | Catégories and grades each have a `rang` (positive integer). Two catégories open at the same time cannot share a rank; two grades of the same catégorie open at the same time cannot share a rank. **(asked)** | Gives a stable order for lists, the tree and reports. |
| D7 | **A grade is higher than another** when its catégorie's rank is higher, or, in the same catégorie, its own rank is higher. A model method returns this sort key; this phase uses it for ordering, phase 3.1 for the promotion check. A higher rank means a higher position. | One definition of "higher", written once. |
| D8 | Échelons are ordered by `numero`. | Natural order of steps. |

### History and reform

| # | Decision | Reason |
| --- | --- | --- |
| D9 | Every row has a `date_ouverture` (required) and a `date_fermeture` (optional). It is **open on day D** when `date_ouverture <= D < date_fermeture`. **(asked)** | Same rule as organisation units (1.1 D7): a reform closes the old row and opens the new one on the same effective date. |
| D10 | **Échelons have their own dates**, within their grade's period, so a grade can gain or lose a step without a reform. **(asked)** | Adding or retiring one step is a normal change of the grid. |
| D11 | **A grade's catégorie and an échelon's grade never change** after creation. Codes, names, ranks, numbers and dates may be corrected; every change is in the audit log. | Principle 3: a position that points to a grade keeps its catégorie. Corrections of typing errors stay possible. Same as 1.1 D8. |
| D12 | Overlapping periods cannot share: a catégorie code; a grade code (D3); a catégorie rank; a grade rank within its catégorie; an échelon number within its grade. Each is a PostgreSQL **exclusion constraint** on the key and the date range. A closed row's code, rank or number can be reused by its successor. | The key identifies a row at a given date; reuse after a reform is normal. Same technique as 1.1 D9. |
| D13 | A row's period lies within its parent's: a grade within its catégorie, an échelon within its grade. A parent cannot be closed while one of its children stays open after that date. | The grid at any date is complete: no open grade under a closed catégorie, no open échelon under a closed grade. Same as 1.1 D10. |
| D14 | Nothing is deleted: there is no delete permission on the three tables, and the API is read-only. | Principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D15 | **In the database**: positive rank and échelon number; closing date after opening date; the five exclusion constraints of D12; `PROTECT` on every foreign key. | Principle 1: invalid states are unrepresentable where practical. |
| D16 | **In the model**: the fixed parent (D11) and the periods (D13), checked by one method per model called from `clean()` (admin, serializers) and from `save()` (scripts). Messages in French, per field. The helpers of `models.py` (`open_on`, `still_open_after`, `raise_if`, `DateRange`) are reused, not copied. | These rules read other rows. Same split as 1.1 D14. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D17 | Every holder of `access_referentiels` **reads** the grid, through the API and the screen. | Every service needs grades; phase 0.4 already gives them the module. |
| D18 | **Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière** get view, add and change on the three tables. Nobody gets delete. **(asked)** | Gestion de carrière records grades and promotions (`CAR-06`); same editors as the organisation. Rémunération reads the grid and maintains the amounts in 6.2. |
| D19 | The permissions go into `roles.py` as one `CLASSIFICATION_EDIT_PERMISSIONS` tuple added to the three groups in `EXTRA_PERMISSIONS`. The group setup grants them after every `migrate` and only ever adds (1.1 D18, D31). | One declaration; administrators' adjustments survive deployments. |
| D20 | The demo accounts of the three groups already have "Statut équipe" (1.1 D17); nothing changes in `create_demo_users`. | Avoids touching what works. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D21 | Three admin classes with `BaseModelAdmin`, each with list columns, filters (parent, "ouvert aujourd'hui"), search, the parent through autocomplete, and the parent read-only when changing a row (D11). | Same as the organisation admin. |
| D22 | **No inlines** (no échelons inside the grade form). | `BaseModelAdmin` stamps the author on the main object only (`save_model`), not on inline rows; inline échelons would also be checked before their new grade exists. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D23 | The three models inherit `BaseModel` with `module = "referentiels"`. Row labels: `CODE — Nom` for catégories and grades, `GRADE — Échelon N` for échelons. | Captured automatically (phase 0.6); readers who open Référentiels see these entries. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D24 | **Three flat endpoints** under `/api/referentiels/`: `categories`, `grades`, `echelons`. Each returns the rows open on `?date=` (default today), or all rows with `?toutes=1`. Not paginated. The client builds the tree from the parent ids. **(asked)** | Mirrors `unites` and `sites`; flat lists also suit the dropdowns of phase 2.4. A grid has a few hundred rows at most. |
| D25 | Fields: a catégorie returns `id`, `code`, `nom`, `rang`, `date_ouverture`, `date_fermeture`; a grade adds `categorie` (id); an échelon returns `id`, `grade` (id), `numero`, `libelle` (`GRADE — Échelon N`), and the dates. All add the base fields. Rows are ordered by D7 and D8. Writes answer `405`. | What the screen and later forms need; editing comes with 1.9. |
| D26 | The three endpoints use `HasModuleAccess("referentiels")`. An invalid `date` answers `400` on that field, with the same validation as `unites`. | `tech-stack.md`: access enforced in the API, errors per field. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D27 | A third tab **"Classification"** on the "Référentiels" page, after "Organisation" and "Sites". **(asked)** | The page was built with tabs for the next reference tables (1.1 D24). |
| D28 | The tab shows a TreeTable catégorie → grade → échelon: name (indented; `Échelon N` for an échelon), code, level (Tag: Catégorie, Grade, Échelon), rank, opening and closing dates. A date picker "Classification au" (default today), a text filter that keeps the ancestors of a match, expand all and collapse all; empty and error states. | Shows the grid as it was or will be on any date (D9). Same controls as the organisation tree. |
| D29 | The tree helpers are shared: the filter and expand-all functions of `components/tree.ts` become generic over the node type, and the organisation tree keeps its behaviour and tests. | One filter for both trees; no copy. |
| D30 | The screen is read-only. The tab, the classification date and the text filter stay while the user moves around (Pinia); the classification date is kept apart from the organisation date. | Same as 1.1 D27. The two trees answer different questions; one date should not move the other. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D31 | `create_demo_classification` loads a plausible grid in development: four catégories (Cadres de direction, Cadres de collaboration, Agents de maîtrise, Agents d'exécution), two or three grades each, three to five échelons per grade, and one grade reformed in the past (closed, with its échelons, and a successor opened on the same date with the same code). It refuses to run when `DEBUG` is off, and running it twice changes nothing. **(asked)** | Gives the screen and later phases real-looking data without inventing the ARPTC's real grid in production. |
| D32 | Its rows have no author; the audit log shows them as written by "Système". | Same as other setup scripts (1.1 D29). |

### Decision recorded in tech-stack

| # | Decision | Reason |
| --- | --- | --- |
| D33 | `tech-stack.md`: the `referentiels` line of the repository layout names the classification. | `tech-stack.md` changes in the same commit as the stack. |

### Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| | *(to fill during implementation)* | |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q28` — the ARPTC's real grid: list of catégories, grades and their codes, number of échelons per grade, their order. Does a grade belong to exactly one catégorie? Are échelons numbered from 1 in every grade? | Three nested levels, each grade in one catégorie, échelons numbered per grade (D1, D4). HR enters the real grid in Django admin. Added to `docs/questions-ouvertes.md` by this phase; the merge does not wait for the answer. **(asked)** |
| `Q7`, `Q11` — which pay components depend on the grade, and their amounts. | Not needed here; D1 leaves room for amounts per grade or per grade and échelon in phase 6.2. |
