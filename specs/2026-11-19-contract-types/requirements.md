# Contract types — requirements

Roadmap phase **1.4 Contract types**: CDI, CDD, stage, journalier. Fourth phase of Milestone 1
(reference data).

Branch: `feature/contract-types`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.1: the configurable reference data include "Types de contrat :
  durée indéterminée, durée déterminée, stage, journalier".
- Section 4.2: an agent's contract holds a **type**, a hiring date, a **probation period** and an
  **end date where relevant** ("date de fin éventuelle"). Contracts come in phase 2.3; they will
  point to the rows created here.
- `CAR-03`: follow the probation period and alert before it ends. `CAR-04`: follow fixed-term
  contracts and alert before they end. `TRA-04`: alerts on end of probation, end of contract and
  end of internship (Milestone 4). Phase 2.3 needs to know, from the type alone, whether a
  contract must have an end date and whether it may have a probation period.
- `ADM-19` to `ADM-23`: interns and day labourers are kept in registers separate from the agents',
  with a way to become an agent without re-typing. Those registers are phases 5.8 and 5.9.
- Section 1 (exit reasons): "fin de contrat à durée déterminée" is a possible exit reason
  (phase 1.6, `Q2`).
- `missions.md`, principle 3: history is never overwritten; principle 6: rules are parameters,
  not code; principle 8: nothing is physically deleted.
- Phase 1.3 set the closest pattern: a flat, dated table in `apps.referentiels` with a code and a
  name, the `closing_after_opening()` and `unique_per_period()` constraint helpers, the shared
  `check_closing_after_opening()` rule (1.3 D25), editing in Django admin, a read-only API filtered
  by date, a read-only tab on "Référentiels", a `DEBUG`-only demo command, and a section in
  `docs/user-guide.md`.
- The ARPTC's real list of contract types and their rules is not in the cahier des charges.

## Scope

### In scope

1. **One table in `apps.referentiels`**: `TypeContrat`, with a code, a name and two rule flags.
2. **Dated rows**: an opening date and an optional closing date; a type is renamed or retired by
   closing it.
3. **Database constraints** that keep codes unique at any date and the dates consistent.
4. **Editing in Django admin** for the same editors as the other reference tables.
5. **Read-only API**: one flat endpoint, rows open at a date (or all).
6. **Read-only tab** "Types de contrat" on the "Référentiels" screen.
7. **Demo data** for development: a management command that loads the four types of section 4.1
   and one retired type.
8. **User guide**: the new tab documented in `docs/user-guide.md`, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Giving an agent a contract (type, hiring date, probation, end date) | Phase 2.3 Contract |
| Enforcing the flags on a contract (end date required, probation allowed) | Phase 2.3, reading the flags of D2 |
| Probation length, notice periods, maximum length or renewals of a CDD | Not in the cahier des charges; asked in `Q30`; a parameter (1.8) if HR gives one rule, a field here later if it depends on the type |
| Separate registers for interns and day labourers (`ADM-23`) | Phases 5.8 and 5.9 |
| Alerts before the end of probation or contract | Milestone 4 (`CAR-03`, `CAR-04`, `TRA-04`) |
| "Fin de contrat" as an exit reason | Phase 1.6 (`Q2`) |
| Creating, correcting and closing rows from the app | Phase 1.9; Django admin until then |
| Loading the real ARPTC list | Entered by HR in Django admin (open point `Q30`) |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-19. The others follow
from [`missions.md`](../missions.md), [`tech-stack.md`](../tech-stack.md), the cahier des charges
and the pattern of phase 1.3.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One flat table** `TypeContrat`: `code` (up to 20 characters, saved in capitals), `nom` (up to 150), and the two flags of D2. No parent. **(asked)** | Section 4.1 lists the types as a plain list. |
| D2 | Two required booleans: **`duree_determinee`** ("Durée déterminée": a contract of this type must have an end date) and **`periode_essai`** ("Période d'essai": a contract of this type may have a probation period). **(asked)** | Section 4.2 gives a contract an end date "where relevant" and a probation period; `CAR-03` and `CAR-04` follow them. Phase 2.3 reads the rule from the type instead of hard-coding "CDD" (principle 6). |
| D3 | Stage and journalier are contract types like the others. Whether interns and day labourers live in separate registers (`ADM-23`) is decided by phases 5.8 and 5.9, which may point to these types. **(asked)** | Section 4.1 lists them as contract types; deciding the registers now would design phases 5.8 and 5.9 without their requirements. |
| D4 | The code is unique among types open at the same time; the name is not constrained. | Same as fonctions (1.3 D3). |
| D5 | Types sort by name. | Four to ten rows; no order is given by the cahier des charges. |

### History

| # | Decision | Reason |
| --- | --- | --- |
| D6 | `date_ouverture` (required) and `date_fermeture` (optional). A type is **open on day D** when `date_ouverture <= D < date_fermeture`. **(asked)** | Same rule as every reference table (1.3 D5). |
| D7 | A type whose rules change (a flag) or whose name changes is closed and a successor opened, with the same code if HR wants; a typing error may be corrected in place. A type no longer used is closed with no successor. Every change is in the audit log. | Principle 3: an old contract keeps the rules it was signed under. |
| D8 | Nothing is deleted: no delete permission on the table, and the API is read-only. | Principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D9 | **In the database**: closing date after opening date (`closing_after_opening()`); code unique per period (`unique_per_period()`). | Principle 1; reuses the phase 1.2 helpers. |
| D10 | **In the model**: code saved in capitals, and `check_closing_after_opening()` (1.3 D25), from `clean()`; capitals also from `save()`. Same methods as `Fonction`. | No rule reads other rows. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D11 | Every holder of `access_referentiels` **reads** the types, through the API and the screen. | Every service shows an agent's contract type. |
| D12 | **Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière** get view, add and change on `TypeContrat`. Nobody gets delete. **(asked)** | Gestion de carrière writes the contract (section 3, `CAR-01`); same editors as 1.1 to 1.3. |
| D13 | The permissions go into `roles.py` as a `TYPE_CONTRAT_EDIT_PERMISSIONS` tuple, added to `REFERENTIELS_EDIT_PERMISSIONS`. | One declaration; the group setup only ever adds (1.3 D12). |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D14 | One admin class with `BaseModelAdmin`: list columns (code, nom, the two flags, dates), filters (each flag, the shared "ouvert aujourd'hui" filter), search on code and name. Each flag has a help text that says what phase 2.3 will do with it. | Same as the other reference tables; the help texts tell HR what ticking a box means. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D15 | `TypeContrat` inherits `BaseModel` with `module = "referentiels"`. Row label: `CODE — Nom`. | Captured automatically (phase 0.6). |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D16 | One endpoint `/api/referentiels/types-contrat/`: the rows open on `?date=` (default today), or all with `?toutes=1`, through `PeriodeMixin`. Not paginated. Writes answer `405`. | Mirrors the other reference endpoints. |
| D17 | Fields: `id`, `code`, `nom`, `duree_determinee`, `periode_essai`, `date_ouverture`, `date_fermeture`, plus the base fields. Ordered by D5. | What the screen and the contract form of phase 2.3 need. |
| D18 | `HasModuleAccess("referentiels")`. An invalid `date` answers `400` on that field. | `tech-stack.md`. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D19 | A fifth tab **"Types de contrat"** on the "Référentiels" page, after "Fonctions". **(asked)** | The page has a tab per reference table. |
| D20 | The tab shows a table: code, nom, "Durée déterminée" and "Période d'essai" (each "Oui" or "Non"), opening and closing dates. A date picker "Types au" (default today) and a text filter on code and name; loading, empty and error states. | Same controls as the Fonctions tab. |
| D21 | The screen is read-only. The tab, its date and its filter stay while the user moves around, in their own `typesContrat` object of the store. The text filter reuses `normalise()` from `components/tree.ts`. | Same as 1.3 D20; one way to ignore case and accents. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D22 | `create_demo_types_contrat` loads the four types of section 4.1 in development: CDI (no end date, probation), CDD (end date, probation), Stage (end date, no probation), Journalier (no end date, no probation), and one retired type with no successor (Contrat d'apprentissage, closed in 2023). It refuses to run when `DEBUG` is off, and running it twice changes nothing; its rows have no author. | Shows both flags in all four combinations, and a retirement, which phase 1.3's demo (a rename) did not. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D23 | `docs/user-guide.md` gets a "Types de contrat" subsection under "Reference data", with screenshots taken by `docs/capture_screenshots.py` (extended for the new tab), and `docs/user-guide.html` is rebuilt. **(asked)** | The guide describes the screen tab by tab. |
| D24 | `tech-stack.md`: the `referentiels` lines of the repository and frontend layouts name the contract types. | `tech-stack.md` changes with the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q30` — the ARPTC's contract types: are there others (apprentissage, consultance, détachement entrant)? Which require an end date and which allow a probation period? How long is the probation period, does it depend on the type or the catégorie, and can a CDD be renewed? | The four types of section 4.1 with the flags of D22; probation length and renewals are not modelled. Added to `docs/questions-ouvertes.md` by this phase; the merge does not wait for the answer. |
| `Q2` — other exit reasons, including the end of a fixed-term contract. | Phase 1.6. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D25 | `Fonction` and `TypeContrat` share their rules through one `FlatListRules` mixin (label `CODE — Nom`, code in capitals, `check_closing_after_opening()`), as plan step 1.3 allowed. `Fonction`'s tests pass unchanged. | The two models repeated the same four methods word for word. |
| D26 | The Fonctions and Types de contrat tabs filter through one generic `filterByCodeAndName()` in `components/lists.ts`, as plan step 5.1 allowed; `components/fonctions.ts` keeps only the nature colours. | The two filters were identical. |
