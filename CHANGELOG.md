# Changelog

All notable changes to SyRH, newest first. Each section is written from the git history before
the work is merged.

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
<!-- commits: 962c423 2ab2964 a2634c4 12c13de -->

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
