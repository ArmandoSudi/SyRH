# Bank account — requirements

Roadmap phase **2.5 Bank account**: the bank and account number each agent is paid into, dated,
never overwritten (`REM-28`, `SOC-02`). Fifth phase of Milestone 2 (agent record, MVP).

Branch: `feature/bank-account`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges: `REM-28`, keep the banks' reference list and **attach to each agent their
  bank and account number**; block payment of an agent without a **validated** account. `REM-11`,
  pay in USD only, by bank transfer. `REM-20`, one Excel file per bank with matricule, name,
  account number and net amount. Section 3 lists "banque et numéro de compte bancaire" in the
  agent's pay data.
- `missions.md`: principle 3, an evolving fact is a dated row; principle 5, data affecting pay
  goes through entry then validation (phase 2.11); principle 9, least privilege — pay data is
  seen by the pay profiles only.
- Phase 1.7 created `referentiels.Banque` (code, nom, SWIFT/BIC, open from `date_ouverture`
  included to `date_fermeture` excluded), edited by Rémunération and the administrator.
- Phase 2.4 set the pattern for start-only histories (`Affectation`, `Classement`).
- Open questions: `Q33` (the real banks), `Q16` (the transfer file template).
- Readers to come: 2.11 Validation workflow (the account's status), 6.x payroll (the account in
  force on the pay date, the transfer file per bank, blocking without a validated account),
  2.15 Data import.

## Scope

### In scope

1. **One table** `CompteBancaire` in `apps.agents`: bank, account number and effective date, one
   row per change, several per agent.
2. **The rules**: one row per agent and effective date; the bank open on that date; a number
   format; one bank and number never held by two agents.
3. **Helper**: the account in force on a day.
4. **Editing in Django admin** on its own page, for Rémunération and its chef.
5. **Read-only API** for the pay profiles only, apart from the agent endpoints.
6. **Demo data**: accounts for the demo agents.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Validated status of an account; blocking payment without one | Phases 2.11, 6.x |
| Transfer file per bank (`REM-20`, `Q16`) | Milestone 6 |
| Checking a number against each bank's real format | `Q36`, then a later phase |
| Bank statement or scanned proof of the account | Phases 2.6, 2.7 |
| Accounts on a screen; writes through the API | Phases 2.9, 2.10 and the pay screens |
| Loading the real accounts | Phase 2.15 |
| A separate `paie` app | Milestone 6 |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and earlier phases.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One table** `CompteBancaire` (`agent`, `banque`, `numero`, `date_effet`) in `apps.agents`, `related_name` `comptes_bancaires`, `module = "paie"`. | It is part of the agent record (Milestone 2) but pay data; the module decides who sees its audit entries. The `paie` app comes with Milestone 6. |
| D2 | **Only the effective date is stored**, as phase 2.4: a row applies from its `date_effet` until the agent's next row; the last applies until further notice. **(asked)** | Payroll needs the account in force on each pay date, including back pay. |
| D3 | **One row per agent and `date_effet`** (unique constraint). | Two accounts on one day would leave the pay destination undefined. |
| D4 | All fields required. The `agent` never changes after creation; bank, number and date may be corrected in place (a typing error), the rules re-checked. A real change of account is a new row. | Same as positions D6. |
| D5 | Rows sort by agent, then `date_effet`. Label: `BANQUE — NUMÉRO depuis le JJ/MM/AAAA — MATRICULE`. | The label names the row in the audit log, seen by pay readers only (D15). |
| D6 | The entry date is `date_creation`; a `date_effet` in the past or the future is accepted. | A change of account announced for next month is entered today. |

### Rules

| # | Decision | Reason |
| --- | --- | --- |
| D7 | **Number format**: capital letters, digits, spaces and dashes, 5 to 34 characters; stored in capitals, surrounding spaces removed. Checked by a `CheckConstraint` and in the model with a French message. **(asked)** | Banks differ and `Q36` is open; 34 is the IBAN maximum. |
| D8 | **A bank and number belong to one agent only**: PostgreSQL exclusion constraint `EXCLUDE (banque WITH =, numero WITH =, agent WITH <>)`; the same agent may come back to an old account. Reported on `numero` by the model. **(asked: refused in the database)** | Two agents paid into one account is a fraud or a typing error. |
| D9 | The bank must be **open on `date_effet`**; a later closing is not checked. | As positions D9; a merged bank gets new rows from HR. |
| D10 | **No contract rule**: the date may fall before hiring or between contracts. | The account is where pay goes when there is pay; it may exist before hiring. |

### Helpers

| # | Decision | Reason |
| --- | --- | --- |
| D11 | **`Agent.compte_bancaire_au(jour)`**: the row with the latest `date_effet` on or before that day, or `None`; reads prefetched rows when present. | Payroll asks "where is this agent paid this month?". |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D12 | **In the database**: foreign keys `PROTECT`; the unique constraint (D3), the format check (D7) and the exclusion constraint (D8), each with a French message. | Principle 1. |
| D13 | **In the model**, from `clean()` and `save()`: closed bank on `banque`; number held by another agent on `numero`; changed agent on `agent`. | These rules read other rows. |
| D14 | Nothing is deleted: `default_permissions = NO_DELETE`; `delete()` raises. | Principle 8. |

### Access and admin

| # | Decision | Reason |
| --- | --- | --- |
| D15 | **Only profiles opening `paie`** read accounts: Rémunération, its chef, Direction RH. The audit entries, under module `paie`, follow the same rule. **(asked)** | Principle 9; an account number is sensitive. |
| D16 | **Rémunération and its chef** get view, add and change on `comptebancaire`, plus `view_agent` so that the agent can be picked; nobody gets delete. `COMPTE_BANCAIRE_EDIT_PERMISSIONS` in `roles.py`. **(asked)** | `REM-28` gives the accounts to Rémunération. The agent autocomplete needs view on agents. |
| D17 | **Own admin page** "Comptes bancaires": list with matricule, name, bank, number and date, searchable by matricule, name and number, filterable by bank; form with the agent by autocomplete. Gestion de carrière's agent page is unchanged. **(asked)** | Rémunération cannot change agents, and Django admin refuses saving an agent page without that right. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D18 | **Separate read-only endpoint** `/api/agents/<id>/comptes-bancaires/`: the agent's accounts in date order (`id`, `banque`, `banque_code`, `banque_nom`, `numero`, `date_effet`, base fields) and `compte_actuel`, the row in force today or `null`. Requires `access_agents` and `access_paie`. `/api/agents/` and `/api/agents/<id>/` are unchanged. **(asked)** | No field that appears or disappears by role; easy to prove nothing leaks. |

### Audit and demo data

| # | Decision | Reason |
| --- | --- | --- |
| D19 | `create_demo_agents` first runs the demo banks command (idempotent), then gives each agent with a contract an account dated on their hiring date; one agent changes bank later; one agent has a change dated in the future; the agent without contract has none. Running it twice changes nothing. | Covers the shapes of the endpoint and of "current". |
| D20 | `tech-stack.md`'s `agents/` line names the bank accounts and their `paie` audience. | The constitution lists what each app holds. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q36` (new) — the account number format of each bank. | The loose format of D7. |
| `Q33` — the real banks. | Demo banks only; the merge does not wait. |
| Who validates an account, and whether Gestion de carrière enters it at hiring. | Rémunération enters it; validation comes with 2.11 (`Q20` to `Q26`). |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D21 | The `numero` column holds 40 characters although 34 are allowed: the format rule (D7) alone reports a number that is too long, with one message, in the model and in PostgreSQL. A number held by another agent is reported on `numero` by the model, so `full_clean()` skips the exclusion constraint and shows one message. | A 34-character column added Django's own length message beside D7's, and refused a long raw insert before the check constraint. |
