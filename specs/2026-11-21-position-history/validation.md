# Position history — validation

How to know phase 2.4 is done and `feature/position-history` can be merged. All parts must pass:
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

The migrations `agents.0005_affectation` and `agents.0006_classement` apply on an empty database
and on the current development database.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | An assignment has an agent, a unit, a function and an effective date; a classification an agent, an échelon and an effective date; all required. An agent may have several of each, or none. | D1, D4, D6 |
| S2 | Two rows of one table for one agent on the same `date_effet` are refused by the database; `full_clean()` reports it. Two agents may share a date. | D3, D13 |
| S3 | A classification exposes its grade and catégorie through its échelon; no grade is stored. | D4 |
| S4 | Any unit level is accepted. | D5 |
| S5 | The agent cannot change after creation; references and date can be corrected, the rules re-checked. | D6, D14 |
| S6 | Rows sort by agent then `date_effet`; the labels read `DRH · Chef de service depuis le 01/03/2021 — ARPTC/0001/2020` and `A2 — Échelon 3 depuis le 01/03/2021 — ARPTC/0001/2020`. | D7 |

### Rules

| # | Criterion | Decision |
| --- | --- | --- |
| R1 | A unit, function or échelon closed on `date_effet`, or opened after it, is reported on its field; one closing later is accepted. | D9, D14 |
| R2 | A `date_effet` before the first contract, in a gap between contracts, or after the last contract's end is reported on `date_effet`; a contract's first and last days are accepted. | D10, D14 |
| R3 | A past or future `date_effet` inside a contract is accepted. | D8 |
| R4 | Deleting a row raises; there is no delete permission. | D15 |

### Helpers

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | `affectation_au(jour)` and `classement_au(jour)` return `None` before the first row, the row on its own date, the earlier row between two rows, the last row after it; same results with and without prefetch, whatever the entry order. | D2, D12 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating and correcting either row writes audit entries under module `agents`, with the labels of D7 and their author, including through the admin inlines. | D18, D21 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, Gestion de carrière and its chef have view, add and change on both tables; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D17 |
| P2 | The agent admin page shows "Affectations" and "Classements" inlines after the contracts, in date order, one empty row each, no delete box; rule errors next to their field; the editor recorded as author. | D18 |
| P3 | `/api/agents/<id>/` returns `affectations` and `classements` in date order with the fields of D19, `[]` without rows, in a fixed number of queries. | D19 |
| P4 | `/api/agents/` returns `affectation_actuelle` and `classement_actuel`: the row in force today (a row dated today is current, a future row is not), `null` without one; tested with a frozen date. The query count is the same for 1 and 10 agents. | D20 |
| P5 | Access is unchanged: anonymous `401`; no group and Administrateur système `403`; every profile opening `agents` `200`; writes `405`. | D16 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_agents` loads the demo reference data, then valid rows of the shapes of D22 (each agent with a contract placed on their hiring date; a transfer, a function change, a promotion, a future promotion; one agent without); a second run creates nothing and writes no audit entry; its entries show no author. | D22 |

## 3. Manual walkthrough

On the scratch database (`backend-scratch`, port 8001, and `frontend-scratch`, port 5174): a
saved row cannot be deleted. Set up first with `migrate`, `create_demo_users` and
`create_demo_agents` on that database.

1. Sign in to `/admin/` as `demo.carriere`. Open an agent with a transfer and a promotion: the
   "Affectations" and "Classements" inlines list their rows in date order after the contracts,
   one empty row each, no delete box.
2. Add an assignment dated before the agent's first contract: refused next to "Date d'effet".
   Date it inside the contract with a closed unit: refused next to "Unité". Pick an open unit:
   saved.
3. Add a classification on the same date as an existing one: refused as a duplicate. Move it one
   day later: saved.
4. Open the "Journal d'audit" screen as `demo.direction`: both rows appear under "Agents" with
   their labels and author.
5. As `demo.formation`, open `/api/agents/<id>/`: both histories in date order. Open
   `/api/agents/`: the agent with a future promotion shows their current grade, not the future
   one; the agent without contract shows `null` for both.

Also check: French text with correct accents in the admin labels, help texts and messages.

## 4. Security checks

- As `demo.carriere`, a `PATCH` to `/api/agents/<id>/` with `affectations` answers `405`.
- An account in no group, and `demo.admin`, get `403` on `/api/agents/` and
  `/api/agents/<id>/`.
- In `psql`:
  - inserting a second assignment for an agent on an existing `date_effet` fails on the unique
    constraint; same for a classification;
  - deleting an échelon, unit or function referenced by a row fails on its foreign key.
- `SELECT codename FROM auth_permission WHERE codename IN ('delete_affectation',
  'delete_classement')` returns nothing.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope slipped in: no decision reference, no document, no interim,
      no exit, no alert, no salary, no search, no screen, no API write.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `tech-stack.md` names both histories and their start-only dating.
- [ ] **2.4 Position history** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
