# Exit and suspension reasons — requirements

Roadmap phase **1.6 Exit and suspension reasons**: why an agent leaves for good, and the
positions that suspend a career without ending it. Sixth phase of Milestone 1 (reference data).

Branch: `feature/exit-suspension-reasons`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.1: the reference data include "motifs de sortie".
- Section 2.2, exit reasons: retirement at 30 years of career, retirement at 65 years of age,
  resignation, death; "le référentiel des motifs reste paramétrable pour accueillir d'autres cas
  (licenciement, fin de contrat à durée déterminée)".
- Section 2.3, career suspensions: **mise en disponibilité** (2 years, renewable once, 4 years at
  most; a second renewal is refused) and **détachement** (length set by the decision). During
  both, pay, family allowances and care vouchers stop. "La période de détachement compte dans les
  30 ans de carrière"; whether the disponibilité counts is open (`Q3`).
- `CAR-16`: an exit records its reason, effective date and supporting document ("décision de
  retraite, lettre de démission, acte de décès"). `CAR-08`: a suspension records its decision and
  dates. `CAR-14`, `CAR-15`: retirement alerts and forecast. `CAR-18`: on death, the heirs come
  from the dependants. `SOC-07`, `CAR-10`: seniority.
- `Q2`: other exit reasons (dismissal, end of contract, removal, unfitness)? MVP assumption: a
  configurable list starting with death, resignation and retirement. `Q3`: MVP assumption: a
  "counts toward seniority" flag per suspension type.
- Phase 1.5 decided that each exit reason, not the "Sortie" event, names the document it requires
  (document types D3). Phase 1.4 set the pattern for a flat dated list whose flags are rules for
  later phases (`TypeContrat`, `FlatListRules`).
- None of the events exists yet: suspensions are phase 3.4, seniority 3.5, exits 3.6, the
  retirement forecast 3.7, alerts 4.2.

## Scope

### In scope

1. **Two tables in `apps.referentiels`**:
   - `MotifSortie`: the reasons an agent leaves for good, with the document each requires and
     whether it is a retirement or a death;
   - `TypeSuspension`: the positions that suspend a career, with the document each requires,
     whether it counts toward seniority, its maximum length and its maximum renewals.
2. **Dated rows** with database constraints and model rules that keep the periods consistent, the
   document type included.
3. **Editing in Django admin** for the same editors as the other reference tables.
4. **Read-only API**: two flat endpoints, rows open at a date (or all).
5. **Read-only tab** "Sorties et suspensions" on the "Référentiels" screen.
6. **Demo data** for development.
7. **User guide**: the new tab documented in `docs/user-guide.md`, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Recording a suspension, its renewals and the return to service; refusing a renewal beyond the maximum; stopping pay, allowances and care vouchers (`CAR-08`, `Q4`) | Phase 3.4 Suspensions, reading `TypeSuspension` |
| Computing seniority, honouring `compte_anciennete` (`CAR-10`, `SOC-07`) | Phase 3.5 Seniority |
| Recording an exit, deactivating the agent (`CAR-16`, `CAR-19`) | Phase 3.6 Exit, reading `MotifSortie` |
| The retirement thresholds (30 years, 65 years) | Phase 1.8 General parameters |
| Retirement forecast and alerts (`CAR-14`, `CAR-15`) | Phases 3.7 and 4.2, using the `retraite` flag |
| Heirs on death (`CAR-18`); final settlement (`CAR-17`) | Phase 3.6 and Milestone 6, using the `deces` flag |
| Resignation notice (préavis) length | Phase 3.6, if HR confirms it is a parameter (open point `Q32`) |
| Exit documents (attestation de service, certificat de fin de service, `CAR-20`) | Phase 3.6 or later |
| Creating, correcting and closing rows from the app | Phase 1.9; Django admin until then |
| Loading the real ARPTC lists | Entered by HR in Django admin (open points `Q2`, `Q3`, `Q32`) |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phases 1.1 to 1.5.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **Two flat tables**, each with `code` (up to 20 characters, in capitals), `nom` (up to 150), a required `type_document` (`PROTECT`) and the dates. **(asked)** | Section 4.1 and `Q2`, `Q3`: both lists are reference data HR maintains (principle 6). Exit reasons and suspensions are different events with different rules, so two tables, not one with a kind. |
| D2 | `MotifSortie` adds two booleans: **`retraite`** (the reason is a retirement: phases 3.7 and 4.2 count it in the forecast and alerts) and **`deces`** (the reason is a death: phase 3.6 turns to the heirs, `CAR-18`). Both cannot be set on one reason. **(asked)** | Later phases must not recognise a retirement or a death by its code, which HR chooses (principle 6). |
| D3 | `TypeSuspension` adds **`compte_anciennete`** (required boolean: the period counts toward seniority and the 30 years of career), **`duree_max_mois`** (optional positive integer: the longest single period; blank when the decision sets it) and **`renouvellements_max`** (optional integer, zero or more: how many times a period may be renewed; blank for no limit). **(asked)** | Section 2.3: 2 years renewable once for disponibilité, a length set by the decision for détachement; `Q3`: the seniority flag. Phase 3.4 enforces them; they stay parameters, not code. |
| D4 | `type_document` is the document the exit or suspension rests on: the decision of retirement, the resignation letter, the death certificate, the decision of disponibilité or détachement. One document type may serve several reasons. **(asked)** | Document types D3; `CAR-16`, `CAR-08`. Documents every exit needs whatever its reason stay on the "Sortie" event of `PieceRequise`. |
| D5 | Codes are unique among rows of the same table open at the same time; names are not constrained. | Same as 1.3 D3 and 1.4 D4. |
| D6 | Both tables sort by name. | Short lists; the name is what HR looks for. |

### History

| # | Decision | Reason |
| --- | --- | --- |
| D7 | Both tables have `date_ouverture` (required) and `date_fermeture` (optional), with the usual rule: open on day D when `date_ouverture <= D < date_fermeture`. | Same as every reference table. |
| D8 | A row whose rules change (its document, a flag, a duration, renewals) or whose name changes is closed and a successor opened, with the same code if HR wants; a typing error may be corrected in place. A row no longer used is closed with no successor. | Principle 3: an exit recorded in 2025 keeps the reason and rules of 2025. Same as 1.4 D7. |
| D9 | A row lies within its document type's period: it cannot open before the type nor stay open after it, and a document type cannot be closed while a reason or suspension type pointing to it stays open after that date. | No open row points to a closed document. Same as document types D8. |
| D10 | Nothing is deleted: no delete permission on either table, and the API is read-only. | Principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D11 | **In the database**: closing date after opening date; code unique per period on each table; not both `retraite` and `deces`; `duree_max_mois` greater than zero when set; `renouvellements_max` zero or more; `PROTECT` on both foreign keys. | Principle 1; the phase 1.2 helpers. |
| D12 | **In the model**: both use `FlatListRules` (code in capitals, label `CODE — Nom`, reversed dates on `date_fermeture`) plus the document period of D9, from `clean()` and `save()`, with French messages per field: "retraite" and "décès" together on `deces`, the document periods on `date_ouverture` / `date_fermeture`. `TypeDocument`'s closing check also looks at its exit reasons and suspension types. | One copy of each rule; the messages say which field to fix. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D13 | Every holder of `access_referentiels` **reads** both tables. | Every service sees an agent's exit or suspension. |
| D14 | **Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière** get view, add and change on both tables. Nobody gets delete. **(asked)** | Gestion de carrière records exits and suspensions; same editors as 1.1 to 1.5. |
| D15 | The permissions go into `roles.py` as `SORTIE_EDIT_PERMISSIONS`, added to `REFERENTIELS_EDIT_PERMISSIONS`. | One declaration; the group setup only adds. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D16 | `MotifSortieAdmin`: code, name, document, retraite, décès, dates; filters on retraite, décès and "ouvert aujourd'hui"; search on code and name. `TypeSuspensionAdmin`: code, name, document, compte dans l'ancienneté, durée maximale, renouvellements, dates; filters on compte dans l'ancienneté and "ouvert aujourd'hui"; search. The document through autocomplete on both. | Same as the other flat lists (1.3, 1.4) and the document autocomplete of 1.5. |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D17 | Both models inherit `BaseModel` with `module = "referentiels"`; label `CODE — Nom`. | Captured automatically. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D18 | Two endpoints, `/api/referentiels/motifs-sortie/` and `/api/referentiels/types-suspension/`: rows open on `?date=` (default today) or all with `?toutes=1`, through `PeriodeMixin`. Not paginated. Writes answer `405`. `HasModuleAccess("referentiels")`; an invalid `date` answers `400` on that field. | Mirrors the other reference endpoints. |
| D19 | A reason returns `id`, `code`, `nom`, `type_document` (id), `type_document_libelle` (`CODE — Nom`), `retraite`, `deces` and the dates; a suspension type returns `id`, `code`, `nom`, `type_document`, `type_document_libelle`, `compte_anciennete`, `duree_max_mois`, `renouvellements_max` and the dates; both add the base fields. Ordered by D6, with a constant number of queries. | The screen shows the document without a second list; phases 3.4 and 3.6 read the rules. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D20 | A seventh tab **"Sorties et suspensions"** on "Référentiels", after "Pièces justificatives". **(asked)** | One tab per reference area; the two lists answer one question ("how does a career stop?"). |
| D21 | The tab shows two tables, one above the other. **"Motifs de sortie"**: code, name, pièce exigée, a "Retraite" or "Décès" tag when set, dates. **"Positions de suspension"**: code, name, pièce exigée, "Compte dans l'ancienneté" (Oui / Non tag), durée maximale ("24 mois", or "Fixée par la décision" when blank), renouvellements ("1", or "Sans limite" when blank), dates. One date picker "Au" (default today) and one text filter on code, name and document, shared by both tables; loading, empty and error states per table. | Short lists side by side on one date; the blank values read as words, not as dashes. |
| D22 | The screen is read-only. The tab, its date and filter stay while the user moves around, in their own `sorties` object of the store; `filterByCodeAndName` of `components/lists.ts` is reused, extended to the document label. | Same as the other tabs. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D23 | `create_demo_sorties` loads, in development: exit reasons **Retraite pour ancienneté** and **Retraite pour limite d'âge** (retraite, "Décision de retraite"), **Démission** ("Lettre de démission"), **Décès** (décès, "Acte de décès"); suspension types **Mise en disponibilité** ("Décision", does not count toward seniority, 24 months, 1 renewal) and **Détachement** ("Décision", counts, blank duration, blank renewals). The two new document types ("Décision de retraite", "Lettre de démission") are added to `create_demo_pieces`, which `create_demo_sorties` runs first. It refuses to run when `DEBUG` is off, running it twice changes nothing, and its rows have no author. | Section 2.2 and 2.3 as written, with the `Q3` assumption for disponibilité; shows both flags, both blank values and a document shared by two suspensions. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D24 | `docs/user-guide.md` gets a "Sorties et suspensions" subsection, with screenshots taken by `docs/capture_screenshots.py`; the tab count and "Who changes the reference data" are updated; `docs/user-guide.html` is rebuilt. **(asked)** | The guide describes the screen tab by tab. |
| D25 | `tech-stack.md`: the `referentiels` lines name the exit reasons and suspension types. | `tech-stack.md` changes with the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q2` — other exit reasons (dismissal, end of contract, removal, unfitness)? | The four reasons of section 2.2; HR adds others in Django admin with the right document and flags. Already in `docs/questions-ouvertes.md`. |
| `Q3` — does the disponibilité count toward the 30 years? | It does not (`compte_anciennete` off in the demo); HR flips it by closing the type and opening a successor. Already in `docs/questions-ouvertes.md`. |
| `Q32` — the ARPTC's exit reasons and suspension positions: their codes, the document each requires, the real durations and renewals; is the resignation notice a fixed length to parametrise? | The demo lists of D23; no notice parameter. Added to `docs/questions-ouvertes.md` by this phase; the merge does not wait for the answer. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D26 | The tab is one component, `SortiesSuspensions.vue`, holding the shared toolbar and both tables, instead of two table components as plan step 6.1 said. | The date and filter belong to both tables; one component avoids passing them around. Each list still loads and fails on its own. |
| D27 | `TypeDocument` lists the exit reasons and suspension types in a new `ClassificationRules.OTHER_CHILDREN`, and the parent period check became a shared `within_parent()` used by `DocumentRules`. The period queryset method is `ouvertes(date)`, as on the other reference tables, rather than `ouverts(date)`. | One copy of each period rule; the same queryset as the views already use. |
| D28 | `create_demo_pieces` gains "Décision de retraite" (DRT) and "Lettre de démission" (LDM), so it now creates 13 types. | D23: the exit reasons need them, and the document types belong to that command. |
