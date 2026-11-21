# Bank account — plan

Task groups for roadmap phase 2.5: the model, then permissions and admin, API, demo data and
wrap-up. No frontend group: the screens come with 2.9, 2.10 and the pay screens. Decision numbers
(`D1`...) refer to [`requirements.md`](requirements.md). Each group ends with its tests passing
and is committed on its own. **(asked)**

## 1. Backend: the `CompteBancaire` model

1. Model `CompteBancaire(BaseModel)` in `apps/agents/models.py`, `module = "paie"` (D1, D4):
   `agent` (`ForeignKey(Agent, PROTECT, related_name="comptes_bancaires")`), `banque`
   (`ForeignKey("referentiels.Banque", PROTECT, related_name="+")`), `numero` (help text giving
   the format), `date_effet` (help text "Premier jour où la paie est versée sur ce compte");
   ordering by agent then `date_effet`; `default_permissions = NO_DELETE`; `__str__` with the
   label of D5.
2. Constraints (D3, D7, D8, D12): `UniqueConstraint(agent, date_effet)`; `CheckConstraint` on the
   number's characters and length; `ExclusionConstraint` (banque `=`, numero `=`, agent `<>`)
   with GiST (`btree_gist` is installed). Each with a French message.
3. Normalisation and rules (D7, D9, D13): `numero` stripped and put in capitals before the rules;
   `check_rules()` from `clean()` and `save()` reports a bad format and a number held by another
   agent on `numero`, a bank not open on `date_effet` on `banque` (reuse `check_open`), a changed
   agent on `agent`; `delete()` raises.
4. Helper (D11): `Agent.compte_bancaire_au(jour)`, through the `_au` helper of 2.4.
5. Migration `0007_comptebancaire`.
6. Tests (`test_comptes_bancaires.py`): each constraint bypassing the model (duplicate date;
   bad format; same bank and number for another agent; same agent coming back to an old account
   accepted; same number at another bank accepted); their messages from `full_clean()`; number
   normalised; bank closed or not yet open reported; dates before hiring accepted; corrections
   accepted, agent fixed; label; `delete()` raises; `compte_bancaire_au` with and without
   prefetch; audit of create and change under `paie` with label and author.

## 2. Backend: permissions and Django admin

1. `roles.py` (D16): `COMPTE_BANCAIRE_EDIT_PERMISSIONS` (view, add, change) and
   `agents.view_agent`, added to Rémunération and its chef. Run `migrate` on the development
   database straight after.
2. `admin.py` (D17): `CompteBancaireAdmin` — list columns matricule, name, bank, number, date;
   search on matricule, name and number; filter on bank; `autocomplete_fields = ["agent"]`;
   `agent` read-only on change; foreign keys with `select_related`; no delete.
3. Tests (`test_access.py`): permissions held by the two groups only, regranted after `migrate`,
   no delete; `demo.remuneration` adds and corrects an account through the page and is its
   author; format, closed bank, duplicate date and number held by another agent show next to
   their fields; the agent cannot be changed; Gestion de carrière and the Auditeur cannot open
   the page; Rémunération sees the agent list read-only and cannot change an agent.

## 3. Backend: API

1. `CompteBancaireSerializer` on `BaseModelSerializer` with the fields of D18.
2. A `comptes-bancaires` action (or nested view) on the agents viewset, read-only, requiring
   `access_agents` and `access_paie`; returns `{"comptes": [...], "compte_actuel": ... }`, "today"
   read once per request.
3. Tests: several rows in date order with every field; `[]` and `null` without rows; current row
   with a frozen today (a row dated today is current, a future one is not); `404` for an unknown
   agent; anonymous `401`; Gestion de carrière, Auditeur, no group and Administrateur système
   `403`; Rémunération, its chef and Direction RH `200`; writes `405`; fixed query count; the
   agent list and detail contain no account field.

## 4. Backend: demo data

1. `create_demo_agents` (D19): call `create_demo_banques`; then, per matricule, the accounts from
   one list (`get_or_create` on agent and `date_effet`); the agent without contract left
   without.
2. Tests: every row passes `full_clean()`; each agent with a contract has an account on their
   hiring date; a change of bank and a future-dated change present; no number shared by two
   agents; a second run creates nothing and writes no audit entry; no author.

## 5. Wrap-up

1. `tech-stack.md` (D20): the `agents/` line names the bank accounts, read by the pay profiles.
2. Run the manual walkthrough, the security checks and the leak checks in
   [`validation.md`](validation.md) on the scratch database.
3. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
4. Record any decision changed on the way under "Found during implementation".
5. Tick **2.5 Bank account** in [`roadmap.md`](../roadmap.md).
6. Run `/changelog` on the branch.
