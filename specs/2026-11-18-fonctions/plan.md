# Fonctions — plan

Task groups for roadmap phase 1.3, backend first, then frontend, then wrap-up. Decision numbers
(`D1`...) refer to [`requirements.md`](requirements.md). Each group ends with its tests passing
and is committed on its own. **(asked)**

## 1. Backend: the `Fonction` model

1. Model `Fonction(BaseModel)` in `apps/referentiels/models.py`, `module = "referentiels"`
   (D1, D14):
   - `code` (20), `nom` (150), `nature` (`TextChoices`: `responsabilite` "Responsabilité",
     `execution` "Exécution"), `date_ouverture`, `date_fermeture` (null, with the help text "Premier
     jour où la fonction n'existe plus");
   - `__str__`: `CODE — Nom`;
   - `Meta`: `ordering` by nature (Responsabilité first) then `nom` (D4);
     `default_permissions = NO_DELETE` (D7).
2. Queryset method `ouvertes(date)`, the same as the classification's (D5).
3. Code saved in capitals from `clean()` and `save()`, as for catégories (D9).
4. Database constraints (D8): `closing_after_opening("fonction_fermeture_apres_ouverture")`;
   `unique_per_period("fonction_code_unique_par_periode", "code", ...)`; a check constraint
   limiting `nature` to its two values.
5. Migration `0004_fonction`.
6. Tests (in `test_models.py` or a new `test_fonctions.py`):
   - each constraint refuses an invalid row through `_base_manager` or raw SQL, without the
     model rules;
   - the same code on overlapping periods is refused, on consecutive periods accepted;
   - two fonctions with the same name are accepted;
   - the code is saved in capitals through `save()` and through `full_clean()`;
   - `ouvertes(date)` includes the opening day and excludes the closing day;
   - the order is Responsabilité first, then by name;
   - a rename (close, open a successor with the same code on the same day) succeeds, and the list
     at the earlier date still shows the old name;
   - creating, correcting and closing a fonction each write an audit entry with the label
     `CODE — Nom` under module `referentiels`.

## 2. Backend: permissions and Django admin

1. `roles.py`: `FONCTION_EDIT_PERMISSIONS` (view, add, change on `fonction`), added to
   `REFERENTIELS_EDIT_PERMISSIONS` (D11, D12).
2. `apps/referentiels/admin.py`: `FonctionAdmin(BaseModelAdmin)` with list columns, filters
   (nature, the shared `OuvertFilter`), search on code and name (D13).
3. Tests (in `test_access.py`, beside the organisation's and classification's):
   - the three editor groups get view, add and change on `fonction` after `migrate`; no group gets
     delete; no other group gets add or change;
   - a permission removed by hand is granted again by the next group setup, and one added by hand
     is kept;
   - `demo.carriere` can add and change a fonction in `/admin/`, and the admin user is the
     author of the row and of its audit entry.

## 3. Backend: read-only API

1. `serializers.py`: `FonctionSerializer` on `BaseModelSerializer`, with `nature_libelle`
   (D16).
2. `views.py`: `FonctionViewSet(PeriodeMixin, ReadOnlyModelViewSet)`,
   `HasModuleAccess("referentiels")`, no pagination (D15, D17).
3. URL `/api/referentiels/fonctions/` in `urls.py`.
4. Tests:
   - the list returns the fonctions open today by default, those open on `?date=`, all with
     `?toutes=1`, in the order of D4, with the fields of D16;
   - an invalid `date` answers `400` on the `date` field;
   - anonymous `401`, an account in no group `403`, every profile with Référentiels `200`;
   - `POST`, `PUT`, `PATCH` and `DELETE` answer `405`.

## 4. Backend: demo data

1. Management command `create_demo_fonctions` (D21, D22):
   - refuses to run when `DEBUG` is off;
   - creates the list with `get_or_create` on the code and opening date, so a second run changes
     nothing;
   - includes one fonction renamed in the past, with its successor;
   - prints what it created.
2. Tests: refused without `DEBUG`; a run creates a valid list with both natures and the renamed
   fonction; a second run creates nothing and writes no audit entry.

## 5. Frontend: "Fonctions" tab

1. `features/referentiels/`:
   - `api/referentiels.ts`: type `Fonction` (with `nature` and `nature_libelle`);
     `fetchFonctions({ date, toutes })`;
   - `stores/referentiels.ts`: the `fonctions` tab value, and a `fonctions` object with its own
     date and text filter (D20);
   - `components/FonctionsTable.vue`: DataTable with code, nom, nature (Tag), opening and
     closing dates; "Fonctions au" date picker and text filter on code and name; loading, empty
     and error states (D19);
   - `views/ReferentielsView.vue`: the fourth tab (D18).
2. Tests:
   - the tab loads the fonctions for today, reloads when the date changes, and shows the API
     error;
   - the text filter matches code and name, ignoring case and accents as the other tabs do;
   - the nature shows as a Tag with its French label;
   - the store keeps the tab, date and filter across remounts, and changing the fonctions date
     leaves the organisation and classification dates alone;
   - the tab offers no button that changes data;
   - the existing Référentiels tests stay green.

## 6. Wrap-up

1. Add `Q29` (the real list of fonctions) to `docs/questions-ouvertes.md`.
2. `tech-stack.md`: the `referentiels` lines of both layouts name the fonctions (D24).
3. User guide (D23):
   - `docs/capture_screenshots.py`: run `create_demo_fonctions` first, then capture the new tab
     (today, and filtered by text);
   - `docs/user-guide.md`: a "Fonctions" subsection under "Reference data", with steps and the new
     screenshots; update the tab list and "Who changes the reference data";
   - rebuild `docs/user-guide.html` with `docs/build_user_guide.py`.
4. Run the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
5. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
6. Record any decision changed on the way under "Found during implementation" in
   `requirements.md`.
7. Tick **1.3 Fonctions** in [`roadmap.md`](../roadmap.md).
8. Run `/changelog` on the branch.
