# Exit and suspension reasons — plan

Task groups for roadmap phase 1.6, one model per group, then permissions, API, demo data,
frontend and wrap-up. Decision numbers (`D1`...) refer to [`requirements.md`](requirements.md).
Each group ends with its tests passing and is committed on its own. **(asked)**

## 1. Backend: the `MotifSortie` model

1. A shared rule for rows that point to a document type (D9, D12): a helper (or small mixin on
   top of `FlatListRules`) that refuses a row opening before its `type_document` or staying open
   after it, with French messages on `date_ouverture` / `date_fermeture`.
2. Model `MotifSortie(FlatListRules, BaseModel)` in `apps/referentiels/models.py`,
   `module = "referentiels"` (D1, D2, D17): `code` (20), `nom` (150), `type_document`
   (`PROTECT`, related name `motifs_sortie`), `retraite`, `deces` (booleans, default off, help
   texts saying what later phases do with them), `date_ouverture`, `date_fermeture`;
   `verbose_name` "motif de sortie", plural "motifs de sortie"; ordering by `nom` (D6);
   `default_permissions = NO_DELETE` (D10).
3. Rules: "retraite" and "décès" together refused on `deces` (D12).
4. Constraints (D11): `closing_after_opening(...)`, `unique_per_period(..., "code", ...)`, a check
   that `retraite` and `deces` are not both true.
5. `TypeDocument`: its closing check also refuses a closing date while an exit reason pointing to
   it stays open after that date (D9). Extend `ClassificationRules` with extra child relations
   rather than writing a second copy of the check; the classification models and `PieceRequise`
   keep their behaviour and tests.
6. Migration `0008_motifsortie`.
7. Tests (new `test_sorties.py`): each constraint bypassing the model; code in capitals, unique per
   period, reused on consecutive periods; same name accepted; reversed dates on the field;
   retraite and décès together refused on the field; within the document's period (open before,
   stay open after, closing the document refused); the document can be corrected; `ouverts(date)`;
   order by name; deleting a referenced document type refused; audit of create, correct and close
   with the label.

## 2. Backend: the `TypeSuspension` model

1. Model `TypeSuspension(FlatListRules, BaseModel)`, `module = "referentiels"` (D1, D3, D17):
   `code`, `nom`, `type_document` (`PROTECT`, related name `types_suspension`),
   `compte_anciennete` (required boolean), `duree_max_mois` (`PositiveSmallIntegerField`, null),
   `renouvellements_max` (`PositiveSmallIntegerField`, null), the dates; `verbose_name` "type de
   suspension", plural "types de suspension"; ordering by `nom`; `NO_DELETE`.
2. The document period rule of group 1; `TypeDocument`'s closing check extended to
   `types_suspension`.
3. Constraints (D11): closing after opening; code unique per period; `duree_max_mois > 0` when
   set; `renouvellements_max >= 0` when set.
4. Migration `0009_typesuspension`.
5. Tests: each constraint bypassing the model; capitals and code per period; zero months refused,
   blank accepted; zero renewals accepted, blank accepted; within the document's period; closing
   a document type with an open suspension type refused; `ouverts(date)`; order by name; audit.

## 3. Backend: permissions and Django admin

1. `roles.py`: `SORTIE_EDIT_PERMISSIONS` (view, add, change on `motifsortie` and
   `typesuspension`), added to `REFERENTIELS_EDIT_PERMISSIONS` (D14, D15). Run `migrate` on the
   development database straight after, so the groups get them.
2. `admin.py` (D16): `MotifSortieAdmin` and `TypeSuspensionAdmin` on `BaseModelAdmin`, with
   `OuvertFilter`, the boolean filters, search on code and name, `autocomplete_fields =
   ["type_document"]`.
3. Tests (`test_access.py`): editors hold the six permissions, nobody deletes, the group setup
   regrants and keeps hand-made ones; `demo.carriere` adds a reason and a suspension type and is
   their author; the document autocomplete answers; a reason flagged retraite and décès shows next
   to "Décès"; a row opening before its document shows next to "Date d'ouverture"; a duplicate
   open code shows at the top; other profiles get `403`.

## 4. Backend: read-only API

1. `MotifSortieSerializer`, `TypeSuspensionSerializer` with `type_document_libelle` (D19).
2. `MotifSortieViewSet`, `TypeSuspensionViewSet` on `PeriodeMixin`, `HasModuleAccess
   ("referentiels")`, no pagination, `select_related("type_document")`; URLs `motifs-sortie` and
   `types-suspension` (D18).
3. Tests: open today, on `?date=`, all with `?toutes=1`, by name, with the fields of D19 (blank
   duration and renewals as `null`); invalid date `400`; `401`, `403`, `200` per profile; writes
   `405`; the query count does not grow with rows.

## 5. Backend: demo data

1. `create_demo_pieces`: add "Décision de retraite" and "Lettre de démission" to its types.
2. `create_demo_sorties` (D23): refuses without `DEBUG`; runs `create_demo_pieces` first;
   `get_or_create` on code and opening date; prints what it created.
3. Tests: refused without `DEBUG`; every row passes `full_clean()`; two retirement reasons, one
   death, one with neither; disponibilité 24 months, 1 renewal, not counted; détachement counted
   with blank duration and renewals; both suspensions share the decision; a second run creates
   nothing and writes no audit entry; no author. Update the `create_demo_pieces` counts in
   `test_pieces.py` and `test_access.py`.

## 6. Frontend: "Sorties et suspensions" tab

1. `features/referentiels/`:
   - `api/referentiels.ts`: types `MotifSortie`, `TypeSuspension`; `fetchMotifsSortie`,
     `fetchTypesSuspension`;
   - `components/lists.ts`: let `filterByCodeAndName` also match the document label (or add a
     small variant), keeping its current callers unchanged;
   - `components/sorties.ts`: `dureeLibelle(mois)` ("24 mois" / "Fixée par la décision") and
     `renouvellementsLibelle(n)` ("1" / "Sans limite");
   - `components/MotifsSortieTable.vue`, `components/TypesSuspensionTable.vue` (D21);
   - `stores/referentiels.ts`: the `sorties` tab value and a `sorties` object (date, text) (D22);
   - `views/ReferentielsView.vue`: the seventh tab with the shared date and filter (D20).
2. Tests:
   - the label helpers, blank and set;
   - the filter on code, name and document label;
   - the tab comes after "Pièces justificatives"; loads both lists for today; reloads both on a
     new date; shows each list's API error on its own table; filters both tables; tags for
     retraite, décès and the seniority flag; no button that changes data; its store state is kept
     apart from the other tabs.

## 7. Wrap-up

1. Add `Q32` to `docs/questions-ouvertes.md`; note on `Q2` and `Q3` that phase 1.6 applies their
   MVP assumptions.
2. `tech-stack.md`: the `referentiels` lines name the exit reasons and suspension types (D25).
3. User guide (D24): extend `docs/capture_screenshots.py` (run `create_demo_sorties` first;
   capture the tab and a filter); add the "Sorties et suspensions" subsection; update the tab
   count and "Who changes the reference data"; rebuild the HTML.
4. Run the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
5. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
6. Record any decision changed on the way under "Found during implementation".
7. Tick **1.6 Exit and suspension reasons** in [`roadmap.md`](../roadmap.md).
8. Run `/changelog` on the branch.
