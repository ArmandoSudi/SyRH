# Banks — validation

How to know phase 1.7 is done and `feature/banks` can be merged. All parts must pass: quality
gates, automated tests for every acceptance criterion, the manual walkthrough, the security checks
and the user guide update. **(asked)**

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

The migration `0010_banque` must apply on an empty database and on the current development
database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure and constraints

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A bank has a code, a name and an opening date, all required; the SWIFT/BIC is optional. | D1 |
| S2 | The code and the SWIFT/BIC are saved in capitals; two banks with the same code over overlapping periods are refused by the database, on consecutive periods accepted; the same name and the same SWIFT/BIC are accepted. | D2, D4, D9 |
| S3 | A SWIFT/BIC of 8 or 11 characters of the right shape, or empty, is accepted; any other is refused by the database, and by `full_clean()` on `swift` with a French message. | D2, D9, D10 |
| S4 | A closing date on or before the opening date is refused by the database; `full_clean()` reports it on `date_fermeture`, with no database error. | D9, D10 |
| S5 | Banks sort by name. | D5 |

### History

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | The table follows the opening-included, closing-excluded rule in `ouvertes(date)`. | D6 |
| H2 | A merger recorded by closing a bank and opening a successor with the same code keeps the old name at earlier dates. | D7 |
| H3 | There is no delete permission. | D8 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating, correcting and closing a bank write audit entries under module `referentiels`, labelled `CODE — Nom`, with their author. | D15 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, Administrateur système, Rémunération and Chef de service — Rémunération have view, add and change on banks; no other group has add or change, Gestion de carrière included; nobody has delete; a hand-made change survives the next `migrate`; the permissions on the other reference tables are unchanged. | D12, D13 |
| P2 | `create_demo_users` gives the two Rémunération accounts staff status. | D13 |
| P3 | The admin lists, filters and searches banks; a Rémunération account adds one and is its author; rule errors show next to their field and constraint errors at the top; Gestion de carrière gets `403` on the bank pages. | D12, D14 |
| P4 | The endpoint returns the banks open today by default, on `?date=`, or all with `?toutes=1`, by name, with the fields of D17; an invalid `date` answers `400` on that field. | D16, D17 |
| P5 | Anonymous `401`; no group `403`; every profile with Référentiels `200`; writes `405`. | D11, D16 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_banques` refuses to run when `DEBUG` is off. | D21 |
| E2 | It creates valid rows: one bank without SWIFT/BIC; a merged bank whose old and new rows share the code without overlapping; no closed bank in today's list. A second run creates nothing and writes no audit entry; its entries show no author. | D21 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The "Référentiels" page has an eighth tab "Banques", after "Sorties et suspensions". | D18 |
| F2 | The tab shows code, name, SWIFT/BIC ("—" when blank) and dates; it loads today's banks, reloads when "Banques au" changes, and shows loading, empty and error states. | D19 |
| F3 | The text filter matches a bank's code, name or SWIFT/BIC. | D19, D20 |
| F4 | The tab, its date and filter survive navigation, apart from the other tabs; the tab offers no button that changes data. | D20 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_banques
```

and re-run `create_demo_users` so the Rémunération accounts have staff status.

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.remuneration`. Open "Référentiels", tab "Banques": the demo banks by name,
   one with "—" as SWIFT/BIC. Filter on part of a SWIFT/BIC: only that bank stays.
2. Set "Banques au" to a date before the merger: the old bank name shows instead of the new one.
   Switch to "Sorties et suspensions": its date is still today. Go to the dashboard and back: the
   tab, its date and filter are kept.
3. In `/admin/`: check the bank list, its filter and search. Submit (without saving) a bank with
   the SWIFT/BIC `ABC`, then one whose code is already open: the first is refused next to "Code
   SWIFT/BIC", the second at the top. There is no delete button or action. The other reference
   tables are not offered.
4. Sign in as `demo.carriere`: the tab opens read-only, and `/admin/referentiels/banque/` answers
   `403` while the other reference tables still open. Sign in as `demo.auditeur`: the tab opens
   read-only; `/admin/` does not let them in.

Saving rows by hand in the admin, and their audit entries, are covered by the automated tests
(A1, P1, P3); they are not repeated on the development database, whose audit log keeps every
write.

Also check: French text with correct accents (labels, admin labels and messages); dates as
`dd/mm/yyyy`; at 375 px the table scrolls inside its card, the toolbar wraps and the page does not
scroll sideways; no JavaScript error in the console beyond the `401` of the sign-in check.

## 4. Security checks

- As `demo.remuneration`, a `POST` to `/api/referentiels/banques/` answers `405`.
- An account in no group gets `403` on the endpoint.
- In `psql`, inserting a bank with the SWIFT/BIC `abcdcdki` fails with the check constraint, and a
  second open bank with the same code fails with the exclusion constraint.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_banque'` returns nothing.
- `demo.remuneration` still has no add or change permission on any other reference table.

## 5. User guide

- `docs/user-guide.md` has a "Banques" subsection with short steps and screenshots; the tab count
  and "Who changes the reference data" mention the banks and that Rémunération changes them.
- The screenshots were taken by `docs/capture_screenshots.py`; every image path exists and is
  non-empty, and every screenshot in `docs/screenshots/` is used.
- `docs/user-guide.html` has been rebuilt and shows the new subsection.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope slipped in: no transfer file template, no agent account, no
      account number format, no branches, no edit form in the app, no real list in a migration.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `Q33` is in `docs/questions-ouvertes.md`. Neither its answer nor `Q16`'s is required to
      merge.
- [ ] `tech-stack.md` names the banks in the `referentiels` lines.
- [ ] **1.7 Banks** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
