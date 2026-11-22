# Documents on events — plan

Task groups for roadmap phase 2.7: event kinds, the link table, the events protocol and status
service, permissions and admin, API, screen, demo data, user guide and wrap-up. Decision numbers
(`D1`...) refer to [`requirements.md`](requirements.md). Each group ends with its tests passing
and is committed on its own. **(asked)**

## 1. Reference data: two new event kinds

1. `Evenement` (D11): `renouvellement` "Renouvellement de contrat" and `avancement` "Avancement
   d'échelon", after Engagement; migration of `PieceRequise.evenement` choices and its check
   constraint.
2. Frontend mirror (`EVENEMENTS` in `features/referentiels/components/pieces.ts` and the
   `Evenement` type); the Pièces justificatives tab lists them.
3. `create_demo_pieces` (D25): Renouvellement requires CTR (mandatory), Avancement DEC (optional).
4. Tests: the new kinds accepted by the constraint; the mirror test; the tab's order; demo
   idempotent.

## 2. Backend: the `PieceJointe` model

1. Model `PieceJointe(BaseModel)` in `apps/agents/models.py` (D1, D2, D5): `document`,
   `content_type`, `objet_id`, `evenement_objet` (`GenericForeignKey`), `date_retrait`,
   `retire_par`; partial unique constraint on active links; check constraint "removed has a
   date"; `default_permissions = NO_DELETE`; `__str__` with the label of D5.
2. Rules (D3, D4): `check_rules()` from `clean()` and `save()` — same agent, document not
   retired, event of a known model, link fixed once saved except removal; `retirer(auteur)` once;
   `delete()` raises.
3. `GenericRelation` `pieces_jointes` on `Contrat`, `Affectation`, `Classement` (D6).
4. Migration `0009_piecejointe`.
5. Tests (`test_pieces_jointes.py`): attach; duplicate active link refused by the model and the
   database; attach again after removal; other agent's document and retired document refused;
   removal once; `delete()` raises; audit of attach and removal with label and author.

## 3. Backend: events and their status

1. `apps/agents/evenements.py` (D7 to D10, D12): the protocol; `evenement` and `date_evenement`
   on `Contrat`, `Affectation`, `Classement`, computed from the agent's prefetched history;
   `evenements_de(agent)` lists them newest first.
2. `apps/agents/pieces.py` (D13 to D18): `etat_pieces`, `etats_pieces`, `pieces_manquantes`;
   requirements read once per kind and date range, matching by type code; confidential documents
   counted, listed only to readers.
3. Tests (`test_evenements.py`): each kind (first and later contract; assignment on the hiring
   date and later; classification on the hiring date, grade change, échelon step); kinds follow a
   corrected date; requirements on the event's date (criminal record before and after 2024);
   satisfaction by code across a replaced type; optional pieces never block; retired document and
   removed link stop counting; kind `None` complete; confidential counted but hidden; fixed
   number of queries for `etats_pieces`.

## 4. Backend: permissions and Django admin

1. `roles.py` (D20): `PIECE_JOINTE_EDIT_PERMISSIONS` (view, add, change on `piecejointe`) for the
   four document editor groups. Run `migrate` on the development database straight after.
2. `admin.py`: `PieceJointeAdmin` read-only (document, event, active or removed), queryset through
   readable documents; no add, change or delete.
3. Tests (`test_access.py`): permissions held by the four groups only, regranted after `migrate`,
   no delete; admin read-only and hides links to confidential documents from non-members.

## 5. Backend: API

1. Serializers for an event with its status (D21) and for the attach request.
2. Views (D21, D22): `GET /api/agents/<id>/evenements/`; attach; remove. Module check before the
   agent lookup; the event must belong to the agent (`404` otherwise); `<modele>` limited to the
   three wired models.
3. Tests: every field of D21; newest first; status before and after attach and removal; a
   confidential piece counted and hidden for Formation, listed for Social; attach refusals
   (`400` on `document`: other agent, retired, unreadable, duplicate); event of another agent
   `404`; unknown model `404`; anonymous `401`; no Agents `403`; readers without the permission
   `403` on attach and remove; other methods `405`; fixed number of queries.

## 6. Frontend: the Événements section

1. `features/agents/api/evenements.ts`: typed `listEvenements`, `attachDocument`, `detachDocument`.
2. `components/EvenementsPanel.vue` (D23) and `components/AttachDocumentDialog.vue` (D24);
   `AddDocumentDialog.vue` accepts a preselected type and emits the new document;
   `AgentDocumentsView.vue` mounts the section under the documents panel and refreshes it when a
   document is added or retired.
3. Tests (Vitest): cards in order with their tags; required pieces ticked or missing;
   confidential pieces shown as "pièce confidentielle fournie"; buttons hidden without the
   permissions; attach an existing document; upload-and-attach; remove a link; API errors shown.
4. Check the section in the light and dark themes, empty, loading and error states.

## 7. Backend: demo data

1. `create_demo_agents` (D25): extra demo documents and links, idempotent, no author.
2. Tests: the four shapes of D25 present; statuses as expected; a second run creates nothing and
   writes no audit entry.

## 8. User guide

1. `docs/user-guide.md`: "Événements et pièces exigées" under the agents' documents section —
   reading the status, attaching, uploading and attaching, removing a link, what the rule date
   means.
2. Screenshots through `docs/capture_screenshots.py` (light theme); rebuild `user-guide.html`.

## 9. Wrap-up

1. `tech-stack.md`: the `agents/` line names the links and the events protocol; "Files and
   documents" names `PieceJointe` and `pieces_manquantes`.
2. `docs/questions-ouvertes.md`: add `Q39`.
3. Run the walkthrough and checks in [`validation.md`](validation.md) on the scratch database.
4. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
5. Record any decision changed on the way under "Found during implementation".
6. Tick **2.7 Documents on events** in [`roadmap.md`](../roadmap.md).
7. Run `/changelog` on the branch.
