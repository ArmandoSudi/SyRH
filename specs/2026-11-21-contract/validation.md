# Contract — validation

How to know phase 2.3 is done and `feature/contract` can be merged. All parts must pass: quality
gates, automated tests for every acceptance criterion, the manual walkthrough and the security
checks. There is no user guide part: this phase adds no screen. **(asked)**

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

The migration `agents.0004_contrat` must apply on an empty database and on the current
development database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure and dates

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | A contract has an agent, a type and a start date, all required; an agent may have several contracts, or none. | D1, D4 |
| S2 | Two contracts of one agent over overlapping periods are refused by the database, including one starting on the other's last day and an open-ended contract followed by another; consecutive contracts (the next starting the day after the last day) and a gap are accepted; two agents may share dates. `full_clean()` reports the overlap. | D2, D3, D12, D13 |
| S3 | An end date before the start, or a probation end before the start or after the end, is refused by the database and reported on its field by `full_clean()`. | D3, D8, D12, D13 |
| S4 | The agent cannot change after creation; the type and dates can be corrected, the rules re-checked. | D4, D13 |
| S5 | Contracts sort by agent then start date; the label reads `CDD du 01/03/2020 au 28/02/2021 — ARPTC/0001/2020`, or `CDI depuis le 01/03/2021 — …`. | D5 |

### Rules from the contract type

| # | Criterion | Decision |
| --- | --- | --- |
| T1 | A type closed on the start date, or opened after it, is reported on `type_contrat`. | D6, D13 |
| T2 | A fixed-term type without an end date, and an open-ended type with one, are reported on `date_fin`. | D7, D13 |
| T3 | A probation end on a type that does not allow probation is reported on `fin_periode_essai`; on a type that allows it, it is optional. | D8, D13 |
| T4 | Deleting a contract raises; there is no delete permission. | D14 |

### Hiring date and contract in force

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | `date_engagement` is the start of the agent's first contract, `None` without one, whatever order the contracts were entered in. | D10 |
| H2 | `contrat_au(jour)` returns the contract in force before, inside and on the last day of a contract, and `None` in a gap, before the first and after the last. | D3, D11 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating and correcting a contract write audit entries under module `agents`, with the label of D5 and their author, including through the admin inline. | D17, D18 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, Gestion de carrière and its chef have view, add and change on `contrat`; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D16 |
| P2 | The agent admin page shows a "Contrats" inline in date order, with one empty row and no delete box; rule errors show next to their field; the editor is recorded as author. | D17 |
| P3 | `/api/agents/<id>/` returns `date_engagement` and `contrats` in date order with the fields of D19; `[]` and `null` without contract; `/api/agents/` is unchanged; the detail runs a fixed number of queries. | D19 |
| P4 | Access is unchanged: anonymous `401`; no group and Administrateur système `403`; every profile opening `agents` `200`; writes `405`. | D15, D19 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_agents` loads the demo contract types, then valid contracts of the shapes of D20, leaving one agent without; a second run creates nothing and writes no audit entry; its entries show no author. | D20 |

## 3. Manual walkthrough

Run it on the scratch database (`backend-scratch`, port 8001), as for phases 2.1 and 2.2: a saved
contract cannot be deleted. Set up first with `migrate`, `create_demo_users` and
`create_demo_agents` on that database.

1. Sign in to `/admin/` as `demo.carriere`. Open an agent with a renewed CDD: the "Contrats"
   inline lists the CDDs then the CDI in date order, with one empty row and no delete box.
2. Open the agent without a contract. Add a CDD from 01/03/2024 with no end date: refused next to
   "Date de fin". Give it an end date of 28/02/2025 and a probation end of 31/05/2024: saved.
3. Add a second contract, a CDI starting 28/02/2025: refused as overlapping. Change its start to
   01/03/2025: saved. Add a probation end to a stage contract: refused next to "Fin de la période
   d'essai".
4. Open the "Journal d'audit" screen as `demo.direction` (`frontend-scratch`, port 5174): both
   contracts appear under "Agents" with their labels and author.
5. As `demo.formation`, open `/api/agents/<id>/` for that agent: `date_engagement` is
   `2024-03-01` and `contrats` lists the CDD then the CDI. Open `/api/agents/`: no `contrats`
   key.

Also check: French text with correct accents in the admin labels and messages; the help texts on
the end dates say they are last days.

## 4. Security checks

- As `demo.carriere`, a `PATCH` to `/api/agents/<id>/` with `contrats` answers `405`.
- An account in no group, and `demo.admin`, get `403` on `/api/agents/<id>/`.
- In `psql`:
  - inserting a contract that overlaps another of the same agent fails on the exclusion
    constraint;
  - inserting a contract whose end is before its start fails on its check constraint;
  - inserting a probation end after the contract's end fails on its check constraint.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_contrat'` returns nothing.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope slipped in: no document, no alert, no exit, no renewal or
      probation limit, no salary, no screen, no API write.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `Q30` is still open in `docs/questions-ouvertes.md`; its answer is not required to merge.
- [ ] `tech-stack.md` names the contracts and their inclusive end date.
- [ ] **2.3 Contract** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
