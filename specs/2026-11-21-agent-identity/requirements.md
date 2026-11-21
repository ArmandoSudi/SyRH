# Agent identity — requirements

Roadmap phase **2.1 Agent identity**: the agent record and its matricule, unique and never
reused. First phase of Milestone 2 (agent record, MVP).

Branch: `feature/agent-identity`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- `missions.md`, MVP goal: **one reliable, historised agent record shared by all five
  services**. Every later module points at the table this phase creates.
- Cahier des charges, section 4: the record's identity block is "matricule unique, nom, postnom,
  prénom, sexe, date et lieu de naissance, nationalité, photo, pièce d'identité". `SOC-01`:
  **a unique matricule, never reused**.
- `Q5`: should SyRH generate the matricule as préfixe / numéro d'ordre / année d'engagement, as
  on the payslip provided? Unanswered.
- `tech-stack.md`: the matricule is a unique business key, not the primary key; `agents` is the
  next Django app; business rows are never hard-deleted (principle 8, `CAR-19`).
- `ADM-12` (phase 2.12) needs the agent's sex: a female agent's husband is not a dependant.
  `SOC-07` (phase 2.10) needs the date of birth to compute the age.
- Roles (phase 0.4): every HR profile, Direction RH and the Auditeur already open the `agents`
  module; the Administrateur système does not. `CAR-01`: Gestion de carrière creates the agent at
  hiring.
- Readers to come: 2.2 to 2.7 (contact, contract, position, bank account, documents), 2.8 list,
  2.9 creation form, 2.10 summary, 2.11 validation, 2.12 to 2.15 (dependants, import).

## Scope

### In scope

1. **A new Django app `apps.agents`**, module `agents`.
2. **One table `Agent`**: matricule and the identity fields of section 4 that are plain values.
3. **The matricule rules**: typed by HR, unique without regard to case, fixed after creation,
   never freed because an agent is never deleted.
4. **Editing in Django admin** for Gestion de carrière and its chef.
5. **Read-only API**: list and detail under `/api/agents/`.
6. **Demo data** for development.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Photo and scanned identity document | Phase 2.6 Document storage |
| Situation matrimoniale and dependants | Phases 2.12 to 2.14 (historised civil status) |
| Contact details | Phase 2.2 |
| Contract, hiring date, position, grade | Phases 2.3 and 2.4 |
| Status (active, exited) and search filters | Phases 2.8, 3.6 |
| Age and seniority computation | Phase 2.10 (`SOC-07`) |
| Draft / submitted / validated workflow | Phase 2.11 |
| Agents list, creation form, summary screens | Phases 2.8, 2.9, 2.10 |
| Generating the matricule, or checking its format | Once `Q5` is answered |
| Loading the real agents | Phase 2.15 Data import |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phases 0.x and 1.x.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **A new app `apps.agents`** owns the agent tables; its models declare `module = "agents"`. **(asked)** | One app per domain (`tech-stack.md`); the module already exists in `roles.py`. |
| D2 | **One table `Agent`**: `matricule`, `nom`, `postnom`, `prenom`, `sexe`, `date_naissance`, `lieu_naissance`, `nationalite`, plus the base fields. Primary key `BigAutoField`. **(asked)** | The identity block of section 4, minus what needs files (photo, ID document) or history (civil status). |
| D3 | `nom` required; `postnom` and `prenom` optional (blank, not null); at least one character after trimming for `nom`. Names are stored as typed, trimmed. | Not every agent has a postnom; HR writes names their own way, and the payslip shows them as recorded. |
| D4 | `sexe` is a fixed choice `M` "Masculin" / `F` "Féminin", required. | Read by `ADM-12` and the statistics by sex (`FOR-10`, `TRA-08`). |
| D5 | `date_naissance` required; `lieu_naissance` required free text; `nationalite` required free text, default "Congolaise". | Section 4; a reference list of countries is not worth a table yet. |
| D6 | Rows sort by `nom`, `postnom`, `prenom`, then `matricule`. Label `MATRICULE — NOM Postnom Prénom`. | The order HR looks agents up in; the label names the agent in the audit log and the admin. |

### Matricule

| # | Decision | Reason |
| --- | --- | --- |
| D7 | **Typed by HR**, not generated, until `Q5` is answered. Stored trimmed and in upper case, 1 to 20 characters among letters, digits, `/`, `-` and `.`. **(asked)** | Existing agents already have matricules (phase 2.15 loads them as they are); the bulletin format uses slashes. |
| D8 | **Unique without regard to case**, by a database constraint on `UPPER(matricule)`. | Principle 1: two agents can never share one, whatever was typed. |
| D9 | **Fixed after creation**: the model refuses a change, and a database trigger refuses an `UPDATE` that changes it. | A matricule identifies the agent in every module and on every past payslip. |
| D10 | **Never reused**: an agent is never deleted, so a matricule is never freed. No delete permission; `Agent.delete()` raises; a database trigger refuses `DELETE` on `agents_agent`; foreign keys to `Agent` will use `PROTECT`. | `SOC-01`; principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D11 | **In the database**: unique upper-case matricule (D8); the matricule's characters and length; `nom` not blank; `sexe` among `M`, `F`; `date_naissance` on or after 1 January 1900; the two triggers (D9, D10). | Principle 1. |
| D12 | **In the model**, from `clean()` and `save()`, with French messages per field: the normalisation and characters of the matricule; a matricule already taken (any case) on `matricule`; a changed matricule on `matricule`; a date of birth in the future on `date_naissance`. | The message says which field to fix; "today" cannot sit in a check constraint. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D13 | Every holder of `access_agents` **reads** the agents through the API. | Every service works from the same record. |
| D14 | **Gestion de carrière and Chef de service — Gestion de carrière** get view, add and change on `agent`. Nobody gets delete; the Administrateur système gets nothing. **(asked)** | `CAR-01`; least privilege. Who validates comes with 2.11. |
| D15 | The permissions go into `roles.py` as `AGENT_EDIT_PERMISSIONS`, added to those two groups in `EXTRA_PERMISSIONS`. | One declaration; the group setup only adds. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D16 | `AgentAdmin` on `BaseModelAdmin`: matricule, names, sexe, date of birth in the list; search on matricule and names; filter on sexe; matricule read-only when changing a row; no delete action. | Early data entry until the form of 2.9; same pattern as the reference tables. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D17 | `Agent` inherits `BaseModel` with `module = "agents"`; the label of D6 names the row. | Captured automatically, read by holders of `agents`. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D18 | `/api/agents/` (list) and `/api/agents/<id>/` (detail), `HasModuleAccess("agents")`, read-only: writes answer `405`. Not paginated in this phase. | The creation form (2.9) adds writes; the list screen (2.8) adds search and pagination. |
| D19 | A row returns `id`, `matricule`, `nom`, `postnom`, `prenom`, `sexe`, `sexe_libelle`, `date_naissance`, `lieu_naissance`, `nationalite`, plus the base fields, in the order of D6. | What the screens of 2.8 to 2.10 need; the label avoids a client copy of the choices. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D20 | `create_demo_agents` loads, in development, about twelve fictional agents of both sexes, with and without postnom, matricules in the bulletin style (`ARPTC/0001/2010`). It refuses to run when `DEBUG` is off, running it twice changes nothing (keyed on the matricule), and its rows have no author. | Something to look at in the admin and the API; feeds the phases that follow. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D21 | `tech-stack.md`: `agents/` added to the repository layout and named as in place. No user guide change: there is no screen. **(asked)** | `tech-stack.md` changes with the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q5` — is the matricule generated as préfixe / numéro d'ordre / année d'engagement? | No: typed by HR, free format within D7. If the answer is yes, a later phase adds the generator and a format check; the uniqueness and the triggers stay. Already in `docs/questions-ouvertes.md`. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
