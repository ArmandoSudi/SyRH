# Agent identity — validation

How to know phase 2.1 is done and `feature/agent-identity` can be merged. All parts must pass:
quality gates, automated tests for every acceptance criterion, the manual walkthrough and the
security checks. There is no user guide part: this phase adds no screen. **(asked)**

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

The migrations `agents.0001_initial` and `agents.0002_triggers` must apply on an empty database
and on the current development database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint and trigger is also proven by a test that bypasses the model.

### Structure

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | An agent has a matricule, a nom, a sexe, a date and place of birth and a nationality, all required; postnom and prénom are optional; the nationality defaults to "Congolaise". | D2, D3, D5 |
| S2 | A blank `nom`, an unknown `sexe` or a birth before 1900 is refused by the database; a future birth is reported by `full_clean()` on `date_naissance`. | D3, D4, D11, D12 |
| S3 | Agents sort by nom, postnom, prénom, then matricule; the label reads `MATRICULE — NOM Postnom Prénom`. | D6 |

### Matricule

| # | Criterion | Decision |
| --- | --- | --- |
| M1 | The matricule is stored trimmed and upper case; characters outside letters, digits, `/`, `-`, `.`, or more than 20, are refused by the database and reported on `matricule` by `full_clean()`. | D7, D11, D12 |
| M2 | Two agents with the same matricule in different cases are refused by the database; `full_clean()` reports it on `matricule`. | D8, D12 |
| M3 | Changing a matricule is refused by `full_clean()` and `save()`, and by the trigger in raw SQL; changing a name is accepted. | D9 |
| M4 | Deleting an agent is refused by `delete()` and by the trigger in raw SQL; there is no delete permission. | D10 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating and changing an agent write audit entries under module `agents`, with the label of D6 and their author. | D17 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, Gestion de carrière and its chef have view, add and change on `agent`; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D14, D15 |
| P2 | The admin lists, searches and filters agents; the matricule is read-only on change; rule errors show next to their field; there is no delete button or action; other profiles get `403`. | D16 |
| P3 | `/api/agents/` lists agents in the order of D6 with the fields of D19; `/api/agents/<id>/` returns one; an unknown id answers `404`. | D18, D19 |
| P4 | Anonymous `401`; no group and Administrateur système `403`; every profile opening `agents` `200`; writes `405`. | D13, D18 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_agents` refuses to run when `DEBUG` is off. | D20 |
| E2 | It creates valid agents of both sexes, some without postnom. A second run creates nothing and writes no audit entry; its entries show no author. | D20 |

## 3. Manual walkthrough

Set up first:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py create_demo_agents
```

1. Sign in to `/admin/` as `demo.carriere`. The agent list shows the demo agents sorted by name;
   search a matricule and a postnom; filter on "Féminin".
2. Add an agent with matricule ` arptc/0999/2026 ` (with spaces): it is saved as
   `ARPTC/0999/2026`. Try a second agent with `Arptc/0999/2026`: refused next to "Matricule".
   Try a date of birth tomorrow: refused next to "Date de naissance".
3. Open the new agent: the matricule is read-only; change the postnom and save. There is no
   delete button or action.
4. Open the "Journal d'audit" screen as `demo.direction`: the creation and the change appear
   under "Agents", labelled with the matricule and name.
5. In the browser, signed in as `demo.formation`, open `/api/agents/` and one detail: the fields
   of D19, in the order of D6. As `demo.admin`: `403`.

Also check: French text with correct accents in the admin labels and messages; dates as
`dd/mm/yyyy` in the admin.

## 4. Security checks

- As `demo.carriere`, a `POST` to `/api/agents/` answers `405`.
- An account in no group gets `403` on `/api/agents/`.
- In `psql`:
  - inserting a second agent with the same matricule in lower case fails on the unique
    constraint;
  - `UPDATE agents_agent SET matricule = 'X' WHERE id = …` fails with the trigger's message;
  - `DELETE FROM agents_agent WHERE id = …` fails with the trigger's message.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_agent'` returns nothing.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope slipped in: no photo or document, no civil status, no
      contract or position, no status, no age computation, no screen, no matricule generator.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `Q5` is still open in `docs/questions-ouvertes.md`; its answer is not required to merge.
- [ ] `tech-stack.md` lists `agents/` in the repository layout.
- [ ] **2.1 Agent identity** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
