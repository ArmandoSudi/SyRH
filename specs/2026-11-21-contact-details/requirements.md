# Contact details — requirements

Roadmap phase **2.2 Contact details**: an agent's address, phones, email and emergency contact.
Second phase of Milestone 2 (agent record, MVP).

Branch: `feature/contact-details`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.2: the agent's file has a "Coordonnées" block: **adresse,
  téléphone, courriel, personne à contacter en cas d'urgence**. It has no requirement ID of its
  own.
- `SOC-02` lists the data whose dated history must be kept: grade, fonction, salaire,
  affectation, état civil. Contact details are not in it; the audit log (`TRA-10`) already keeps
  every old value with its author and time.
- Phase 2.1 created `apps.agents` and `Agent`: identity only, never deleted, edited in Django
  admin by Gestion de carrière and its chef, read by every profile opening Agents through
  `/api/agents/`.
- `TRA-04` and `REM-18` will send alerts and payslips by email (Milestones 4 and 6); they will read
  the email recorded here.
- Readers to come: 2.9 creation form, 2.10 summary page, 2.15 data import, 4.4 notifications.

## Scope

### In scope

1. **One table `Coordonnees`** in `apps.agents`, at most one row per agent.
2. **The rules**: required address, town and phone; phone format; valid email; an emergency
   contact given whole or not at all.
3. **Editing in Django admin**, inline on the agent page, for the editors of 2.1.
4. **Read-only API**: the contact details nested in the agent detail.
5. **Demo data**: contact details for the demo agents.
6. **Open question `Q35`** added to `docs/questions-ouvertes.md`.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Dated history of addresses | Not planned: the audit log keeps old values (D3) |
| Several emergency contacts | Answer to `Q35`, then a later phase |
| Sending email (alerts, payslips) | Phases 4.4 and 6.11 |
| Contact details on a screen | Phases 2.9 and 2.10 |
| Writes through the API | Phase 2.9 creation form |
| Loading the real contact details | Phase 2.15 Data import |
| A reference list of communes and towns | Not planned: free text (D5) |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phase 2.1.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One table `Coordonnees`** in `apps.agents`, `module = "agents"`, with a one-to-one `agent` (`on_delete=PROTECT`, `related_name="coordonnees"`). An agent has no row until one is entered. **(asked)** | The contact block belongs to the agent record; keeping it apart from `Agent` lets the identity be created first and the import (2.15) load agents whose contact details are missing. |
| D2 | Fields: `adresse` (street and number), `commune`, `ville`, `telephone`, `telephone_secondaire`, `courriel`, `urgence_nom`, `urgence_lien`, `urgence_telephone`. **(asked)** | The four items of section 4.2, split where a later screen or report needs the part (town for statistics, the second phone for reaching an agent). |
| D3 | **Current values, corrected in place.** No dated rows. **(asked)** | Contact details are not in `SOC-02`; nothing is computed from a past address. The audit log keeps every old value, with author and time. |
| D4 | The `agent` never changes after creation. | A row describes one agent; moving it would rewrite another agent's file. |
| D5 | `adresse` and `ville` required, `commune` optional; all free text, trimmed. | Every agent can be written to; Kinshasa addresses use communes, other towns may not. |
| D6 | Label `Coordonnées de MATRICULE — NOM Postnom Prénom` (the agent's label). | Names the row in the audit log. |

### Phones and email

| # | Decision | Reason |
| --- | --- | --- |
| D7 | `telephone` required, `telephone_secondaire` optional. A phone is stored trimmed with runs of spaces collapsed, and holds an optional leading `+` then digits and single spaces, 8 to 20 characters (`+243 81 234 5678`, `0812345678`). | Numbers are typed as HR finds them; the rule catches letters and typing slips without forcing one national format. |
| D8 | `courriel` optional, a valid address (Django's `EmailField`), stored trimmed and lower case. Not unique. | Not every agent has an email; two agents may share a family address. |

### Emergency contact

| # | Decision | Reason |
| --- | --- | --- |
| D9 | **One emergency contact**, optional as a whole: `urgence_nom`, `urgence_lien` (free text: "Épouse", "Frère"...) and `urgence_telephone`. **(asked)** | Section 4.2 names one person. Several contacts wait for `Q35`. |
| D10 | Name and phone go together: both blank or both given; the relationship is optional. | A name without a number, or a number without a name, cannot be used in an emergency. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D11 | **In the database**: one row per agent (the one-to-one's unique index); `adresse`, `ville` and `telephone` not blank; each phone, when given, matching the pattern of D7; the emergency name and phone both blank or both given. | Principle 1. |
| D12 | **In the model**, from `clean()` and `save()`, with French messages per field: the normalisation of D5, D7 and D8; the phone pattern on its field; a missing emergency name or phone on the empty one; a changed agent on `agent`. | The message says which field to fix. |
| D13 | Nothing is deleted: `default_permissions = NO_DELETE`; `Coordonnees.delete()` raises. | Principle 8; a contact block is corrected, never removed. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D14 | Every holder of `access_agents` **reads** the contact details through the agent detail. | Every service may need to reach an agent. Whether some should not see addresses is part of `Q35`. |
| D15 | **Gestion de carrière and its chef** get view, add and change on `coordonnees`; nobody gets delete. Declared as `COORDONNEES_EDIT_PERMISSIONS` in `roles.py`, added with `AGENT_EDIT_PERMISSIONS`. **(asked)** | Same editors as the identity until `Q35` says otherwise. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D16 | A **stacked inline** "Coordonnées" on the agent page (`max_num = 1`, no delete box), its fields grouped as address, phones and email, emergency contact. The inline stamps the signed-in user as author of its row (`save_formset`). No separate admin page. | One page per agent; the authors stay right in the audit log. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D17 | `Coordonnees` inherits `BaseModel` with `module = "agents"`; the label of D6. | Captured automatically, read by holders of `agents`. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D18 | `/api/agents/<id>/` gains `coordonnees`: an object with the fields of D2 plus the base fields, or `null` when none was entered. The list `/api/agents/` does not include it. Still read-only. | The summary page (2.10) reads one agent at a time; the list stays light for 2.8. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D19 | `create_demo_agents` also gives each demo agent contact details: Kinshasa and provincial addresses, some agents with no second phone, no email or no emergency contact, and one agent with none at all. Running it twice changes nothing. | Something to see in the admin and the API, with the empty cases. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D20 | `docs/questions-ouvertes.md` gets `Q35`; `tech-stack.md`'s `agents/` line names the contact details. No user guide change: there is no screen. | Open points are tracked in one place; `tech-stack.md` changes with the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q35` — contact details: should Administration du personnel edit them too; should every service see an agent's address and phones, or only the HR services; should an agent have several emergency contacts? | Gestion de carrière and its chef edit; every profile opening Agents reads; one emergency contact. Added by this phase; the merge does not wait for the answer. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
