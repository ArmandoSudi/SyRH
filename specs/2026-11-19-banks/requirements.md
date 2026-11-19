# Banks — requirements

Roadmap phase **1.7 Banks**: the banks agents are paid through. Seventh phase of Milestone 1
(reference data).

Branch: `feature/banks`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.1: the reference data include "Banques : dénomination, code,
  modèle du fichier de virement". Section 4.2: the agent's pay data hold "banque et numéro de
  compte bancaire".
- `REM-28`: keep the list of banks, attach to each agent a bank and an account number, and block
  payment of an agent without a validated bank account. `REM-11`: pay is in USD, by bank transfer
  only. `REM-20`: for each bank, the Excel file that goes with the employer's transfer order
  (matricule, name, account number, net amount, number of agents, total).
- `Q16`: which columns does each bank expect in its transfer file? Unanswered.
- Later phases: **2.5 Bank account** (bank and account number per agent, reading this list),
  **6.13 Bank transfer file** (`REM-20`, `Q16`).
- Pay is the Rémunération service's domain; the Administrateur système has no access to pay
  amounts, but a bank list holds none. Until now, only Gestion de carrière and the administrator
  edit reference data.
- Phases 1.3 and 1.4 set the pattern for a flat dated list (`FlatListRules`).
- The ARPTC's real list of banks is not in the cahier des charges.

## Scope

### In scope

1. **One table in `apps.referentiels`**: `Banque`, with a code, a name and an optional SWIFT/BIC
   code.
2. **Dated rows** with database constraints and model rules.
3. **Editing in Django admin** by the Rémunération profiles and the administrator.
4. **Read-only API**: one flat endpoint, rows open at a date (or all).
5. **Read-only tab** "Banques" on the "Référentiels" screen.
6. **Demo data** for development.
7. **User guide**: the new tab documented in `docs/user-guide.md`, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| The transfer file template per bank (columns, format) | Phase 6.13 Bank transfer file, once `Q16` is answered |
| Each agent's bank and account number; validating an account; blocking payment without one (`REM-28`) | Phase 2.5 Bank account, and the payroll phases |
| Account number formats (RIB, IBAN) | Phase 2.5 |
| Bank branches (agences), addresses, contacts | Not asked for; added if HR needs them |
| Creating, correcting and closing rows from the app | Phase 1.9; Django admin until then |
| Loading the real ARPTC list | Entered by Rémunération in Django admin (open point `Q33`) |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phases 1.1 to 1.6.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One flat table `Banque`**: `code` (up to 20 characters, in capitals), `nom` (up to 150), `swift` (optional, the SWIFT/BIC code), the dates. **(asked)** | Section 4.1 "dénomination, code"; the SWIFT/BIC identifies the bank in a transfer and costs nothing to keep. |
| D2 | `swift`, when set, is saved in capitals and has the SWIFT/BIC shape: 4 letters (bank), 2 letters (country), 2 letters or digits (place), optionally 3 letters or digits (branch), so 8 or 11 characters. Blank is stored as an empty string. | A typing error in a transfer identifier is caught at entry (principle 1). |
| D3 | **The transfer file template is not modelled here.** **(asked)** | `Q16` is open; phase 6.13 adds what each bank's file needs, as fields or a related table, when the answer is known. |
| D4 | The code is unique among banks open at the same time; names and SWIFT/BIC codes are not constrained. | Same as 1.3 D3. Two rows may share a SWIFT/BIC across a rename; a duplicate open one is a data question HR sees on the list. |
| D5 | Banks sort by name. | Short list; the name is what HR looks for. |

### History

| # | Decision | Reason |
| --- | --- | --- |
| D6 | `date_ouverture` (required) and `date_fermeture` (optional): open on day D when `date_ouverture <= D < date_fermeture`. | Same as every reference table. |
| D7 | A bank that is renamed, merged or whose SWIFT/BIC changes is closed and a successor opened, with the same code if HR wants; a typing error may be corrected in place. A bank no longer used is closed with no successor. | Principle 3: a transfer of 2024 names the bank as it was in 2024. Same as 1.4 D7. |
| D8 | Nothing is deleted: no delete permission, and the API is read-only. | Principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D9 | **In the database**: closing date after opening date; code unique per period; `swift` empty or of the shape of D2. | Principle 1; the phase 1.2 helpers. |
| D10 | **In the model**: `FlatListRules` (code in capitals, label `CODE — Nom`, reversed dates on `date_fermeture`), plus `swift` trimmed and put in capitals, and a French message on `swift` when its shape is wrong. | The message says which field to fix. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D11 | Every holder of `access_referentiels` **reads** the list. | Every service sees an agent's bank. |
| D12 | **Administrateur système, Rémunération and Chef de service — Rémunération** get view, add and change. Nobody gets delete. Gestion de carrière reads only. **(asked)** | Banks belong to pay (`REM-28`); the administrator keeps every reference table. |
| D13 | The permissions go into `roles.py` as `BANQUE_EDIT_PERMISSIONS`, **not** into `REFERENTIELS_EDIT_PERMISSIONS`; `EXTRA_PERMISSIONS` gains the two Rémunération groups, so their demo accounts get "Statut équipe" (re-run `create_demo_users`). | The other reference tables keep their editors; one declaration per editor set. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D14 | `BanqueAdmin`: code, name, SWIFT/BIC, dates; "ouvert aujourd'hui" filter; search on code, name and SWIFT/BIC. | Same as the other flat lists. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D15 | `Banque` inherits `BaseModel` with `module = "referentiels"`; label `CODE — Nom`. | Captured automatically. The audit log shows it to every reader of Référentiels, the Rémunération profiles included. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D16 | `/api/referentiels/banques/`: rows open on `?date=` (default today) or all with `?toutes=1`, through `PeriodeMixin`. Not paginated. Writes answer `405`. `HasModuleAccess("referentiels")`; an invalid `date` answers `400` on that field. | Mirrors the other reference endpoints. |
| D17 | A bank returns `id`, `code`, `nom`, `swift` and the dates, plus the base fields, ordered by D5. | What the screen and phase 2.5 need. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D18 | An eighth tab **"Banques"** on "Référentiels", after "Sorties et suspensions". **(asked)** | One tab per reference area. |
| D19 | The tab shows a table: code, name, SWIFT/BIC ("—" when blank), dates. A date picker "Banques au" (default today), a text filter on code, name and SWIFT/BIC; loading, empty and error states. | Same as the contract types tab. |
| D20 | The screen is read-only. The tab, its date and filter stay while the user moves around, in their own `banques` object of the store. `filterByCodeAndName` of `components/lists.ts` also matches the SWIFT/BIC. | Same as the other tabs. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D21 | `create_demo_banques` loads, in development, about six **fictional** banks with fictional SWIFT/BIC codes in the Congo (`CD`), one without a SWIFT/BIC, and one closed in the past and replaced by a successor under a new name and the same code (a merger). It refuses to run when `DEBUG` is off, running it twice changes nothing, and its rows have no author. | Shows a blank SWIFT/BIC and history, without passing invented identifiers off as real banks' codes. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D22 | `docs/user-guide.md` gets a "Banques" subsection, with screenshots taken by `docs/capture_screenshots.py`; the tab count and "Who changes the reference data" are updated (the banks are changed by Rémunération); `docs/user-guide.html` is rebuilt. **(asked)** | The guide describes the screen tab by tab. |
| D23 | `tech-stack.md`: the `referentiels` lines name the banks. | `tech-stack.md` changes with the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q16` — the columns of each bank's transfer file. | Not modelled (D3). Already in `docs/questions-ouvertes.md`. |
| `Q33` — the ARPTC's banks: which banks pay agents, with which code and SWIFT/BIC? Should Gestion de carrière be able to add a bank when it records a new agent's account? | The demo list of D21; Rémunération and the administrator enter the real list in Django admin. Added to `docs/questions-ouvertes.md` by this phase; the merge does not wait for the answer. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
