# Documents on events — requirements

Roadmap phase **2.7 Documents on events**: attach the scanned documents of an agent's file to the
events they justify, and tell which events still miss a mandatory piece, so that validation
(phase 2.11) can refuse them (`SOC-04`, `CAR-02`, `ADM-14`). Seventh phase of Milestone 2 (agent
record, MVP).

Branch: `feature/documents-on-events`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges: `SOC-04`, attach to each event the scanned document it rests on; `CAR-02`,
  require the hiring documents defined in the reference data before validation; `ADM-14`, refuse
  a dependant's validation without its scanned document.
- `missions.md`: principle 4, **no proof, no validation**; principle 7, everything traceable;
  principle 8, nothing physically deleted; principle 9, least privilege.
- Phase 1.5 created `referentiels.PieceRequise`: for an event kind (`Evenement`, a fixed list in
  code), a document type it requires, mandatory or optional, dated. Adding an event kind is a code
  change made by the phase that needs it (document types D2).
- Phase 2.6 created `agents.Document`: an agent's encrypted scanned file, its type, retired but
  never deleted; confidential types read only by their groups (`lisibles_par`).
- Phases 2.3 and 2.4 created the records that are events today: `Contrat`, `Affectation`,
  `Classement`.
- The validation workflow (draft, submitted, validated, rejected) comes with phase 2.11, after
  `Q20` to `Q26`. Nothing is validated yet.
- Readers to come: 2.10 (the agent summary page shows the events and their pieces), 2.11 (refuses
  validation while a mandatory piece is missing, freezes the links of a validated event), 2.12 to
  2.14 (dependants' events), Milestone 3 (promotions, transfers, suspensions, exits as events of
  their own).

## Scope

### In scope

1. **One link table** `PieceJointe` in `apps.agents`: a document attached to an event (any
   model), removable before validation, never deleted.
2. **Events wired now**: contracts, assignments and classifications, each with its event kind
   computed from the agent's history.
3. **Two new event kinds**: Renouvellement de contrat, Avancement d'échelon.
4. **Required pieces of an event**: read from `PieceRequise` on the event's date; each one
   satisfied or missing; the event complete or not. A service 2.11 calls to refuse validation.
5. **API**: an agent's events with their pieces and status; attach and remove a link.
6. **Screen**: an "Événements" section on the "Pièces des agents" page: each event, its required
   pieces ticked or missing, attach an existing document or upload one, remove a link.
7. **Demo data**: requirements for the new kinds; links making some demo events complete and
   others not.
8. **User guide**: the section documented with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Validation, rejection, the author-cannot-validate rule; freezing a validated event's links | Phase 2.11 |
| Dependants and their events (marriage, birth, end of status) | Phases 2.12 to 2.14 |
| Promotions, transfers, suspensions, exits recorded as decisions of their own | Milestone 3 |
| The document an exit reason or an absence type requires | Phases 3.6 and 5.1 |
| Blocking the save of an event without its pieces | Not planned: an event is entered, then completed (D12) |
| Alerts on incomplete events | Milestone 4 |
| The agent summary page | Phase 2.10, which reuses the section |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner on 2026-11-22; the others
follow from the cahier des charges, `missions.md`, `tech-stack.md` and earlier phases.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One generic link table** `PieceJointe(BaseModel)` in `apps.agents`, `module = "agents"`: `document` (`PROTECT`), `content_type` and `objet_id` (the event, through a `GenericForeignKey`), `date_retrait`, `retire_par`. **(asked)** | One scan can justify several events (a decision covering a transfer and a promotion); every later event table plugs in without touching `Document`. |
| D2 | **One active link per document and event**: partial unique constraint on (`document`, `content_type`, `objet_id`) where `date_retrait` is null. | A double click must not count twice. |
| D3 | **Same agent**: the document's agent is the event's agent (model rule, French message on `document`). A retired document cannot be attached. | A piece of another agent's file proves nothing here. |
| D4 | **Removing a link** sets `date_retrait` and `retire_par`; the row stays, the document stays. A removed link can be attached again (a new row). `delete()` raises. **(asked: removable until validation)** | Principle 8; a wrong link is a correction, kept in the history. 2.11 refuses removal on a validated event. |
| D5 | Label: `TYPE — nom_original → événement — MATRICULE`, the event named by its own label. | Names the row in the audit log. |
| D6 | Event models (`Contrat`, `Affectation`, `Classement`) get a `GenericRelation` `pieces_jointes`, for prefetching; the relation never cascades a delete (events are never deleted). | A fixed number of queries per agent (validation C3). |

### Events and their kinds

| # | Decision | Reason |
| --- | --- | --- |
| D7 | **Every event model implements one protocol** (`apps/agents/evenements.py`): `evenement` (its kind, a `PieceRequise.Evenement` value or `None`), `date_evenement`, `agent`, and its label. 2.12 onwards implement the same protocol. | One check for every event, now and later. |
| D8 | **Contracts**: the agent's first contract is **Engagement**, dated on its start; each later one is **Renouvellement de contrat**, dated on its start. **(asked)** | `CAR-02`: hiring requires its pieces; a renewal needs its signed contract, not a new identity document. |
| D9 | **Assignments**: one dated on the hiring date belongs to the Engagement (kind `None`: no requirement of its own); a later one is **Mutation ou changement de fonction**. **(asked)** | The first post is decided by the hiring. |
| D10 | **Classifications**: one dated on the hiring date belongs to the Engagement; a later one whose grade differs from the previous row's is **Promotion**; one that keeps the grade is **Avancement d'échelon**. **(asked)** | `CAR-06` names the promotion decision; an échelon step is a lighter decision. |
| D11 | **Two new kinds** in `Evenement`, after Engagement: `renouvellement` "Renouvellement de contrat" and `avancement` "Avancement d'échelon". The frontend mirror and the Pièces justificatives tab follow. **(asked)** | Document types D2: a phase that needs a kind adds it. |
| D12 | Kinds are **computed, never stored**: correcting a date or adding an earlier contract changes them. | One source of truth: the history itself. |

### Required pieces and status

| # | Decision | Reason |
| --- | --- | --- |
| D13 | **Required pieces** of an event: the `PieceRequise` rows of its kind **open on its `date_evenement`**. **(asked)** | A 2020 hiring keeps the 2020 rule (the criminal record, required until 2024). |
| D14 | **A required piece is satisfied** by an active link to a non-retired document whose type has the **same code** as the required type. | A type replaced by a successor keeps its code; documents uploaded under the old row still count. |
| D15 | **Status of an event**: `complet` when every mandatory piece is satisfied; otherwise `manquantes` lists the missing mandatory types. Optional pieces are shown, satisfied or not, and never block. An event of kind `None` or with no requirement is complete. **(asked: check service + status)** | 2.11 refuses validation of an incomplete event; nothing blocks saving today. |
| D16 | **Service** `apps/agents/pieces.py`: `etat_pieces(evenement)` (one event) and `etats_pieces(agent)` (all of an agent's events, from prefetched rows, a fixed number of queries); `pieces_manquantes(evenement)` returns the missing types. 2.11 calls `pieces_manquantes`. | Same rule for the API, the screen and the workflow. |
| D17 | **Retiring a document** (2.6) leaves its links in place but they stop counting (D14): its events may become incomplete again. | The retired scan no longer proves anything. |
| D18 | **Confidential documents** count for everyone (a requirement shows satisfied even to a profile that cannot read the piece) but are listed only to their readers; others see "pièce confidentielle fournie". | The status is not confidential, the file is (2.6 D14). |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D19 | **Reading** the events and their status: every profile opening Agents, as the documents. | Same audience as the agent's file. |
| D20 | **Attaching and removing**: the document editors (Gestion de carrière, Administration du personnel and their chefs), on every event, through `agents.add_piecejointe` and `agents.change_piecejointe` (`PIECE_JOINTE_EDIT_PERMISSIONS`). Attaching also requires reading the document. Nobody has delete. **(asked)** | They already add the documents; per-event ownership comes with 2.11's circuits. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D21 | `GET /api/agents/<id>/evenements/`: the agent's events, newest first, each with `cle` (`contrat-12`), `modele`, `id`, `evenement`, `evenement_libelle`, `date`, `libelle`, `complet`, `manquantes` (codes), `pieces` (each required type: `code`, `nom`, `obligatoire`, `satisfaite`, `documents` the user may read, `confidentielles` count of the others), and `autres` (attached documents matching no requirement). | Everything the section needs in one call. |
| D22 | `POST /api/agents/<id>/evenements/<modele>/<objet_id>/pieces/` (`document`) attaches; `POST .../pieces/<lien>/retrait/` removes. Both answer the event as in D21. `<modele>` is one of `contrat`, `affectation`, `classement`. No `PUT`, `PATCH`, `DELETE`. | One event at a time; the event comes back with its new status. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D23 | The "Pièces des agents" page shows, under the documents panel, an **"Événements"** section (`EvenementsPanel.vue`, taking an agent id): one card per event, newest first, with its kind, date and label, a "Complet" or "N pièce(s) manquante(s)" tag, and its required pieces ticked or missing, each with its documents (open link) and, for editors, "Joindre" and "Retirer le lien". **(asked)** | 2.10 mounts the same component on the summary page. |
| D24 | "Joindre" opens a dialog: pick one of the agent's non-retired documents of the required type (others listed below, any type accepted), or "Déposer une nouvelle pièce", which opens the 2.6 add dialog with the type preselected and attaches the new document on success. Adding or retiring a document in the documents panel refreshes the section. | No re-upload of a scan already in the file. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D25 | `create_demo_pieces` adds Renouvellement (CTR mandatory) and Avancement (DEC optional). `create_demo_agents` adds a few documents and links: one agent with a complete engagement, one missing the diploma, one with a complete mutation, one with a linked document that was then retired. Idempotent. | Every status of the section. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q39` (new) — the pieces a contract renewal and an échelon step require. | Renouvellement: signed contract, mandatory. Avancement: decision, optional. |
| Whether a change of function only (same unit) needs other pieces than a transfer. | One kind, Mutation ou changement de fonction, as in phase 1.5. |
| Events entered before 2.11 will have no validation status when it arrives. | 2.11 decides how existing rows start (validated or draft). |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
