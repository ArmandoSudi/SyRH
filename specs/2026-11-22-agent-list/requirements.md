# Agent list — requirements

Roadmap phase **2.8 Agent list**: find any agent by matricule, name, service, grade, function or
status (`SOC-06`), on one screen that every profile opening Agents can use. Eighth phase of
Milestone 2 (agent record, MVP).

Branch: `feature/agent-list`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges: `SOC-06`, search an agent by matricule, name, service, grade, function or
  status; `NF-08`, a usual screen shows in under 3 seconds; `NF-09`, sized for today's workforce
  and ten years of growth, history included.
- `missions.md`: success means "an HR officer finds any agent"; principle 9, least privilege —
  pay data is not part of the agent list.
- Phase 2.1 created `/api/agents/` and `/api/agents/<id>/`, read-only, **not paginated**, for every
  profile opening Agents (agent identity D18), and said 2.8 adds search and pagination. Phase 2.4
  added the assignment and classification in force today to each row (position history D20).
- Phase 2.3 created the contracts (never overlapping, end date included); there is no exit,
  suspension or détachement yet (Milestone 3).
- Phase 1.1 created the units as a tree (direction, département, service, bureau).
- Phase 2.6 created the "Pièces des agents" page, whose agent picker loads every agent from
  `/api/agents/`.
- The menu entry "Agents" opens a placeholder; the top bar shows a search box that does nothing.
- Readers to come: 2.9 (the creation form lands back on the list), 2.10 (a row opens the summary
  page), Milestone 3 (new statuses), 4.x and the dashboard (counts by status).

## Scope

### In scope

1. **Computed status** of an agent at a date, from their contracts.
2. **Server-side search** on `/api/agents/`: text, unit (with its sub-units), grade, function,
   status, at a date; sorted; **paginated**.
3. **The "Agents" screen** at `/agents`: search box, filters, date, table, pagination; a row opens
   the agent's "Pièces des agents" page.
4. **The top-bar search box** opens the list filtered on the typed text.
5. **The "Pièces des agents" picker** searches on the server instead of loading every agent.
6. **Load-test data**: a development command generating thousands of agents with their histories.
7. **User guide**: an "Agents" section with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Statuses Détaché, En disponibilité, Sorti | Milestone 3 (3.4, 3.6), added to the same computed status |
| Creating an agent from the list | Phase 2.9 |
| The agent summary page | Phase 2.10, which the row then opens |
| Export (Excel, CSV) | Reports phases, after the "Excel export library" decision |
| Saved searches, column choice | Not planned |
| Searching dependants | Phases 2.12 to 2.14 |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner on 2026-11-22; the others
follow from the cahier des charges, `missions.md`, `tech-stack.md` and earlier phases.

### Status

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **Status is computed, never stored**, from the agent's contracts at a date: `actif` "En activité" (a contract in force that day), `a_venir` "À venir" (no contract started yet, a later one exists), `inactif` "Sans contrat en cours" (contracts before, none in force), `sans_contrat` "Sans contrat" (none at all). **(asked)** | One source of truth; a contract corrected changes the status. |
| D2 | The statuses are a `TextChoices` `StatutAgent` in `apps.agents`, in that order, mirrored by the frontend (a test checks the mirror). Milestone 3 adds its statuses there, each with its rule, and they take precedence over `actif`. | The same list for the filter, the column and later the dashboard. |
| D3 | The rule lives once, as a queryset annotation `with_statut(jour)` (PostgreSQL `EXISTS` subqueries), used by both the filter and the column; `Agent.statut_au(jour)` reads prefetched contracts for a single agent with the same result. | The list must filter in SQL (D6); one test proves both agree. |

### Search API

| # | Decision | Reason |
| --- | --- | --- |
| D4 | `/api/agents/` accepts, all optional and combined with AND: `q` (text), `unite`, `grade`, `fonction` (ids), `statut` (one or more codes, comma-separated), `date` (YYYY-MM-DD, default today), `tri` (`nom` default, `matricule`), `page`, `taille` (default 25, at most 100). Without `statut`, every status is returned. **(asked: server-side)** | `SOC-06`; `NF-08`, `NF-09`. |
| D5 | `q` matches the matricule or any of nom, postnom, prénom, **ignoring case and accents**, each word of `q` matching somewhere (`"kab jean"` finds Kabongo Jean). PostgreSQL `unaccent`, installed by a migration. | People type names without accents. |
| D6 | `unite` matches agents whose **assignment in force on `date`** is that unit **or any unit below it**; `fonction` the assignment's function; `grade` the grade of the classification in force on `date`. Done in SQL with subqueries on the latest row dated on or before `date`. **(asked: unit and sub-units)** | Choosing a direction lists its whole staff. |
| D7 | Sorted by nom, postnom, prénom, matricule (agent identity D6), or by matricule with `tri=matricule`. | The order HR reads lists in. |
| D8 | **Paginated**: `{"count", "next", "previous", "results"}`; an out-of-range page answers `404`. | A breaking change of the list endpoint: its two callers (the picker, the tests) move with it. |
| D9 | A row adds to the existing fields (agent identity D19) `statut` and `statut_libelle`; `affectation_actuelle` and `classement_actuel` are those in force **on `date`**. A fixed number of queries per page. No contact, contract, bank or pay field. | What the table shows, nothing more (principle 9). |
| D10 | Unknown ids, a malformed date or an unknown status answer `400` with a French message on the parameter. | Errors per field, as everywhere. |
| D11 | `/api/agents/<id>/` and the bank accounts endpoint are unchanged. Access is unchanged: every profile opening Agents. | 2.1 D13. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D12 | **`/agents`** replaces the placeholder: a search box (matricule or name), filters Service (tree select over the units open on the date), Grade, Fonction, Statut (multi-select, **default En activité**), a date "Situation au" (default today), "Effacer les filtres", the count of results. **(asked: default En activité)** | `SOC-06`. |
| D13 | Table columns: Matricule, Nom (nom postnom prénom), Service (unit code and name), Fonction, Grade (and échelon), Statut (a tag). 25 rows per page, pagination below, sort by name or matricule. Loading, empty and error states. | The fields the search uses, visible. |
| D14 | **Filters live in the URL query** (`/agents?q=kab&statut=actif&page=2`) and in a Pinia store, so a search survives navigation, refresh and can be shared. The text search waits 300 ms after typing. **(asked)** | `tech-stack.md`: state survives navigation; deep links land on the right screen. |
| D15 | **A row opens `/agents/pieces?agent=<id>`** until roadmap 2.10 points it to the summary page. Rows are links (open in a new tab works). **(asked)** | The only agent page so far. |
| D16 | **The top-bar search** box: Entrée opens `/agents?q=<text>` from any page (status filter at its default). **(asked)** | It exists on every screen and promised this. |
| D17 | The "Pièces des agents" **picker** asks `/api/agents/?q=…&taille=20` as the user types (all statuses), instead of loading every agent. | The full list no longer comes in one call (D8). |

### Load-test data

| # | Decision | Reason |
| --- | --- | --- |
| D18 | `create_load_agents --nombre N` (default 3000) generates, in development only (refuses without `DEBUG`), agents with matricules `CHARGE/00001`…, each with one or two contracts, two or three assignments and classifications over the demo units, grades and functions, some without contract or with a future one. Bulk-created; their audit entries are written in bulk through `apps.audit.service`. Idempotent (skips existing matricules). | `NF-09`: prove the list stays fast at scale (validation part 4). |

## Open points

| Point | Assumption until answered |
| --- | --- |
| Whether an agent between two contracts (a gap) should show as "Sans contrat en cours" or keep a status of their own. | "Sans contrat en cours" until Milestone 3's statuses. |
| Whether the Auditeur and other services need every agent, including those without a contract. | Every profile opening Agents sees every agent (2.1 D13). |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
