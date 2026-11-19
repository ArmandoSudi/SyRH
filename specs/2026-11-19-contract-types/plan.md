# Contract types — plan

Task groups for roadmap phase 1.4, backend first, then frontend, then wrap-up. Decision numbers
(`D1`...) refer to [`requirements.md`](requirements.md). Each group ends with its tests passing
and is committed on its own. **(asked)**

## 1. Backend: the `TypeContrat` model

1. Model `TypeContrat(BaseModel)` in `apps/referentiels/models.py`, `module = "referentiels"`
   (D1, D2, D15):
   - `code` (20), `nom` (150), `duree_determinee` and `periode_essai` (booleans, no default, with
     help texts: "Un contrat de ce type doit avoir une date de fin." and "Un contrat de ce type
     peut comporter une période d'essai."), `date_ouverture`, `date_fermeture` (null, help text
     "Premier jour où le type n'existe plus");
   - `verbose_name` "type de contrat", plural "types de contrat";
   - `__str__`: `CODE — Nom`;
   - `Meta`: `ordering` by `nom` then `date_ouverture` (D5); `default_permissions = NO_DELETE`
     (D8).
2. Queryset method `ouvertes(date)`, shared with the other dated tables (D6).
3. Code in capitals and `check_closing_after_opening()` from `clean()`; capitals from `save()`
   (D10). If this repeats `Fonction`'s three methods word for word, move them into one small mixin
   used by both, with `Fonction`'s tests unchanged.
4. Constraints (D9): `closing_after_opening("typecontrat_fermeture_apres_ouverture")`,
   `unique_per_period("typecontrat_code_unique_par_periode", "code", ...)`.
5. Migration `0005_typecontrat`.
6. Tests (new `test_types_contrat.py`):
   - each constraint refuses an invalid row through `_base_manager`, without the model;
   - the same code on overlapping periods is refused, on consecutive periods accepted; two types
     with the same name are accepted;
   - code in capitals through `save()` and `full_clean()`; both flags required by `full_clean()`;
   - reversed dates report on `date_fermeture`, with no database error;
   - `ouvertes(date)` includes the opening day and excludes the closing day;
   - ordered by name;
   - changing a flag by closing the type and opening a successor with the same code succeeds, and
     the earlier date still shows the old flags;
   - creating, correcting and closing a type each write an audit entry labelled `CODE — Nom`
     under module `referentiels`.

## 2. Backend: permissions and Django admin

1. `roles.py`: `TYPE_CONTRAT_EDIT_PERMISSIONS` (view, add, change on `typecontrat`), added to
   `REFERENTIELS_EDIT_PERMISSIONS` (D12, D13).
2. `admin.py`: `TypeContratAdmin(BaseModelAdmin)` with list columns, filters (each flag,
   `OuvertFilter`), search on code and name (D14).
3. Tests (`test_access.py`):
   - the three editor groups get view, add and change on `typecontrat`; no other group gets add
     or change; nobody gets delete; the group setup grants a removed permission again and keeps a
     hand-made one;
   - `demo.carriere` adds and corrects a type in `/admin/`, and is the author of the row and of
     its audit entry; list, filters and search open;
   - a duplicate code shows at the top of the form; reversed dates show next to "Date de
     fermeture";
   - no delete; other profiles get `403` on the admin pages.

## 3. Backend: read-only API

1. `TypeContratSerializer` on `BaseModelSerializer` (D17).
2. `TypeContratViewSet(PeriodeMixin, ReadOnlyModelViewSet)`, `HasModuleAccess("referentiels")`,
   no pagination; URL `/api/referentiels/types-contrat/` (D16, D18).
3. Tests: open today by default, on `?date=`, all with `?toutes=1`, in name order, with the fields
   of D17; invalid `date` answers `400` on `date`; anonymous `401`, no group `403`, every profile
   with Référentiels `200`; `POST`, `PUT`, `PATCH`, `DELETE` answer `405`.

## 4. Backend: demo data

1. Management command `create_demo_types_contrat` (D22): refuses without `DEBUG`;
   `get_or_create` on code and opening date; the four types and the retired one; prints what it
   created.
2. Tests: refused without `DEBUG`; a run creates valid rows covering the four flag combinations
   and the retired type (open in 2022, not today); a second run creates nothing and writes no
   audit entry; its entries have no author.

## 5. Frontend: "Types de contrat" tab

1. `features/referentiels/`:
   - `api/referentiels.ts`: type `TypeContrat`; `fetchTypesContrat({ date, toutes })`;
   - `stores/referentiels.ts`: the `typesContrat` tab value and a `typesContrat` object with its
     own date and text filter (D21);
   - `components/typesContrat.ts`: `filterTypesContrat(list, texte)` built on `normalise()`;
     if it matches `filterFonctions` word for word, make one generic `filterByCodeAndName()`
     used by both;
   - `components/TypesContratTable.vue`: DataTable with code, nom, "Durée déterminée",
     "Période d'essai" ("Oui"/"Non"), opening and closing dates; "Types au" date picker and text
     filter; loading, empty and error states (D20);
   - `views/ReferentielsView.vue`: the fifth tab (D19).
2. Tests:
   - the tab comes after "Fonctions";
   - it loads the types for today, reloads when the date changes, shows the API error;
   - the flags show as "Oui" and "Non"; the text filter matches code and name, ignoring case and
     accents;
   - the store keeps the tab, date and filter, apart from the other tabs' dates;
   - the tab offers no button that changes data;
   - the existing Référentiels tests stay green.

## 6. Wrap-up

1. Add `Q30` to `docs/questions-ouvertes.md`.
2. `tech-stack.md`: the `referentiels` lines name the contract types (D24).
3. User guide (D23): `docs/capture_screenshots.py` captures the new tab (today, and at a date
   when the retired type was open); `docs/user-guide.md` gets a "Types de contrat" subsection, and
   the tab count and "Who changes the reference data" are updated; rebuild `docs/user-guide.html`.
4. Run the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
5. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
6. Record any decision changed on the way under "Found during implementation" in
   `requirements.md`.
7. Tick **1.4 Contract types** in [`roadmap.md`](../roadmap.md).
8. Run `/changelog` on the branch.
