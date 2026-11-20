# Reference data screens — validation

How to know phase 1.9 is done and `feature/reference-data-screens` can be merged. All parts must
pass: quality gates, automated tests for every acceptance criterion, the manual walkthrough with
real saves on a scratch database, the security checks and the user guide update. **(asked)**

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

This phase adds no migration.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL.

### Write API

| # | Criterion | Decision |
| --- | --- | --- |
| W1 | On each of the six endpoints, an editor creates a row (`201`, the saved row returned), corrects one with `PATCH` (`200`), and closes one by setting its closing date. | D3, D9 |
| W2 | `POST /{id}/successeur/` closes the row on `date_effet` and opens a successor from that date, with the old values overridden by the fields sent; the old row keeps its values at earlier dates. | D3, D4 |
| W3 | A successor is refused for a row already closed, and for a `date_effet` on or before the opening date; an invalid successor leaves the old row unchanged. | D4 |
| W4 | Every model rule comes back as a `400` on its field, or in `non_field_errors`, with the model's French message; nothing is saved. Shown for at least: a duplicate open code, reversed dates, a bank SWIFT/BIC, retirement and death together, zero months, a parameter out of bounds. | D5 |
| W5 | A parameter's key cannot be changed through `PATCH`; every other field of the six tables can. | D8 |
| W6 | The rows written and their audit entries carry the signed-in user. | D7 |
| W7 | Anonymous `401`; a reader `403` on `POST`, `PATCH` and `successeur`; Rémunération writes banks and gets `403` on the other five; Gestion de carrière the reverse; the administrator writes all six. `PUT` and `DELETE` answer `405`. A session write without the CSRF token is refused. | D3, D6 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| U1 | A reader sees each tab as before, with no "Ajouter" button and no row menu. | D10 |
| U2 | An editor sees "Ajouter" and a row menu with Corriger, Remplacer à une date and Fermer; a closed row offers only Corriger; the bank actions follow the bank permissions. | D10, D11 |
| U3 | The dialog renders each table's fields with their labels and help; the document type is chosen among the open types; a parameter's key is fixed when correcting. | D8, D12 |
| U4 | Each mode sends the right request; server errors show under their fields, others at the top; after a save the dialog closes, the list reloads at the tab's date and a confirmation shows. | D5, D13 |
| U5 | The dialog opens on its first field, Escape cancels, Enter saves. | D14 |

## 3. Manual walkthrough (real saves, scratch database)

Saving is the feature, so the walkthrough saves rows; it does it on a **scratch database**, never
on the development one, whose audit log keeps every write. Set up:

```bash
cd backend
createdb syrh_walkthrough   # or CREATE DATABASE from the Django shell
DATABASE_URL=<same server>/syrh_walkthrough uv run python manage.py migrate
# then each create_demo_* command, and create_demo_users, with the same DATABASE_URL
DATABASE_URL=<same server>/syrh_walkthrough uv run python manage.py runserver 8000
```

(stop the usual backend first, and drop `syrh_walkthrough` afterwards).

Do the whole list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. On "Fonctions", **Ajouter** a fonction; it appears in the list.
   **Corriger** its name; the list shows the new name. **Remplacer à une date** with a new name
   from a future date: today's list shows the old name, the list at that date the new one.
   **Fermer** another fonction today: it disappears from today's list.
2. Try a duplicate code: the error shows in the dialog and nothing is saved. On "Paramètres",
   correct the retirement age to 650: the range error shows under "Valeur".
3. On "Sorties et suspensions", add a suspension type with a document type from the list; on
   "Types de contrat", replace a type at a date.
4. Open "Journal d'audit" as `demo.admin`: the writes appear with `demo.carriere` as author.
5. Sign in as `demo.remuneration`: "Banques" offers the actions, the other tabs do not. Add a bank
   with SWIFT/BIC `ABC`: refused under "Code SWIFT/BIC"; with a valid one: saved.
6. Sign in as `demo.auditeur`: no action anywhere.

Also check: French text with correct accents; dates as `dd/mm/yyyy`; at 375 px the dialog fits
and scrolls, its buttons stay reachable; keyboard use (Tab, Escape, Enter); no JavaScript error in
the console beyond the `401` of the sign-in check.

## 4. Security checks

- A `POST` with the session cookie but no `X-CSRFToken` is refused (`403`).
- As `demo.auditeur`, `POST`, `PATCH` and `successeur` on each endpoint answer `403`.
- As `demo.remuneration`, `POST /api/referentiels/fonctions/` answers `403`; as `demo.carriere`,
  `POST /api/referentiels/banques/` answers `403`.
- `DELETE` on each endpoint answers `405`, for every profile.
- No delete permission exists on the six models.

## 5. User guide

- `docs/user-guide.md` has a "Change the reference data" subsection (add, correct, replace at a
  date, close) with screenshots; "Who changes the reference data" names what is edited in SyRH
  and what stays in Django admin until 1.10.
- The screenshots were taken by `docs/capture_screenshots.py` against the scratch database; every
  image path exists and is non-empty, and every screenshot in `docs/screenshots/` is used.
- `docs/user-guide.html` has been rebuilt and shows the new subsection.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope slipped in: no editing of the tree tables, no delete, no
      validation circuit, no bulk edit or import, no permission change.
- [ ] `roadmap.md` has **1.10 Tree reference data screens**, and **1.9** is ticked.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `tech-stack.md` is updated.
- [ ] `/changelog` has been run on the branch.
- [ ] The scratch database is dropped; the development database has no row written by the
      walkthrough.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
