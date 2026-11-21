# Contract — requirements

Roadmap phase **2.3 Contract**: an agent's successive contracts, with type, start, probation and
end date, and the hiring date they give. Third phase of Milestone 2 (agent record, MVP).

Branch: `feature/contract`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.2: the agent's file has a "Contrat" block: **type, date
  d'engagement, période d'essai, date de fin éventuelle**. `CAR-01`: the agent is created at the
  start of the contract. `CAR-03` and `CAR-04`: probation and fixed-term contracts are followed
  and alerted before they end (alerts come with Milestone 4).
- Phase 1.4 created `TypeContrat` (CDI, CDD, stage, journalier) with two flags written for this
  phase: **`duree_determinee`** (a contract of this type must have an end date) and
  **`periode_essai`** (it may have a probation period). Types are dated: open from
  `date_ouverture`, closed from `date_fermeture`.
- `missions.md`: the 30-year career count starts at the **hiring date at the ARPTC**; principle 3,
  **history is never overwritten**: a renewal or a change of contract is a new dated record.
- `Q30`: the probation length, whether it depends on the type or the category, and how many times
  a CDD may be renewed. Unanswered.
- Interns and day labourers keep separate registers (`ADM-19` to `ADM-23`, phases 5.8 and 5.9);
  the contracts here are agents' contracts.
- Phases 2.1 and 2.2 created `Agent` and `Coordonnees` in `apps.agents`, edited in Django admin by
  Gestion de carrière and its chef, read through `/api/agents/` by every profile opening Agents.
- Readers to come: 3.5 Seniority and 3.7 Retirement forecast (hiring date), 3.6 Exit (closes the
  current contract), 4.2 Career alerts (end of probation, end of contract), 2.9 creation form,
  2.10 summary page.

## Scope

### In scope

1. **One table `Contrat`** in `apps.agents`: one row per contract, several per agent, never
   overlapping.
2. **The rules**: type open on the start date; end date required exactly for fixed-term types;
   probation only for types that allow it, inside the contract.
3. **The hiring date**, computed from the first contract, and the contract in force on a day,
   as helpers for later phases.
4. **Editing in Django admin**, inline on the agent page, for the editors of 2.1 and 2.2.
5. **Read-only API**: the contracts and the hiring date in the agent detail.
6. **Demo data**: contracts for the demo agents.

### Out of scope

| Item | Where it goes |
| --- | --- |
| The signed contract as a scanned document | Phases 2.6 and 2.7 |
| Alerts before the end of probation or of a contract | Phase 4.2 |
| Ending an open-ended contract on exit | Phase 3.6 Exit |
| Limits on probation length and on CDD renewals | Answer to `Q30` |
| Base salary and grade at hiring | Phases 2.4 and 6.x |
| Validation of a hiring (`TRA-01`) | Phase 2.11 |
| Contracts on a screen; writes through the API | Phases 2.9 and 2.10 |
| Loading the real contracts | Phase 2.15 Data import |
| Interns' and day labourers' registers | Phases 5.8 and 5.9 |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phases 1.4, 2.1 and
2.2.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One table `Contrat`** in `apps.agents`, `module = "agents"`: `agent` (`PROTECT`, `related_name="contrats"`), `type_contrat` (`PROTECT` to `TypeContrat`), `date_debut`, `date_fin`, `fin_periode_essai`. **(asked)** | Principle 3: a renewal or a CDD followed by a CDI is a new row, so the career shows every contract with its dates. |
| D2 | **Successive contracts never overlap** for one agent; a gap between two contracts is allowed. **(asked)** | An agent works under one contract at a time; a gap is a real interruption. |
| D3 | **`date_fin` is the last day of the contract**, as printed on it (included). A successor starts the next day at the earliest. `fin_periode_essai` is likewise the last day of probation. **(asked)** | HR copies the dates from the signed contract; this differs from the reference tables, whose closing date is the first day closed, and is stated on the fields' help texts. |
| D4 | `date_debut` and `type_contrat` required. The `agent` never changes after creation; the other fields may be corrected in place (a typing error), the rules re-checked. | A row describes one agent's contract; a renewal is a new row, not an edit. |
| D5 | Rows sort by agent, then `date_debut`. Label `CODE du JJ/MM/AAAA au JJ/MM/AAAA — MATRICULE` (`CODE depuis le JJ/MM/AAAA — MATRICULE` without an end date). | The career in date order; the label names the contract in the audit log. |

### Rules from the contract type

| # | Decision | Reason |
| --- | --- | --- |
| D6 | The type must be **open on `date_debut`**. | A type withdrawn in 2023 cannot start a contract in 2024; an older contract keeps its type. |
| D7 | **`date_fin` required when the type has "durée déterminée", empty otherwise.** **(asked)** | Phase 1.4 D2. An open-ended contract ends on exit, which phase 3.6 records. |
| D8 | **`fin_periode_essai` only when the type has "période d'essai"**, optional, on or after `date_debut` and on or before `date_fin` when there is one. No maximum length. **(asked)** | Phase 1.4 D2; the length is `Q30`. |
| D9 | No limit on the number of renewals. | `Q30`. |

### Hiring date and contract in force

| # | Decision | Reason |
| --- | --- | --- |
| D10 | **`Agent.date_engagement`** is the `date_debut` of the agent's first contract, or `None` without one. Computed, never stored. **(asked)** | One source of truth (principle 2); the 30-year count (3.5, 3.7) reads it. |
| D11 | **`Agent.contrat_au(jour)`** returns the contract in force on that day, or `None`. | Alerts (4.2) and payroll (Milestone 6) ask "which contract applies on this day?". |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D12 | **In the database**: `date_fin` on or after `date_debut`; `fin_periode_essai` on or after `date_debut` and, with an end date, on or before it; no two contracts of one agent over overlapping periods (exclusion constraint on `agent` and `daterange(date_debut, date_fin, '[]')`). | Principle 1. |
| D13 | **In the model**, from `clean()` and `save()`, with French messages per field: reversed or out-of-contract dates on `date_fin` or `fin_periode_essai`; a type closed on the start date on `type_contrat`; a missing or forbidden end date on `date_fin`; a forbidden probation on `fin_periode_essai`; a changed agent on `agent`. The overlap is reported by the constraint's message. | These rules read the type, another row; the message says which field to fix. |
| D14 | Nothing is deleted: `default_permissions = NO_DELETE`; `Contrat.delete()` raises. | Principle 8; a contract entered by mistake is corrected. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D15 | Every holder of `access_agents` **reads** the contracts through the agent detail. | Every service needs to know whether an agent is under contract. |
| D16 | **Gestion de carrière and its chef** get view, add and change on `contrat`; nobody gets delete. Declared as `CONTRAT_EDIT_PERMISSIONS` in `roles.py`. **(asked)** | `CAR-01`: Gestion de carrière creates the contract at hiring. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D17 | A **tabular inline** "Contrats" on the agent page, in date order, without delete boxes, with one empty row to add a contract; the type list shows every type, the rule of D6 checks the date. The inline's rows get their authors from `AgentAdmin.save_formset` (phase 2.2). | One page per agent, as the contact details. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D18 | `Contrat` inherits `BaseModel` with `module = "agents"`; the label of D5. | Captured automatically, read by holders of `agents`. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D19 | `/api/agents/<id>/` gains `date_engagement` (or `null`) and `contrats`, in date order: `id`, `type_contrat`, `type_code`, `type_nom`, `date_debut`, `date_fin`, `fin_periode_essai`, plus the base fields. The detail keeps a fixed number of queries. The list `/api/agents/` is unchanged. Still read-only. | What the summary page (2.10) shows; the list grows with 2.8. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D20 | `create_demo_agents` first runs `create_demo_types_contrat` (idempotent), then gives each demo agent contracts: mostly a CDI with a probation, two agents with a CDD renewed then a CDI, one agent on a current CDD, and one without a contract. Running it twice changes nothing. | Covers the shapes the summary page and the alerts will show. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D21 | `tech-stack.md`'s `agents/` line names the contracts, and the "Exclusion constraints" paragraph notes that contracts use an inclusive end date. No user guide change: there is no screen. | `tech-stack.md` states the date convention for history tables. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q30` — probation length (by type or category?) and number of CDD renewals. | No maximum length, no renewal limit; the end of probation is typed from the contract. Already in `docs/questions-ouvertes.md`; the merge does not wait for the answer. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D22 | Demo contracts start no earlier than 1 January 2015, when the demo contract types open; the five agents with matricules from 2008 to 2012 start a CDI that day, and `ARPTC/0006/2014` its first CDD, as if older contracts were never loaded. Their hiring date is 2015, not their matricule's year. | Opening the demo types earlier would add overlapping duplicates on databases that already have them (the command keys on code and opening date) and leave the user guide's screenshots out of date. |
| D23 | `agents` reuses `DateRange` and `fr()` from `apps.referentiels.models`. | `agents` already depends on `referentiels` for the contract type; one implementation of the range function and of French dates. |
| D24 | The agent-page tests send both inlines' management fields through one helper (`inline()` adds an empty contracts formset; `contrats()` builds rows). | Each new inline otherwise breaks every earlier POST of the agent page. |
| D25 | The contract type select keeps Django's add, change and view links. | Gestion de carrière already edits the contract types (phase 1.4); removing them is a screen concern for 2.9. |
