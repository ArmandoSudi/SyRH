# Base models — validation

How to know phase 0.5 is done and `feature/base-models` can be merged. All parts must pass:
quality gates, automated tests for every acceptance criterion and the security checks. There is
no manual walkthrough: nothing visible changes in this phase (D15).

Decision numbers refer to [`requirements.md`](requirements.md).

## 1. Quality gates

All six, from [`tech-stack.md`](../tech-stack.md), green on the branch tip:

| Check | Command |
| --- | --- |
| Backend tests | `cd backend && uv run python manage.py test` |
| Backend lint and format | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| No missing migration | `cd backend && uv run python manage.py makemigrations --check` |
| Frontend tests | `cd frontend && npx vitest run` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend type-check and build | `cd frontend && npm run build` |

This phase adds **no migration** (D9). `git diff main --stat` shows no file under
`backend/apps/*/migrations/` and nothing under `frontend/`.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL on the
test-only model (D14).

### Model

| # | Criterion | Decision |
| --- | --- | --- |
| M1 | `BaseModel` is abstract and gives `date_creation`, `date_modification`, `cree_par`, `modifie_par`, with French verbose names. | D2, D3 |
| M2 | Creating a row sets both dates, timezone-aware. | D4 |
| M3 | Saving again moves `date_modification` forward; `date_creation` does not change. | D4 |
| M4 | `save(update_fields=[...])` still updates `date_modification` and `modifie_par`. | D5 |
| M5 | A row can be saved with no author. | D6 |
| M6 | Deleting a user referenced as `cree_par` or `modifie_par` raises `ProtectedError`. | D6 |
| M7 | `User` gains no reverse accessor from the base. | D6 |
| M8 | The test-only model has no migration and is absent from the app registry outside its tests. | D14 |

### API

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | A create through a viewset with `AuthorMixin` sets `cree_par` and `modifie_par` to the signed-in user. | D10 |
| A2 | An update by another user changes `modifie_par` and `date_modification` only; `cree_par` and `date_creation` stay. | D10 |
| A3 | Values a client sends for the four fields are ignored, on create and on update. | D11 |
| A4 | The response includes the four fields; the authors are user ids. | D11 |
| A5 | An anonymous write still gets `401`; the mixins grant no access. | D12 |

### Admin

| # | Criterion | Decision |
| --- | --- | --- |
| G1 | Adding a row through `BaseModelAdmin.save_model` sets both authors to the admin user. | D13 |
| G2 | Changing a row sets `modifie_par` only. | D13 |
| G3 | The four fields are read-only, together with any read-only fields the subclass declares. | D13 |

## 3. Security checks

- No API path lets a client choose `cree_par`, `modifie_par` or either date (A3).
- The author always comes from `request.user`; nothing reads a user id from the request body,
  headers or query string.
- No middleware, thread-local or signal was added to fill the author (D7):
  `git diff main -- backend/config/settings.py` shows no `MIDDLEWARE` change.
- Users referenced as authors cannot be hard-deleted (M6), consistent with principle 8.

## 4. Definition of done

- [ ] Parts 1 to 3 pass.
- [ ] Nothing listed as out of scope in `requirements.md` slipped in: no active flag, no audit
      history, no real business table, no frontend change.
- [ ] Any decision changed during implementation is recorded in `requirements.md` under
      "Found during implementation".
- [ ] `tech-stack.md` says every business model inherits `BaseModel` and how the author is
      filled.
- [ ] **0.5 Base models** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
