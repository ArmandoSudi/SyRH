# Banks — plan

Task groups for roadmap phase 1.7, as in phase 1.4: model, permissions and admin, API, demo
data, frontend and wrap-up. Decision numbers (`D1`...) refer to
[`requirements.md`](requirements.md). Each group ends with its tests passing and is committed on
its own. **(asked)**

## 1. Backend: the `Banque` model

1. Model `Banque(FlatListRules, BaseModel)` in `apps/referentiels/models.py`,
   `module = "referentiels"` (D1, D15): `code` (20), `nom` (150), `swift` (`CharField` 11,
   `blank=True`, verbose name "code SWIFT/BIC"), `date_ouverture`, `date_fermeture` (help text
   "Premier jour où la banque n'existe plus"); `verbose_name` "banque"; ordering by `nom` (D5);
   `default_permissions = NO_DELETE` (D8); manager `ClassificationQuerySet` (`ouvertes(date)`).
2. Rules (D2, D10): `normalise()` also trims `swift` and puts it in capitals; `clean()` reports a
   wrong shape on `swift` in French ("8 ou 11 caractères : 4 lettres pour la banque, 2 pour le
   pays, ...").
3. Constraints (D9): `closing_after_opening(...)`, `unique_per_period(..., "code", ...)`, a check
   that `swift` is empty or matches `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` (Django
   `Q(swift__regex=...)`).
4. Migration `0010_banque`.
5. Tests (new `test_banques.py`): each constraint bypassing the model (8 and 11 characters
   accepted, 9 characters, lower case and a digit in the country refused, empty accepted); code
   and SWIFT/BIC in capitals through `full_clean()` and `save()`; the shape error on `swift`;
   code unique per period, reused on consecutive periods; same name and same SWIFT/BIC accepted;
   reversed dates on the field; required fields; `ouvertes(date)`; order by name; a merger
   (closed row and successor) keeps the old name at earlier dates; audit of create, correct and
   close with the label.

## 2. Backend: permissions and Django admin

1. `roles.py` (D12, D13): `BANQUE_EDIT_PERMISSIONS` (view, add, change on `banque`); the
   administrator gets it on top of its current permissions; `EXTRA_PERMISSIONS` gains
   "Rémunération" and "Chef de service — Rémunération" with it. Run `migrate` on the development
   database straight after.
2. `admin.py` (D14): `BanqueAdmin` on `BaseModelAdmin`, with `OuvertFilter` and search on code,
   name and SWIFT/BIC.
3. Tests (`test_access.py`): the three editor groups hold the three permissions and nobody else
   holds add or change (Gestion de carrière included); nobody deletes; the group setup regrants
   and keeps hand-made ones; the existing reference permissions are unchanged (Rémunération still
   cannot change a fonction); `create_demo_users` gives the Rémunération accounts staff status;
   `demo.remuneration` adds a bank in the admin and is its author; a wrong SWIFT/BIC shows next
   to its field; a duplicate open code shows at the top; Gestion de carrière gets `403` on the
   bank admin pages; no delete button.

## 3. Backend: read-only API

1. `BanqueSerializer` (D17).
2. `BanqueViewSet` on `PeriodeMixin`, `HasModuleAccess("referentiels")`, no pagination; URL
   `banques` (D16).
3. Tests: open today, on `?date=`, all with `?toutes=1`, by name, with the fields of D17 (blank
   SWIFT/BIC as `""`); invalid date `400`; `401`, `403`, `200` per profile; writes `405`.

## 4. Backend: demo data

1. `create_demo_banques` (D21): refuses without `DEBUG`; `get_or_create` on code and opening
   date; prints what it created.
2. Tests: refused without `DEBUG`; every row passes `full_clean()`; one bank without SWIFT/BIC;
   the merged bank's old and new rows share the code and do not overlap; today's list has no
   closed bank; a second run creates nothing and writes no audit entry; no author.

## 5. Frontend: "Banques" tab

1. `features/referentiels/`:
   - `api/referentiels.ts`: type `Banque`; `fetchBanques`;
   - `components/lists.ts`: `filterByCodeAndName` also matches an optional `swift`, its current
     callers unchanged;
   - `components/BanquesTable.vue` (D19), on the model of `TypesContratTable.vue`;
   - `stores/referentiels.ts`: the `banques` tab value and a `banques` object (date, text) (D20);
   - `views/ReferentielsView.vue`: the eighth tab (D18).
2. Tests: the filter on a SWIFT/BIC; the tab comes after "Sorties et suspensions"; loads today's
   banks; shows "—" for a blank SWIFT/BIC; filters on code, name or SWIFT/BIC; reloads on a new
   date leaving the other dates alone; shows the API error; no button that changes data; its
   store state is kept apart from the other tabs.

## 6. Wrap-up

1. Add `Q33` to `docs/questions-ouvertes.md`.
2. `tech-stack.md`: the `referentiels` lines name the banks (D23).
3. User guide (D22): extend `docs/capture_screenshots.py` (run `create_demo_banques` first;
   capture the tab and the list before the merger); add the "Banques" subsection; update the tab
   count and "Who changes the reference data"; rebuild the HTML.
4. Re-run `create_demo_users` on the development database so the Rémunération accounts get staff
   status (password from `demo-users.md`).
5. Check the migration applies, reverses and reapplies on a scratch database.
6. Run the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
7. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
8. Record any decision changed on the way under "Found during implementation".
9. Tick **1.7 Banks** in [`roadmap.md`](../roadmap.md).
10. Run `/changelog` on the branch.
