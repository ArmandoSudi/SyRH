# Document storage — validation

How to know phase 2.6 is done and `feature/document-storage` can be merged. All parts must pass:
quality gates, automated tests for every acceptance criterion, the manual walkthrough, the
security checks and the user guide. **(asked)**

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

The new `referentiels` migration and `agents.0008_document` apply on an empty database and on the
current development database.

## 2. Acceptance criteria

Each criterion is covered by at least one automated test, run against PostgreSQL. Every database
constraint is also proven by a test that bypasses the model.

### Storage

| # | Criterion | Decision |
| --- | --- | --- |
| F1 | A stored file round-trips byte for byte; the bytes on disk differ from it and are not a readable PDF or image. | D7 |
| F2 | After adding a new first key, old files still open and new files use the new key; a file encrypted with an unknown key raises, and the API answers `500` with a French message and none of the file's bytes. | D8, D10 |
| F3 | The app refuses to start (system check) without `SYRH_DOCUMENT_KEYS` or with a malformed key. | D8 |
| F4 | The stored name is a UUID under `documents/<yyyy>/<mm>/`, whatever the original name; the storage has no public URL. | D4, D9 |

### Uploads

| # | Criterion | Decision |
| --- | --- | --- |
| U1 | A PDF, a JPEG and a PNG are accepted and their `type_mime` comes from the content, even with a wrong extension. | D11 |
| U2 | An executable or an HTML page renamed `.pdf`, an empty file, and a file one byte over the parameter's limit are refused with French messages on `fichier`; changing the parameter changes the limit. | D11, D12 |
| U3 | The same file for the same agent and type is refused; for another agent or type it is accepted. | D6 |
| U4 | A type closed on the upload day is refused on `type_document`. | D3 |
| U5 | An original name with `../`, a path or control characters is stored cleaned, 150 characters at most. | D4 |
| U6 | Metadata cannot change after upload, except through retirement. | D2 |

### Confidential types and retirement

| # | Criterion | Decision |
| --- | --- | --- |
| C1 | A confidential type without a group is refused on `groupes_autorises`. | D13 |
| C2 | A confidential document is listed and downloadable for members of its groups and superusers; for any other Agents reader it is absent from the list and its download answers `404`. | D14 |
| R1 | Retiring sets reason, date and author once; a short reason and a second retirement are refused; the database refuses a retired row without reason. A retired document leaves the default list, appears with `?retires=1`, and still downloads. | D17 |
| R2 | Deleting a document raises; there is no delete permission. | D17 |

### Audit, access and API

| # | Criterion | Decision |
| --- | --- | --- |
| A1 | Upload and retirement write audit entries under `agents` with the label of D5 and their author; no entry holds file content. | D16 |
| P1 | After `migrate`, Gestion de carrière, Administration du personnel and their chefs have view, add and change on `document`; no other group has add or change; nobody has delete; a hand-made change survives the next `migrate`. | D15 |
| P2 | The documents endpoints answer anonymous `401`; no Agents access `403`; an Agents reader without `add_document` `403` on upload and retire; `PUT`, `PATCH`, `DELETE` `405`; an unknown agent `404` for an Agents reader. | D15, D18 |
| P3 | The list returns the fields of D20 and never the storage path or hash, in a fixed number of queries. Download sends the stored type, inline or attachment with the accented name encoded, `nosniff` and `no-store`. | D19, D20 |
| P4 | The admin page is read-only, without add or delete, and hides confidential documents from non-members. | D14, D15 |

### Screen

| # | Criterion | Decision |
| --- | --- | --- |
| V1 | The panel lists the documents, toggles retired rows, hides "Ajouter" and "Retirer" without the permission, shows upload progress, and shows API field errors next to their field. | D21, D22 |
| V2 | The add dialog refuses a wrong extension or a too-large file before sending, with the API's French messages; the type list holds only open types the user may read. | D22 |

### Demo data

| # | Criterion | Decision |
| --- | --- | --- |
| E1 | The demo commands create the confidential flags, the size parameter and documents of every shape (PDF, PNG, confidential, retired); a second run creates nothing and writes no audit entry. | D23 |

## 3. Manual walkthrough

On the scratch database (`backend-scratch`, port 8001) with the Vite dev server: set up first with
`migrate`, `create_demo_users`, the demo reference commands and `create_demo_agents`.

1. Sign in as `demo.carriere`. Open "Pièces des agents" from the menu, pick an agent by matricule:
   their documents are listed.
2. Add a PDF with a document date: a progress bar shows, then the row appears with a success
   message. **Open** it: the PDF shows inline in a new tab. **Download** it: the file keeps its
   original name, accents included. Do the same with a JPEG and a PNG.
3. Try a `.docx`, then a PDF over 10 Mo: each refused with a French message next to the file field,
   before sending. Rename a `.txt` to `.pdf`: refused by the server, message next to the field.
4. Retire a document with a reason: it leaves the list; "Afficher les pièces retirées" shows it
   greyed with its reason, and it still opens.
5. Sign in as `demo.social`: the demo medical certificate is listed; as `demo.formation` it is not,
   and the "Ajouter" and "Retirer" buttons are hidden.
6. Check the page in the **light and dark themes**: loading, empty agent, list and dialogs.

Also check: French text with correct accents in the page, dialogs, messages and admin labels.

## 4. Security checks

- **Encrypted on disk**: open a file under `SYRH_DOCUMENT_ROOT` with `file` and `head -c 8`: not
  recognised as PDF or image. Start the server with a different key: opening a document answers
  the French error, never the file.
- **No direct file URL**: `GET /media/...`, `/documents/...` and the storage path of a known file
  answer `404`; there is no `MEDIA_URL` route in `config/urls.py`. Guessing another document id as
  `demo.formation` for a confidential one gives `404`. Download responses carry
  `Content-Disposition`, `X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`.
- **Spoofed content refused**: with `curl` as `demo.carriere` (session and CSRF), upload an HTML
  file and an executable named `.pdf` with `Content-Type: application/pdf`, a file over the limit,
  and a file named `../../etc/passwd.pdf`: the first three answer `400`; the last is stored under a
  UUID with a cleaned name.
- As `demo.formation`, a `POST` upload and a `POST .../retrait/` answer `403`; `DELETE` answers
  `405` for everyone.
- In `psql`: setting `retire = true` without a reason fails on the check constraint; deleting a
  `TypeDocument` referenced by a document fails on its foreign key.
- `SELECT codename FROM auth_permission WHERE codename = 'delete_document'` returns nothing.

## 5. User guide

- `docs/user-guide.md` has the section "Pièces justificatives de l'agent" (find an agent, add,
  open, download, retire, confidential pieces), with light-theme screenshots taken by
  `docs/capture_screenshots.py`, and `user-guide.html` is rebuilt.

## 6. Definition of done

- [ ] Parts 1 to 5 pass.
- [ ] Nothing listed as out of scope slipped in: no event link, no validation status, no version
      history, no extra format, no agent list or summary page.
- [ ] Any decision changed during implementation is recorded under "Found during
      implementation" in `requirements.md`.
- [ ] `tech-stack.md` names the documents, the encrypted storage and `cryptography`;
      `docs/deployment.md` covers the key and the document directory.
- [ ] `Q37` and `Q38` are in `docs/questions-ouvertes.md`.
- [ ] **2.6 Document storage** is ticked in `roadmap.md`.
- [ ] `/changelog` has been run on the branch.
- [ ] The branch is one reviewable change, per the roadmap's working rules.
