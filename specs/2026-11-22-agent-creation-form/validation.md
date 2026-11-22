# Agent creation form — validation

How to know phase 2.9 is done and `feature/agent-creation-form` can be merged. All parts must
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

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL.

### Hiring endpoint

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | A full hiring creates the agent, contact details, contract, assignment and classification, the positions dated on the contract's start; without contact details, no contact row. | D1 |
| H2 | Each refusal (taken or malformed matricule, CDD without end, probation on a type without, closed contract type, closed unit, function or échelon, missing section) answers `400` on its nested field with the model's French message. | D2, D3 |
| H3 | Errors in several sections come back together. | D2 |
| H4 | A refusal in the last section leaves no row in any table and no audit entry. | D2 |
| H5 | Every created row has the signed-in user as author and an audit entry by them. | D4 |
| H6 | The answer is `201` with the detail of the new agent. | D5 |
| H7 | Anonymous `401`; Rémunération, Formation, Auditeur, Direction RH, Administrateur système `403`; Gestion de carrière and its chef `201`; `PUT`, `PATCH`, `DELETE` on an agent `405`. | D9, D10 |

### Matricule and duplicates

| # | Criterion | Decision |
| --- | --- | --- |
| M1 | The suggestion is `ARPTC/0001/YYYY` with no matching matricule, one more than the highest `ARPTC/<n>/<year>` otherwise, padded to 4 digits, other shapes ignored. | D6 |
| M2 | Duplicates match nom (case and accents ignored) and birth date, and prénom when given; at most 10. | D7 |
| M3 | Both endpoints answer `403` without `add_agent`; bad parameters `400`. | D9 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| V1 | Each step blocks "Suivant" until its required fields are filled; the end date and probation fields follow the contract type. | D11, D12 |
| V2 | The reference lists are those open on the start date, reloaded when it changes, a closed choice cleared. | D13 |
| V3 | The matricule is suggested from the start year and never overwrites typed text. | D14 |
| V4 | Server errors bring the user to the first step with an error, each under its field. | D12 |
| V5 | The summary lists the required hiring pieces and possible duplicates; saving needs the duplicate box ticked when there are some. | D8, D15 |
| V6 | Saving shows a confirmation and opens `/agents/pieces?agent=<id>`; leaving a filled form asks first. | D16, D17 |
| V7 | "Nouvel agent" shows on the list only with `agents.add_agent`. | D16 |

## 3. Walkthrough

On the scratch database (`backend-scratch` and `frontend-scratch`) with the demo data.

1. Sign in as `demo.carriere`, open **Agents**, click **Nouvel agent**.
2. **Identité**: leave the nom empty: "Suivant" refuses. Fill it, with an accented prénom.
3. **Contrat**: choose CDD: the end date appears and is required; choose CDI: it disappears. Set
   the start to today: the matricule `ARPTC/0013/<year>` appears on step 1.
4. **Poste**: pick a direction in the tree, a function, a grade then an échelon. Change the
   start date to 2014: the lists empty the choices no longer open.
5. **Récapitulatif**: the data, the required pieces (contrat signé, pièce d'identité, diplôme).
   Save: the Pièces page opens, its Engagement card says "3 pièces manquantes".
6. Hire again with the matricule of step 5: the form returns to Identité with "Ce matricule est
   déjà attribué à un autre agent." under the field.
7. Hire again someone with the same nom and birth date as a demo agent: the summary shows them
   with a link and saving waits for the box.
8. Fill a step, click another menu entry: the browser asks before leaving.

Also check: French text with correct accents everywhere.

## 4. Checks

- **All-or-nothing proof**: POST a hiring whose échelon is closed on the start date; then in
  `psql`, no `agents_agent`, `agents_contrat`, `agents_affectation`, `agents_classement` or
  `audit_entreeaudit` row was added (counts before and after equal).
- **Access**: as `demo.remuneration`, `demo.auditeur` and `demo.formation`, the list shows no
  "Nouvel agent", `/agents/nouveau` shows "Accès refusé", and a `POST /api/agents/` answers `403`.
- **Light and dark themes, tablet width (768 px)**: every step, the summary with duplicates, an
  error state.

## 5. User guide

- `docs/user-guide.md` has "Engager un agent" under Agents with light-theme screenshots taken by
  `docs/capture_screenshots.py` against the scratch servers; `user-guide.html` is rebuilt.

## 6. Definition of done

- [x] Parts 1 to 5 pass.
- [x] Nothing listed as out of scope slipped in: no correction form, no salary, no bank account,
      no upload in the form, no validation status.
- [x] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [x] `tech-stack.md` names the hiring endpoint.
- [x] **2.9 Agent creation form** is ticked in `roadmap.md`.
- [x] `/changelog` has been run on the branch.
- [x] The branch is one reviewable change, per the roadmap's working rules.
