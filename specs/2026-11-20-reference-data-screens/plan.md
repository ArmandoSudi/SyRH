# Reference data screens — plan

Task groups for roadmap phase 1.9: the generic backend first, proven on one table, then the other
tables, then the generic frontend, then each tab, then wrap-up. Decision numbers (`D1`...) refer
to [`requirements.md`](requirements.md). Each group ends with its tests passing and is committed
on its own. **(asked)**

## 1. Backend: the generic write mixin, on fonctions

1. `apps/referentiels/edition.py`:
   - `ModelRulesSerializerMixin`: `validate()` builds the instance (or applies the changes to
     it), calls `full_clean()`, and turns a Django `ValidationError` into a DRF one, field by
     field, `__all__` becoming `non_field_errors` (D5);
   - `ModelPermission`: a DRF permission requiring module access for reads, the model's `add`
     for `POST`, `change` for `PATCH`, both for `successeur` (D6);
   - `EditionMixin` (with `AuthorMixin`): `create`, `partial_update`, and a `successeur` action
     that, in one transaction, sets `date_fermeture = date_effet` on the current row and creates
     the successor from the row's values overridden by the request, then returns it with `201`
     (D3, D4, D7, D9). `update` (PUT) and `destroy` stay refused (`405`).
2. `FonctionViewSet` becomes `EditionMixin` + read; its serializer accepts writes.
3. Tests (new `test_edition.py`, on fonctions):
   - create: `201`, the row and its audit entry carry the user; a model error comes back on its
     field (`code` duplicate on the period → `non_field_errors`; reversed dates → on
     `date_fermeture`), nothing saved;
   - correct: `PATCH` a name, `200`; set a closing date closes the row; unknown fields ignored;
   - successor: closes on `date_effet` and opens the new row; the old row keeps its name at
     earlier dates; `date_effet` on or before the opening date refused; a row already closed
     refused; an invalid successor leaves the old row open (atomic);
   - permissions: anonymous `401`, reader `403` on each write, editor allowed; `PUT` and
     `DELETE` `405`; the CSRF check applies to session writes (`enforce_csrf_checks`);
   - the read tests of phase 1.3 still pass; "writes 405" becomes "writes need permission".

## 2. Backend: the other five tables

1. `TypeContrat`, `Banque`, `MotifSortie`, `TypeSuspension`, `Parametre` viewsets on
   `EditionMixin`; their serializers accept writes (`type_document` as an id; `cle_libelle`,
   `unite`, `type_document_libelle` read-only).
2. Tests per table: create, correct, successor, one model rule coming back on its field (bank
   SWIFT/BIC, retirement and death together, zero months, a parameter out of bounds, a
   parameter's key not changeable), and the editors: Rémunération writes banks and gets `403`
   on the others; Gestion de carrière writes the others and gets `403` on banks.
3. Update the earlier API tests whose writes expected `405` (`POST` and `PATCH` now `403` for
   readers; `PUT` and `DELETE` still `405`).

## 3. Frontend: the generic dialog

1. `shared/utils/http.ts`: make sure `request` sends `POST` / `PATCH` bodies as JSON with the
   CSRF header, and exposes a `400` body (field errors) to the caller.
2. `features/referentiels/api/edition.ts`: `creer(table, data)`, `corriger(table, id, data)`,
   `remplacer(table, id, dateEffet, data)`.
3. `features/referentiels/components/edition/champs.ts`: the field description of each of the
   six tables (name, label, kind, required, help, choices) (D12); `peutModifier(user, table)` and
   `peutAjouter(user, table)` from the permissions (D10).
4. `components/edition/EditionDialog.vue`: modes `ajouter`, `corriger`, `remplacer`, `fermer`
   (D11, D13); renders the fields; shows field and top errors; emits `enregistre`.
5. `components/edition/ActionsLigne.vue`: the row menu (Corriger, Remplacer à une date, Fermer).
6. Tests: each mode builds the right request; server errors land under their fields and at the
   top; required fields; Escape cancels; the document type select lists open types; the
   permission helpers.

## 4. Frontend: wiring the tabs

1. `FonctionsTable.vue`, `TypesContratTable.vue`, `BanquesTable.vue`, `SortiesSuspensions.vue`
   (both tables), `ParametresTable.vue` (a row with "Non renseigné" offers "Ajouter" for that
   key): the "Ajouter" button and row menu for editors only; reload after a save; a toast.
2. Tests per tab: no button for a reader; buttons for an editor; a save reloads the list; for
   banks, the buttons follow the bank permissions, not the others.

## 5. Wrap-up

1. `roadmap.md`: add **1.10 Tree reference data screens** (D2).
2. `tech-stack.md` (D16).
3. User guide (D15): extend `docs/capture_screenshots.py` to capture the dialog (add, replace at
   a date, a field error) on a **scratch database** (see validation part 3), never the
   development one; add the subsection; rebuild the HTML.
4. Run the manual walkthrough in [`validation.md`](validation.md) on the scratch database, in
   light and dark themes.
5. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
6. Record any decision changed on the way under "Found during implementation".
7. Tick **1.9 Reference data screens** in [`roadmap.md`](../roadmap.md).
8. Run `/changelog` on the branch.
