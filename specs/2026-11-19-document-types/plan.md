# Document types — plan

Task groups for roadmap phase 1.5, one model per group, then permissions, API, demo data,
frontend and wrap-up. Decision numbers (`D1`...) refer to [`requirements.md`](requirements.md).
Each group ends with its tests passing and is committed on its own. **(asked)**

## 1. Backend: the `TypeDocument` model

1. Model `TypeDocument(BaseModel)` in `apps/referentiels/models.py`, `module = "referentiels"`
   (D1, D17): `code` (20), `nom` (150), `date_ouverture`, `date_fermeture` (help text "Premier
   jour où le type n'existe plus"); `verbose_name` "type de pièce", plural "types de pièce";
   `ordering` by `nom` (D6); `default_permissions = NO_DELETE` (D10).
2. Rules: `ClassificationRules` with `CHILDREN = "pieces_requises"` and its French words, so it
   gets the code in capitals, reversed dates on `date_fermeture`, and (once group 2 exists) the
   "requirements still open after this date" check (D8, D12). Label `CODE — Nom`.
3. Constraints: `closing_after_opening(...)`, `unique_per_period(..., "code", ...)` (D11).
4. Migration `0006_typedocument`.
5. Tests (new `test_pieces.py`): constraints bypassing the model; code unique per period, reused
   on consecutive periods; same name accepted; capitals; reversed dates on the field;
   `ouvertes(date)`; order by name; audit of create, correct and close with the label.

## 2. Backend: the `PieceRequise` model

1. Model `PieceRequise(BaseModel)`, `module = "referentiels"` (D1 to D4, D17):
   - `Evenement` choices in the order of D2 (values: `engagement`, `promotion`, `mutation`,
     `detachement`, `disponibilite`, `reprise`, `interim`, `sanction`, `distinction`, `sortie`,
     `mariage`, `naissance`, `fin_dependance`, `formation`);
   - `evenement`, `type_document` (`PROTECT`, related name `pieces_requises`), `obligatoire`
     (required boolean), `date_ouverture`, `date_fermeture`;
   - label `Événement — CODE (obligatoire)` / `(facultative)`.
2. Ordering by the order of D2 (D6): a queryset method `in_event_order()` annotating the position
   of `evenement` in the choices with `Case`/`When`, then `-obligatoire`, then the type's name.
   The API, admin list and demo use it.
3. Constraints (D11): closing after opening; `unique_per_period(..., "evenement",
   "type_document", ...)`; `evenement` limited to its values by a check constraint.
4. Rules (D8, D9, D12): `ClassificationRules` with `PARENT = "type_document"`. Extend
   `ClassificationRules` with an optional `FIXED` tuple of extra fields that cannot change after
   creation (here `evenement`), checked with the parent; the classification models do not set it
   and keep their behaviour and tests.
5. Migration `0007_piecerequise`.
6. Tests: each constraint bypassing the model; the same document twice for one event over
   overlapping periods refused, on consecutive periods accepted, for two events accepted;
   requirement within its type's period; closing a type with a requirement open after that date
   refused; event and type read-only after creation (`full_clean()` and `save()`); `obligatoire`
   correctable; `ouvertes(date)`; order by event, mandatory first, then name; making a document
   optional by closing and reopening keeps the old rule at earlier dates; audit labels.

## 3. Backend: permissions and Django admin

1. `roles.py`: `DOCUMENT_EDIT_PERMISSIONS` (view, add, change on `typedocument` and
   `piecerequise`), added to `REFERENTIELS_EDIT_PERMISSIONS` (D14, D15).
2. `admin.py` (D16): `TypeDocumentAdmin` (search fields needed for the autocomplete) and
   `PieceRequiseAdmin` on `ClassificationAdmin`-style read-only fields for the event and type
   when changing a row.
3. Tests (`test_access.py`): editors hold the six permissions, nobody deletes, the group setup
   regrants and keeps hand-made ones; `demo.carriere` adds a type and a requirement and is their
   author; event and type read-only on change; the type autocomplete answers; a requirement
   opening before its type shows next to "Date d'ouverture"; a duplicate requirement shows at the
   top; other profiles get `403`.

## 4. Backend: read-only API

1. `TypeDocumentSerializer`, `PieceRequiseSerializer` with `evenement_libelle` (D19).
2. `TypeDocumentViewSet`, `PieceRequiseViewSet` on `PeriodeMixin`, `HasModuleAccess
   ("referentiels")`, no pagination, the requirement queryset in event order; URLs
   `types-document` and `pieces-requises` (D18).
3. Tests: open today, on `?date=`, all with `?toutes=1`, in the order of D6, with the fields of
   D19; invalid date `400`; `401`, `403`, `200` per profile; writes `405`; the query count of the
   requirements list does not grow with rows.

## 5. Backend: demo data

1. `create_demo_pieces` (D23): refuses without `DEBUG`; `get_or_create` on code and opening date
   for types, on event, type and opening date for requirements; prints what it created.
2. Tests: refused without `DEBUG`; every row passes `full_clean()`; hiring requires three
   mandatory documents today and four in 2023; "Sortie" requires nothing; the decision is used by
   several events; both natures of requirement exist; a second run creates nothing and writes no
   audit entry; no author.

## 6. Frontend: "Pièces justificatives" tab

1. `features/referentiels/`:
   - `api/referentiels.ts`: types `TypeDocument`, `PieceRequise`, `Evenement`;
     `fetchTypesDocument`, `fetchPiecesRequises`;
   - `components/pieces.ts`: `EVENEMENTS` (value and label, in the order of D2, matching the
     backend), and `buildPieces(types, pieces)` building the tree nodes (keys `ev-…`, `pr-…`), an
     event with no requirement kept as an empty root;
   - `components/PiecesTree.vue` (D21), reusing `filterTree` and `expandedKeys` from `tree.ts`;
   - `stores/referentiels.ts`: the `pieces` tab value and a `pieces` object (date, text,
     expanded) (D22);
   - `views/ReferentielsView.vue`: the sixth tab (D20).
2. Tests:
   - `buildPieces`: every event kind as a root, in order, with its count; documents mandatory
     first; a requirement whose type is missing from the list is not lost (shown with its id);
   - the client list of event kinds matches the backend's (a backend test exports the choices to
     compare, or the frontend test lists them explicitly with a comment pointing to D2);
   - the tab comes after "Types de contrat"; loads both lists for today; reloads on a new date;
     shows the API error; filters on a document or an event, keeping the event row; expand and
     collapse all; no button that changes data; its store state is kept apart from the other tabs.

## 7. Wrap-up

1. Add `Q31` to `docs/questions-ouvertes.md`.
2. `tech-stack.md`: the `referentiels` lines name the document types (D25).
3. User guide (D24): extend `docs/capture_screenshots.py` (run `create_demo_pieces` first;
   capture the tab expanded, a filter, and the list in 2023); add the "Pièces justificatives"
   subsection; update the tab count and "Who changes the reference data"; rebuild the HTML.
4. Run `migrate` on the development database (the group setup grants the new permissions), then
   the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
5. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
6. Record any decision changed on the way under "Found during implementation".
7. Tick **1.5 Document types** in [`roadmap.md`](../roadmap.md).
8. Run `/changelog` on the branch.
