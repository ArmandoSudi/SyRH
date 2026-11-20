# Tree reference data screens — plan

Task groups for roadmap phase 1.10: the backend writes, then the carrying over of children, then
the dialog, then each tab, then wrap-up. Decision numbers (`D1`...) refer to
[`requirements.md`](requirements.md). Each group ends with its tests passing and is committed on
its own. **(asked)**

## 1. Backend: write endpoints for the seven tables

1. Serializers of `Site`, `UniteOrganisationnelle` (`site` written as an id, read as today's
   nested summary, or a separate `site_id` write field), `Categorie`, `Grade`, `Echelon`,
   `TypeDocument`, `PieceRequise` on `ModelRulesSerializerMixin`; computed fields read-only.
2. Their viewsets on `EditionMixin` (D1, D3).
3. Tests (new `test_edition_arbres.py`): per table, create, correct, a fixed field refused on
   `PATCH` with the model's message, a parent rule coming back on its field (a grade opening
   before its catégorie, a unit under a lower level, a second head office), readers `403`,
   `PUT` / `DELETE` `405`. Update the earlier "writes 405" API tests of these tables.

## 2. Backend: carrying children over

1. `EditionMixin.SUITE`: the related names a viewset carries over (D5): `unites` → `enfants`;
   `categories` → `grades`; `grades` → `echelons`; `types-document` → `pieces_requises`,
   `motifs_sortie`, `types_suspension`; `sites` and the leaves → none (D6).
2. A walk in `edition.py`: collect the open descendants at `date_effet` (refusing children that
   open on or after it, D7); close them bottom-up; create the successor; create the copies
   top-down with their parent pointing to the new row; one `transaction.atomic()`; every error
   as a `400` naming the row it concerns (D4, D10). The copy is built from the row's own field
   values, its parent key replaced.
3. `GET {id}/suite/?date_effet=`: counts by kind (the model's `verbose_name_plural`) and the
   blocking children (D9).
4. Tests: renaming a direction carries its départements, services and bureaux (ids new, codes
   and names kept, old rows closed on the date, the tree at earlier dates unchanged); a reform of
   a catégorie carries grades and échelons; replacing a document type re-points its
   requirements, exit reasons and suspension types; a refused copy cancels everything (nothing
   closed, nothing created); a child opening after the date blocks it, named; closing a parent
   with open children still refused; the preview counts match what is done; authors and audit
   entries on every row.

## 3. Frontend: dialog extensions

1. `champs.ts`: descriptions of the seven tables; a field kind `parent` with the endpoint to list
   and a filter (unit levels, D11); `fixe` on the fixed fields.
2. `EditionDialog.vue`: the `parent` select (loaded when opened, open rows at today); the preview
   of D9 in `remplacer` mode once a date is chosen, with a confirmation step and the blocking
   rows (D16).
3. `api/edition.ts`: `suite(table, id, dateEffet)`; `TableEditable` widened to the thirteen
   tables.
4. Tests: parent options and the unit level filter; fixed fields disabled when correcting; the
   preview shown, confirmation required when the count is not zero, saving disabled when rows
   block.

## 4. Frontend: Sites and Organisation

1. `SitesTable.vue`: "Ajouter" and the row menu (D12).
2. `OrganisationTree.vue`: "Ajouter une direction"; per row the menu and "Ajouter une
   sous-unité" (parent, site, next type prefilled) (D13); reload keeping expanded rows (D17).
3. Tests: readers see nothing; editors see the actions; "Ajouter une sous-unité" opens the
   dialog with the right values; a save reloads the tree.

## 5. Frontend: Classification

1. `ClassificationTree.vue`: "Ajouter une catégorie", "Ajouter un grade", "Ajouter un échelon"
   (next number), the row menu (D14).
2. Tests as in group 4.

## 6. Frontend: Pièces justificatives

1. `PiecesTree.vue`: "Ajouter une pièce exigée" on event rows; the row menu on requirement rows;
   a "Types de pièce" table under the tree with "Ajouter" and the row menu (D15).
2. Tests as in group 4, plus the types table following the tab's date.

## 7. Wrap-up

1. `tech-stack.md` (D19).
2. User guide (D18): screenshots on the scratch servers (`backend-scratch`, `frontend-scratch`,
   `SYRH_BASE`) of adding a sub-unit, the replacement preview of a direction, and a refused
   closing; update the subsections; rebuild the HTML.
3. Manual walkthrough of [`validation.md`](validation.md) on the scratch database, light and
   dark; drop the scratch database.
4. All quality gates; "Found during implementation"; tick **1.10** in
   [`roadmap.md`](../roadmap.md); `/changelog`.
