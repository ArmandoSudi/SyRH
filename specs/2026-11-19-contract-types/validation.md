# Contract types — validation

How to know phase 1.4 is done and `feature/contract-types` can be merged. All parts must pass:
quality gates, automated tests for every acceptance criterion, the manual walkthrough, the
security checks and the user guide update. **(asked)**

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

The migration `0005_typecontrat` must apply on an empty database and on the current development
database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure and constraints

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A type has a code, a name, both flags and an opening date; all are required. | D1, D2 |
| S2 | The code is saved in capitals, through `save()` and `full_clean()`. | D10 |
| S3 | Two types with the same code and overlapping periods are refused by the database; the same code on consecutive periods is accepted. Two types with the same name are accepted. | D4, D9 |
| S4 | A closing date on or before the opening date is refused by the database, and by `full_clean()` with a message on `date_fermeture` and no database error. | D9, D10 |
| S5 | Types sort by name. | D5 |

### History

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | A type is open from its opening date included to its closing date excluded; `ouvertes(date)` returns exactly those. | D6 |
| H2 | Changing a flag by closing the type and opening a successor with the same code succeeds, and the earlier date still shows the old flags. A type closed with no successor is gone after its closing date. | D7 |
| H3 | There is no delete permission on `typecontrat`. | D8 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating, correcting and closing a type each write an audit entry under module `referentiels`, labelled `CODE — Nom`, with the author who made the change. | D15 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, the three editor groups have view, add and change on `typecontrat`; no other group has add or change; nobody has delete. A hand-made change to the groups survives the next `migrate`. | D12, D13 |
| P2 | The admin lists types with code, name, both flags and dates; filters on each flag and "ouvert aujourd'hui"; searches code and name; shows the flags' help texts. | D14 |
| P3 | `GET /api/referentiels/types-contrat/` returns the types open today by default, on `?date=`, or all with `?toutes=1`, ordered by name, with the fields of D17. An invalid `date` answers `400` on that field. | D16, D17, D18 |
| P4 | Anonymous `401`; an account in no group `403`; every profile with Référentiels `200`. `POST`, `PUT`, `PATCH`, `DELETE` answer `405`. | D11, D16, D18 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_types_contrat` refuses to run when `DEBUG` is off. | D22 |
| E2 | It creates CDI, CDD, Stage and Journalier with the flags of D22 and a retired Contrat d'apprentissage; a second run creates nothing and writes no audit entry; its entries show no author. | D22 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The "Référentiels" page has a fifth tab "Types de contrat", after "Fonctions". | D19 |
| F2 | The tab loads the types for today, reloads when "Types au" changes, and shows loading, empty and error states. | D20 |
| F3 | The flags show as "Oui" or "Non"; the text filter matches code and name, ignoring case and accents. | D20, D21 |
| F4 | The tab, its date and filter survive navigation; changing its date leaves the other tabs' dates alone. | D21 |
| F5 | The tab offers no button that changes data. | D21 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_types_contrat
```

(The other demo commands, `create_demo_users`, `create_demo_organisation`,
`create_demo_classification` and `create_demo_fonctions`, must have run once.)

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. Open "Référentiels", tab "Types de contrat": CDD, CDI,
   Journalier and Stage in name order, with "Oui" and "Non" in the two flag columns. Filter on
   part of a code, then part of a name.
2. Set "Types au" to a date in 2022: "Contrat d'apprentissage" appears. Switch to "Fonctions":
   its date is still today. Go to the dashboard and back: the tab, its date and filter are kept.
3. In `/admin/`, check the list, the filters on each flag, the search and the help texts of the
   flags. Submit (without saving) a type with a code already open, then one with a closing date
   before its opening date: the first is refused at the top of the form, the second next to
   "Date de fermeture". There is no delete button or action.
4. Sign in as `demo.remuneration`, then `demo.auditeur`: the tab opens read-only; `/admin/` does
   not let them in.

Creating, correcting and closing a type in the admin, and their audit entries, are covered by the
automated tests (A1, P1); they are not repeated by hand on the development database, whose audit
log keeps every write for good.

Also check:

- Text is in French with correct accents: tab, column titles, "Oui"/"Non", admin labels, help
  texts and messages.
- Dates are shown as `dd/mm/yyyy`.
- At 375 px wide the tab is usable: the table scrolls inside its card, the toolbar wraps, and the
  page does not scroll sideways.
- No JavaScript errors in the browser console, beyond the `401` of the sign-in check.

## 4. Security checks

- As `demo.carriere`, a `POST` to `/api/referentiels/types-contrat/` answers `405`.
- An account in no group gets `403` on the endpoint.
- In `psql`, inserting a type with the code of an open type over the same period fails with the
  exclusion constraint.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_typecontrat'` returns nothing.

## 5. User guide

- `docs/user-guide.md` has a "Types de contrat" subsection under "Reference data", with short
  steps and at least one screenshot; the tab count and "Who changes the reference data" mention
  the contract types.
- The screenshots were taken by `docs/capture_screenshots.py` against the demo data; every image
  path in the guide exists and is non-empty, and every screenshot in `docs/screenshots/` is used.
- `docs/user-guide.html` has been rebuilt and shows the new subsection.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope slipped in: no agent contract, no probation length or
      renewal rule, no separate intern or day-labourer register, no alert, no edit form in the
      app, no real list in a migration.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `Q30` is in `docs/questions-ouvertes.md`. Its answer is **not** required to merge.
- [ ] `tech-stack.md` names the contract types in the `referentiels` lines.
- [ ] **1.4 Contract types** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
