# Contract — plan

Task groups for roadmap phase 2.3, as in phase 2.2: model, permissions and admin, API, demo data
and wrap-up. No frontend group: the screens come with 2.9 and 2.10. Decision numbers (`D1`...)
refer to [`requirements.md`](requirements.md). Each group ends with its tests passing and is
committed on its own. **(asked)**

## 1. Backend: the `Contrat` model

1. Model `Contrat(BaseModel)` in `apps/agents/models.py`, `module = "agents"` (D1, D3, D4, D18):
   `agent` (`ForeignKey(Agent, PROTECT, related_name="contrats")`), `type_contrat`
   (`ForeignKey("referentiels.TypeContrat", PROTECT)`), `date_debut`, `date_fin`,
   `fin_periode_essai` (help texts: "Dernier jour du contrat", "Dernier jour de la période
   d'essai"); `verbose_name` "contrat"; ordering by agent then `date_debut` (D5);
   `default_permissions = NO_DELETE`; `__str__` with the label of D5.
2. Constraints (D2, D12): `date_fin >= date_debut`; `fin_periode_essai >= date_debut` and
   `<= date_fin` when both are set; an `ExclusionConstraint` on `agent` (`=`) and
   `daterange(date_debut, date_fin, '[]')` (`&&`), with a French message.
3. Rules (D4, D6 to D8, D13, D14): `clean()` and `save()` report reversed dates, a closed type, a
   missing or forbidden end date, a forbidden or out-of-contract probation and a changed agent,
   each on its field; `delete()` raises.
4. Helpers (D10, D11): `Agent.date_engagement` (property, earliest `date_debut`, reading a
   prefetched `contrats` when present) and `Agent.contrat_au(jour)`.
5. Migration `0004_contrat`.
6. Tests (`test_contrats.py`): each constraint bypassing the model (reversed dates, probation
   before the start or after the end, overlapping contracts including one starting on the
   other's last day, an open-ended contract overlapping a later one; consecutive contracts and
   a gap accepted; two agents on the same dates accepted); each rule's message on its field (CDD
   without end, CDI with end, probation on a type without it, type closed on the start date, type
   opened later); the overlap message from `full_clean()`; corrections accepted, agent fixed;
   label with and without end; `delete()` raises; `date_engagement` with none, one and several
   contracts; `contrat_au` before, inside, on the last day, in a gap, after; audit of create and
   change under `agents` with the label and author.

## 2. Backend: permissions and Django admin

1. `roles.py` (D16): `CONTRAT_EDIT_PERMISSIONS` (view, add, change on `contrat`), added to
   Gestion de carrière and its chef. Run `migrate` on the development database straight after.
2. `admin.py` (D17): `ContratInline(admin.TabularInline)` on `AgentAdmin`, after the contact
   details, `extra = 1`, `can_delete = False`, ordered by `date_debut`, `type_contrat` with
   `select_related`. `save_formset` already stamps authors.
3. Tests (`test_access.py`): permissions held by the two groups only, regranted, no delete; the
   2.1 and 2.2 admin tests send the new inline's management fields; `demo.carriere` adds a CDD
   and then its renewal through the inline and is their author; a CDD without end, an overlap and
   a probation on a type without it show next to their fields (the overlap at the row's top); no
   delete box; the inline hidden without the permission.

## 3. Backend: API

1. `ContratSerializer` on `BaseModelSerializer` with `type_code` and `type_nom` (D19).
2. `AgentDetailSerializer` adds `date_engagement` and `contrats`; `AgentViewSet.get_queryset`
   adds `prefetch_related` of the contracts with their types for `retrieve`.
3. Tests: detail with several contracts in date order and every field; `date_engagement` from the
   first; an agent without contract (`[]`, `null`); the list unchanged; access and `405`
   unchanged; the detail runs exactly two queries after the permissions warm-up.

## 4. Backend: demo data

1. `create_demo_agents` (D20): call `create_demo_types_contrat`; then, per matricule, the
   contracts from a list (`get_or_create` on agent and start date); one agent left without.
2. Tests: every contract passes `full_clean()`; the shapes of D20 present (a renewed CDD followed
   by a CDI, a current CDD, a probation, an agent without contract); each `date_engagement`
   matches the matricule's year where the list says so; a second run creates nothing and writes
   no audit entry; no author.

## 5. Wrap-up

1. `tech-stack.md` (D21): the `agents/` line and the inclusive end date of contracts.
2. Check the migration applies, reverses and reapplies on a scratch database.
3. Run the manual walkthrough in [`validation.md`](validation.md) on the scratch database.
4. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
5. Record any decision changed on the way under "Found during implementation".
6. Tick **2.3 Contract** in [`roadmap.md`](../roadmap.md).
7. Run `/changelog` on the branch.
