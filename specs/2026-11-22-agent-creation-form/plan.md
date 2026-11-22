# Agent creation form — plan

Task groups for roadmap phase 2.9: the hiring endpoint, matricule suggestion and duplicates, the
form, the list button, user guide and wrap-up. Decision numbers (`D1`...) refer to
[`requirements.md`](requirements.md). Each group ends with its tests passing and is committed on
its own. **(asked)**

## 1. Backend: the hiring endpoint

1. `apps/agents/engagement.py` (D1 to D4): `EngagementSerializer` with nested sections
   (`coordonnees` optional, `contrat`, `affectation`, `classement`); `engager(data, auteur)` saving
   in order inside `transaction.atomic()`, catching each section's `ValidationError`, going on
   with the next where it can, and raising all errors nested by section at the end (rolling back).
2. `AgentViewSet.create` (D5, D9, D10): permission class checking the add permissions (with
   `add_coordonnees` only when sent); response = detail serializer, `201`. `update`,
   `partial_update`, `destroy` still `405`.
3. Tests (`test_engagement.py`): a full hiring creates five rows dated on the start, each audited
   with its author; without contact details, four rows; every refusal on its nested field (taken
   matricule, bad format, CDD without end, probation for a type without, closed unit, closed
   échelon, missing sections); several errors at once in different sections; a refusal in the
   last section leaves no row and no audit entry; access (`401`, `403` for Rémunération,
   Auditeur, Formation; `201` for Gestion de carrière and its chef); detail writes `405`.

## 2. Backend: matricule suggestion and duplicates

1. `matricule-suivant` and `doublons` actions on `AgentViewSet` (D6, D7, D9).
2. Tests: suggestion with no matching matricule (`ARPTC/0001/YYYY`), after the demo ones, ignoring
   other shapes (`CHARGE/…`), with a year; duplicates by nom and birth date ignoring accents, with
   and without prénom, limit 10; both `403` without `add_agent`; bad parameters `400`.

## 3. Frontend: the hiring form

1. `features/agents/api/engagement.ts`: `engager`, `matriculeSuivant`, `doublons`, typed with
   nested errors (an `ApiError` whose `fieldErrors` hold section objects: flatten helper).
2. `views/AgentCreateView.vue` and step components under `components/engagement/` (D11 to D15):
   PrimeVue `Stepper`; reference lists open on the start date (types de contrat, units as a tree,
   fonctions, grades then échelons); matricule suggestion; required pieces from
   `fetchPiecesRequises` for Engagement; duplicates on the summary with the confirmation box.
3. Route `/agents/nouveau` with `meta.permission: 'agents.add_agent'`; leave guard when the form
   is dirty (D16); after saving, toast and redirect to `/agents/pieces?agent=<id>` (D17).
4. Tests (Vitest): step checks; type-dependent fields; lists reload on date change and drop a
   closed choice; suggestion filled and not overwriting typed text; server errors land on their
   step and field; duplicates require the box; success redirects; leave guard.
5. Check the form in the light and dark themes and at tablet width.

## 4. Frontend: entry point

1. "Nouvel agent" button on `AgentListView.vue` with `agents.add_agent` (D16).
2. Tests: shown for the editor, hidden otherwise; opens `/agents/nouveau`.

## 5. User guide

1. `docs/user-guide.md`: "Engager un agent" under Agents — the steps, the suggested matricule,
   errors, duplicates, then attaching the hiring pieces; who can do it.
2. Screenshots through `docs/capture_screenshots.py` (light theme), against the scratch servers
   since they create an agent; rebuild `user-guide.html`.

## 6. Wrap-up

1. `tech-stack.md`: the `agents/` line names the hiring endpoint.
2. Run the walkthrough and checks in [`validation.md`](validation.md) on the scratch database.
3. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
4. Record any decision changed on the way under "Found during implementation".
5. Tick **2.9 Agent creation form** in [`roadmap.md`](../roadmap.md).
6. Run `/changelog` on the branch.
