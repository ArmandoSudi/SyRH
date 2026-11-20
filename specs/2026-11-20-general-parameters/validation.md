# General parameters — validation

How to know phase 1.8 is done and `feature/general-parameters` can be merged. All parts must
pass: quality gates, automated tests for every acceptance criterion, the manual walkthrough, the
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

The migration `0011_parametre` must apply on an empty database and on the current development
database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure and constraints

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A row has a key, a value and an opening date, all required; the key is one of the four of D2, each with a label, a unit and bounds. | D1, D2 |
| S2 | A key outside the list, or a value outside its key's bounds, is refused by the database; the bounds themselves are accepted; `full_clean()` reports the bounds on `valeur` with the range and unit. | D2, D9, D10 |
| S3 | Two rows of the same key over overlapping periods are refused by the database; on consecutive periods accepted; two keys over the same period accepted. | D3, D9 |
| S4 | A closing date on or before the opening date is refused by the database; `full_clean()` reports it on `date_fermeture`, with no database error. | D9, D10 |
| S5 | Rows sort by the key order of D2, then by opening date. | D4 |
| S6 | `valeur_au(cle, jour)` returns the value open that day, before, on and after a change; with no open row it raises `ParametreManquant` naming the key and the date. | D5 |

### History

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | The table follows the opening-included, closing-excluded rule in `ouvertes(date)`. | D6 |
| H2 | The key cannot change after creation, through `full_clean()` and `save()`; the value and dates can be corrected. | D7, D10 |
| H3 | There is no delete permission. | D8 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating, correcting and closing a value write audit entries under module `referentiels`, labelled like `Âge de la retraite : 65 ans`, with their author. | D15 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, the three editor groups have view, add and change; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D12, D13 |
| P2 | The admin lists and filters the values; the key is read-only on change; rule errors show next to their field and constraint errors at the top; other profiles get `403`. | D14 |
| P3 | The endpoint returns the values open today by default, on `?date=`, or all with `?toutes=1`, in key order, with the fields of D17; an invalid `date` answers `400` on that field. | D16, D17 |
| P4 | Anonymous `401`; no group `403`; every profile with Référentiels `200`; writes `405`. | D11, D16 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_parametres` refuses to run when `DEBUG` is off. | D21 |
| E2 | It creates valid rows: 25, 65 and 30 today; 4 children in 2019 and 6 today. A second run creates nothing and writes no audit entry; its entries show no author. | D21 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The "Référentiels" page has a ninth tab "Paramètres", after "Banques". | D18 |
| F2 | The tab shows the four keys in order with their value and unit and dates; a key with no value shows "Non renseigné". | D19 |
| F3 | It loads today's values, reloads when "Paramètres au" changes, and shows loading, empty and error states. | D19 |
| F4 | The tab and its date survive navigation, apart from the other tabs; the tab offers no button that changes data. | D20 |
| F5 | The client key list matches the backend's. | D2, D20 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_parametres
```

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. Open "Référentiels", tab "Paramètres": the four parameters in
   order, "25 ans", "6 enfants", "65 ans", "30 ans".
2. Set "Paramètres au" to a date in 2019: the maximum is "4 enfants". Set it to a date before 2015:
   every row shows "Non renseigné". Switch to "Banques": its date is still today. Go to the
   dashboard and back: the tab and its date are kept.
3. In `/admin/`: check the list and its filters. Submit (without saving) a retirement age of 650,
   then a second open value for the child age limit: the first is refused next to "Valeur" with
   the allowed range, the second at the top. Open an existing row: the key is read-only. There is
   no delete button or action.
4. Sign in as `demo.remuneration`, then `demo.auditeur`: the tab opens read-only; the parameter
   admin pages are refused.

Saving rows by hand in the admin, and their audit entries, are covered by the automated tests
(A1, P1, P2); they are not repeated on the development database, whose audit log keeps every
write.

Also check: French text with correct accents (labels, admin labels and messages); dates as
`dd/mm/yyyy`; at 375 px the table scrolls inside its card and the page does not scroll sideways;
no JavaScript error in the console beyond the `401` of the sign-in check.

## 4. Security checks

- As `demo.carriere`, a `POST` to `/api/referentiels/parametres/` answers `405`.
- An account in no group gets `403` on the endpoint.
- In `psql`, inserting a value with an unknown key, or a retirement age of 650, fails with a check
  constraint, and a second open value for the same key fails with the exclusion constraint.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_parametre'` returns nothing.

## 5. User guide

- `docs/user-guide.md` has a "Paramètres" subsection with short steps and screenshots; the tab
  count and "Who changes the reference data" mention the parameters.
- The screenshots were taken by `docs/capture_screenshots.py`; every image path exists and is
  non-empty, and every screenshot in `docs/screenshots/` is used.
- `docs/user-guide.html` has been rebuilt and shows the new subsection.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope slipped in: no alert delays, no pay scales, no rule applying
      a parameter, no text or decimal values, no edit form in the app, no real value in a
      migration.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `Q34` is in `docs/questions-ouvertes.md`. Neither its answer nor `Q1`'s is required to
      merge.
- [ ] `tech-stack.md` names the general parameters in the `referentiels` lines.
- [ ] **1.8 General parameters** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
