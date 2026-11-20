# Changelog

All notable changes to SyRH, newest first. Each section is written from the git history before
the work is merged.

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
<!-- commits: 11ea6fa c754996 fd0bef7 e440d45 c5d0c4d ce6e21c d5f68c9 9a86341 2bbab6b 43b8abd 71d0617 4852398 33c6f03 021cc46 -->

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
