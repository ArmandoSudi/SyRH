# Fonctions — validation

How to know phase 1.3 is done and `feature/fonctions` can be merged. All parts must pass:
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

The migration `0004_fonction` must apply on an empty database and on the current development
database (organisation and classification already in it), and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model (`_base_manager` or raw SQL), so the
database refuses the invalid row on its own.

### Structure and constraints

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A fonction has a code, a name, a nature and an opening date; all are required. | D1, D2 |
| S2 | The code is saved in capitals, through `save()` and through `full_clean()`. | D9 |
| S3 | Two fonctions with the same code and overlapping periods are refused by the database; the same code on consecutive periods is accepted. Two fonctions with the same name are accepted. | D3, D8 |
| S4 | A nature other than `responsabilite` or `execution`, and a closing date on or before the opening date, are refused by the database. | D8 |
| S5 | Fonctions sort Responsabilité first, then by name. | D4 |

### History

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | A fonction is open from its opening date included to its closing date excluded; `ouvertes(date)` returns exactly those. | D5 |
| H2 | A rename (close the fonction, open a successor with the same code on the same day) succeeds, and the list at the earlier date still shows the old name. | D5, D6 |
| H3 | There is no delete permission on `fonction`. | D7 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating, correcting and closing a fonction each write an audit entry under module `referentiels`, labelled `CODE — Nom`, with the author who made the change. | D14 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière have view, add and change on `fonction`; no other group has add or change; nobody has delete. A hand-made change to the groups survives the next `migrate`. | D11, D12 |
| P2 | The admin lists fonctions with code, name, nature and dates; filters on nature and "ouvert aujourd'hui"; searches code and name. | D13 |
| P3 | `GET /api/referentiels/fonctions/` returns the fonctions open today by default, on `?date=`, or all with `?toutes=1`, ordered per D4, with the fields of D16. An invalid `date` answers `400` on that field. | D15, D16, D17 |
| P4 | Anonymous `401`; an account in no group `403`; every profile with Référentiels `200`. `POST`, `PUT`, `PATCH`, `DELETE` answer `405`. | D10, D15, D17 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_fonctions` refuses to run when `DEBUG` is off. | D21 |
| E2 | It creates a valid list with both natures and one renamed fonction with its successor; a second run creates nothing and writes no audit entry; its entries show no author. | D21, D22 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The "Référentiels" page has a fourth tab "Fonctions", after "Classification". | D18 |
| F2 | The tab loads the fonctions for today, reloads when "Fonctions au" changes, and shows loading, empty and error states. | D19 |
| F3 | The nature shows as a Tag ("Responsabilité", "Exécution"); the text filter matches code and name. | D19 |
| F4 | The tab, its date and filter survive navigation; changing the fonctions date leaves the organisation and classification dates alone. | D20 |
| F5 | The tab offers no button that changes data. | D20 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_users && uv run python manage.py create_demo_organisation && uv run python manage.py create_demo_classification && uv run python manage.py create_demo_fonctions
```

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. Open "Référentiels", tab "Fonctions": posts of responsibility
   first, then execution posts, each alphabetical, with a Tag for the nature. Filter on part of a
   code, then part of a name: only the matches remain.
2. Set "Fonctions au" to a date before the demo rename: the old name appears and its successor
   does not. Switch to "Classification": its date is still today. Go to the dashboard and back:
   the "Fonctions" tab, its date and filter are as you left them.
3. In `/admin/`, still as `demo.carriere`: add a fonction opening today, with a code in lower
   case; it is saved in capitals. Correct its name. Then try:
   - a second fonction with the same code, open at the same time: refused;
   - a closing date before the opening date: refused, message next to the field;
   - a fonction with the same name as another: accepted;
   - deleting any fonction: no delete button or action.
4. Close the new fonction as of tomorrow. On the screen, today it is still listed; set the date
   to tomorrow: it is gone.
5. Sign in as `demo.admin`. In "Journal d'audit", filter on module "Référentiels": the creation,
   correction and closing of the fonction are listed with `demo.carriere` as author and the
   label `CODE — Nom`; the demo data entries show "Système".
6. Sign in as `demo.remuneration`, then `demo.auditeur`: the "Fonctions" tab opens read-only;
   `/admin/` does not let them in.

Also check:

- Text is in French with correct accents: tab, column titles, natures, admin labels and messages.
- Dates are shown as `dd/mm/yyyy`.
- At 375 px wide the tab is usable: the table scrolls inside its card, the toolbar wraps, and the
  page does not scroll sideways.
- No JavaScript errors in the browser console.

## 4. Security checks

- The API refuses writes whatever the frontend shows: as `demo.carriere`, a `POST` to
  `/api/referentiels/fonctions/` answers `405`.
- An account in no group gets `403` on the endpoint.
- In `psql`, inserting a fonction with the code of an open fonction over the same period fails
  with the exclusion constraint, and a nature outside the two values fails with the check
  constraint.
- No delete permission exists on the table: `SELECT codename FROM auth_permission WHERE codename
  = 'delete_fonction'` returns nothing.

## 5. User guide

- `docs/user-guide.md` has a "Fonctions" subsection under "Reference data" with short steps and
  at least one screenshot of the tab; the tab list and "Who changes the reference data" mention
  the fonctions.
- The screenshots were taken by `docs/capture_screenshots.py` against the demo data, and every
  image path in the guide exists and is non-empty.
- `docs/user-guide.html` has been rebuilt with `docs/build_user_guide.py` and shows the new
  subsection.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope in `requirements.md` slipped in: no agent position, no link
      between a fonction and a unit, no minimum grade, no pay by fonction, no edit form in the
      app, no real list in a migration.
- [ ] Any decision changed during implementation is recorded in `requirements.md` under
      "Found during implementation".
- [ ] `Q29` is in `docs/questions-ouvertes.md`. Its answer is **not** required to merge.
- [ ] `tech-stack.md` names the fonctions in the `referentiels` lines.
- [ ] **1.3 Fonctions** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
