# General parameters — requirements

Roadmap phase **1.8 General parameters**: the dated numbers that business rules read instead of
hard-coding them. Eighth phase of Milestone 1 (reference data).

Branch: `feature/general-parameters`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- `missions.md`, principle 6: **rules are parameters, not code** (pay scales, age limits,
  durations, maximum number of children).
- Cahier des charges, section 2.2: retirement at **30 years of career** (counted from the hiring
  date at the ARPTC) or at **65 years of age**, whichever comes first. `CAR-14`: alerts 12, 6 and
  3 months before either.
- `ADM-15`, `ADM-16`: a child stops being a dependant at **25**. `ADM-17`: the number of children
  sent to payroll is capped by a **configurable maximum**. Both are settled in
  `docs/questions-ouvertes.md` ("Déjà tranché"); the maximum's value is not given.
- `Q1`: is a child's entitlement extended past 25 for studies? MVP assumption: no.
- The Administrateur système "gère comptes, profils et paramètres" (section 3). Pay scales are
  Rémunération's parameters (section 7, `REM-23`) and come with Milestone 6.
- Readers to come: phase 2.13 Children and 4.3 Dependant alerts (age limit), 6.x family
  allowances (maximum), 3.7 Retirement forecast and 4.2 Career alerts (retirement age, career
  length), 3.5 Seniority.

## Scope

### In scope

1. **One table in `apps.referentiels`**: `Parametre`, a dated integer value for one of a fixed
   list of keys.
2. **The key list in code**, with each key's label, unit and bounds.
3. **A helper** that returns a key's value at a date, for later phases.
4. **Editing in Django admin** for the usual reference data editors.
5. **Read-only API**: one flat endpoint, values open at a date (or all).
6. **Read-only tab** "Paramètres" on the "Référentiels" screen.
7. **Demo data** for development.
8. **User guide**: the new tab documented in `docs/user-guide.md`, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Alert delays (12, 6, 3 months) | Phase 4.2 Career alerts, as new keys if HR wants them configurable |
| Pay scales, rates and formulas (`REM-23`) | Milestone 6, Rémunération's own parameters |
| Durations of suspensions | Already on `TypeSuspension` (phase 1.6) |
| Applying the parameters (dependants, retirement, seniority) | The phases listed in the context |
| Text, date or decimal parameters | Added with the key that needs them |
| Editing from the app | Phase 1.9; Django admin until then |
| Loading the real values in production | Entered in Django admin (open point `Q34`) |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phases 1.1 to 1.7.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One table `Parametre`**: `cle` (one of the keys of D2), `valeur` (a positive integer), the dates. **(asked)** | A key/value table holds every number of principle 6 without a migration per value; a fixed key list keeps later phases from looking up a name that does not exist. |
| D2 | **The keys are a fixed list in code** (`Parametre.Cle`), in this order, each with a label, a unit and bounds: `age_limite_enfant` "Âge limite des enfants à charge" (ans, 18 to 30); `enfants_max` "Nombre maximal d'enfants pris en charge" (enfants, 1 to 20); `age_retraite` "Âge de la retraite" (ans, 55 to 75); `duree_carriere` "Durée de carrière avant la retraite" (ans, 20 to 45). **(asked)** | Each key is read by code in a later phase; adding one is a code change made by that phase. The bounds catch a typing error (250 instead of 25). |
| D3 | **One value per key at a time**: two rows of the same key cannot overlap. A key with no open row at a date has no value then. | A rule reads one number on a given day. |
| D4 | Rows sort by the key order of D2, then by opening date. | The screen and the admin show the keys in a stable order. |
| D5 | **A helper `Parametre.valeur_au(cle, jour)`** returns the integer open on that day, or raises `ParametreManquant` with a French message naming the key and the date. | Later phases call one function; a missing value stops them loudly rather than using a guess. |

### History

| # | Decision | Reason |
| --- | --- | --- |
| D6 | `date_ouverture` (required) and `date_fermeture` (optional): open on day D when `date_ouverture <= D < date_fermeture`. | Same as every reference table. |
| D7 | A new value is recorded by closing the current row and opening a new one from its effective date; a typing error in a value may be corrected in place. The key never changes after creation. | Principle 3: a child who turned 25 in 2024 was judged on the limit of 2024. |
| D8 | Nothing is deleted: no delete permission, and the API is read-only. | Principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D9 | **In the database**: closing date after opening date; one value per key per period; `cle` limited to the keys of D2; `valeur` within its key's bounds (one check built from the key list). | Principle 1. |
| D10 | **In the model**: reversed dates on `date_fermeture`; the bounds on `valeur` with a French message giving the key's range and unit; the fixed key on `cle`, from `clean()` and `save()`. | The message says which field to fix and what is allowed. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D11 | Every holder of `access_referentiels` **reads** the parameters. | Every service applies them. |
| D12 | **Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière** get view, add and change. Nobody gets delete. **(asked)** | Same editors as 1.1 to 1.6. Whether Administration du personnel or Rémunération should edit the dependant keys is part of `Q34`. |
| D13 | The permissions go into `roles.py` as `PARAMETRE_EDIT_PERMISSIONS`, added to `REFERENTIELS_EDIT_PERMISSIONS`. | One declaration; the group setup only adds. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D14 | `ParametreAdmin`: key, value, unit, dates; filters on the key and "ouvert aujourd'hui"; the key read-only when changing a row; the unit and bounds shown as help next to the value. | Same as the other reference tables; the editor sees what is allowed. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D15 | `Parametre` inherits `BaseModel` with `module = "referentiels"`; label `Libellé : valeur unité`, for example `Âge de la retraite : 65 ans`. | Captured automatically; the label says what changed. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D16 | `/api/referentiels/parametres/`: rows open on `?date=` (default today) or all with `?toutes=1`, through `PeriodeMixin`. Not paginated. Writes answer `405`. `HasModuleAccess("referentiels")`; an invalid `date` answers `400` on that field. | Mirrors the other reference endpoints. |
| D17 | A row returns `id`, `cle`, `cle_libelle`, `unite`, `valeur` and the dates, plus the base fields, ordered by D4. | The screen shows the label and unit without its own copy of them. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D18 | A ninth tab **"Paramètres"** on "Référentiels", after "Banques". **(asked)** | One tab per reference area. |
| D19 | The tab shows one row per key of D2, in order: label, value with its unit ("25 ans"), dates; a key with no value at the date shows "Non renseigné". A date picker "Paramètres au" (default today); no text filter (four rows). Loading, empty and error states. | Answers "what is the retirement age on this date?"; a missing value is visible, not hidden. |
| D20 | The screen is read-only. The tab and its date stay while the user moves around, in their own `parametres` object of the store. The client's key list (`components/parametres.ts`) matches the backend's, checked by a backend test. | Same as the other tabs and the event list of 1.5. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D21 | `create_demo_parametres` loads, in development, from 1 January 2015: child age limit 25, retirement age 65, career length 30, and a maximum of 4 children until 1 January 2020 then 6 (fictional values: the real maximum is `Q34`). It refuses to run when `DEBUG` is off, running it twice changes nothing, and its rows have no author. | The confirmed values, plus one change over time to show the history. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D22 | `docs/user-guide.md` gets a "Paramètres" subsection, with screenshots taken by `docs/capture_screenshots.py`; the tab count and "Who changes the reference data" are updated; `docs/user-guide.html` is rebuilt. **(asked)** | The guide describes the screen tab by tab. |
| D23 | `tech-stack.md`: the `referentiels` lines name the general parameters. | `tech-stack.md` changes with the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q1` — is a child's entitlement extended past 25 for studies? | No: a single age limit, no extension. Already in `docs/questions-ouvertes.md`. |
| `Q34` — the real values: the maximum number of children covered, and since when each value has applied; should Administration du personnel or Rémunération edit the dependant parameters; should the alert delays (12, 6, 3 months) be parameters? | The demo values of D21; the usual editors; alert delays decided in phase 4.2. Added to `docs/questions-ouvertes.md` by this phase; the merge does not wait for the answer. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D24 | `Cle` and the `DEFINITIONS` of each key's unit and bounds are declared at module level (`Parametre.Cle` is an alias), and the bounds constraint is built from `DEFINITIONS`. | One list feeds the choices, the database check, the admin help and the messages, as the event kinds of 1.5 (D27 there). |
| D25 | The tab shows no row at all when the values cannot be loaded, rather than four "Non renseigné". | "Non renseigné" would wrongly say the values are missing. |
