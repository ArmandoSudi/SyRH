# Document types — validation

How to know phase 1.5 is done and `feature/document-types` can be merged. All parts must pass:
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

The migrations `0006_typedocument` and `0007_piecerequise` must apply on an empty database and on
the current development database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure and constraints

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A type has a code, a name and an opening date; a requirement has an event, a type, the mandatory flag and an opening date; all are required. | D1, D4 |
| S2 | A type's code is saved in capitals; two types with the same code over overlapping periods are refused by the database, on consecutive periods accepted; the same name is accepted. | D5, D11 |
| S3 | An event requiring the same type twice over overlapping periods is refused by the database; the same type for two events is accepted. | D5, D11 |
| S4 | An event outside the list of D2, and a closing date on or before the opening date on either table, are refused by the database; reversed dates are reported by `full_clean()` on `date_fermeture`, with no database error. | D2, D11, D12 |
| S5 | Deleting a type that a requirement points to is refused. | D10, D11 |
| S6 | Types sort by name; requirements by the event order of D2, then mandatory first, then the type's name. | D6 |

### History

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | Both tables follow the opening-included, closing-excluded rule in `ouvertes(date)`. | D7 |
| H2 | A requirement cannot open before its type nor stay open after it; a type cannot be closed while a requirement stays open after that date. Messages are in French, on the field. | D8, D12 |
| H3 | A requirement's event and type cannot change after creation, through `full_clean()` and `save()`; its flag and dates can be corrected. The classification models keep their behaviour. | D9, D12 |
| H4 | Making a document optional by closing the requirement and opening a new one keeps the old rule at earlier dates. | D7, D9 |
| H5 | There is no delete permission on either table. | D10 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating, correcting and closing a type and a requirement write audit entries under module `referentiels`, labelled `CODE — Nom` and `Événement — CODE (obligatoire)` or `(facultative)`, with their author. | D17 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, the three editor groups have view, add and change on both tables; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D14, D15 |
| P2 | The admin lists, filters and searches both tables; the type is chosen through autocomplete; the event and type are read-only when changing a requirement; rule errors show next to their field and constraint errors at the top. | D16 |
| P3 | Both endpoints return the rows open today by default, on `?date=`, or all with `?toutes=1`, in the order of D6, with the fields of D19; an invalid `date` answers `400` on that field; the requirements list runs a constant number of queries. | D18, D19 |
| P4 | Anonymous `401`; no group `403`; every profile with Référentiels `200`; writes `405`. | D13, D18 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_pieces` refuses to run when `DEBUG` is off. | D23 |
| E2 | It creates valid rows: hiring requires three mandatory documents today and four in 2023; "Sortie" requires nothing; the decision serves several events; both mandatory and optional requirements exist. A second run creates nothing and writes no audit entry; its entries show no author. | D23 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | The "Référentiels" page has a sixth tab "Pièces justificatives", after "Types de contrat". | D20 |
| F2 | The tab shows every event kind of D2 in order, with its number of documents; under each, its documents with code, name, "Obligatoire" or "Facultative" and dates; an event with none shows "Aucune pièce exigée". | D21 |
| F3 | It loads both lists for today, reloads when "Pièces au" changes, and shows loading, empty and error states. | D21 |
| F4 | The text filter matches a document's code or name, or an event's label, keeping the event row; expand all and collapse all work. | D21, D22 |
| F5 | The tab, its date, filter and expanded rows survive navigation, apart from the other tabs; the tab offers no button that changes data. | D22 |
| F6 | The client list of event kinds matches the backend's. | D2 |

## 3. Manual walkthrough

Set up first (the other demo commands must have run once):

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_pieces
```

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. Open "Référentiels", tab "Pièces justificatives": the fourteen
   event kinds in the agent's life order, each with its count. Expand all: "Engagement" lists the
   signed contract, the identity document and the diploma, all "Obligatoire"; "Sortie" shows
   "Aucune pièce exigée". Filter on "décision": every career event that requires it stays, with
   the document under it.
2. Set "Pièces au" to a date in 2023: "Engagement" also requires the criminal record extract.
   Switch to "Types de contrat": its date is still today. Go to the dashboard and back: the tab,
   its date, filter and expanded rows are kept.
3. In `/admin/`: check both lists, their filters and search, and the type autocomplete on a new
   requirement. Submit (without saving) a requirement that opens before its type, then one that
   repeats an open requirement: the first is refused next to "Date d'ouverture", the second at the
   top. Open an existing requirement: the event and the type are read-only. There is no delete
   button or action.
4. Sign in as `demo.personnel`, then `demo.auditeur`: the tab opens read-only; `/admin/` does not
   let them in.

Saving rows by hand in the admin, and their audit entries, are covered by the automated tests
(A1, P1, P2); they are not repeated on the development database, whose audit log keeps every
write.

Also check: French text with correct accents (event labels, tags, admin labels and messages);
dates as `dd/mm/yyyy`; at 375 px the tree scrolls inside its card, the toolbar wraps and the page
does not scroll sideways; no JavaScript error in the console beyond the `401` of the sign-in check.

## 4. Security checks

- As `demo.carriere`, a `POST` to `/api/referentiels/types-document/` and to
  `/api/referentiels/pieces-requises/` answers `405`.
- An account in no group gets `403` on both endpoints.
- In `psql`, inserting a requirement for an event outside the list fails with the check
  constraint, and a second open requirement for the same event and type fails with the exclusion
  constraint.
- `SELECT codename FROM auth_permission WHERE codename IN ('delete_typedocument',
  'delete_piecerequise')` returns nothing.

## 5. User guide

- `docs/user-guide.md` has a "Pièces justificatives" subsection with short steps and screenshots;
  the tab count and "Who changes the reference data" mention the document types.
- The screenshots were taken by `docs/capture_screenshots.py`; every image path exists and is
  non-empty, and every screenshot in `docs/screenshots/` is used.
- `docs/user-guide.html` has been rebuilt and shows the new subsection.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope slipped in: no file upload or storage, no attachment to an
      event, no validation blocking, no event model, no absence type or exit reason, no edit form
      in the app, no real list in a migration.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `Q31` is in `docs/questions-ouvertes.md`. Its answer is **not** required to merge.
- [ ] `tech-stack.md` names the document types in the `referentiels` lines.
- [ ] **1.5 Document types** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
