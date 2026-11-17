# Audit log — plan

Task groups for roadmap phase 0.6, backend first, then frontend. Decision numbers (`D1`...) refer
to [`requirements.md`](requirements.md). Each group ends with its tests passing and can be
committed on its own.

## 1. Backend: the audit app and its table

1. Create `apps/audit` (`verbose_name = "Journal d'audit"`), add it to `INSTALLED_APPS`.
2. Model `EntreeAudit`: `date` (default now), `auteur` (user, `PROTECT`, nullable), `action`
   (choices `creation`, `modification`, `suppression`), `table` (content type, `PROTECT`),
   `objet_id`, `objet_libelle`, `module`, `changements` (JSON list of
   `{champ, libelle, avant, apres}`) (D2 to D4, D18).
3. Indexes on `date`, on (`table`, `objet_id`) and on (`module`, `date`) (D28). Default ordering
   newest first.
4. `save()` refuses an entry that already has a primary key; `delete()` raises (D16).
5. Migration with `RunSQL`: a trigger function that raises on `UPDATE` and `DELETE`, attached
   `BEFORE UPDATE OR DELETE ... FOR EACH ROW`, with its reverse SQL (D16, D17).
6. Not registered in Django admin (D19).
7. Tests:
   - an entry can be created and read back with its JSON changes;
   - saving it again, `QuerySet.update()` and `QuerySet.delete()` fail;
   - raw SQL `UPDATE` and `DELETE` on the table raise a database error;
   - the table is absent from the admin site.

## 2. Backend: values and the record service

1. `apps/audit/values.py`: turn a field value into JSON (D5): dates and decimals as text, foreign
   keys as `{id, libelle}`, many-to-many changes as `{ajoutes, retires}`; masked fields (D7).
2. `apps/audit/service.py`:
   - `snapshot(instance)`: the logged fields of an instance, skipping D6's fields;
   - `diff(before, after)`: the changed fields with their French labels;
   - `record(instance, action, auteur, changements, module)`: writes one entry, skipped when
     `changements` is empty for a modification (D8).
3. Tests: each value kind; masked password; skipped fields; an empty diff writes nothing.

## 3. Backend: capture on `BaseModel`

1. `BaseModel` gains a `module` class attribute, empty on the base (D22).
2. System check in `apps/core/checks.py`: every concrete `BaseModel` subclass has a module from
   `roles.MODULES`; error `core.E001` otherwise (D22).
3. `BaseModel.save()`: in `transaction.atomic()`, read the old row (for an update), save, then
   `record()` a creation (author `cree_par`) or a modification (author `modifie_par`) (D10 to
   D12).
4. `BaseModel.delete(auteur=None)`: snapshot, delete, `record()` a deletion, in one transaction
   (D11).
5. Default manager with a QuerySet whose `update()` and `delete()` raise, and
   `update_audited(auteur, **values)` that saves row by row (D13). Document `bulk_create` and
   `bulk_update` in the docstring.
6. `AuthorMixin.perform_destroy` and `BaseModelAdmin.delete_model` / `delete_queryset` pass the
   request user to `delete()` (D11).
7. Update phase 0.5's tests: `Probe` declares `module`; `make_old()` uses `Probe._base_manager`
   for its direct update.
8. Tests on `Probe`:
   - creation, modification and deletion each write one entry with the right author, action,
     module, label and old/new values;
   - a save without change writes nothing (D8);
   - a rolled-back save leaves no entry (D10);
   - `objects.update()` and `objects.filter(...).delete()` raise; `update_audited()` logs one
     entry per row;
   - the system check reports a `BaseModel` subclass without module, or with an unknown one;
   - through the API and admin mixins, the author is the request user, deletion included.

## 4. Backend: account administration

1. `roles.py`: add the `audit` module ("Journal d'audit") and grant it to Auditeur, Direction RH
   and Administrateur système (D20). Migration for the new `access_audit` permission.
2. Audit mixin for `UserAdmin` and `GroupAdmin` in `apps/accounts/admin.py` (D15):
   - `save_model`: snapshot the fields and many-to-many sets before saving;
   - `save_related`: after saving, record one entry with field changes and membership or
     permission changes;
   - `user_change_password`: record a masked password change;
   - entries carry the scope `comptes` (D21).
3. `PasswordView` (own password): record a masked change by the user themself.
4. `sync_groups()`: record, with an empty author, each permission it adds to a group (D15).
5. Tests:
   - adding a user to a group in admin records the membership change and the admin as author;
   - changing a group's permissions records the permissions added and removed;
   - changing a password (admin form and own-password endpoint) records a masked change, and no
     entry contains the hash;
   - signing in writes no entry (`last_login`, D6);
   - running `sync_groups()` on a fresh database records what it added; a second run records
     nothing;
   - `access_audit` belongs to exactly the three groups.

## 5. Backend: read-only API

1. `apps/audit/serializers.py`: list and detail serializers; author as `{id, nom}` or
   "Système"; table as its French label (D27).
2. `apps/audit/views.py`: a read-only viewset, `HasModuleAccess("audit")`, queryset filtered to
   the reader's modules plus `comptes` (D21, D26); 50 per page (D24).
3. Filters of D24, validated (unknown module or action → `400` per field).
4. URLs under `/api/audit/`.
5. Tests:
   - `401` anonymous, `403` without `access_audit`;
   - with entries in Paie, Social, Agents, Référentiels and `comptes`: the Auditeur sees Agents,
     Référentiels and `comptes`; Direction RH sees all; the Administrateur système sees
     Référentiels and `comptes`;
   - a hidden entry answers `404` on detail (D23);
   - each filter, alone and combined; pagination; newest first;
   - `POST`, `PUT`, `PATCH`, `DELETE` answer `405`.

## 6. Frontend: "Journal d'audit" screen

1. `shared/utils/modules.ts`: add `audit: 'accounts.access_audit'`.
2. `features/audit/`: `api/audit.ts` (typed `fetchEntries`, `fetchEntry`), `stores/audit.ts`
   (filters kept across navigation), `views/AuditView.vue`, `components/AuditEntryPanel.vue`,
   `routes.ts` (`/audit`, lazy, `meta.permission`) (D29, D32).
3. `AuditView.vue`: PrimeVue DataTable in lazy mode, the columns and filters of D30; the module
   filter lists only the reader's modules plus "Comptes".
4. `AuditEntryPanel.vue`: side panel with label, old value, new value per field; masked values
   as "••••••" (D31).
5. `AppShell.vue`: menu entry "Journal d'audit" under Administration, with its permission.
6. Tests:
   - the store keeps filters and builds the query string;
   - the view renders a page of entries and asks for the next page;
   - the panel renders creation, modification and deletion entries;
   - the menu shows "Journal d'audit" for the three profiles and not for Gestion de carrière.

## 7. Wrap-up

1. Run the manual walkthrough in [`validation.md`](validation.md) with the demo accounts, in
   light and dark themes.
2. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
3. `tech-stack.md`: `apps.audit` in the repository layout and app list; how capture works and
   the `module` attribute in the Database section; the audit decision moved out of "Decisions not
   yet taken" (D33).
4. Tick **0.6 Audit log** in [`roadmap.md`](../roadmap.md).
5. Run `/changelog` before merging.
