# Organisation — plan

Task groups for roadmap phase 1.1, backend first, then frontend. Decision numbers (`D1`...) refer
to [`requirements.md`](requirements.md). Each group ends with its tests passing and can be
committed on its own.

## 1. Backend: the `referentiels` app and sites

1. Create `apps/referentiels` (`verbose_name = "Référentiels"`), add it to `INSTALLED_APPS`
   after `apps.audit`.
2. Model `Site(BaseModel)`, `module = "referentiels"`: `code` (unique), `nom`, `ville`, `siege`
   (boolean, default false), `date_fermeture` (nullable) (D6). `default_permissions = ("view",
   "add", "change")` (D12). `__str__` is `CODE — Nom` (D19).
3. Constraints: unique `code`; unique `siege` where `siege` is true and `date_fermeture` is null
   (D6, D13).
4. Tests:
   - a site is created, read back and audited under `referentiels`;
   - a second open head office is refused by the database; a closed one is allowed;
   - a duplicate code is refused;
   - the model has no delete permission.

## 2. Backend: organisation units

1. Migration that installs the `btree_gist` extension (`BtreeGistExtension`), before the unit
   table (D9).
2. Model `UniteOrganisationnelle(BaseModel)`, `module = "referentiels"`:
   - `type` (choices `direction`, `departement`, `service`, `bureau`, French labels, with a level
     order) (D1);
   - `code` (20, saved in capitals), `nom` (150) (D4);
   - `parent` (self, `PROTECT`, nullable, `related_name="enfants"`), `site` (`PROTECT`) (D5);
   - `date_ouverture`, `date_fermeture` (nullable) (D7);
   - `default_permissions = ("view", "add", "change")`; ordering by type level, then code;
     `__str__` is `CODE — Nom`.
3. Database constraints (D13):
   - check: `type = 'direction'` if and only if `parent` is null;
   - check: `parent` differs from `id`;
   - check: `date_fermeture` is null or after `date_ouverture`;
   - exclusion: `code WITH =`, `daterange(date_ouverture, date_fermeture, '[)') WITH &&` (D9).
4. Queryset method `ouvertes(date)`: units open on that date (D7).
5. One rules method, called by `clean()` and by `save()`, raising `ValidationError` per field in
   French (D14):
   - the parent's level is higher (D2);
   - on update, `type`, `parent` and `site` are unchanged, read from the database (D8);
   - the unit opens no earlier than its parent and closes no later (D10);
   - closing (or moving the closing date earlier) is refused while a child stays open after it
     (D10);
   - the site is open at the opening date (D11).
6. `Site` rules: closing is refused while an open unit is located there (D11).
7. Tests:
   - each database constraint, by bypassing the rules (`_base_manager` or raw SQL);
   - each model rule, through `full_clean()` and through `save()`;
   - a restructuring: close a service on a date, open its successor with the same code on the
     same date; overlapping periods with the same code are refused;
   - `ouvertes(date)` on the day before, on and after the opening and closing dates;
   - deleting a site or a parent that is still referenced is refused (`PROTECT`);
   - creating, renaming and closing a unit each write one audit entry with the right label.

## 3. Backend: permissions and Django admin

1. `roles.py`: replace `ADMIN_EXTRA_PERMISSIONS` with per-group extra permissions; give
   `referentiels.view/add/change` on `site` and `uniteorganisationnelle` to Administrateur
   système, Gestion de carrière and Chef de service — Gestion de carrière (D16).
2. Run the group setup once per `migrate`, after every app has its permissions (it runs today
   after `accounts` only, before `referentiels` exists in the permission table) (D18).
3. `create_demo_users`: tick "Statut équipe" for the demo accounts of the three editing groups
   (D17).
4. `apps/referentiels/admin.py`, both classes with `BaseModelAdmin` (D16):
   - `SiteAdmin`: list of code, name, city, head office, closing date; search on code, name and
     city;
   - `UniteOrganisationnelleAdmin`: list of code, name, type, parent, site, dates; filters on
     type, site and "ouverte aujourd'hui"; search on code and name; parent and site through
     autocomplete; `type`, `parent` and `site` read-only when changing a unit (D8).
5. Tests:
   - the permission matrix of `test_roles.py` includes the new permissions, exactly for the three
     groups; nobody has delete;
   - running the group setup on a fresh database grants them, and a second run adds nothing;
   - in admin, a Gestion de carrière staff account adds and changes a unit, is refused deletion,
     and the admin form shows rule errors next to the field;
   - a Rémunération staff account cannot open the unit admin.

## 4. Backend: read-only API

1. `apps/referentiels/serializers.py`: `SiteSerializer`, `UniteOrganisationnelleSerializer` on
   `BaseModelSerializer`, with the fields of D22.
2. `apps/referentiels/views.py`: two read-only viewsets, `HasModuleAccess("referentiels")`, no
   pagination; `?date=` (validated, default today) and `?toutes=1` (D20, D21, D23).
   `select_related` on parent and site.
3. URLs under `/api/referentiels/` (`unites`, `sites`).
4. Tests:
   - `401` anonymous, `403` without `access_referentiels`, `200` for each profile that has it;
   - units open today by default; at a past date, the closed unit appears and its successor does
     not; `?toutes=1` returns both;
   - an invalid date answers `400` on `date`;
   - `POST`, `PUT`, `PATCH`, `DELETE` answer `405`;
   - the number of queries does not grow with the number of units.

## 5. Backend: demo data

1. Management command `create_demo_organisation` (D28, D29):
   - refuses to run when `DEBUG` is off;
   - creates sites and units with `get_or_create` on the code, so a second run changes nothing;
   - prints what it created.
2. Tests: refused without `DEBUG`; a run creates a valid tree (every rule passes); a second run
   creates nothing and writes no audit entry.

## 6. Frontend: "Référentiels" screen

1. `features/referentiels/`:
   - `api/referentiels.ts`: types `Site`, `Unite`, functions `fetchUnites({ date, toutes })`,
     `fetchSites({ toutes })`;
   - `components/tree.ts`: build the TreeTable nodes from the flat list (D20); filter by text,
     keeping the ancestors of a match;
   - `components/OrganisationTree.vue` and `components/SitesTable.vue`;
   - `stores/referentiels.ts`: tab, date, text filter, closed sites shown (D27);
   - `views/ReferentielsView.vue`: the two tabs (D24);
   - `routes.ts`: `/referentiels`, lazy, `meta.permission` from `MODULE_PERMISSIONS`.
2. `router/index.ts`: remove `referentiels` from the placeholder list; add the feature's routes.
3. `OrganisationTree.vue` (D25): TreeTable with name (indented), code, type (Tag), site, opening
   and closing dates; "Organisation au" date picker, text filter, expand all and collapse all;
   empty and error states.
4. `SitesTable.vue` (D26): DataTable with code, name, city, head office, status; "Afficher les
   sites fermés" toggle.
5. Tests:
   - `tree.ts`: nesting, sibling order, a filter keeps the ancestors, an orphan (parent not in the
     list) is shown at the root rather than lost;
   - the view loads units for today, reloads when the date changes, and shows the API error;
   - the sites tab lists sites and asks for closed ones when toggled;
   - the store keeps tab, date and filter across remounts;
   - the screen offers no button that changes data.

## 7. Wrap-up

1. Add `Q27` (organigramme, codes, sites, levels) to `docs/questions-ouvertes.md`.
2. `tech-stack.md`: `referentiels` in the repository layout; exclusion constraints with
   `btree_gist` in the Database section (D30).
3. Run the manual walkthrough in [`validation.md`](validation.md), in light and dark themes.
4. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
5. Record any decision changed on the way under "Found during implementation" in
   `requirements.md`.
6. Tick **1.1 Organisation** in [`roadmap.md`](../roadmap.md).
