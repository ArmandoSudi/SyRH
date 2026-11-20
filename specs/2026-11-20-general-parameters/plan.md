# General parameters — plan

Task groups for roadmap phase 1.8, as in phase 1.7: model, permissions and admin, API, demo
data, frontend and wrap-up. Decision numbers (`D1`...) refer to
[`requirements.md`](requirements.md). Each group ends with its tests passing and is committed on
its own. **(asked)**

## 1. Backend: the `Parametre` model

1. Key list (D2): `Cle` `TextChoices` at module level, and a `DEFINITIONS` mapping each key to
   its unit and bounds (`unite`, `minimum`, `maximum`); a test checks every key has a definition.
2. Model `Parametre(BaseModel)` in `apps/referentiels/models.py`, `module = "referentiels"`
   (D1, D15): `cle` (`CharField`, choices), `valeur` (`PositiveSmallIntegerField`),
   `date_ouverture`, `date_fermeture` (help text "Premier jour où la valeur ne s'applique plus");
   `verbose_name` "paramètre"; ordering by the key order (a `Case`, as `PieceRequise`), then
   opening date (D4); `default_permissions = NO_DELETE` (D8); manager `ClassificationQuerySet`.
3. Constraints (D9): `closing_after_opening(...)`; `unique_per_period(..., "cle", ...)`; `cle`
   among the keys; `valeur` within its key's bounds, one `CheckConstraint` OR-ing
   `Q(cle=k, valeur__gte=min, valeur__lte=max)` over `DEFINITIONS`.
4. Rules (D7, D10): `clean()` and `save()` report reversed dates on `date_fermeture`, the bounds
   on `valeur` ("Entre 18 et 30 ans."), and a changed key on `cle`.
5. Helper (D5): `Parametre.valeur_au(cle, jour) -> int`, raising `ParametreManquant`
   (a `LookupError`) with a French message; label `Libellé : valeur unité` (D15), and a `unite`
   property.
6. Migration `0011_parametre`.
7. Tests (new `test_parametres.py`): each constraint bypassing the model (unknown key, value
   below and above each key's bounds, the bounds themselves accepted, overlapping periods of one
   key refused, two keys on the same period accepted, consecutive periods accepted); the bound
   and key messages on their fields; reversed dates; required fields; key fixed after creation,
   value correctable; `ouvertes(date)`; order by key then date; `valeur_au` before, on and after
   a change, and `ParametreManquant` with no row; audit of create, correct and close with the
   label.

## 2. Backend: permissions and Django admin

1. `roles.py` (D12, D13): `PARAMETRE_EDIT_PERMISSIONS` (view, add, change on `parametre`), added
   to `REFERENTIELS_EDIT_PERMISSIONS`. Run `migrate` on the development database straight after.
2. `admin.py` (D14): `ParametreAdmin` on `BaseModelAdmin`, with filters on the key and
   `OuvertFilter`; the key read-only on change (`get_readonly_fields`); a help text on `valeur`
   listing each key's unit and bounds.
3. Tests (`test_access.py`): the three editors hold the three permissions, nobody else adds or
   changes, nobody deletes; the group setup regrants and keeps hand-made ones; `demo.carriere`
   adds a value and is its author; a value out of bounds shows next to "Valeur"; an overlapping
   value for the same key shows at the top; the key is read-only on change; Rémunération gets
   `403`.

## 3. Backend: read-only API

1. `ParametreSerializer` with `cle_libelle` and `unite` (D17).
2. `ParametreViewSet` on `PeriodeMixin`, `HasModuleAccess("referentiels")`, no pagination; URL
   `parametres` (D16).
3. Tests: open today, on `?date=`, all with `?toutes=1`, in key order, with the fields of D17;
   invalid date `400`; `401`, `403`, `200` per profile; writes `405`.

## 4. Backend: demo data

1. `create_demo_parametres` (D21): refuses without `DEBUG`; `get_or_create` on key and opening
   date; prints what it created.
2. Tests: refused without `DEBUG`; every row passes `full_clean()`; `valeur_au` gives 25, 65 and
   30 today, 4 children in 2019 and 6 today; a second run creates nothing and writes no audit
   entry; no author.

## 5. Frontend: "Paramètres" tab

1. `features/referentiels/`:
   - `api/referentiels.ts`: types `Parametre`, `CleParametre`; `fetchParametres`;
   - `components/parametres.ts`: `PARAMETRES` (key and label, in the order of D2, matching the
     backend), and `buildParametres(rows)` giving one row per key, `null` value when missing;
     `valeurLibelle(row)` ("25 ans", "Non renseigné");
   - `components/ParametresTable.vue` (D19);
   - `stores/referentiels.ts`: the `parametres` tab value and a `parametres` object (date) (D20);
   - `views/ReferentielsView.vue`: the ninth tab (D18).
2. Tests:
   - `buildParametres`: every key in order, a missing key kept as "Non renseigné", a row whose
     key is unknown to the client not lost;
   - the client key list matches the backend's (a backend test reads `components/parametres.ts`,
     as for the event kinds of 1.5);
   - the tab comes after "Banques"; loads today's values; reloads on a new date leaving the other
     dates alone; shows the API error; no button that changes data; its store state is kept apart
     from the other tabs.

## 6. Wrap-up

1. Add `Q34` to `docs/questions-ouvertes.md`.
2. `tech-stack.md`: the `referentiels` lines name the general parameters (D23).
3. User guide (D22): extend `docs/capture_screenshots.py` (run `create_demo_parametres` first;
   capture the tab today and in 2019); add the "Paramètres" subsection; update the tab count and
   "Who changes the reference data"; rebuild the HTML.
4. Check the migration applies, reverses and reapplies on a scratch database.
5. Run the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
6. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
7. Record any decision changed on the way under "Found during implementation".
8. Tick **1.8 General parameters** in [`roadmap.md`](../roadmap.md).
9. Run `/changelog` on the branch.
