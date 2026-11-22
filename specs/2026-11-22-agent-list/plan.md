# Agent list — plan

Task groups for roadmap phase 2.8: status, search API, load-test data, the screen, the top bar
and the picker, user guide and wrap-up. Decision numbers (`D1`...) refer to
[`requirements.md`](requirements.md). Each group ends with its tests passing and is committed on
its own. **(asked)**

## 1. Backend: computed status

1. `StatutAgent` choices (D1, D2) in `apps/agents/models.py`.
2. `AgentQuerySet.with_statut(jour)` (D3): `EXISTS` subqueries on contracts in force, started
   before, starting after; `Agent.statut_au(jour)` from prefetched contracts.
3. Tests (`test_statut.py`): each status on its boundary days (first and last day of a contract,
   the day after, a gap, a future contract, none); the annotation and the method agree on every
   demo agent over several dates.

## 2. Backend: search API

1. Migration in `apps.core` (or `agents`) installing `UnaccentExtension` (D5).
2. `AgentFilterSerializer` validating `q`, `unite`, `grade`, `fonction`, `statut`, `date`, `tri`,
   `taille` with French messages (D4, D10).
3. `AgentQuerySet.search(...)` (D5 to D7): words of `q` against matricule and `unaccent` names;
   annotations of the unit, function and grade in force on `date`; unit descendants computed once
   from the open units; ordering.
4. `AgentViewSet.list` (D8, D9): pagination class (`taille` up to 100); `aujourdhui` in the
   serializer context becomes the requested date; `statut` and `statut_libelle` on rows; same
   prefetches.
5. Tests (`test_api.py`, `test_recherche.py`): each filter alone and combined; accents and case;
   several words; unit with sub-units and at another date; grade and function at a date; statuses
   alone and several; default all statuses; both sorts; pagination shape, size limit, page out of
   range `404`; bad parameters `400` on their field; fixed number of queries per page; no pay or
   contact field in rows; detail unchanged; access unchanged (`401`, `403`).

## 3. Backend: load-test data

1. `create_load_agents` (D18) in `apps/agents/management/commands/`, reading the demo reference
   data (runs the demo reference commands first), deterministic (seeded).
2. Tests: refuses without `DEBUG`; creates N valid rows (sampled `full_clean()`); audit entries
   written; a second run creates nothing.

## 4. Frontend: the Agents screen

1. `features/agents/api/agents.ts`: `searchAgents(filters)` typed with the page shape;
   `StatutAgent` mirror (D2).
2. `stores/agentList.ts` (Pinia) and URL sync (D14); debounced text.
3. `views/AgentListView.vue` (D12, D13, D15): filters (TreeSelect for units from the
   referentiels API, Select for grade and function, MultiSelect for status, DatePicker), table,
   paginator, states; route `/agents` replaces the placeholder in `router/index.ts`.
4. Tests (Vitest): default status sent; each filter sent; URL ↔ store both ways; reset; rows link
   to the Pièces page; pagination; empty and error states.
5. Check the screen in the light and dark themes and at tablet width.

## 5. Frontend: top bar and picker

1. `AppShell.vue` (D16): Entrée in the search box opens `/agents?q=…`; empty text opens the list.
2. `AgentDocumentsView.vue` (D17): the picker searches through `searchAgents` as the user types;
   `?agent=<id>` loads that agent by `/api/agents/<id>/`.
3. Tests: top-bar search navigates; picker calls the search and still restores `?agent=`.

## 6. User guide

1. `docs/user-guide.md`: an "Agents" section (searching, filters, status meanings, the date,
   pages, opening an agent); section 3 no longer lists Agents as not built; the top-bar search.
2. Screenshots through `docs/capture_screenshots.py` (light theme); rebuild `user-guide.html`.

## 7. Wrap-up

1. `tech-stack.md`: the `agents/` line names the search and computed status; `unaccent` under
   Database.
2. Run the walkthrough, the load test, the leak check and the theme checks in
   [`validation.md`](validation.md) on the scratch database.
3. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
4. Record any decision changed on the way under "Found during implementation".
5. Tick **2.8 Agent list** in [`roadmap.md`](../roadmap.md).
6. Run `/changelog` on the branch.
