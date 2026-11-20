# Tree reference data screens — validation

How to know phase 1.10 is done and `feature/tree-reference-screens` can be merged. All parts must
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
| W1 | On each of the seven endpoints an editor creates, corrects and replaces a row; readers get `403`; `PUT` and `DELETE` answer `405`. | D1, D3 |
| W2 | A fixed field (a unit's type, parent or site, a grade's catégorie, an échelon's grade, a requirement's event or type) is refused on `PATCH` with the model's message; a successor may change it. | D2 |
| W3 | The parent rules come back on their fields: a child opening before its parent, a unit under a unit of the same or a lower level, a second open head office. | D2 |

### Carrying children over

| # | Criterion | Decision |
| --- | --- | --- |
| C1 | Replacing a direction on a date closes its open départements, services and bureaux on that date and reopens copies (new ids, same codes, names and sites) under the successor; at earlier dates the old tree is unchanged. | D4, D5 |
| C2 | Replacing a catégorie carries its grades and their échelons; replacing a grade carries its échelons. | D5 |
| C3 | Replacing a document type carries its requirements and re-points its exit reasons and suspension types to the new type. | D5 |
| C4 | If any copy is refused, nothing is closed and nothing is created, and the error names the row concerned. | D4 |
| C5 | A child opening on or after the date blocks the replacement, named in the error and in the preview. | D7 |
| C6 | Replacing or closing a site with open units stays refused; closing a parent with open children stays refused. | D6, D8 |
| C7 | The preview's counts by kind equal what the replacement then does. | D9 |
| C8 | Every closed and created row carries the signed-in user, and each has its audit entry. | D10 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| U1 | Readers see the four tabs as before, with no edit action. | D12 to D15 |
| U2 | Editors see "Ajouter" and the row menus on Sites, the Organisation and Classification trees and the Pièces justificatives tree; the "add under" actions open the dialog with the parent (and site, type, next number or event) prefilled. | D12 to D15 |
| U3 | Parent fields list only valid open parents; fixed fields are read-only when correcting. | D2, D11 |
| U4 | Replacing a parent shows the preview once a date is chosen, asks to confirm when rows follow, and disables saving when rows block it. | D16 |
| U5 | After a save, the tree reloads at the tab's date with the opened rows kept. | D17 |
| U6 | The "Types de pièce" table lists the types at the tab's date, with "Ajouter" and the row menu for editors. | D15 |

## 3. Manual walkthrough (real saves, scratch database)

On the scratch servers of phase 1.9: create `syrh_walkthrough`, `migrate`, run every
`create_demo_*` command and `create_demo_users` against it, then `preview_start` the
`backend-scratch` and `frontend-scratch` configurations and work on `http://localhost:5174`.
Drop the database afterwards.

Do the list once in the **light** theme and once in the **dark** theme.

1. Sign in as `demo.carriere`. **Organisation**: add a service under a département with
   "Ajouter une sous-unité"; it appears under it. Replace its direction at a future date with a
   new name: the dialog announces the rows that follow; after saving, the tree at that date shows
   the new name with the whole subtree, the tree today the old one.
2. Try **Fermer** on a direction with open services: refused, the services named.
3. **Classification**: add a grade under a catégorie, then an échelon (next number offered);
   replace the catégorie at a date and check its grades and échelons at that date.
4. **Pièces justificatives**: add a required document under "Mariage"; in "Types de pièce",
   replace "Décision" at a date: the career events, the suspension types and the retirement exit
   reasons follow it (check "Sorties et suspensions" at that date).
5. **Sites**: add a site; try to close the head office: refused, the units named.
6. `demo.admin`, **Journal d'audit**: the replacements appear row by row with `demo.carriere`.
7. `demo.auditeur`: no action on any tab.

Also check: French text; dates `dd/mm/yyyy`; at 375 px the dialog and its preview fit; the
keyboard; no JavaScript error beyond the sign-in `401`.

## 4. Security checks

- As `demo.auditeur` and `demo.remuneration`, `POST`, `PATCH` and `successeur` on the seven
  endpoints answer `403`; `GET suite` answers `403` too (it needs the right to replace).
- `DELETE` answers `405` everywhere; a session write without the CSRF token is refused.

## 5. User guide

- `docs/user-guide.md` covers adding under a row, replacing a parent and what follows it, and the
  refused closing, with screenshots taken on the scratch servers; "Who changes the reference
  data" no longer sends users to Django admin.
- Every image path exists and is non-empty, every screenshot is used, and
  `docs/user-guide.html` is rebuilt.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing out of scope slipped in: no move without replacement, no site carry-over, no
      delete, no undo.
- [ ] "Found during implementation" records any decision changed on the way.
- [ ] `tech-stack.md` updated; **1.10** ticked in `roadmap.md`; `/changelog` run.
- [ ] The scratch database is dropped; the development database has no row written by the
      walkthrough.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
