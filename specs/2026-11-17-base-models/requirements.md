# Base models — requirements

Roadmap phase **0.5 Base models**: abstract base with created/updated timestamps and author,
shared by all business models.

Branch: `feature/base-models`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- Phases 0.2 Login and 0.4 Roles are merged. Every write to the API comes from a signed-in user,
  available as `request.user`; the login spec named this phase as one that depends on it.
- No business table exists yet. Milestone 1 (reference data) is next and every one of its tables
  will inherit what this phase builds, then the agent record, then every module.
- `tech-stack.md` already reserves `apps/core/` for "shared base models". Tables, columns and
  domain terms are in French; code structure and comments in English. Business rows are never
  hard-deleted; foreign keys use `on_delete=PROTECT` by default.
- `missions.md`, principle 7: every create, update, validation and deletion is logged with
  author, time, old and new value (`TRA-10`). That full history is phase **0.6 Audit log**. This
  phase only stamps each row with who created it and who last changed it, and when.
- Settings: `USE_TZ = True`, `TIME_ZONE = "Africa/Kinshasa"`, `LANGUAGE_CODE = "fr"`.

## Scope

### In scope

1. **Abstract base model** in `apps/core/models.py` with four fields: creation date,
   modification date, created by, modified by.
2. **API building blocks**: a viewset mixin that fills the author from the signed-in user, and a
   serializer base that makes the four fields read-only.
3. **Django admin building block**: a `ModelAdmin` mixin that fills the author and shows the four
   fields read-only.
4. **Tests** of all three on a test-only concrete model.
5. **Documentation** in `tech-stack.md`: every business model inherits the base, and its
   endpoints and admin use the mixins.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Full history of changes (old and new value, every write) | Phase 0.6 Audit log |
| Recording deletions and validations | Phase 0.6 Audit log, phase 2.11 Validation workflow |
| An "actif" flag or soft-delete manager on the base | Each model retires rows with its own status or end date (`tech-stack.md`) |
| Automatic author outside requests (middleware, thread-local, signals) | Not planned; see D7 |
| Applying the base to `accounts.User` or `ModuleAccess` | Not planned: they are not business models |
| Showing "created by / modified by" on screens | The first screen that needs it |
| Any real business table | Milestone 1 |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-17. The others follow
from [`missions.md`](../missions.md) and [`tech-stack.md`](../tech-stack.md).

### The base model

| # | Decision | Reason |
| --- | --- | --- |
| D1 | The base carries **timestamps and author only**: no active flag, no soft-delete manager. **(asked)** | Matches the roadmap. How a row is retired differs per model (status, end date), so it stays with each model. |
| D2 | The class is `BaseModel` in `apps/core/models.py`, `abstract = True`. | `tech-stack.md`: code structure in English; `core` owns shared base models. |
| D3 | Field names are French: `date_creation`, `date_modification`, `cree_par`, `modifie_par`. Verbose names: "date de création", "date de modification", "créé par", "modifié par". | `tech-stack.md`: columns in French, in the style of `date_engagement` and `date_effet`. |
| D4 | `date_creation` is set once on insert; `date_modification` on every save. Both are timezone-aware, not editable, not null. | Every row says when it appeared and when it last changed. |
| D5 | A save with `update_fields` still updates `date_modification` and `modifie_par`: the base adds them to the list. | Otherwise a partial save would leave a stale modification date. |
| D6 | `cree_par` and `modifie_par` are foreign keys to `settings.AUTH_USER_MODEL`, `on_delete=PROTECT`, nullable, not editable, with `related_name="+"`. | `PROTECT`: a user who wrote data cannot be deleted, only deactivated (principle 8). Nullable: migrations, data imports and management commands write without a user. `"+"`: dozens of models would otherwise each add a reverse accessor to `User`. |
| D7 | The author is filled **explicitly**, by the API and admin mixins, from `request.user`. No middleware, no thread-local, no signal. Scripts set the fields themselves or leave them empty. **(asked)** | No hidden global state; what fills the author is visible in the code that saves. |
| D8 | No default ordering and no extra index on the four fields. | Each model chooses its ordering and indexes when a list screen needs them. |
| D9 | The base adds no migration of its own; each concrete model's migration includes the four columns. | An abstract model has no table. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D10 | `AuthorMixin` (in `apps/core/mixins.py`) for DRF viewsets: on create it saves `cree_par` and `modifie_par` as `request.user`; on update, `modifie_par` only. | One place that every business endpoint reuses. |
| D11 | `BaseModelSerializer` declares the four fields **read-only**. Values a client sends for them are ignored. The authors are returned as user ids. | The client never decides who wrote a row or when. Names can be added when a screen shows them. |
| D12 | The mixins add no permission of their own. Endpoints keep `HasModuleAccess` and the default authenticated session. | Access rules stay where phase 0.4 put them. |

### Django admin

| # | Decision | Reason |
| --- | --- | --- |
| D13 | `BaseModelAdmin` mixin (in `apps/core/admin.py`): `save_model` sets `cree_par` on add and `modifie_par` on every save; the four fields are listed in `readonly_fields`. | Reference tables are first entered in Django admin (`tech-stack.md`); their author must be recorded there too. |

### Tests

| # | Decision | Reason |
| --- | --- | --- |
| D14 | Tests use a **test-only concrete model** declared inside the test module with `isolate_apps`, its table created and dropped with the schema editor. It has no migration and is not in `INSTALLED_APPS`. | No real table exists yet, and a test model must never reach a migration or production. |
| D15 | Validation is **automated tests and the quality gates only**; no manual walkthrough. **(asked)** | Nothing visible changes in this phase. |

### Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D16 | Replaces the `isolate_apps` part of D14: the test model `Probe` is declared at module level in `apps/core/test_base_models.py`, with `managed = False`. Each test class creates its table with the schema editor inside the class transaction, which rolls it back. | An isolated app registry cannot resolve the inherited foreign keys to `accounts.User`. The test module is never imported by `makemigrations`, and a test checks that no `core` migration knows the model. |
| D17 | Both mixins treat an anonymous request as "no author" (`None`) instead of failing. | Endpoints are authenticated by default, but a view that opts out must not crash on save. |
| D18 | `BASE_FIELDS` in `apps/core/models.py` lists the four fields once; the serializer, the admin mixin and the tests read it. | One source of truth for the field list. |

## Open points

None.
