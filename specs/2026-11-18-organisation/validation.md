# Organisation — validation

How to know phase 1.1 is done and `feature/organisation` can be merged. All parts must pass:
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

This phase adds the `referentiels` migrations (the `btree_gist` extension, sites, units). They
must apply on an empty database and on the current development database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL.

### Structure and constraints

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A direction without parent, and a département, service or bureau with a parent, are accepted; a direction with a parent, or another unit without one, is refused by the database. | D3, D13 |
| S2 | A parent of the same or a lower level is refused; a skipped level (service under a direction) is accepted. | D2 |
| S3 | A unit cannot be its own parent; a closing date on or before the opening date is refused. | D13 |
| S4 | Codes are saved in capitals; two units with the same code and overlapping periods are refused by the database; the same code on consecutive periods is accepted. | D4, D9 |
| S5 | A second open head office, and a duplicate site code, are refused by the database. | D6 |
| S6 | Deleting a referenced site or parent unit is refused. | D12, D13 |

### History

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | A unit is open from its opening date included to its closing date excluded; `ouvertes(date)` returns exactly those. | D7 |
| H2 | Changing a unit's type, parent or site is refused, through `full_clean()` and through `save()`; its code, name and dates can be corrected. | D8, D14 |
| H3 | A unit cannot open before its parent nor stay open after it; closing a parent with a child still open after that date is refused. | D10 |
| H4 | A unit cannot be created at a closed site; closing a site that still hosts an open unit is refused. | D11 |
| H5 | A restructuring (close a service, open its successor with the same code on the same date) succeeds, and the tree at the earlier date still shows the old service. | D7 to D9 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| L1 | Creating, renaming and closing a unit or a site each write one entry, module `referentiels`, label `CODE — Nom`, with the editor as author in admin. | D19 |
| L2 | The demo command's rows are logged with no author; a second run writes nothing. | D28, D29 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière hold view, add and change on both tables; no other group holds them; nobody holds delete. | D12, D16 |
| A2 | The group setup grants them on a fresh database and adds nothing on a second run. | D18 |
| A3 | In Django admin, a Gestion de carrière staff account creates and changes units and sites, sees rule errors next to the field, sees type, parent and site read-only on an existing unit, and cannot delete. | D8, D14, D16 |
| A4 | `create_demo_users` ticks "Statut équipe" for exactly the demo accounts of the three editing groups and the administrator. | D17 |
| A5 | Both endpoints answer `401` anonymous, `403` without `access_referentiels`, `200` for every profile that has it. | D15, D23 |
| A6 | `unites` returns the units open today by default, those open on `?date=`, all with `?toutes=1`, with the fields of D22; an invalid date answers `400` on `date`. | D20, D22, D23 |
| A7 | `sites` returns open sites by default and all with `?toutes=1`. | D21 |
| A8 | Writes on both endpoints answer `405`. | D12, D22 |
| A9 | The number of queries of `unites` does not depend on the number of units. | D20 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_organisation` refuses to run with `DEBUG` off. | D28 |
| E2 | It creates the structure of D28, every unit passing the model rules, and a second run creates nothing. | D28 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | `/referentiels` shows the page to holders of `access_referentiels`, "Accès refusé" to others; the placeholder is gone. | D24 |
| F2 | "Organisation" shows the tree of today's units with the columns of D25; changing the date reloads the tree at that date. | D25 |
| F3 | The text filter keeps the matching units and their ancestors; expand all and collapse all work. | D25 |
| F4 | "Sites" lists open sites, and closed ones when asked. | D26 |
| F5 | The tab, date and filters survive leaving and coming back. | D27 |
| F6 | The screen offers no action that changes data. | D27 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_users && uv run python manage.py create_demo_organisation
```

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. Open "Référentiels": the "Organisation" tab shows the demo tree,
   directions at the root, with codes, types and sites. Expand all, collapse all, filter on
   "Formation": the service appears with its direction.
2. Set "Organisation au" to a date before the demo restructuring: the closed unit appears and its
   successor does not. Set it back to today.
3. Open the "Sites" tab: the head office and the provincial sites. Go to the dashboard and back:
   the tab, date and filter are as you left them.
4. In `/admin/`, still as `demo.carriere`: create a bureau under a service of the DRH, at the
   head office, opening today. Rename it. Then try:
   - a bureau with a direction as parent: accepted (skipped level);
   - a service under a bureau: refused, message next to "parent";
   - a unit opening before its parent: refused, message next to "date d'ouverture";
   - changing the parent of an existing unit: the field is read-only;
   - deleting a unit: no delete button or action.
5. Close the new bureau as of tomorrow. On the screen, today it is still in the tree; set the date
   to tomorrow: it is gone.
6. Sign in as `demo.admin`. In "Journal d'audit", filter on module "Référentiels": the creation,
   rename and closing of the bureau are listed with `demo.carriere` as author and the label
   `CODE — Nom`; the demo data entries show "Système".
7. Sign in as `demo.remuneration`: "Référentiels" opens read-only; `/admin/` does not let the
   account in.
8. Sign in as `demo.auditeur`: "Référentiels" opens read-only.

Also check:

- Text is in French with correct accents: tabs, column titles, unit types, admin messages.
- Dates are shown as `dd/mm/yyyy`.
- The narrow layout (below 640 px) shows a usable tree: it scrolls inside its card, the toolbar
  wraps, and the page itself does not scroll sideways.
- No JavaScript errors in the browser console.

## 4. Security checks

- The API refuses writes whatever the frontend shows: as `demo.carriere`, a `POST` to
  `/api/referentiels/unites/` answers `405` (editing goes through admin).
- A profile without `access_referentiels` (none today; test with an account in no group) gets
  `403` on both endpoints.
- In `psql`, inserting a unit with a code already used by an open unit over the same period fails
  with the exclusion constraint.
- No delete permission exists on the two tables: `SELECT codename FROM auth_permission WHERE
  codename LIKE 'delete_%' AND content_type_id IN (...)` returns nothing for `referentiels`.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope in `requirements.md` slipped in: no unit head, no agent
      assignment, no edit form in the app, no real organigramme in a migration.
- [ ] Any decision changed during implementation is recorded in `requirements.md` under
      "Found during implementation".
- [ ] `Q27` is in `docs/questions-ouvertes.md`.
- [ ] `tech-stack.md` lists `referentiels` and describes exclusion constraints with `btree_gist`.
- [ ] **1.1 Organisation** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
