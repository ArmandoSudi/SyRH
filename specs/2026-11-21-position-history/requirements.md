# Position history — requirements

Roadmap phase **2.4 Position history**: an agent's dated assignment (organisation unit and
function) and classification (grade and échelon), never overlapping, never overwritten
(`SOC-02`, `SOC-03`). Fourth phase of Milestone 2 (agent record, MVP).

Branch: `feature/position-history`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges: `SOC-02`, keep the dated history of everything that evolves, **grade,
  fonction, salaire, affectation**, état civil; `SOC-03`, each event has an **effective date
  distinct from its entry date**, so that payroll can apply back pay. `CAR-01`: the agent is
  created with identity, contract, **affectation, grade** and base salary.
- `missions.md`, principle 3: an evolving fact is a dated row, not a column overwritten in place;
  principle 2: a fact is stored once.
- Phases 1.1 to 1.3 created the reference data this phase points to, all dated (open from
  `date_ouverture` included, closed from `date_fermeture` excluded):
  - `UniteOrganisationnelle`: direction, département, service, bureau, as a tree;
  - `Fonction`: job functions, of nature responsabilité or exécution;
  - `Categorie` › `Grade` › `Echelon`: an échelon belongs to one grade and opens and closes
    within it.
- Phase 2.3 created `Contrat`, with `Agent.date_engagement` and `Agent.contrat_au(jour)`.
- Readers to come: 3.1 Promotions (a new classification row with its decision), 3.2 Transfers
  and function changes (a new assignment row), 3.3 Interim, 3.6 Exit (ends the last rows),
  2.8 Agent list (search by service, grade, function), 2.10 Summary page (timeline), 6.2 and 6.4
  pay scales and base salary per grade.

## Scope

### In scope

1. **Two tables** in `apps.agents`: `Affectation` (unit and function) and `Classement` (grade
   through the échelon), one row per change, several per agent.
2. **The rules**: one row per agent and effective date; references open on that date; the
   effective date inside one of the agent's contracts.
3. **Helpers**: the assignment and the classification in force on a day.
4. **Editing in Django admin**, as two inlines on the agent page, for Gestion de carrière and its
   chef.
5. **Read-only API**: both histories in the agent detail; the current assignment and
   classification in the agent list.
6. **Demo data**: histories for the demo agents.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Decision reference and scanned decision on a row | Phases 2.7, 3.1, 3.2 |
| Promotion and transfer as validated events | Phases 3.1, 3.2, 2.11 |
| Interim assignments | Phase 3.3 |
| Ending the last rows on exit | Phase 3.6 |
| Alert when an agent's unit, function or échelon closes | Milestone 4 |
| Base salary per grade | Phases 6.2, 6.4 |
| Search and filters on the list; pagination | Phase 2.8 |
| Histories on a screen; writes through the API | Phases 2.9, 2.10 |
| Loading the real histories | Phase 2.15 |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phases 1.1 to 2.3.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **Two tables** in `apps.agents`, `module = "agents"`: `Affectation` (`agent`, `unite`, `fonction`, `date_effet`) and `Classement` (`agent`, `echelon`, `date_effet`). `related_name` `affectations` and `classements`. **(asked)** | A transfer or function change (3.2) and a promotion (3.1) are separate events with separate decisions; one table would copy the untouched half on every change. |
| D2 | **Only the effective date is stored.** A row applies from its `date_effet` until the next row of the same agent in the same table; the last row applies until further notice. **(asked)** | No gap and no overlap by construction; no end date to keep in step with the successor. |
| D3 | **One row per agent and `date_effet`** in each table (unique constraint). | Two rows on the same day would leave the position on that day undefined. |
| D4 | **The classification stores the échelon only**; its grade (and catégorie) is read through it. **(asked: échelon required)** | Principle 2: storing the grade beside it would allow an échelon of another grade. |
| D5 | **Any unit level** (direction, département, service, bureau) can receive an agent. **(asked)** | Directors sit in a direction, analysts in a bureau. |
| D6 | All fields required. The `agent` never changes after creation; the other fields may be corrected in place (a typing error), the rules re-checked. A real change is a new row. | Principle 3: the audit log keeps corrections, the rows keep the career. |
| D7 | Rows sort by agent, then `date_effet`. Labels: `UNITE · FONCTION depuis le JJ/MM/AAAA — MATRICULE` and `GRADE — Échelon N depuis le JJ/MM/AAAA — MATRICULE`. | The career in date order; the label names the row in the audit log. |
| D8 | The entry date (`SOC-03`) is `date_creation` from `BaseModel`; no new column. A `date_effet` in the past or the future is accepted. | Back-dated decisions feed back pay; a decision effective next month is entered today. |

### Rules

| # | Decision | Reason |
| --- | --- | --- |
| D9 | The unit, the function and the échelon must be **open on `date_effet`**. A later closing is not checked. | Mirrors contract D6. A unit closing under an agent is a restructuring, alerted later. |
| D10 | **`date_effet` must fall inside one of the agent's contracts** (`Agent.contrat_au(date_effet)` is not `None`). Nothing else is checked against contracts. **(asked)** | A position only makes sense under contract; gaps between contracts do not need special handling. |
| D11 | No rule ties the function's nature to the unit's level, nor the grade to the function. | Not in the cahier des charges. |

### Helpers

| # | Decision | Reason |
| --- | --- | --- |
| D12 | **`Agent.affectation_au(jour)`** and **`Agent.classement_au(jour)`**: the row with the latest `date_effet` on or before that day, or `None`. They read prefetched rows when present, as `contrat_au`. | Payroll, alerts and the list ask "where and at which grade on this day?". |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D13 | **In the database**: foreign keys `PROTECT`; `UniqueConstraint(agent, date_effet)` per table with a French message. | Principle 1. |
| D14 | **In the model**, from `clean()` and `save()`, with French messages per field: a closed reference on its field; a date outside every contract on `date_effet`; a changed agent on `agent`. | These rules read other rows. |
| D15 | Nothing is deleted: `default_permissions = NO_DELETE`; `delete()` raises. | Principle 8. |

### Access and admin

| # | Decision | Reason |
| --- | --- | --- |
| D16 | Every holder of `access_agents` reads both histories. | Every service needs to know where an agent works and at which grade. |
| D17 | **Gestion de carrière and its chef** get view, add and change on `affectation` and `classement`; nobody gets delete. `AFFECTATION_EDIT_PERMISSIONS` and `CLASSEMENT_EDIT_PERMISSIONS` in `roles.py`. **(asked)** | `CAR-01`, `CAR-06`, `CAR-08`: Gestion de carrière records them. |
| D18 | Two **tabular inlines** "Affectations" and "Classements" on the agent page, after the contracts, in date order, without delete boxes, one empty row each. Authors from `AgentAdmin.save_formset`. **(asked)** | One page per agent, as the contracts. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D19 | `/api/agents/<id>/` gains `affectations` (`id`, `unite`, `unite_code`, `unite_nom`, `unite_type`, `fonction`, `fonction_code`, `fonction_nom`, `date_effet`, base fields) and `classements` (`id`, `echelon`, `echelon_numero`, `grade`, `grade_code`, `grade_nom`, `categorie_code`, `date_effet`, base fields), in date order. Fixed number of queries. **(asked)** | What the summary page (2.10) shows. |
| D20 | `/api/agents/` gains `affectation_actuelle` and `classement_actuel`: the row **in force today** (a future-dated row is not current yet), with the fields of D19 without base fields, or `null`. Fixed number of queries whatever the number of agents. Still read-only. **(asked)** | The list (2.8) shows and filters on service, function and grade. |

### Audit and demo data

| # | Decision | Reason |
| --- | --- | --- |
| D21 | Both tables inherit `BaseModel` with `module = "agents"`; the labels of D7. | Captured automatically. |
| D22 | `create_demo_agents` first runs the demo organisation, functions and classification commands (idempotent), then gives each agent with a contract an assignment and a classification on their hiring date; some agents get a later transfer, a function change or a promotion; one agent gets a future-dated promotion; the agent without contract has neither. Running it twice changes nothing. | Covers the shapes of the summary page and of "current" in the list. |
| D23 | `tech-stack.md`'s `agents/` line names both histories and their start-only dating. | `tech-stack.md` states the date convention for history tables. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| What happens to an agent whose unit, function or échelon closes. | Nothing is checked after `date_effet`; HR enters a new row. Alerting comes with Milestone 4. |
| `Q27` to `Q29` — the real organisation, classification and functions. | Demo data only; the merge does not wait. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D24 | In Django admin, a contract must be saved before an assignment or classification that rests on it: the inlines are validated before anything is saved, so a row typed on the same save as its contract, or on the add page of a new agent, is refused on `date_effet` ("sous aucun contrat"). Save the contract first, then add the rows. | D10 reads saved contracts; the creation form of 2.9 will save them in order. The add page reports the error instead of failing on save. |
| D25 | The agent-page tests build every tabular inline through one `formset(prefix, *rows)` helper; `inline()` adds the empty assignments and classifications formsets. | Same reason as contract D24. |
