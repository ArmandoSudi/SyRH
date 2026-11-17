# Base models — plan

Task groups for roadmap phase 0.5, backend only. Decision numbers (`D1`...) refer to
[`requirements.md`](requirements.md). Each group ends with its tests passing and can be committed
on its own.

## 1. Test scaffolding

1. Create `apps/core/test_base_models.py`.
2. Declare a test-only model inheriting `BaseModel` (one `nom` field) under
   `django.test.utils.isolate_apps("apps.core")`; create its table in `setUpClass` and drop it in
   `tearDownClass` with `connection.schema_editor()` (D14).
3. If the schema editor approach fights the foreign key to `User`, fall back to a test-only app
   added to `INSTALLED_APPS` in the test run only, and record the change in `requirements.md`
   under "Found during implementation".

## 2. Abstract base model

1. `apps/core/models.py`: `BaseModel`, `abstract = True`, with `date_creation`,
   `date_modification`, `cree_par`, `modifie_par` and their French verbose names (D2, D3).
2. Timestamps: `date_creation` set on insert, `date_modification` on every save, not editable
   (D4).
3. Override `save()` so that, when `update_fields` is given, `date_modification` and
   `modifie_par` are added to it (D5).
4. Author fields: `AUTH_USER_MODEL`, `PROTECT`, `null=True`, `blank=True`, `editable=False`,
   `related_name="+"` (D6).
5. Docstring: what the base gives, that the author is filled by the mixins or by hand (D7), and
   that `QuerySet.update()` and `bulk_update()` bypass `save()`, so callers set
   `date_modification` themselves.
6. Tests:
   - creating a row sets both dates, equal or nearly so, timezone-aware;
   - saving again moves `date_modification` forward and leaves `date_creation` unchanged;
   - `save(update_fields=["nom"])` still updates `date_modification` and `modifie_par`;
   - both authors may be empty;
   - deleting a user who is `cree_par` or `modifie_par` of a row raises `ProtectedError`;
   - `User` gains no reverse accessor from the base;
   - `makemigrations --check` finds nothing for `core` (D9).

## 3. API mixin and serializer

1. `apps/core/mixins.py`: `AuthorMixin` with `perform_create` (`cree_par` and `modifie_par`) and
   `perform_update` (`modifie_par`) (D10).
2. `apps/core/serializers.py`: `BaseModelSerializer`, a `ModelSerializer` whose `Meta` makes the
   four fields read-only; subclasses list them in `fields` to expose them (D11).
3. Tests, with a test viewset on the test model called through `APIRequestFactory`:
   - a create by user A sets both authors to A;
   - an update by user B sets `modifie_par` to B and keeps `cree_par` as A;
   - a `PATCH` updates `date_modification` and `modifie_par`;
   - values sent by the client for the four fields are ignored;
   - the response contains the four fields, authors as user ids;
   - an anonymous request still gets `401` (D12).

## 4. Admin mixin

1. `apps/core/admin.py`: `BaseModelAdmin` mixin with `save_model` (`cree_par` on add,
   `modifie_par` always) and the four fields added to `readonly_fields` (D13).
2. Keep any `readonly_fields` a subclass declares: append to them rather than replace them.
3. Tests, with a separate `AdminSite` and a `RequestFactory` request:
   - adding through `save_model` sets both authors;
   - changing sets `modifie_par` only;
   - the four fields are read-only, alongside a subclass's own read-only fields.

## 5. Wrap-up

1. Run all quality gates from [`tech-stack.md`](../tech-stack.md); the frontend gates must pass
   unchanged.
2. `tech-stack.md`:
   - Database section: every business model inherits `apps.core.models.BaseModel`;
   - API section: business viewsets use `AuthorMixin`, serializers extend `BaseModelSerializer`;
   - Backend section: reference-table admins use `BaseModelAdmin`;
   - say that the author is filled explicitly, never by middleware.
3. Tick **0.5 Base models** in [`roadmap.md`](../roadmap.md).
4. Run `/changelog` before merging.
