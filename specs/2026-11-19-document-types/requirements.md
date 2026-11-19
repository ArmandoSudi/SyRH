# Document types — requirements

Roadmap phase **1.5 Document types**: the supporting documents each event requires. Fifth phase
of Milestone 1 (reference data).

Branch: `feature/document-types`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- Cahier des charges, section 4.1: the reference data include "types de pièces justificatives".
  Section 4.2: the agent's file holds "copies numérisées de tous les justificatifs".
- `SOC-04`: attach to each event the scanned document it rests on. `missions.md`, principle 4:
  **no proof, no validation**; an event that rests on a document cannot be validated without it.
- Which documents, per event:
  - `CAR-02`: hiring requires the documents "définies au référentiel (contrat signé, pièce
    d'identité, diplômes)": the list is reference data, not code;
  - `CAR-06` promotion (the promotion decision), `CAR-08` transfer, change of function,
    détachement, mise en disponibilité and return to service (their decision), `CAR-09` interim
    (decision), `CAR-11` sanctions and distinctions;
  - `CAR-16` exit: "décision de retraite, lettre de démission, acte de décès", which depend on the
    exit reason (phase 1.6);
  - `ADM-12` marriage certificate, `ADM-13` birth certificate, `ADM-14` no dependant validated
    without its scanned document, `ADM-15` end of dependant status (death, divorce, age);
  - `ADM-03` absences: the document "prévue pour chaque type" (certificat médical, ordre de
    mission), which depends on the absence type (phase 5.1);
  - `FOR-05` training: the certificate or diploma obtained.
- None of these events exists yet. Phase 2.6 stores the scanned files; phase 2.7 attaches them to
  events and blocks validation without them; each event arrives with its own phase (2.9, 2.12 to
  2.14, Milestone 3, Milestone 8).
- `NF-03`: identity documents are encrypted at rest; `TRA-03`: PDF and image formats. Both are
  about the files, in phase 2.6.
- Phases 1.3 and 1.4 set the pattern for flat dated lists (`FlatListRules`); phase 1.2 set the
  pattern for rows that sit inside a parent's period (`ClassificationRules`).
- The ARPTC's real list of documents per event is not in the cahier des charges.

## Scope

### In scope

1. **Two tables in `apps.referentiels`**:
   - `TypeDocument`: the kinds of supporting document (contrat signé, acte de naissance, ...);
   - `PieceRequise`: for an event kind, a document type it requires, mandatory or optional.
2. **A fixed list of event kinds** in code, one per event the cahier des charges says rests on a
   document.
3. **Dated rows** in both tables, with database constraints and model rules that keep the periods
   consistent.
4. **Editing in Django admin** for the same editors as the other reference tables.
5. **Read-only API**: two flat endpoints, rows open at a date (or all).
6. **Read-only tab** "Pièces justificatives" on the "Référentiels" screen: the documents each event
   requires.
7. **Demo data** for development.
8. **User guide**: the new tab documented in `docs/user-guide.md`, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Uploading, storing, encrypting and serving the scanned files; allowed formats and sizes | Phase 2.6 Document storage (`TRA-03`, `NF-03`) |
| Attaching a document to an event; blocking validation when a mandatory one is missing | Phase 2.7 Documents on events, reading `PieceRequise` |
| The events themselves (hiring, promotion, marriage, ...) | Their own phases (2.9, 2.12 to 2.14, Milestone 3, Milestone 8) |
| The document an absence type requires (`ADM-03`) | Phase 5.1 Absence types: each type points to a `TypeDocument` |
| The document an exit reason requires (acte de décès, lettre de démission) | Phase 1.6 Exit reasons: each reason points to a `TypeDocument` |
| Who may see which document (medical, identity) | Phase 2.6, with the existing roles |
| Creating, correcting and closing rows from the app | Phase 1.9; Django admin until then |
| Loading the real ARPTC list | Entered by HR in Django admin (open point `Q31`) |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-19. The others follow
from [`missions.md`](../missions.md), [`tech-stack.md`](../tech-stack.md), the cahier des charges
and the pattern of phases 1.2 to 1.4.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **Two tables**: `TypeDocument` (`code` up to 20 characters in capitals, `nom` up to 150, dates) and `PieceRequise` (`evenement`, `type_document`, `obligatoire`, dates). **(asked)** | `CAR-02`: the documents each event requires are reference data (principle 6). A requirement row per event and document lets one document serve several events (a decision for a promotion, a transfer and an interim). |
| D2 | **Event kinds are a fixed list in code** (`PieceRequise.Evenement`), in this order: Engagement, Promotion, Mutation ou changement de fonction, Détachement, Mise en disponibilité, Reprise de service, Intérim, Sanction, Distinction, Sortie, Mariage, Naissance, Fin de qualité de dépendant, Formation. **(asked)** | Each kind is an event a later phase builds, with its own screen and rules; adding one is a code change made by that phase. HR decides which documents each needs. |
| D3 | **Absences and exit reasons are not event kinds here**: the document an absence type or an exit reason requires is a field of that type (phases 5.1 and 1.6), pointing to `TypeDocument`. "Sortie" holds only the documents every exit needs, whatever its reason. **(asked)** | `ADM-03` and `CAR-16` tie the document to the type or the reason, of which there are many and which HR maintains. |
| D4 | `obligatoire` (required boolean): a mandatory document blocks the event's validation (phase 2.7); an optional one can be attached but does not block. | `ADM-15`: ending a dependant's status needs a death certificate **or** a divorce judgment, depending on the cause; both are optional on the event, and phase 2.14 checks the right one. |
| D5 | A type's code is unique among types open at the same time; its name is not constrained. An event cannot require the same document type twice over overlapping periods. | Same as 1.3 D3; a duplicate requirement has no meaning. |
| D6 | Types sort by name. Requirements sort by event (the order of D2), then mandatory first, then the document's name. | The order of D2 follows the agent's life, as `missions.md` lists it. |

### History

| # | Decision | Reason |
| --- | --- | --- |
| D7 | Both tables have `date_ouverture` (required) and `date_fermeture` (optional), with the usual rule: open on day D when `date_ouverture <= D < date_fermeture`. **(asked)** | An event validated in 2024 was checked against the documents required in 2024 (principle 3). |
| D8 | A requirement lies within its document type's period: it cannot open before the type nor stay open after it, and a type cannot be closed while one of its requirements stays open after that date. | The list at any date is complete: no requirement points to a closed type. Same as 1.2 D13. |
| D9 | A requirement's event and document type never change after creation; making a document optional, or no longer required, closes the requirement and opens a new one. Its `obligatoire` flag and dates may be corrected for a typing error. | Principle 3; same as 1.2 D11. |
| D10 | Nothing is deleted: no delete permission on either table, and the API is read-only. | Principle 8. |

### Where the rules live

| # | Decision | Reason |
| --- | --- | --- |
| D11 | **In the database**: closing date after opening date on both tables; type code unique per period; event and document type unique per period; `evenement` limited to the values of D2; `PROTECT` on the foreign key. | Principle 1; the phase 1.2 helpers. |
| D12 | **In the model**: the code in capitals, reversed dates on `date_fermeture`, the fixed event and type (D9) and the periods (D8), from `clean()` and `save()`, with French messages per field. `TypeDocument` and `PieceRequise` use the parent and child machinery of `ClassificationRules` (parent `type_document`, children `pieces_requises`), extended so that more than one field can be fixed. | These rules read other rows, as in the classification; no third copy of the period rules. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D13 | Every holder of `access_referentiels` **reads** both tables. | Every service will attach documents. |
| D14 | **Administrateur système, Gestion de carrière and Chef de service — Gestion de carrière** get view, add and change on both tables. Nobody gets delete. **(asked)** | Same editors as 1.1 to 1.4. Administration du personnel, which records dependants, reads the list; whether it should edit the dependant rows is part of `Q31`. |
| D15 | The permissions go into `roles.py` as `DOCUMENT_EDIT_PERMISSIONS`, added to `REFERENTIELS_EDIT_PERMISSIONS`. | One declaration; the group setup only adds. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D16 | `TypeDocumentAdmin`: code, name, dates; "ouvert aujourd'hui" filter; search. `PieceRequiseAdmin`: event, document type, mandatory, dates; filters on event, mandatory and "ouvert aujourd'hui"; the type through autocomplete; event and type read-only when changing a row (D9). No inlines. | Same as the classification admin (1.2 D21, D22). |

### Audit

| # | Decision | Reason |
| --- | --- | --- |
| D17 | Both models inherit `BaseModel` with `module = "referentiels"`. Labels: `CODE — Nom` for a type; `Événement — CODE (obligatoire)` or `(facultative)` for a requirement. | Captured automatically; the label says what was required. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D18 | Two endpoints, `/api/referentiels/types-document/` and `/api/referentiels/pieces-requises/`: rows open on `?date=` (default today) or all with `?toutes=1`, through `PeriodeMixin`. Not paginated. Writes answer `405`. `HasModuleAccess("referentiels")`; an invalid `date` answers `400` on that field. | Mirrors the other reference endpoints. |
| D19 | A type returns `id`, `code`, `nom` and the dates; a requirement returns `id`, `evenement`, `evenement_libelle`, `type_document` (id), `obligatoire` and the dates; both add the base fields. Ordered by D6. | What the screen and phase 2.7 need; the client joins the two lists by id, as the classification tree does. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D20 | A sixth tab **"Pièces justificatives"** on "Référentiels", after "Types de contrat". **(asked)** | One tab per reference area. |
| D21 | The tab shows a TreeTable: one root row per event kind, in the order of D2, with the number of documents it requires; under it, its documents with code, name, "Obligatoire" or "Facultative" (Tag), and dates. An event with no requirement shows "Aucune pièce exigée". A date picker "Pièces au" (default today), a text filter on the document's code and name and on the event's label, expand all and collapse all; loading, empty and error states. | Answers the question HR asks ("what must I collect for a marriage?"); the event kinds come from the API's `evenement_libelle`, plus a fixed client list for events with no row. |
| D22 | The screen is read-only. The tab, its date, filter and expanded rows stay while the user moves around, in their own `pieces` object of the store. The filter and expand helpers of `components/tree.ts` are reused. | Same as the other tabs. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D23 | `create_demo_pieces` loads, in development, about a dozen document types (Contrat signé, Pièce d'identité, Diplôme, Décision, Acte de mariage, Acte de naissance, Acte de décès, Jugement de divorce, Certificat de formation, Certificat médical, Extrait de casier judiciaire) and requirements for most event kinds: hiring needs the contract, the identity document and the diploma; the career events need the decision; marriage and birth their certificate; end of dependant status the death certificate or divorce judgment, both optional; training the certificate, optional. One requirement is closed in the past with no successor (the criminal record extract, required for hiring until 2024). "Sortie" requires nothing (D3). It refuses to run when `DEBUG` is off, running it twice changes nothing, and its rows have no author. | Shows both flags, an event with no requirement, a document used by several events, and a past rule. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D24 | `docs/user-guide.md` gets a "Pièces justificatives" subsection, with screenshots taken by `docs/capture_screenshots.py`, and `docs/user-guide.html` is rebuilt. **(asked)** | The guide describes the screen tab by tab. |
| D25 | `tech-stack.md`: the `referentiels` lines name the document types. | `tech-stack.md` changes with the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q31` — the ARPTC's supporting documents: which document types exist, and for each event which ones are mandatory and which optional? Does a requirement ever depend on the agent (catégorie, contract type, nationality)? Should Administration du personnel edit the requirements for dependants? | The demo list of D23; a requirement depends only on the event kind. HR enters the real list in Django admin. Added to `docs/questions-ouvertes.md` by this phase; the merge does not wait for the answer. |
