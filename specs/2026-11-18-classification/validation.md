# Classification — validation

How to know phase 1.2 is done and `feature/classification` can be merged. All parts must pass:
quality gates, automated tests for every acceptance criterion, the manual walkthrough and the
security checks.

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

This phase adds `referentiels` migrations for the three tables. They must apply on an empty
database and on the current development database (with the organisation already in it), and
reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. **Every
database constraint is also proven by a test that bypasses the model rules** (`_base_manager` or
raw SQL), so the database refuses the invalid row on its own. **(asked)**

### Structure and constraints

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A grade belongs to one catégorie and an échelon to one grade; both foreign keys are required. | D1 |
| S2 | Codes are saved in capitals; two catégories, or two grades (even in different catégories), with the same code and overlapping periods are refused by the database; the same code on consecutive periods is accepted. | D2, D3, D12 |
| S3 | Two catégories open at the same time with the same rank, two grades of one catégorie open at the same time with the same rank, and two échelons of one grade open at the same time with the same number, are refused by the database. Grades of different catégories may share a rank. | D6, D12 |
| S4 | A rank or échelon number of zero or below, and a closing date on or before the opening date, are refused by the database. | D15 |
| S5 | A gap in échelon numbers is accepted. | D5 |
| S6 | Deleting a referenced catégorie or grade is refused. | D14, D15 |

### Order

| # | Criterion | Decision |
| --- | --- | --- |
| O1 | Every grade of a higher-ranked catégorie sorts above every grade of a lower-ranked one; within a catégorie, grades sort by rank; échelons sort by number. | D7, D8 |

### History

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | A row is open from its opening date included to its closing date excluded; `ouvertes(date)` returns exactly those, for each of the three models. | D9 |
| H2 | Changing a grade's catégorie or an échelon's grade is refused, through `full_clean()` and through `save()`; codes, names, ranks, numbers and dates can be corrected. | D11, D16 |
| H3 | A grade cannot open before its catégorie nor stay open after it; an échelon likewise within its grade. Closing a catégorie or a grade with a child still open after that date is refused. | D10, D13 |
| H4 | An échelon can be opened or closed on its own while its grade stays open. | D10 |
| H5 | A reform (close a grade's échelons and the grade, open a successor with the same code and new échelons on the same date) succeeds, and the grid at the earlier date still shows the old grade with its échelons. | D9, D12, D13 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| L1 | Creating, correcting and closing a catégorie, a grade or an échelon each write one entry, module `referentiels`, label `CODE — Nom` or `GRADE — Échelon N`, with the editor as author in admin. | D23 |
| L2 | The demo command's rows are logged with no author; a second run writes nothing. | D31, D32 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière hold view, add and change on the three tables; no other group holds them; nobody holds delete. | D14, D18 |
| A2 | The group setup grants them on a fresh database and adds nothing on a second run. | D19 |
| A3 | In Django admin, a Gestion de carrière staff account creates and corrects catégories, grades and échelons, sees rule errors (at the top for constraints, next to the field for model rules), sees the parent read-only on an existing row, and cannot delete. | D11, D16, D21 |
| A4 | The three endpoints answer `401` anonymous, `403` without `access_referentiels`, `200` for every profile that has it. | D17, D26 |
| A5 | Each endpoint returns the rows open today by default, those open on `?date=`, all with `?toutes=1`, with the fields and order of D25; an invalid date answers `400` on `date`. | D24 to D26 |
| A6 | Writes on the three endpoints answer `405`. | D14, D25 |
| A7 | The number of queries of each endpoint does not depend on the number of rows. | D24 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_classification` refuses to run with `DEBUG` off. | D31 |
| E2 | It creates the grid of D31, every row passing the model rules, including the reformed grade and its successor, and a second run creates nothing. | D31 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The "Référentiels" page shows a third tab "Classification" to holders of `access_referentiels`; "Organisation" and "Sites" behave as before. | D27 |
| F2 | The tab shows today's grid as a tree catégorie → grade → échelon with the columns of D28, in the order of D7 and D8; changing "Classification au" reloads the grid at that date. | D28 |
| F3 | The text filter keeps the matching rows and their ancestors; expand all and collapse all work. | D28, D29 |
| F4 | The tab, classification date and filter survive leaving and coming back; changing the classification date does not change the organisation date, and the reverse. | D30 |
| F5 | The tab offers no action that changes data. | D30 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_users && uv run python manage.py create_demo_organisation && uv run python manage.py create_demo_classification
```

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. Open "Référentiels", tab "Classification": four catégories,
   highest rank first, each with its grades and échelons. Expand all, collapse all, filter on a
   grade code: the grade appears with its catégorie and échelons.
2. Set "Classification au" to a date before the demo reform: the old grade appears with its
   échelons and its successor does not. Switch to "Organisation": its date is still today. Go to
   the dashboard and back: the "Classification" tab, its date and filter are as you left them.
3. In `/admin/`, still as `demo.carriere`: add a grade to a catégorie, opening today, then three
   échelons for it. Correct the grade's name. Then try:
   - a second grade in another catégorie with the same code: refused;
   - a grade with the same rank as another of its catégorie: refused;
   - an échelon opening before its grade: refused, message next to "date d'ouverture";
   - échelons 1, 2 and 4 (a gap): accepted;
   - changing the catégorie of an existing grade: the field is read-only;
   - closing the grade while its échelons are open: refused;
   - deleting any row: no delete button or action.
4. Close the échelons, then the grade, as of tomorrow. On the screen, today they are still in the
   tree; set the date to tomorrow: they are gone.
5. Sign in as `demo.admin`. In "Journal d'audit", filter on module "Référentiels": the creation,
   correction and closing of the grade and its échelons are listed with `demo.carriere` as author
   and the labels `CODE — Nom` and `GRADE — Échelon N`; the demo data entries show "Système".
6. Sign in as `demo.remuneration`: the "Classification" tab opens read-only; `/admin/` does not
   let the account in.
7. Sign in as `demo.auditeur`: the "Classification" tab opens read-only.

Also check:

- Text is in French with correct accents: tab, column titles, levels (Catégorie, Grade,
  Échelon), admin labels and messages.
- Dates are shown as `dd/mm/yyyy`.
- The narrow layout (below 640 px) shows a usable tree: it scrolls inside its card, the toolbar
  wraps, and the page itself does not scroll sideways.
- No JavaScript errors in the browser console.

## 4. Security checks

- The API refuses writes whatever the frontend shows: as `demo.carriere`, a `POST` to each of
  `/api/referentiels/categories/`, `grades/` and `echelons/` answers `405`.
- An account in no group gets `403` on the three endpoints.
- In `psql`, inserting a grade with a code already used by an open grade over the same period
  fails with the exclusion constraint, and so does an échelon number already open in the same
  grade.
- No delete permission exists on the three tables: `SELECT codename FROM auth_permission WHERE
  codename LIKE 'delete_%' AND content_type_id IN (...)` returns nothing for `categorie`, `grade`
  and `echelon`.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope in `requirements.md` slipped in: no pay amounts, no
      fonctions, no agent position, no promotion check, no edit form in the app, no real grid in a
      migration.
- [ ] Any decision changed during implementation is recorded in `requirements.md` under
      "Found during implementation".
- [ ] `Q28` is in `docs/questions-ouvertes.md`. Its answer is **not** required to merge.
      **(asked)**
- [ ] `tech-stack.md` names the classification in the `referentiels` line.
- [ ] **1.2 Classification** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
