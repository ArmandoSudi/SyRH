# Contact details — validation

How to know phase 2.2 is done and `feature/contact-details` can be merged. All parts must pass:
quality gates, automated tests for every acceptance criterion, the manual walkthrough and the
security checks. There is no user guide part: this phase adds no screen. **(asked)**

Decision numbers refer to [`requirements.md`](requirements.md).

## 1. Quality gates

All six, from [`tech-stack.md`](../tech-stack.md), green on the branch tip:

| Check | Command |
| --- | --- |
| Backend tests | `cd backend && uv run python manage.py test` |
| Backend lint and format | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| No missing migration | `cd backend && uv run python manage.py makemigrations --check` |
| Frontend tests | `cd frontend && npx vitest run` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend type-check and build | `cd frontend && npm run build` |

The migration `agents.0003_coordonnees` must apply on an empty database and on the current
development database, and reverse cleanly.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Structure

| # | Criterion | Decision |
| --- | --- | --- |
| S1 | An agent has at most one contact record; a second one is refused by the database. An agent with none is valid. | D1, D11 |
| S2 | Address, town and phone are required and not blank; commune, second phone, email and the emergency contact are optional. | D2, D5, D7, D11 |
| S3 | The agent of a record cannot change after creation; the other fields can be corrected. | D3, D4, D12 |
| S4 | The label reads `Coordonnées de MATRICULE — NOM Postnom Prénom`. | D6 |

### Phones, email and emergency contact

| # | Criterion | Decision |
| --- | --- | --- |
| C1 | Phones are stored trimmed with single spaces; a phone with letters, a misplaced `+`, fewer than 8 or more than 20 characters is refused by the database and reported on its field by `full_clean()`. | D7, D11, D12 |
| C2 | An invalid email is reported on `courriel`; a valid one is stored trimmed and lower case; two agents may share an email. | D8 |
| C3 | An emergency name without a phone, or a phone without a name, is refused by the database and reported on the empty field; both blank, or both given with or without a relationship, is accepted. | D9, D10, D11, D12 |
| C4 | Deleting a contact record raises; there is no delete permission. | D13 |

### Audit

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Creating and correcting a contact record write audit entries under module `agents`, with the label of D6 and their author, including when saved through the admin inline. | D16, D17 |

### Access, admin and API

| # | Criterion | Decision |
| --- | --- | --- |
| P1 | After `migrate`, Gestion de carrière and its chef have view, add and change on `coordonnees`; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D15 |
| P2 | The agent admin page shows one "Coordonnées" inline, without a delete box or a second row; rule errors show next to their field; the editor is recorded as author. | D16 |
| P3 | `/api/agents/<id>/` returns `coordonnees` with the fields of D2, or `null`; `/api/agents/` has no `coordonnees` key; the detail runs a fixed number of queries. | D18 |
| P4 | Access is unchanged from 2.1: anonymous `401`; no group and Administrateur système `403`; every profile opening `agents` `200`; writes `405`. | D14, D18 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | `create_demo_agents` gives eleven demo agents valid contact details, some without email, second phone or emergency contact, and leaves one without; a second run creates nothing and writes no audit entry; its entries show no author. | D19 |

## 3. Manual walkthrough

Run it on the scratch database, as for phase 2.1: a saved row cannot be deleted. Set up first:

```bash
cd backend && DATABASE_URL=<scratch> uv run python manage.py migrate \
  && DATABASE_URL=<scratch> DEBUG=True uv run python manage.py create_demo_users --password <demo> \
  && DATABASE_URL=<scratch> DEBUG=True uv run python manage.py create_demo_agents
```

Then start the `backend-scratch` server (port 8001).

1. Sign in to `/admin/` as `demo.carriere`. Open a demo agent with contact details: the
   "Coordonnées" block shows the address, phones, email and emergency contact, with no delete box
   and no "add another" link.
2. Open the agent without contact details: fill the address, town and phone
   ` +243  81 234 5678 `; save. It is stored as `+243 81 234 5678`.
3. On the same agent, type a phone `08A1234567`: refused next to "Téléphone". Type an emergency
   name without a phone: refused next to the emergency phone. Type `Agent@Example.CD` as email:
   saved as `agent@example.cd`.
4. Open the "Journal d'audit" screen as `demo.direction` (`frontend-scratch`, port 5174): the
   creation and the correction appear under "Agents", labelled `Coordonnées de …`, with their
   author.
5. As `demo.formation`, open `/api/agents/<id>/` for an agent with and without contact details:
   the nested object, then `null`. Open `/api/agents/`: no `coordonnees` key.

Also check: French text with correct accents in the admin labels and messages.

## 4. Security checks

- As `demo.carriere`, a `PATCH` to `/api/agents/<id>/` with `coordonnees` answers `405`.
- An account in no group, and `demo.admin`, get `403` on `/api/agents/<id>/`.
- In `psql`:
  - inserting a second contact record for the same agent fails on the unique constraint;
  - inserting a phone `08A1234567` fails on its check constraint;
  - inserting an emergency name with no phone fails on its check constraint.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_coordonnees'` returns nothing.

## 5. Definition of done

- [ ] Parts 1 to 4 pass.
- [ ] Nothing listed as out of scope slipped in: no address history, no second emergency contact,
      no email sending, no screen, no API write.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `Q35` is in `docs/questions-ouvertes.md`; its answer is not required to merge.
- [ ] `tech-stack.md`'s `agents/` line names the contact details.
- [ ] **2.2 Contact details** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
