# Classification — plan

Task groups for roadmap phase 1.2, backend first, then frontend. Decision numbers (`D1`...) refer
to [`requirements.md`](requirements.md). Each group ends with its tests passing and can be
committed on its own.

## 1. Backend: catégories

1. Model `Categorie(BaseModel)` in `apps/referentiels/models.py`, `module = "referentiels"`:
   `code` (20, saved in capitals), `nom` (150), `rang` (positive integer), `date_ouverture`,
   `date_fermeture` (nullable) (D2, D6, D9). `default_permissions = ("view", "add", "change")`
   (D14); ordering by `rang`; `__str__` is `CODE — Nom` (D23).
2. Queryset method `ouvertes(date)`, built on the existing `open_on()` helper (D9, D16).
3. Database constraints (D15):
   - check: `rang > 0`;
   - check: `date_fermeture` is null or after `date_ouverture`;
   - exclusion: `code WITH =`, `DateRange(date_ouverture, date_fermeture) WITH &&`;
   - exclusion: `rang WITH =`, same date range (D6, D12).
4. Tests:
   - a catégorie is created, read back with its code in capitals, and audited under
     `referentiels` with the label `CODE — Nom`;
   - each constraint, by bypassing the model (`_base_manager` or raw SQL);
   - the same code or rank on consecutive periods is accepted;
   - `ouvertes(date)` on the day before, on and after the opening and closing dates;
   - the model has no delete permission.

## 2. Backend: grades and échelons

1. Model `Grade(BaseModel)`, `module = "referentiels"`: `categorie` (`PROTECT`,
   `related_name="grades"`), `code`, `nom`, `rang`, dates (D1 to D3, D6). Ordering by catégorie
   rank, then grade rank. Method (or property) `cle_ordre` returning `(categorie.rang, rang)` (D7).
   `__str__` is `CODE — Nom`.
2. Model `Echelon(BaseModel)`, `module = "referentiels"`: `grade` (`PROTECT`,
   `related_name="echelons"`), `numero` (positive integer), dates (D1, D4). Ordering by grade
   order, then `numero` (D8). `__str__` is `GRADE — Échelon N` (D4, D23).
3. Database constraints (D12, D15):
   - grade: `rang > 0`; closing after opening; exclusion on `code` (whole grid, D3); exclusion on
     `categorie WITH =, rang WITH =` and the date range;
   - échelon: `numero > 0`; closing after opening; exclusion on `grade WITH =, numero WITH =` and
     the date range.
4. `ouvertes(date)` on both querysets.
5. One `check_rules()` method per model, called by `clean()` and by `save()`, raising
   `ValidationError` per field in French, reusing `raise_if()` and `still_open_after()` (D16):
   - grade and échelon: on update, the parent is unchanged, read from the database (D11);
   - grade: opens no earlier than its catégorie and closes no later; échelon: same within its
     grade (D10, D13);
   - catégorie and grade: closing (or moving the closing date earlier) is refused while a child
     stays open after it (D13).
6. Tests:
   - each database constraint, by bypassing the rules;
   - each model rule, through `full_clean()` and through `save()`;
   - a grade code already used in another catégorie over the same period is refused (D3);
   - `cle_ordre` puts a grade of a higher catégorie above every grade of a lower one, and orders
     grades of the same catégorie by rank (D7);
   - a gap in échelon numbers is accepted (D5);
   - a reform: close a grade's échelons, then the grade, on a date; open a successor with the same
     code and new échelons on that date; overlapping periods with the same code are refused;
   - deleting a catégorie or grade that is still referenced is refused (`PROTECT`);
   - creating, correcting and closing each kind of row writes one audit entry with the right
     label.

## 3. Backend: permissions and Django admin

1. `roles.py`: `CLASSIFICATION_EDIT_PERMISSIONS` (view, add, change on `categorie`, `grade`,
   `echelon`), added to Administrateur système, Gestion de carrière and Chef de service — Gestion
   de carrière in `EXTRA_PERMISSIONS` (D18, D19).
2. `apps/referentiels/admin.py`, three classes with `BaseModelAdmin`, no inlines (D21, D22):
   - `CategorieAdmin`: list of code, name, rank, dates; filter "ouverte aujourd'hui"; search on
     code and name;
   - `GradeAdmin`: list of code, name, catégorie, rank, dates; filters on catégorie and "ouvert
     aujourd'hui"; search on code and name; catégorie through autocomplete, read-only on change;
   - `EchelonAdmin`: list of grade, number, dates; filters on grade's catégorie and "ouvert
     aujourd'hui"; search on the grade's code; grade through autocomplete, read-only on change.
3. Tests:
   - the permission matrix of `test_roles.py` includes the new permissions, exactly for the three
     groups; nobody has delete;
   - running the group setup on a fresh database grants them, and a second run adds nothing;
   - in admin, a Gestion de carrière staff account adds and changes a grade and an échelon, is
     refused deletion, and sees rule errors next to the field;
   - a Rémunération staff account cannot open the classification admin.

## 4. Backend: read-only API

1. `serializers.py`: `CategorieSerializer`, `GradeSerializer`, `EchelonSerializer` on
   `BaseModelSerializer`, with the fields of D25.
2. `views.py`: three read-only viewsets, `HasModuleAccess("referentiels")`, no pagination,
   `?date=` (default today) and `?toutes=1`, with the date validation shared with `unites`
   (factor it out if it is inline today) (D24, D26). `select_related` for the ordering and the
   échelon label.
3. URLs under `/api/referentiels/` (`categories`, `grades`, `echelons`).
4. Tests:
   - `401` anonymous, `403` without `access_referentiels`, `200` for each profile that has it, on
     all three;
   - rows open today by default; at a past date, the reformed grade appears and its successor
     does not; `?toutes=1` returns both;
   - the order follows D7 and D8;
   - an invalid date answers `400` on `date`;
   - `POST`, `PUT`, `PATCH`, `DELETE` answer `405`;
   - the number of queries does not grow with the number of rows.

## 5. Backend: demo data

1. Management command `create_demo_classification` (D31, D32):
   - refuses to run when `DEBUG` is off;
   - creates the grid with `get_or_create` (on the code and opening date for catégories and
     grades, on grade and number for échelons), so a second run changes nothing;
   - prints what it created.
2. Tests: refused without `DEBUG`; a run creates a valid grid (every rule passes) including the
   reformed grade and its successor; a second run creates nothing and writes no audit entry.

## 6. Frontend: "Classification" tab

1. `features/referentiels/`:
   - `api/referentiels.ts`: types `Categorie`, `Grade`, `Echelon`; functions
     `fetchCategories`, `fetchGrades`, `fetchEchelons`, each with `{ date, toutes }`;
   - `components/tree.ts`: make `filterTree` and `expandedKeys` generic over the node type (D29);
     the organisation tests stay green unchanged;
   - `components/classification.ts`: build the TreeTable nodes from the three lists, with keys
     that cannot collide across levels (`c-1`, `g-1`, `e-1`); an orphan is shown at the root
     rather than lost;
   - `components/ClassificationTree.vue` (D28);
   - `stores/referentiels.ts`: the `classification` tab, the classification date and filter,
     separate from the organisation ones (D30);
   - `views/ReferentielsView.vue`: the third tab (D27).
2. `ClassificationTree.vue`: loads the three lists in parallel for the chosen date; TreeTable with
   name, code, level (Tag), rank, opening and closing dates; "Classification au" date picker,
   text filter, expand all and collapse all; loading, empty and error states.
3. Tests:
   - `classification.ts`: nesting, order by rank and number, no key collision between a
     catégorie and a grade with the same id, orphans at the root;
   - the generic filter keeps the ancestors of a matching échelon;
   - the tab loads the grid for today, reloads when the date changes, and shows the API error;
   - the store keeps the tab, classification date and filter across remounts, and changing one
     date leaves the other alone;
   - the tab offers no button that changes data.

## 7. Wrap-up

1. Add `Q28` (the real grid) to `docs/questions-ouvertes.md`.
2. `tech-stack.md`: the `referentiels` line names the classification (D33).
3. Run the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
4. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
5. Record any decision changed on the way under "Found during implementation" in
   `requirements.md`.
6. Tick **1.2 Classification** in [`roadmap.md`](../roadmap.md).
