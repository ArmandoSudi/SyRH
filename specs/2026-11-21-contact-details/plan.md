# Contact details — plan

Task groups for roadmap phase 2.2, as in phase 2.1: model, permissions and admin, API, demo data
and wrap-up. No frontend group: the screens come with 2.9 and 2.10. Decision numbers (`D1`...)
refer to [`requirements.md`](requirements.md). Each group ends with its tests passing and is
committed on its own. **(asked)**

## 1. Backend: the `Coordonnees` model

1. Model `Coordonnees(BaseModel)` in `apps/agents/models.py`, `module = "agents"` (D1, D2,
   D17): `agent` (`OneToOneField(Agent, on_delete=PROTECT, related_name="coordonnees")`),
   `adresse`, `commune`, `ville`, `telephone`, `telephone_secondaire`, `courriel`
   (`EmailField`), `urgence_nom`, `urgence_lien`, `urgence_telephone`; `verbose_name`
   "coordonnées" (singular and plural); `default_permissions = NO_DELETE`; `__str__` with the
   label of D6.
2. Constraints (D11): `adresse`, `ville`, `telephone` not blank; `telephone` matching the phone
   pattern; `telephone_secondaire` and `urgence_telephone` blank or matching it; emergency name
   and phone both blank or both given.
3. Rules (D4, D5, D7, D8, D10, D12, D13): normalise in `clean()` and `save()` (trim the text,
   collapse spaces in phones, lower-case the email); report a bad phone on its field, a missing
   emergency name or phone on the empty one, a changed agent on `agent`, in French; `delete()`
   raises.
4. Migration `0003_coordonnees`.
5. Tests (`test_coordonnees.py`): each constraint bypassing the model (second row for one agent,
   blank address, town or phone, phones with letters, too short, too long, a double `+`;
   emergency name without phone and phone without name; valid rows with and without the optional
   fields); normalisation (`" +243  81 234 5678 "` stored `+243 81 234 5678`,
   `" Agent@Example.CD "` stored `agent@example.cd`); the messages on their fields; a bad email on
   `courriel`; the agent fixed after creation; label; `delete()` raises; audit of create and
   change under `agents`, with the label and author.

## 2. Backend: permissions and Django admin

1. `roles.py` (D15): `COORDONNEES_EDIT_PERMISSIONS` (view, add, change on `coordonnees`), added to
   Gestion de carrière and its chef with `AGENT_EDIT_PERMISSIONS`. Run `migrate` on the
   development database straight after.
2. `admin.py` (D16): `CoordonneesInline(admin.StackedInline)` on `AgentAdmin`, `max_num = 1`,
   `can_delete = False`, three fieldsets; `AgentAdmin.save_formset` stamps `cree_par` on new
   rows and `modifie_par` on every saved row.
3. Tests (`test_access.py`): the two groups hold the three permissions, nobody else adds or
   changes, nobody deletes; the group setup regrants and keeps hand-made ones; `demo.carriere`
   adds contact details to an existing agent through the inline and is their author in the audit
   log; a bad phone and a lone emergency name show next to their fields; a second inline row is
   not offered; no delete box.

## 3. Backend: API

1. `CoordonneesSerializer` on `BaseModelSerializer` (fields of D2 and the base fields, without
   `agent`).
2. `AgentDetailSerializer` adds `coordonnees` (nested, `null` when missing); `AgentViewSet` uses
   it for `retrieve` only and `select_related("coordonnees")` (D18).
3. Tests: detail with contact details (every field), detail without (`null`); the list has no
   `coordonnees` key; access and `405` unchanged; the detail runs a fixed number of queries.

## 4. Backend: demo data

1. `create_demo_agents` (D19): after each agent, `get_or_create` its contact details from a list
   keyed on the matricule; one agent left without.
2. Tests: every row passes `full_clean()`; eleven agents with contact details, one without; some
   without email, second phone or emergency contact; a second run creates nothing and writes no
   audit entry; no author.

## 5. Wrap-up

1. Add `Q35` to `docs/questions-ouvertes.md` (D20).
2. `tech-stack.md`: the `agents/` line names the contact details (D20).
3. Check the migration applies, reverses and reapplies on a scratch database.
4. Run the manual walkthrough in [`validation.md`](validation.md) on the scratch database
   (`backend-scratch`), as for phase 2.1.
5. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
6. Record any decision changed on the way under "Found during implementation".
7. Tick **2.2 Contact details** in [`roadmap.md`](../roadmap.md).
8. Run `/changelog` on the branch.
