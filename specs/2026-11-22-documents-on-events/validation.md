# Documents on events — validation

How to know phase 2.7 is done and `feature/documents-on-events` can be merged. All parts must
pass: quality gates, automated tests for every acceptance criterion, the walkthrough, the checks
and the user guide. **(asked)**

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

The new `referentiels` migration and `agents.0009_piecejointe` apply on an empty database and on
the current development database.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Links

| # | Criterion | Decision |
| --- | --- | --- |
| L1 | A document is attached to a contract, an assignment or a classification of its agent; the same document can justify several events. | D1, D3 |
| L2 | A second active link of the same document to the same event is refused by the model and the database; after removal it can be attached again. | D2, D4 |
| L3 | A document of another agent and a retired document are refused on `document`. | D3 |
| L4 | Removing a link sets its date and author once; the row and the document stay; deleting a link raises; there is no delete permission. | D4 |
| L5 | Attaching and removing write audit entries under `agents` with the label of D5 and their author. | D5 |

### Events and status

| # | Criterion | Decision |
| --- | --- | --- |
| K1 | First contract is Engagement, later ones Renouvellement; an assignment or classification on the hiring date has no kind; later assignments are Mutation; a later classification is Promotion when the grade changes, Avancement otherwise. | D8 to D10 |
| K2 | Correcting a date or adding an earlier contract changes the kinds; nothing is stored. | D12 |
| K3 | The two new kinds are accepted by `PieceRequise`, listed in order in the Pièces justificatives tab and mirrored by the frontend. | D11 |
| C1 | Required pieces are those open on the event's date: a hiring in 2020 requires the criminal record, one in 2025 does not. | D13 |
| C2 | A piece is satisfied by an active link to a non-retired document of the same type code, also after the type was replaced; a retired document or a removed link stops counting. | D14, D17 |
| C3 | An event is complete when every mandatory piece is satisfied; optional pieces never block; an event without kind or requirement is complete; `pieces_manquantes` lists the missing codes. | D15, D16 |
| C4 | A confidential document satisfies its requirement for everyone but is listed only to its readers; the others see its count. | D18 |
| C5 | `etats_pieces(agent)` and the events endpoint run in a fixed number of queries whatever the number of events and links. | D6, D16 |

### Access and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, the four document editor groups have view, add and change on `piecejointe`; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D20 |
| P2 | `GET /api/agents/<id>/evenements/` returns the fields of D21, newest first; attach and remove return the event with its new status. | D21, D22 |
| P3 | Anonymous `401`; no Agents `403` (even for an unknown agent); Agents readers without the permissions `403` on attach and remove; another agent's event or an unknown model `404`; attaching an unreadable document `400`; other methods `405`. | D19, D20, D22 |
| P4 | The admin page is read-only and hides links to confidential documents from non-members. | D18, D20 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| V1 | The section lists the events with their tags and required pieces, ticked or missing; confidential pieces show as "pièce confidentielle fournie" to non-readers; "Joindre" and "Retirer le lien" are hidden without the permissions. | D23 |
| V2 | Attaching an existing document, uploading and attaching a new one, and removing a link update the card's status; adding or retiring a document in the documents panel refreshes the section. | D24 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | The demo commands add the new kinds' requirements and the four shapes of D25; a second run creates nothing and writes no audit entry. | D25 |

## 3. Walkthrough

On the scratch database (`backend-scratch` and `frontend-scratch`): `migrate`,
`create_demo_users`, the demo reference commands and `create_demo_agents`.

1. Sign in as `demo.carriere`, open "Pièces des agents" and pick the agent with the complete
   engagement: its card says "Complet", every mandatory piece is ticked.
2. Pick the agent missing the diploma: "1 pièce manquante". Click "Joindre" on Diplôme, then
   "Déposer une nouvelle pièce", upload a PDF: the card turns "Complet" and the document appears
   in the documents panel above.
3. Remove that link: the card is incomplete again, the document stays in the panel. Retire,
   in the documents panel, a document linked to a complete event: the event becomes incomplete.
4. **Rule date**: an agent hired before 2024 requires the extrait de casier judiciaire, one hired
   after does not. In Django admin, add a new mandatory requirement to Engagement opening today:
   only engagements dated today or later require it.
5. **Confidential links**: as `demo.formation`, the engagement's Pièce d'identité shows as
   "pièce confidentielle fournie", with no link to the file; as `demo.carriere` it opens. The
   "Joindre" and "Retirer le lien" buttons are hidden for Formation.
6. Check the section in the **light and dark themes**: loading, an agent with no events, cards
   and dialogs.

Also check: French text with correct accents everywhere.

## 4. Checks

- **Fixed query count**: with Django's `CaptureQueriesContext`, the events endpoint for an agent
  with 3 events and for one with 12 events and many links runs the same number of queries
  (automated, C5), and the development server's log shows no repeated query per event.
- As `demo.formation`, `POST` attach and remove answer `403`; `DELETE` answers `405` for
  everyone; an event id of another agent answers `404`.
- In `psql`: a second active link of the same document and event fails on the unique constraint;
  deleting a document referenced by a link fails on its foreign key.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_piecejointe'` returns nothing.

## 5. User guide

- `docs/user-guide.md` has "Événements et pièces exigées" under the agents' documents section,
  with light-theme screenshots taken by `docs/capture_screenshots.py`, and `user-guide.html` is
  rebuilt.

## 6. Definition of done

- [x] Parts 1 to 5 pass.
- [x] Nothing listed as out of scope slipped in: no validation status, no dependants, no
      Milestone 3 event, no blocking on save.
- [x] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [x] `tech-stack.md` names the links, the events protocol and `pieces_manquantes`.
- [x] `Q39` is in `docs/questions-ouvertes.md`.
- [x] **2.7 Documents on events** is ticked in `roadmap.md`.
- [x] `/changelog` has been run on the branch.
- [x] The branch is one reviewable change, per the roadmap's working rules.
