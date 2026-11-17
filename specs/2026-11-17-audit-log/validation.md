# Audit log — validation

How to know phase 0.6 is done and `feature/audit-log` can be merged. All parts must pass: quality
gates, automated tests for every acceptance criterion, the manual walkthrough and the security
checks.

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

This phase adds migrations in `audit` (the table and its trigger) and in `accounts` (the
`access_audit` permission). Both must apply on an empty database and on the current development
database, and the `audit` migration must reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL.

### Capture

| # | Criterion | Decision |
| --- | --- | --- |
| C1 | Creating, modifying and deleting a `BaseModel` row each write one entry with date, author, action, table, row id, label, module and changed fields. | D2 to D4, D10 |
| C2 | A modification stores the old and new value of each changed field, with its French label; a creation only new values; a deletion only old values. | D4 |
| C3 | Foreign keys are stored as id and label, dates and decimals as text, many-to-many changes as labels added and removed. | D5 |
| C4 | The base fields and `last_login` never appear as changes; signing in writes no entry. | D6 |
| C5 | A password change is logged with masked values; no entry contains a password hash. | D7 |
| C6 | A save with no change writes no entry. | D8 |
| C7 | A rolled-back change leaves no entry. | D10 |
| C8 | The author is the request user through `AuthorMixin` and `BaseModelAdmin`, deletion included; a script write without author has an empty author. | D11 |
| C9 | `QuerySet.update()` and `QuerySet.delete()` raise on `BaseModel` tables; `update_audited()` writes one entry per row. | D13 |
| C10 | In Django admin, changing a user's fields or groups, or a group's permissions, writes one entry with the admin as author and the scope `comptes`. | D15, D21 |
| C11 | `sync_groups()` logs the permissions it adds with an empty author, and nothing on a second run. | D15 |
| C12 | A `BaseModel` subclass without a module, or with an unknown one, fails the system check. | D22 |

### Unalterable log

| # | Criterion | Decision |
| --- | --- | --- |
| U1 | Saving an existing entry, `QuerySet.update()` and `delete()` on entries all fail. | D16 |
| U2 | Raw SQL `UPDATE` and `DELETE` on the audit table raise a database error. | D16 |
| U3 | Deleting a user who authored an entry is refused. | D18 |
| U4 | The audit table is not in Django admin. | D19 |

### Access and API

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | `access_audit` exists, labelled "Accès au module Journal d'audit", and belongs to exactly Auditeur, Direction RH and Administrateur système. | D20 |
| A2 | The list answers `401` anonymous and `403` without `access_audit`. | D26 |
| A3 | The Auditeur sees Agents, Référentiels and `comptes` entries, never Paie or Social; Direction RH sees all; the Administrateur système sees Référentiels and `comptes` only. | D21 |
| A4 | A hidden entry answers `404` on detail. | D23 |
| A5 | Every filter works alone and combined; an unknown module or action answers `400` for that field; results are newest first, 50 per page. | D24 |
| A6 | Writes on both endpoints answer `405`. | D25 |
| A7 | The author is returned as id and name, or "Système"; the table as its French label. | D27 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | `/audit` and its menu entry are shown to the three profiles only; others get "Accès refusé". | D20, D29 |
| F2 | The table loads one page at a time from the API and shows the columns of D30. | D30 |
| F3 | The module filter lists only the reader's modules plus "Comptes". | D21, D30 |
| F4 | The side panel shows each changed field with old and new value; masked values show "••••••". | D31 |
| F5 | Filters survive leaving and coming back to the screen. | D32 |
| F6 | The screen offers no action that changes data. | D32 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_users
```

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.admin`. "Journal d'audit" appears under Administration. Open it: the entries
   written by the group setup after `migrate` are listed, author "Système".
2. In `/admin/`, still as `demo.admin`, add `demo.formation` to the Social group, then remove it.
   Change the first name of `demo.carriere`. Change the password of `demo.social`.
3. Back on the screen, refresh: three new entries, newest first, author `demo.admin`, scope
   "Comptes". Open each: the membership change shows the group added then removed; the first name
   shows old and new value; the password shows "••••••" on both sides.
4. Filter by author "admin", then by action "Modification", then by today's period. The results
   match; clear the filters.
5. Go to the dashboard and back: the filters you had set are still there.
6. Sign in as `demo.auditeur`: the same account entries are visible; the module filter has no
   Paie or Social.
7. Sign in as `demo.direction`: the entries are visible; the module filter lists every HR module.
8. Sign in as `demo.carriere`: no "Journal d'audit" in the menu; `/audit` shows "Accès refusé".
9. Sign in and out as `demo.remuneration`: no new entry appears for the sign-in.

Also check:

- Text is in French with correct accents: menu, column titles, actions, field labels.
- Dates and times are shown in Kinshasa time.
- The narrow layout (below 1000 px) shows the menu icon and a usable table.
- No JavaScript errors in the browser console.

## 4. Security checks

- In `psql`, as the application's database user, `UPDATE audit_entreeaudit SET ...` and
  `DELETE FROM audit_entreeaudit ...` both fail with the trigger's error (U2).
- No entry anywhere contains a password hash: `SELECT count(*) FROM audit_entreeaudit WHERE
  changements::text LIKE '%pbkdf2%'` returns 0 after step 2 of the walkthrough.
- The API filters by module on its own: as `demo.auditeur`, requesting `?module=paie` returns no
  entry (or `400`), and the detail of a Paie entry answers `404`, whatever the frontend shows.
- No middleware, thread-local or signal was added to find the author:
  `git diff main -- backend/config/settings.py` shows no `MIDDLEWARE` change (D9).
- Nothing from the log is written to `localStorage` or `sessionStorage`.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope in `requirements.md` slipped in: no sign-in entries, no
      export, no purge, no history tab on records.
- [ ] Any decision changed during implementation is recorded in `requirements.md` under
      "Found during implementation".
- [ ] `tech-stack.md` describes `apps.audit`, how capture works and the `module` attribute, and
      no longer lists the audit log as undecided.
- [ ] **0.6 Audit log** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
