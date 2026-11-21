# Bank account — validation

How to know phase 2.5 is done and `feature/bank-account` can be merged. All parts must pass:
quality gates, automated tests for every acceptance criterion, the manual walkthrough, the
security checks and the leak checks. There is no user guide part: this phase adds no screen.
**(asked)**

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

The migration `agents.0007_comptebancaire` applies on an empty database and on the current
development database.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure and rules

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | An account has an agent, a bank, a number and an effective date, all required. An agent may have several, or none. | D1, D4 |
| S2 | Two rows for one agent on the same `date_effet` are refused by the database; `full_clean()` reports it. Two agents may share a date. | D3, D12 |
| S3 | A number outside the format (a lower-case or other character, fewer than 5 or more than 34 characters) is refused by the database and reported on `numero`; a typed number is stored in capitals without surrounding spaces. | D7, D12 |
| S4 | A bank and number held by another agent are refused by the database and reported on `numero`; the same agent may come back to an old account; the same number at another bank is accepted. | D8, D12, D13 |
| S5 | A bank closed on `date_effet`, or opened after it, is reported on `banque`; one closing later is accepted. A date before hiring is accepted. | D9, D10 |
| S6 | The agent cannot change after creation; bank, number and date can be corrected, the rules re-checked. | D4, D13 |
| S7 | Rows sort by agent then `date_effet`; the label reads `BCF — 05100 0001234 depuis le 01/03/2021 — ARPTC/0001/2020`. | D5 |
| S8 | Deleting a row raises; there is no delete permission. | D14 |

### Helpers

| # | Criterion | Decision |
| --- | --- | --- |
| H1 | `compte_bancaire_au(jour)` returns `None` before the first row, the row on its own date, the earlier row between two rows, the last row after it; same results with and without prefetch. | D2, D11 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating and correcting an account writes audit entries under module `paie`, with the label of D5 and their author, including through the admin page. | D1, D15 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, Rémunération and its chef have view, add and change on `comptebancaire` and view on `agent`; no other group has add or change on accounts; nobody has delete; a hand-made change survives the next `migrate`. | D16 |
| P2 | The "Comptes bancaires" admin page lists, searches and filters as D17; the agent is picked by autocomplete and read-only on change; rule errors next to their field; the editor recorded as author. Gestion de carrière and Auditeur cannot open it; Rémunération cannot change an agent. | D17 |
| P3 | `/api/agents/<id>/comptes-bancaires/` returns the accounts in date order with the fields of D18 and `compte_actuel` (a row dated today is current, a future row is not; `null` without one), tested with a frozen date, in a fixed number of queries. | D18 |
| P4 | That endpoint answers anonymous `401`; Gestion de carrière, Administration du personnel, Social, Formation, Auditeur, Administrateur système and no group `403`; Rémunération, its chef and Direction RH `200`; unknown agent `404`; writes `405`. | D15, D18 |
| P5 | `/api/agents/` and `/api/agents/<id>/` are unchanged and contain no account field. | D18 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_agents` loads the demo banks, then valid accounts of the shapes of D19 (each agent with a contract paid from their hiring date; a change of bank; a future-dated change; one agent without); a second run creates nothing and writes no audit entry; its entries show no author. | D19 |

## 3. Manual walkthrough

On the scratch database (`backend-scratch`, port 8001): set up first with `migrate`,
`create_demo_users` and `create_demo_agents` on that database.

1. Sign in to `/admin/` as `demo.remuneration`. Open "Comptes bancaires": the demo accounts are
   listed; search by a matricule and filter by a bank.
2. Add an account for an agent found by autocomplete with a number in lower case and spaces
   around it: saved in capitals, trimmed. Add one with `12-AB` then `1234`: the second is
   refused next to "Numéro".
3. Add an account with the number of another agent at the same bank: refused next to "Numéro".
   Same number at another bank: saved.
4. Add an account at a bank closed on the date: refused next to "Banque". Add a second account
   for the same agent on an existing date: refused as a duplicate.
5. Open an existing account: the agent is read-only, there is no delete button. Open "Agents":
   the list and the pages are read-only.
6. As `demo.direction`, open `/api/agents/<id>/comptes-bancaires/` for the agent with a future
   change: the current account is the earlier one.

Also check: French text with correct accents in the admin labels, help texts and messages.

## 4. Security checks

- As `demo.remuneration`, a `POST` and a `PATCH` to `/api/agents/<id>/comptes-bancaires/`
  answer `405`.
- `demo.carriere`, `demo.auditeur`, `demo.admin` and an account in no group get `403` on that
  endpoint; anonymous gets `401`.
- `demo.carriere` gets `403` on `/admin/agents/comptebancaire/`.
- In `psql`:
  - inserting a second account for an agent on an existing `date_effet` fails on the unique
    constraint;
  - inserting a number in lower case, or of 4 characters, fails on the check constraint;
  - inserting another agent's bank and number fails on the exclusion constraint;
  - deleting a bank referenced by an account fails on its foreign key.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_comptebancaire'` returns
  nothing.

## 5. Leak checks

- As `demo.carriere` and `demo.formation`, the responses of `/api/agents/` and
  `/api/agents/<id>/` contain none of the demo account numbers.
- As `demo.auditeur` and `demo.carriere`, `/api/audit/entrees/` shows no entry of table
  `agents.comptebancaire` and no demo account number; as `demo.direction`, those entries are
  there.
- As `demo.carriere`, `/admin/` shows no "Comptes bancaires" entry.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope slipped in: no validated status, no transfer file, no
      per-bank format, no document, no screen, no API write.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `tech-stack.md` names the bank accounts and their audience.
- [ ] **2.5 Bank account** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
