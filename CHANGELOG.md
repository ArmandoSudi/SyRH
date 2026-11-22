# Changelog

All notable changes to SyRH, newest first. Each section is written from the git history before
the work is merged.

## 2026-11-22

- Bank account (roadmap 2.5): Rémunération and its chef add and correct accounts on a "Comptes
  bancaires" admin page and now view agents read-only, to pick one. Never deleted.
- `/api/agents/<id>/comptes-bancaires/` returns an agent's accounts and the one in force today,
  for Rémunération, its chef and Direction RH only; the agent list and detail carry no account.
  Run `migrate`; `create_demo_agents` now also loads the demo banks and gives agents accounts.
- Document storage (roadmap 2.6): agents' scanned documents (PDF, JPEG, PNG) are stored
  encrypted with Fernet and served only through authenticated endpoints, never by URL.
- New "Pièces des agents" page: pick an agent, then open, download, add (with progress) and
  retire their documents. Gestion de carrière and Administration du personnel add and retire.
- Uploads are checked on their content, against the new size parameter (10 Mo in the demo) and
  for duplicates; a wrong upload is retired with a reason, never deleted.
- Document types can be confidential, read only by chosen profiles (demo: medical certificate
  for Social, identity document for the career and staff services); others never see them.
- **Action needed:** set `SYRH_DOCUMENT_KEYS` in `backend/.env` (see `.env.example`); SyRH
  refuses to start without it. Keep the key safe: losing it loses every document. Run `migrate`;
  the test server also needs the new nginx limit and document directory (`docs/deployment.md`).
- User guide section with screenshots; open questions Q37 (confidential types) and Q38 (virus
  scanning).
- Documents on events (roadmap 2.7): an agent's documents can be attached to their events;
  one document can justify several events, a wrong link is removed but kept in the history.
- Contracts, assignments and classifications are events, their kind worked out from the history:
  Engagement, the new Renouvellement de contrat, Mutation, Promotion and the new Avancement
  d'échelon. Each lists the pieces required on its own date and says Complet or what is missing.
- "Pièces des agents" gains an "Événements et pièces exigées" section to attach an existing or a
  new document, and remove links. Confidential pieces count for all but only their readers see
  them. Run `migrate`; open question Q39 (renewal and échelon pieces).
- Agent list (roadmap 2.8): the Agents menu now opens a searchable list — matricule or name
  (case and accents ignored), service with its sub-units, grade, function, status — at a chosen
  date, 25 agents a page, filters kept in the address. A row opens the agent's documents.
- An agent's status is computed from the contracts: En activité, À venir, Sans contrat en cours,
  Sans contrat. The top-bar search opens the list; the Pièces picker searches as you type.
- `/api/agents/` is now paginated and filterable (breaking for any other caller). Run `migrate`
  (installs PostgreSQL `unaccent`); `create_load_agents` generates thousands of test agents.
- Agent creation form (roadmap 2.9): Gestion de carrière hires an agent from "Nouvel agent" on
  the list — identity, optional contact details, first contract, assignment and classification —
  saved all at once or not at all, every refusal shown under its field.
- The form proposes the next matricule (ARPTC/<n>/<year>, editable), warns about an agent with
  the same name and birth date, then opens the new agent's Pièces page on the hiring pieces.
- `POST /api/agents/` now hires (agents themselves stay read-only); nested API errors reach the
  screen as `section.field`.
<!-- commits: b53a19c ecef031 b3296b9 26b0823 dbca804 df86d0e 1b09f83 7a5db67 00b4be2 0775e62 d576192 5a743a3 89905ff 8258e2d e7dd806 09f803c 0427e87 d320dfc d773237 1cad5b4 c28c869 267db12 b8f15f7 3b4f811 bfdf633 863f44c 507c39b 1b45e8c 215b51e ce3bb36 61da7ca 5fa455e 2416ec5 7358de5 fa7cd57 200c792 62b118e 5a3d3bb 16ce196 3f2c6b2 8bcc1ce f46aa14 -->

## 2026-11-21

- Agent identity (roadmap 2.1), opening Milestone 2: a new `agents` app with the agent record's
  identity (matricule, nom, postnom, prénom, sexe, date and place of birth, nationality). The
  matricule is typed by HR, stored in capitals, unique without regard to case and fixed once
  saved; an agent is never deleted, so a matricule is never reused. PostgreSQL triggers refuse a
  matricule change or a delete even in raw SQL.
- Gestion de carrière and its chef add and change agents in Django admin; every profile opening
  Agents reads them from the read-only `/api/agents/`. No screen yet (phases 2.8 to 2.10). Run
  `migrate`; `create_demo_agents` loads twelve fictional agents. The matricule format is still
  open question `Q5`.
- Contact details (roadmap 2.2): each agent can have one contact record with address, commune,
  town, phones, email and one emergency contact, corrected in place (the audit log keeps the old
  values). The database checks the phone format and that the emergency name and phone go
  together. Edited in a "Coordonnées" block on the agent's admin page by the same editors;
  returned in `/api/agents/<id>/`, `null` when missing. Run `migrate`; `create_demo_agents` now
  fills in contact details. Who else edits or reads them is open question `Q35`.
- Contract (roadmap 2.3): an agent's successive contracts (a CDD, its renewals, then a CDI),
  never overlapping. The end and probation dates are last days as printed on the contract; the
  contract type decides whether an end date is required and whether probation is allowed, and
  must be open on the start date. The hiring date is the start of the first contract. Edited in
  a "Contrats" table on the agent's admin page; returned with the hiring date in
  `/api/agents/<id>/`. Run `migrate`; `create_demo_agents` now loads the demo contract types and
  sixteen contracts. Probation length and renewal limits wait for `Q30`.
- Position history (roadmap 2.4): each agent's dated assignments (organisation unit and
  function) and classifications (échelon, its grade read through it), only the effective date
  stored, so rows never overlap. One row per agent and date; the unit, function or échelon must
  be open on that date and the date inside one of the agent's contracts. Never deleted.
- Gestion de carrière and its chef edit both in two inlines on the agent's admin page (save a
  contract before the rows that rest on it). `/api/agents/<id>/` returns both histories; the list
  and detail return the assignment and classification in force today. Run `migrate`;
  `create_demo_agents` now also loads the demo reference data and gives the agents careers.
- Bank account (roadmap 2.5) started: each agent's dated bank accounts (bank, number, effective
  date), audited under `paie`. PostgreSQL checks the number format and refuses one bank and number
  for two agents. The real per-bank format is new open question `Q36`.
<!-- commits: ccffe18 c234b08 31b2cf6 b57fa90 cf18f24 4b84057 7a61c30 2d6dc5f 328b67e 387cebe 3ae19b1 c956db9 381cf24 27a1d98 040c2b0 afba65b 548a102 1f87983 2116a08 bedd292 abc10ae a5c9d81 6fac6fc fb84c37 ee28680 1382425 79a9603 343c10c c8eda85 d4c23f5 203d1b3 1dea3a4 1e5740c -->

## 2026-11-20

- General parameters (roadmap 1.8): the child age limit, the maximum number of children covered,
  the retirement age and the career length, as dated values of a fixed list of keys, each with a
  unit and bounds checked by the database; later phases read them with `Parametre.valeur_au()`.
  Same editors as the other reference data in Django admin; a new read-only "Paramètres" tab,
  described in the user guide. Run `migrate`; `create_demo_parametres` loads 25, 65 and 30 and a
  fictional maximum of children. The real values are open question `Q34`.
- Reference data screens (roadmap 1.9): editors now add, correct, replace from a date and close
  rows in SyRH itself, on the Fonctions, Types de contrat, Sorties et suspensions, Banques and
  Paramètres tabs; other users see no edit action. The write API reuses the model rules (same
  French messages as Django admin) and the existing permissions; nothing is deleted. The other
  reference tables follow in a new phase 1.10. For walkthroughs that save rows,
  `.claude/launch.json` has scratch servers on ports 8001 and 5174.
- Tree reference data screens (roadmap 1.10), closing Milestone 1: sites, the organisation, the
  classification, document types and required documents are now edited in SyRH too, with "add
  under this row" actions in the trees and a new "Types de pièce" table. Replacing a direction,
  catégorie, grade or document type at a date carries everything open under it over to the new
  row in one step, after a preview of the rows that follow; closing a parent with open children
  stays refused. Django admin remains as a fallback.
- Test server on the local network: gunicorn behind nginx on port 8080, over plain HTTP
  (`DJANGO_SECURE_COOKIES` keeps cookies usable without HTTPS). `deploy/update.sh` pulls a
  branch, migrates, builds and restarts; Django's deploy check is reported but does not block.
  `docs/deployment.md` records the one-time setup.
- `docs/build_test_guide.py` builds a PDF for stakeholders: the test server's address, the demo
  accounts and a checklist of every feature so far. It contains the demo password, so the PDF is
  git-ignored.
<!-- commits: 11ea6fa c754996 fd0bef7 e440d45 c5d0c4d ce6e21c d5f68c9 9a86341 2bbab6b 43b8abd 71d0617 4852398 33c6f03 021cc46 f44e3f1 b5aa5f2 ba76474 6297472 8b3adb6 60a849e 67c4b73 beb125e 37ce718 5ca4d4f ce37bf9 c65d5ad b4faa51 5277edb -->

## 2026-11-19

- Fonctions (roadmap 1.3): job functions as dated reference data, each with a code, a name and
  a nature (Responsabilité or Exécution); a rename closes the old fonction and opens a successor.
  Edited in Django admin by the same profiles as the organisation and the classification; a new
  read-only "Fonctions" tab on Référentiels lists them at any date. Run `migrate`;
  `create_demo_fonctions` loads a demo list. The real list is open question `Q29`.
- A closing date before the opening date no longer crashes Django admin on units, catégories,
  grades and échelons: the form shows the message next to "Date de fermeture".
- Contract types (roadmap 1.4): CDI, CDD, stage, journalier as dated reference data, each with
  two rules for the contract phase, "Durée déterminée" (end date required) and "Période
  d'essai" (probation allowed). Same editors in Django admin; a new read-only "Types de contrat"
  tab. Run `migrate`; `create_demo_types_contrat` loads demo types. The real list is open
  question `Q30`.
- Document types (roadmap 1.5): the kinds of supporting document, and for each of fourteen event
  kinds (hiring, promotion, marriage, birth, ...) the documents it requires, mandatory or
  optional, dated like the other reference data. Same editors in Django admin; a new read-only
  "Pièces justificatives" tab lists each event with its documents. Run `migrate`;
  `create_demo_pieces` loads demo data. The real list is open question `Q31`.
- The user guide covers the Fonctions, Types de contrat and Pièces justificatives tabs; its
  screenshots were retaken.
- Exit and suspension reasons (roadmap 1.6): exit reasons (each with its required document and
  "Retraite" or "Décès" flags) and suspension positions (required document, "compte dans
  l'ancienneté", maximum length and renewals), dated like the other reference data. Same editors
  in Django admin; a new read-only "Sorties et suspensions" tab, described in the user guide. Run
  `migrate`; `create_demo_sorties` loads demo data. The real lists are open question `Q32`.
- Banks (roadmap 1.7): dated list of banks with a code, a name and an optional SWIFT/BIC checked
  for shape; edited in Django admin by Rémunération, its Chef de service and the administrator
  (not Gestion de carrière); a new read-only "Banques" tab, described in the user guide. Run
  `migrate`, then re-run `create_demo_users` so the Rémunération accounts get staff status;
  `create_demo_banques` loads fictional banks. The real list is open question `Q33`.
<!-- commits: f3da417 f0aacb2 785feed 870644e c2c5bfb 26d8ba0 573c301 e5031ce 3554bcb 8d0d343 cfe667d ad9b38e 5576e63 8fbb1d5 9d1b91f cd8291e ce97a1b 78890f5 08f3067 6648383 5066896 c20767f 0a25d29 acb197e b9e14c4 fe1373e be30eff ac34cf4 5d9d613 516590d 4dbe7c9 fb9a9e6 bc5ef56 cd721d9 4741666 5cfaf32 5d2af74 -->

## 2026-11-18

- Organisation (roadmap 1.1): sites and a dated tree of directions, départements, services and
  bureaux. A restructuring closes units and opens new ones, so the tree can be read at any date.
  Administrateur système and Gestion de carrière edit it in Django admin (their accounts need
  "Statut équipe"); everyone with Référentiels sees it on the new read-only Référentiels screen.
  Run `migrate` (installs the `btree_gist` extension); `create_demo_organisation` loads demo
  data in development. The real organigramme is open question `Q27`.
- Classification (roadmap 1.2): catégories, grades and échelons as dated, ranked reference data,
  with a reform done by closing a grade and opening its successor. The same profiles edit it in
  Django admin; a new read-only "Classification" tab shows the grid as a tree at any date. Run
  `migrate`; `create_demo_classification` loads a demo grid. The real grid is open question `Q28`.
  On phones, the Référentiels toolbar buttons now wrap instead of overflowing the card.
- User guide for end users in `docs/user-guide.md`, with screenshots of each screen, plus a
  self-contained `docs/user-guide.html` to email or print. Retake the screenshots with
  `docs/capture_screenshots.py` and rebuild the HTML with `docs/build_user_guide.py`.
<!-- commits: bcbedcb 1bba339 04cd9da e52a536 dd57ad6 02fe759 29f0647 92abaf4 85f9906 5fd4253 6e72f82 91eb029 -->

## 2026-11-17

- Frontend reorganised by feature: each business area (`auth`, `dashboard`, `systeme`, ...) has
  its own folder with its screens, state, API calls and routes; common code lives in `shared/`.
- This changelog, kept up to date with the `/changelog` skill before each merge.
- Roles: thirteen profile groups, one access permission per module, a side menu that shows only
  the modules a user may open, and an "Accès refusé" page for the others (roadmap 0.4).
  Salaries are visible to Rémunération and Direction RH only; care details to Social and
  Direction RH only.
- `create_demo_users` creates one demo account per profile for development. Superusers are for
  installation only: create named accounts in the right groups instead.
- Open questions on approval circuits (`Q20` to `Q26` in `docs/questions-ouvertes.md`), with a
  proposed circuit for 13 HR processes; to settle with the stakeholders before roadmap 2.11.
- Base models: every business model will inherit `BaseModel`, which records when each row was
  created and last changed, and by whom (roadmap 0.5). New endpoints use `AuthorMixin` and
  `BaseModelSerializer`, new admin classes `BaseModelAdmin`.
- Audit log: every write to a business table, and every change to users, groups and
  permissions, records its author, time and old and new values; the database refuses to change
  an entry (roadmap 0.6). New "Journal d'audit" screen for Auditeur, Direction RH and
  Administrateur système, each seeing only the modules they may open. Run `migrate`. New
  business models must declare `module`; `QuerySet.update()` and `delete()` now raise on them
  (use `update_audited()`).
<!-- commits: 962c423 2ab2964 a2634c4 12c13de 1968090 3f13781 4f4fa9d e7af37a 88de707 -->

## 2026-11-16

- Project scaffold: Django and Django REST Framework backend on PostgreSQL, Vue 3 single-page
  frontend, health check endpoint (roadmap 0.1).
- Project constitution in `specs/`: mission, tech stack and roadmap.
- Design system with light and dark themes on PrimeVue 4, application shell with side menu and
  top bar, demo dashboard and design guide (roadmap 0.3).
- Login: session authentication with CSRF, login page, protected routes with redirect back after
  sign-in, user menu and password change (roadmap 0.2). Create the first account with
  `createsuperuser`.
<!-- commits: a968d7c b75c0bb 1bfc962 98bf4e1 a80c8b4 -->
