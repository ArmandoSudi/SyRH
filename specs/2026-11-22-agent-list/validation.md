# Agent list — validation

How to know phase 2.8 is done and `feature/agent-list` can be merged. All parts must pass:
quality gates, automated tests for every acceptance criterion, the walkthrough, the load test,
the leak and theme checks, and the user guide. **(asked)**

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

The `unaccent` migration applies on an empty database and on the current development database.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL.

### Status

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | On a contract's first and last day the agent is En activité; the day after the last, Sans contrat en cours; before a first future contract, À venir; with no contract, Sans contrat; in a gap between contracts, Sans contrat en cours. | D1 |
| S2 | The SQL annotation and `statut_au()` give the same status for every demo agent on several dates. | D3 |
| S3 | The frontend status list mirrors `StatutAgent`. | D2 |

### Search API

| # | Criterion | Decision |
| --- | --- | --- |
| R1 | `q` finds by matricule, nom, postnom or prénom, ignoring case and accents; several words must all match. | D5 |
| R2 | `unite` returns agents assigned to the unit or below it on `date`; an agent moved out before `date` is not returned; at an earlier date they are. | D6 |
| R3 | `grade` and `fonction` follow the classification and assignment in force on `date`. | D6 |
| R4 | `statut` filters one or several statuses; without it, every status is returned. | D1, D4 |
| R5 | Filters combine with AND; both sorts order as D7. | D4, D7 |
| R6 | The response is paginated (25 by default, `taille` up to 100); an out-of-range page answers `404`. | D8 |
| R7 | Rows carry `statut`, `statut_libelle` and the position in force on `date`, and no contact, contract, bank or pay field; a page runs in a fixed number of queries. | D9 |
| R8 | An unknown id, a bad date, an unknown status, a `taille` over 100 answer `400` with a French message on that parameter. | D10 |
| R9 | The detail and bank accounts endpoints are unchanged; anonymous `401`, no Agents `403`. | D11 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| V1 | `/agents` sends `statut=actif` by default and every filter the user sets; "Effacer les filtres" returns to the default. | D12 |
| V2 | The table shows the columns of D13, the count, pages and sorting; loading, empty and error states. | D13 |
| V3 | Filters are read from and written to the URL, and kept in the store when navigating away and back. | D14 |
| V4 | A row links to `/agents/pieces?agent=<id>`. | D15 |
| V5 | Entrée in the top-bar search opens `/agents?q=<text>`. | D16 |
| V6 | The Pièces picker searches the server as the user types and still restores `?agent=<id>`. | D17 |

### Load-test data

| # | Criterion | Decision |
| --- | --- | --- |
| C1 | `create_load_agents` refuses without `DEBUG`, creates valid agents with histories and their audit entries, and creates nothing on a second run. | D18 |

## 3. Walkthrough

On the scratch database (`backend-scratch` and `frontend-scratch`) with the demo data.

1. Sign in as `demo.formation`. Open **Agents**: the agents En activité, 25 per page, sorted by
   name, with their service, function, grade and status.
2. Type `kalonji` then `KALONJI`, then `kalonji patrick`: the same agent. Type a matricule
   fragment: the matching agents.
3. Choose a direction in **Service**: its whole staff, from its départements and services too.
   Add a **Grade**: fewer rows. **Effacer les filtres**: back to the default.
4. Set **Situation au** to 01/01/2018: an agent transferred in 2019 shows under their old service;
   statuses follow the date.
5. Choose the statuses **À venir** and **Sans contrat**: the matching demo agents only.
6. Refresh the page and copy its address into a new tab: the same search. Go to another menu and
   come back: the filters are kept.
7. Click a row: the agent's "Pièces des agents" page opens. Its picker finds agents as you type.
8. From the dashboard, type a name in the top-bar search and press Entrée: the list, filtered.

Also check: French text with correct accents everywhere.

## 4. Load test

On the scratch database, after `create_load_agents --nombre 3000`:

- every filter alone and three combinations (text + status, unit + grade, unit + date in 2020)
  answer in **under 1 second** on the development machine, measured on the API (curl
  `time_total`), page 1 and a far page;
- the number of queries per page is the same as with 12 agents (automated, R7);
- the screen shows the first page in under 3 seconds (`NF-08`), observed in the browser's
  network panel.

## 5. Leak, theme and width checks

- **No pay data**: as each demo profile, `/api/agents/` responses contain none of the demo account
  numbers and no field named after a bank, account, salary or amount (automated for every profile,
  and checked by hand for `demo.formation` and `demo.auditeur`).
- **Light and dark themes**: the list, its filters open and its empty state in both.
- **Tablet width (768 px)**: the filters wrap on several lines, the table scrolls inside its card,
  the paginator stays usable.

## 6. User guide

- `docs/user-guide.md` has an "Agents" section with light-theme screenshots taken by
  `docs/capture_screenshots.py`; section 3 no longer lists Agents as not built; the top-bar search
  is described; `user-guide.html` is rebuilt.

## 7. Definition of done

- [x] Parts 1 to 6 pass.
- [x] Nothing listed as out of scope slipped in: no export, no creation, no summary page, no
      Milestone 3 status.
- [x] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [x] `tech-stack.md` names the search, the computed status and `unaccent`.
- [x] **2.8 Agent list** is ticked in `roadmap.md`.
- [x] `/changelog` has been run on the branch.
- [x] The branch is one reviewable change, per the roadmap's working rules.
