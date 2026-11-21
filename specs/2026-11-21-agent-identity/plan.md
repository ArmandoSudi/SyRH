# Agent identity — plan

Task groups for roadmap phase 2.1: app and model, permissions and admin, API, demo data and
wrap-up. No frontend group: the screens come with 2.8 to 2.10. Decision numbers (`D1`...) refer
to [`requirements.md`](requirements.md). Each group ends with its tests passing and is committed
on its own. **(asked)**

## 1. Backend: the `agents` app and the `Agent` model

1. Create `apps/agents/` (D1): `apps.py`, `models.py`, `admin.py`, `serializers.py`,
   `views.py`, `urls.py`, `tests/`, `management/commands/`; add it to `INSTALLED_APPS`.
2. Model `Agent(BaseModel)`, `module = "agents"` (D2 to D6): `matricule` (`CharField(20)`),
   `nom`, `postnom`, `prenom`, `sexe` (`TextChoices` `Sexe`), `date_naissance`,
   `lieu_naissance`, `nationalite` (default "Congolaise"); `verbose_name` "agent";
   `default_permissions = NO_DELETE` (from `apps.referentiels.models`, or moved to `apps.core`
   if importing it across apps reads wrong); ordering of D6; `__str__` with the label of D6.
3. Constraints (D8, D11): `UniqueConstraint(Upper("matricule"))`; `CheckConstraint`s on the
   matricule's characters and length (regex `^[A-Z0-9/.-]{1,20}$`), `nom` not blank, `sexe` in
   the choices, `date_naissance >= 1900-01-01`.
4. Rules (D7, D9, D10, D12): normalise the matricule (trim, upper case) and the names (trim) in
   `clean()` and `save()`; report characters, a taken matricule (any case), a changed matricule
   and a future date of birth on their fields, in French; `delete()` raises with a French
   message.
5. Migration `0001_initial`, then `0002_triggers` with `RunSQL` (reversible): a trigger
   refusing `DELETE` on `agents_agent`, and one refusing an `UPDATE` whose matricule differs.
6. Tests (`tests/test_agent.py`): each constraint bypassing the model (duplicate in another case,
   bad characters, 21 characters, blank `nom`, unknown `sexe`, birth in 1899); each trigger in
   raw SQL (`DELETE`, `UPDATE` of the matricule refused; `UPDATE` of a name accepted); the
   messages on their fields; normalisation (`" arptc/12/2010 "` stored `ARPTC/12/2010`); future
   birth refused; `postnom` and `prenom` optional; default nationality; order and label;
   `delete()` raises; audit of create and change under `agents`, with the label and author.

## 2. Backend: permissions and Django admin

1. `roles.py` (D14, D15): `AGENT_EDIT_PERMISSIONS` (view, add, change on `agent`), added to
   Gestion de carrière and its chef in `EXTRA_PERMISSIONS`. Run `migrate` on the development
   database straight after.
2. `admin.py` (D16): `AgentAdmin` on `BaseModelAdmin`; list columns, search, filter on sexe;
   matricule read-only on change (`get_readonly_fields`); delete action removed.
3. Tests (`tests/test_access.py`): the two groups hold the three permissions, nobody else adds
   or changes, nobody deletes, the Administrateur système has none; the group setup regrants
   and keeps hand-made ones; `demo.carriere` adds an agent and is its author; a duplicate
   matricule in another case shows next to "Matricule"; the matricule is read-only on change;
   Rémunération and the administrator get `403` on the admin pages.

## 3. Backend: read-only API

1. `AgentSerializer` on `BaseModelSerializer`, with `sexe_libelle` (D19).
2. `AgentViewSet` (`ReadOnlyModelViewSet`), `HasModuleAccess("agents")`, no pagination; routed
   under `/api/agents/` from `config/urls.py` (D18).
3. Tests: list in the order of D6 with the fields of D19; detail; unknown id `404`; `401`
   anonymous; `403` without a group and for the Administrateur système; `200` for every profile
   opening `agents`; `POST`, `PUT`, `PATCH`, `DELETE` answer `405`.

## 4. Backend: demo data

1. `create_demo_agents` (D20): refuses without `DEBUG`; `get_or_create` on the matricule; prints
   what it created.
2. Tests: refused without `DEBUG`; every row passes `full_clean()`; both sexes present, some
   agents without postnom; a second run creates nothing and writes no audit entry; no author.

## 5. Wrap-up

1. `tech-stack.md` (D21): `agents/` in the repository layout.
2. Check both migrations apply, reverse and reapply on a scratch database.
3. Run the manual walkthrough in [`validation.md`](validation.md).
4. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
5. Record any decision changed on the way under "Found during implementation".
6. Tick **2.1 Agent identity** in [`roadmap.md`](../roadmap.md).
7. Run `/changelog` on the branch.
