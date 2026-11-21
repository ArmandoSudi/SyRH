# Position history — plan

Task groups for roadmap phase 2.4: one group per table, then permissions and admin, API, demo
data and wrap-up. No frontend group: the screens come with 2.8 to 2.10. Decision numbers (`D1`...)
refer to [`requirements.md`](requirements.md). Each group ends with its tests passing and is
committed on its own. **(asked)**

## 1. Backend: the `Affectation` model

1. Model `Affectation(BaseModel)` in `apps/agents/models.py`, `module = "agents"` (D1, D5, D6,
   D21): `agent` (`ForeignKey(Agent, PROTECT, related_name="affectations")`), `unite`
   (`ForeignKey("referentiels.UniteOrganisationnelle", PROTECT, related_name="+")`), `fonction`
   (`ForeignKey("referentiels.Fonction", PROTECT, related_name="+")`), `date_effet` (help text
   "Premier jour où l'affectation s'applique"); ordering by agent then `date_effet` (D7);
   `default_permissions = NO_DELETE`; `__str__` with the label of D7.
2. Constraint (D3, D13): `UniqueConstraint(agent, date_effet)` with a French message.
3. Rules (D6, D9, D10, D14): `check_rules()` from `clean()` and `save()` reports a unit or
   function not open on `date_effet`, a date outside every contract, a changed agent, each on its
   field; `delete()` raises. Share the "open on a day" and "inside a contract" checks with the
   classification (one helper each).
4. Helper (D12): `Agent.affectation_au(jour)`, prefetch-aware like `contrat_au`.
5. Migration `0005_affectation`.
6. Tests (`test_affectations.py`): the unique constraint bypassing the model; its message from
   `full_clean()`; two agents on the same date accepted; unit and function closed or not yet
   open reported on their field; date before the first contract, in a gap and after the last
   reported on `date_effet`; on a contract's first and last day accepted; corrections accepted,
   agent fixed; label; `delete()` raises; `affectation_au` before the first row, on a row's date,
   between rows, after the last, with and without prefetch; audit of create and change under
   `agents` with label and author.

## 2. Backend: the `Classement` model

1. Model `Classement(BaseModel)` (D1, D4, D6, D21): `agent` (`related_name="classements"`),
   `echelon` (`ForeignKey("referentiels.Echelon", PROTECT, related_name="+")`), `date_effet`;
   same ordering, permissions and label pattern (D7).
2. Constraint: `UniqueConstraint(agent, date_effet)`.
3. Rules (D9, D10, D14): échelon not open on `date_effet`, date outside every contract, changed
   agent; `delete()` raises.
4. Helper (D12): `Agent.classement_au(jour)`.
5. Migration `0006_classement`.
6. Tests (`test_classements.py`): same set as group 1, with the échelon; the grade and catégorie
   read through the échelon.

## 3. Backend: permissions and Django admin

1. `roles.py` (D17): `AFFECTATION_EDIT_PERMISSIONS` and `CLASSEMENT_EDIT_PERMISSIONS` (view, add,
   change), added to Gestion de carrière and its chef. Run `migrate` on the development database
   straight after.
2. `admin.py` (D18): `AffectationInline` and `ClassementInline` (`TabularInline`) on `AgentAdmin`,
   after the contracts, `extra = 1`, `can_delete = False`, ordered by `date_effet`, foreign keys
   with `select_related`.
3. Tests (`test_access.py`): permissions held by the two groups only, regranted after `migrate`,
   no delete; the existing admin tests send the new inlines' management fields (extend the
   `inline()` helper of 2.3); `demo.carriere` adds an assignment and a classification through the
   inlines and is their author; a closed unit, a date outside contracts and a duplicate date show
   next to their fields; no delete box; inlines hidden without the permission.

## 4. Backend: API

1. `AffectationSerializer` and `ClassementSerializer` on `BaseModelSerializer` with the fields of
   D19; slim variants without base fields for the list (D20).
2. `AgentDetailSerializer` adds `affectations` and `classements`; `get_queryset` prefetches them
   with their references for `retrieve`.
3. `AgentSerializer` (list) adds `affectation_actuelle` and `classement_actuel`, the rows in force
   today (D20); the list prefetches rows dated on or before today and picks the last per agent,
   in a fixed number of queries.
4. Tests: detail with several rows of each in date order and every field; empty lists without
   rows; list current rows with a frozen today — a past row, a row dated today, a future row
   ignored, `null` without rows; query counts fixed for the detail and for a list of 1 and of 10
   agents; access and `405` unchanged.

## 5. Backend: demo data

1. `create_demo_agents` (D22): call the demo organisation, functions and classification commands;
   then, per matricule, the assignments and classifications from two lists (`get_or_create` on
   agent and `date_effet`); the agent without contract left without.
2. Tests: every row passes `full_clean()`; the shapes of D22 present (a transfer, a function
   change, a promotion, a future-dated promotion, an agent without); each agent with a contract
   has an assignment and a classification on their hiring date; a second run creates nothing and
   writes no audit entry; no author.

## 6. Wrap-up

1. `tech-stack.md` (D23): the `agents/` line names both histories and their start-only dating.
2. Run the manual walkthrough and the security checks in [`validation.md`](validation.md) on the
   scratch database.
3. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
4. Record any decision changed on the way under "Found during implementation".
5. Tick **2.4 Position history** in [`roadmap.md`](../roadmap.md).
6. Run `/changelog` on the branch.
