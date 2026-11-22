# Agent creation form — requirements

Roadmap phase **2.9 Agent creation form**: Gestion de carrière enters a new agent at hiring —
identity, contact details, first contract, first assignment and classification — in one form,
saved all at once (`CAR-01`), then attaches the hiring pieces (`CAR-02`). Ninth phase of
Milestone 2 (agent record, MVP).

Branch: `feature/agent-creation-form`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges: `CAR-01`, create the agent at the start of their contract: identity,
  contract, assignment, grade, base salary; `CAR-02`, require the hiring pieces defined in the
  reference data before validation; `CAR-05`, a validated agent is available to the other modules
  at once.
- `missions.md`: principle 1, the database refuses invalid states; principle 5, who enters does
  not validate (phase 2.11); principle 7, every write audited.
- Phases 2.1 to 2.4 created the agent's tables with their rules (matricule unique and fixed,
  contracts never overlapping, positions under contract and on open references), edited in
  Django admin by Gestion de carrière and its chef (`AGENT_RECORD_EDIT_PERMISSIONS`).
- `Q5` (matricule format) is open: the matricule is typed by HR (agent identity D7); the demo and
  the bulletin use `ARPTC/0001/2008` (prefix / sequence / hiring year).
- Phase 2.7: the first contract is the Engagement event; its required pieces come from
  `PieceRequise` and are attached on the "Pièces des agents" page.
- Phase 2.8: the Agents list at `/agents`; rows open the agent's Pièces page.
- Base salary comes from the pay scales (Milestone 6); the bank account is entered by Rémunération
  (bank account D16).

## Scope

### In scope

1. **One write endpoint** `POST /api/agents/` creating, in one transaction, the agent, their
   contact details (optional), first contract, first assignment and first classification.
2. **Matricule suggestion**: the next number in the bulletin style, editable.
3. **Duplicate check**: agents with the same names and birth date, shown before saving.
4. **The hiring form** at `/agents/nouveau`: a stepper, reference lists open on the hiring day,
   errors on their field, a summary, then the agent's Pièces page with the missing hiring pieces.
5. **"Nouvel agent"** button on the Agents list.
6. **User guide**: "Engager un agent" with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Correcting an agent, adding later contracts or positions from the app | Phase 2.10 and Milestone 3; Django admin until then |
| Validation of the hiring (draft, submitted, validated) | Phase 2.11 |
| Base salary | Milestone 6 (pay scales) |
| Bank account | Rémunération, Django admin (bank account D16) |
| Uploading the hiring pieces inside the form | The Pièces page, right after saving (D17) |
| Generating the matricule without HR | Once `Q5` is answered |
| Photo, civil status | Later phases |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner on 2026-11-22; the others
follow from the cahier des charges, `missions.md`, `tech-stack.md` and earlier phases.

### What is created

| # | Decision | Reason |
| --- | --- | --- |
| D1 | One hiring creates: the **agent** (identity), their **contact details** (optional: created only when filled), the **first contract**, the **first assignment** (unit, function) and the **first classification** (échelon), the last two dated on the contract's start. **(asked)** | `CAR-01`, minus the salary (Milestone 6). |
| D2 | **All or nothing**: one transaction; any refusal creates no row and writes no audit entry. Every section is checked, so the answer lists **all** errors at once, each on its field, nested by section (`{"matricule": [...], "contrat": {"date_fin": [...]}, "affectation": {"unite": [...]}}`). **(asked)** | No half-hired agent; one round trip to fix everything. |
| D3 | The rules are the models' own (`full_clean()` and `check_rules()`), run in order: agent, contact details, contract, assignment, classification. Nothing is re-implemented in the serializer. | One source of truth (principle 1). |
| D4 | Each row is saved with the signed-in user as author, so each gets its audit entry with that author. | Principle 7. |
| D5 | The response is the new agent's detail (as `GET /api/agents/<id>/`), status `201`. | The screen moves on with the id. |

### Matricule and duplicates

| # | Decision | Reason |
| --- | --- | --- |
| D6 | `GET /api/agents/matricule-suivant/?annee=YYYY` proposes `ARPTC/<n>/<YYYY>`, where `n` is one more than the highest sequence among matricules shaped `ARPTC/<digits>/<4 digits>`, padded to 4 digits. The form fills it in from the hiring year; HR may change it. Uniqueness stays the database's (agent identity D8). **(asked: suggested, editable)** | Follows the bulletin until `Q5` decides. |
| D7 | `GET /api/agents/doublons/?nom=&postnom=&prenom=&date_naissance=` returns the agents with the same nom (ignoring case and accents) and birth date, and, when given, the same prénom; at most 10, as list rows. | Homonyms exist; the same person entered twice must be caught. |
| D8 | A possible duplicate never blocks: the summary step lists them with a link and asks "Il s'agit bien d'un autre agent" to be ticked before saving. **(asked: warn, allow)** | Two real agents may share names and a birth date. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D9 | Creating requires `agents.add_agent`, `add_contrat`, `add_affectation`, `add_classement`, and `add_coordonnees` when contact details are sent: today Gestion de carrière and its chef. Others get `403`; the suggestion and duplicate endpoints require `add_agent`. | Agent identity D14; least privilege. |
| D10 | `/api/agents/<id>/` stays read-only: `PUT`, `PATCH`, `DELETE` answer `405`. **(asked: creation only)** | Corrections come with 2.10. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D11 | `/agents/nouveau`, a **stepper**: 1 Identité (matricule, nom, postnom, prénom, sexe, birth date and place, nationality), 2 Coordonnées (optional), 3 Contrat (type, start, end, end of probation, the last two shown only when the type allows them), 4 Poste (unit as a tree, function, grade then échelon), 5 Récapitulatif. **(asked)** | One concern per step. |
| D12 | Each step checks its required fields before "Suivant"; the server's errors send the user back to the first step holding one, every error shown under its field. | Errors next to the field (`tech-stack.md`). |
| D13 | The contract type, unit, function and échelon lists show the rows **open on the contract's start**; changing that date reloads them and clears a choice no longer open. | The rules refuse a closed reference (position history D9). |
| D14 | The matricule is suggested when the start date is set and the field is still empty or holds the previous suggestion. | HR's own typing is never overwritten. |
| D15 | The summary shows everything entered, the required hiring pieces of the reference data on that date (`PieceRequise` for Engagement), and the possible duplicates (D8). | `CAR-02`: HR knows what to attach next. |
| D16 | "Nouvel agent" on the Agents list, shown with `agents.add_agent`; the route requires it too. Leaving a filled form asks for confirmation. **(asked)** | Entry where HR finds agents. |
| D17 | After saving: a confirmation, then `/agents/pieces?agent=<id>`, where the Engagement card lists the missing pieces with "Joindre". **(asked: pieces after saving)** | Files are never uploaded for an agent that does not exist yet. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q5` — the matricule format, and whether SyRH generates it. | Suggested in the bulletin style, editable (D6). |
| `Q35` — who edits contact details. | Gestion de carrière, at hiring. |
| Whether the bank account should be entered at hiring by Gestion de carrière. | No: Rémunération (bank account D16). |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
