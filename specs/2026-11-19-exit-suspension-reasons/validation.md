# Exit and suspension reasons — validation

How to know phase 1.6 is done and `feature/exit-suspension-reasons` can be merged. All parts must
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

The migrations `0008_motifsortie` and `0009_typesuspension` must apply on an empty database and on
the current development database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure and constraints

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A reason has a code, a name, a document type and an opening date; a suspension type has a code, a name, a document type, the seniority flag and an opening date; all are required. Duration and renewals are optional. | D1, D3 |
| S2 | Codes are saved in capitals; two rows of the same table with the same code over overlapping periods are refused by the database, on consecutive periods accepted; the same name is accepted. | D5, D11 |
| S3 | A reason that is both a retirement and a death is refused by the database, and by `full_clean()` on `deces`. | D2, D11, D12 |
| S4 | A maximum duration of zero months is refused by the database; zero renewals and blank values are accepted. | D3, D11 |
| S5 | A closing date on or before the opening date is refused by the database on both tables; reversed dates are reported by `full_clean()` on `date_fermeture`, with no database error. | D11, D12 |
| S6 | Deleting a document type that a reason or a suspension type points to is refused. | D10, D11 |
| S7 | Both tables sort by name. | D6 |

### History

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | Both tables follow the opening-included, closing-excluded rule in `ouverts(date)`. | D7 |
| H2 | A reason or suspension type cannot open before its document type nor stay open after it; a document type cannot be closed while a reason or suspension type stays open after that date. Messages are in French, on the field. The checks of `PieceRequise` and the classification keep their behaviour. | D9, D12 |
| H3 | Changing a reason's document by closing it and opening a successor keeps the old document at earlier dates; a typing error can be corrected in place. | D8 |
| H4 | There is no delete permission on either table. | D10 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating, correcting and closing a reason and a suspension type write audit entries under module `referentiels`, labelled `CODE — Nom`, with their author. | D17 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, the three editor groups have view, add and change on both tables; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D14, D15 |
| P2 | The admin lists, filters and searches both tables; the document is chosen through autocomplete; rule errors show next to their field and constraint errors at the top. | D16 |
| P3 | Both endpoints return the rows open today by default, on `?date=`, or all with `?toutes=1`, by name, with the fields of D19 (blank values as `null`); an invalid `date` answers `400` on that field; each list runs a constant number of queries. | D18, D19 |
| P4 | Anonymous `401`; no group `403`; every profile with Référentiels `200`; writes `405`. | D13, D18 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_sorties` refuses to run when `DEBUG` is off. | D23 |
| E2 | It creates valid rows: two retirement reasons, one death, one resignation with neither flag, each with its document; disponibilité 24 months, 1 renewal, not counted; détachement counted, duration and renewals blank; both suspensions require the decision. A second run creates nothing and writes no audit entry; its entries show no author. | D23 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The "Référentiels" page has a seventh tab "Sorties et suspensions", after "Pièces justificatives". | D20 |
| F2 | The tab shows "Motifs de sortie" with code, name, document, "Retraite" or "Décès" tag and dates, and "Positions de suspension" with code, name, document, the seniority tag, "24 mois" or "Fixée par la décision", "1" or "Sans limite", and dates. | D21 |
| F3 | It loads both lists for today, reloads both when "Au" changes, and shows loading, empty and error states for each table. | D21 |
| F4 | The text filter matches a row's code, name or document, in both tables. | D21, D22 |
| F5 | The tab, its date and filter survive navigation, apart from the other tabs; the tab offers no button that changes data. | D22 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_sorties
```

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. Open "Référentiels", tab "Sorties et suspensions": four exit
   reasons by name, the two retirements tagged "Retraite" and the death tagged "Décès", each with
   its document; two suspension positions, "Mise en disponibilité" with "Non", "24 mois", "1",
   and "Détachement" with "Oui", "Fixée par la décision", "Sans limite". Filter on "décision":
   the retirements and both suspensions stay.
2. Set "Au" to a date before 2015: both tables show their empty state. Switch to "Pièces
   justificatives": its date is still today. Go to the dashboard and back: the tab, its date and
   filter are kept.
3. In `/admin/`: check both lists, their filters and search, and the document autocomplete on a
   new row. Submit (without saving) a reason flagged both retraite and décès, a suspension type
   with 0 months, and a reason whose code is already open: the first is refused next to "Décès",
   the second and third at the top or on their field. Try to close the "Décision" document type
   today: refused, naming the suspension types still open. There is no delete button or action.
4. Sign in as `demo.personnel`, then `demo.auditeur`: the tab opens read-only; `/admin/` does not
   let them in.

Saving rows by hand in the admin, and their audit entries, are covered by the automated tests
(A1, P1, P2); they are not repeated on the development database, whose audit log keeps every
write.

Also check: French text with correct accents (labels, tags, admin labels and messages); dates as
`dd/mm/yyyy`; at 375 px the tables scroll inside their cards, the toolbar wraps and the page does
not scroll sideways; no JavaScript error in the console beyond the `401` of the sign-in check.

## 4. Security checks

- As `demo.carriere`, a `POST` to `/api/referentiels/motifs-sortie/` and to
  `/api/referentiels/types-suspension/` answers `405`.
- An account in no group gets `403` on both endpoints.
- In `psql`, inserting a reason with both flags fails with the check constraint, a suspension type
  with 0 months fails with its check constraint, and a second open row with the same code fails
  with the exclusion constraint.
- `SELECT codename FROM auth_permission WHERE codename IN ('delete_motifsortie',
  'delete_typesuspension')` returns nothing.

## 5. User guide

- `docs/user-guide.md` has a "Sorties et suspensions" subsection with short steps and screenshots;
  the tab count and "Who changes the reference data" mention the new lists.
- The screenshots were taken by `docs/capture_screenshots.py`; every image path exists and is
  non-empty, and every screenshot in `docs/screenshots/` is used.
- `docs/user-guide.html` has been rebuilt and shows the new subsection.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope slipped in: no suspension or exit recorded, no renewal
      check, no seniority computation, no retirement thresholds, no notice parameter, no edit form
      in the app, no real list in a migration.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `Q32` is in `docs/questions-ouvertes.md`, and `Q2` and `Q3` note the assumptions applied.
      Their answers are **not** required to merge.
- [ ] `tech-stack.md` names the exit reasons and suspension types in the `referentiels` lines.
- [ ] **1.6 Exit and suspension reasons** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
