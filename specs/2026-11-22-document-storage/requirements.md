# Document storage — requirements

Roadmap phase **2.6 Document storage**: upload, store and serve the agents' scanned supporting
documents behind authentication, encrypted at rest (`TRA-03`, `NF-03`). Sixth phase of
Milestone 2 (agent record, MVP).

Branch: `feature/document-storage`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Cahier des charges: `TRA-03`, "numériser, classer et consulter les pièces depuis le dossier de
  l'agent ; formats PDF et image". Section 4.2: the agent's file holds "copies numérisées de tous
  les justificatifs". `NF-03`: sensitive data at rest is encrypted, identity documents named.
- `missions.md`: principle 4, **no proof, no validation** (enforced in 2.7, on top of this phase);
  principle 7, everything traceable; principle 8, nothing physically deleted; principle 9, least
  privilege — medical details go to Social and Direction RH only.
- `tech-stack.md`, "Files and documents": files on the server filesystem through Django's storage
  API, outside the web root, served only through authenticated views; the database keeps the
  metadata.
- Phase 1.5 created `referentiels.TypeDocument` (code, nom, dated) and `PieceRequise` (which
  document each event kind requires). Phase 1.8 created `referentiels.Parametre`, dated integer
  parameters read with `valeur_au()`.
- Phase 2.1 created `agents.Agent`; the agents endpoints need `access_agents`.
- Readers to come: 2.7 Documents on events (links an event to these rows, blocks validation
  without a mandatory one), 2.10 Agent summary page (reuses the documents panel), 2.12 to 2.14
  (civil-status certificates), Milestone 3 (decisions), 2.15 Data import.

## Scope

### In scope

1. **One table** `Document` in `apps.agents`: an agent's scanned file, its document type and its
   metadata. The file itself, encrypted, on the filesystem.
2. **Encrypted storage** of every file with Fernet, the key from the environment.
3. **Upload checks**: PDF, JPEG or PNG recognised from the content; size under a general
   parameter.
4. **Confidential document types**: a flag and the groups allowed to read them.
5. **Retiring** a wrong upload, with a reason; nothing deleted.
6. **API**: list, upload, download (inline or attachment) and retire, per agent.
7. **Screen**: a "Pièces de l'agent" page with an agent picker and a documents panel (list,
   upload, open, retire), the panel reused by 2.10.
8. **Demo data**: a few documents for the demo agents.
9. **User guide**: the page documented in `docs/user-guide.md`, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Linking a document to an event; blocking validation without a mandatory one | Phase 2.7 |
| The agent list and summary page | Phases 2.8, 2.10 |
| Validation workflow of a document | Phase 2.11 |
| Version history ("better scan of the same document") | Not planned; retire and upload again |
| TIFF, Word or other formats; OCR; thumbnails; multi-file merge | Not planned |
| Virus scanning | Open point; the deployment decides |
| Backups of the document directory and of the key | Production deployment decision |
| Loading the existing paper archive | Phase 2.15 or a later import |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner on 2026-11-22; the others
follow from the cahier des charges, `missions.md`, `tech-stack.md` and earlier phases.

### Structure

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **One table** `Document` in `apps.agents`, `module = "agents"`, `related_name` `documents`: `agent` (`PROTECT`), `type_document` (`referentiels.TypeDocument`, `PROTECT`), `fichier` (path in the encrypted storage), `nom_original`, `type_mime`, `taille` (bytes, of the clear file), `empreinte` (SHA-256 of the clear file), `date_document` (optional: date printed on the document), `retire`, `motif_retrait`, `date_retrait`, `retire_par`. **(asked)** | `TRA-03`: the documents form the agent's file and are classed by type. 2.7 links events to these rows. |
| D2 | **Metadata never changes after upload** except the retirement fields; a wrong type or agent is retired and uploaded again. | The file and what it proves stay as they were checked. |
| D3 | The type must be **open on the upload day**. | As every reference row read by a new record. |
| D4 | Stored name: a random UUID with no extension, under `documents/<year>/<month>/`, never derived from the original name. `nom_original` is cleaned (path parts, control characters removed, 150 characters at most). | No path traversal, nothing guessable on disk. |
| D5 | Label: `TYPE — nom_original — MATRICULE`. Rows sort by agent, then upload date, newest first. | Names the row in the audit log and the admin. |
| D6 | The same file (same `empreinte`) uploaded twice for one agent and type is refused with a French message. | A double click or a re-scan would clutter the file. |

### Storage and encryption

| # | Decision | Reason |
| --- | --- | --- |
| D7 | **Every file is encrypted** with Fernet (package `cryptography`) by a custom storage `apps.core.storage.EncryptedFileSystemStorage`, before it reaches the disk. **(asked)** | `NF-03`; one code path, nothing sensitive stored in clear by mistake. |
| D8 | Keys from the environment, `SYRH_DOCUMENT_KEYS`, a comma-separated list read by `MultiFernet`: the first encrypts, all decrypt. Missing key: the app refuses to start outside tests (system check). | Key rotation without re-encrypting at once; the key never in the repository. |
| D9 | Files live under `SYRH_DOCUMENT_ROOT` (default `backend/var/documents/`, ignored by git), outside any static or media URL. No `MEDIA_URL` route. | `tech-stack.md`: served only through authenticated views. |
| D10 | A file is decrypted in memory to be served; a file that fails to decrypt answers `500` with a French message and is logged, never served raw. | 10 MB at most; a wrong key must not leak ciphertext as a "PDF". |

### Upload checks

| # | Decision | Reason |
| --- | --- | --- |
| D11 | **Formats: PDF, JPEG, PNG**, recognised from the first bytes (`%PDF-`, `FF D8 FF`, `89 50 4E 47 0D 0A 1A 0A`), whatever the extension or the browser's type. The stored `type_mime` comes from the content. **(asked)** | `TRA-03`; a renamed executable or HTML page must be refused. |
| D12 | **Size limit**: a new general parameter `taille_max_piece`, "Taille maximale d'une pièce justificative", in Mo, bounds 1 to 50, demo value 10, read with `valeur_au(today)`. An empty file is refused. `DATA_UPLOAD_MAX_MEMORY_SIZE`/`FILE_UPLOAD_MAX_MEMORY_SIZE` cap the request at 50 Mo. **(asked)** | Principle 6, rules are parameters. |

### Access

| # | Decision | Reason |
| --- | --- | --- |
| D13 | **`TypeDocument` gains `confidentiel`** (boolean, default false) and `groupes_autorises` (many-to-many to `auth.Group`, blank). A confidential type requires at least one group (model rule). **(asked)** | Medical and identity documents (`NF-03`, principle 9) are read by fewer profiles than the rest of the file. |
| D14 | **Reading**: any profile opening Agents reads the documents of non-confidential types; a confidential type's documents are read only by members of its groups. A confidential document a user cannot read is **absent** from the list, and its download answers `404`. Superusers read everything. **(asked)** | No hint that a medical document exists. |
| D15 | **Uploading and retiring**: Gestion de carrière, Administration du personnel and their chefs, through permissions `agents.add_document` and `agents.change_document` (`DOCUMENT_EDIT_PERMISSIONS` in `roles.py`); they also need to read the type (D14) to upload one. Nobody has delete. **(asked)** | They keep the agent's file (MVP goal). |
| D16 | **Audit**: rows audited under module `agents` as any write. The audit shows the type, the original name and the retirement, never the content. | Principle 7. The original name's visibility to Agents audit readers is an open point. |

### Retirement

| # | Decision | Reason |
| --- | --- | --- |
| D17 | **Retire with reason**: `retire` true, `motif_retrait` required (10 characters at least), `date_retrait` and `retire_par` set; the file is kept. A retired document leaves the default list (`?retires=1` shows it, greyed) and stays downloadable by its readers. It cannot be un-retired. `delete()` raises. **(asked)** | Principle 8; a mistaken upload remains traceable. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D18 | Nested under the agent: `GET /api/agents/<id>/documents/` (`?retires=1`), `POST` multipart (`type_document`, `fichier`, `date_document`), `GET .../documents/<doc>/fichier/` (`?telechargement=1` for an attachment), `POST .../documents/<doc>/retrait/` (`motif`). No `PUT`, `PATCH` or `DELETE`. | One agent's file at a time, as the screen. |
| D19 | Download headers: the content type stored (D11), `Content-Disposition` inline or attachment with the cleaned original name (RFC 5987 for accents), `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store`. | The browser must neither guess the type nor cache a confidential file. |
| D20 | Serializer fields: `id`, `type_document`, `type_document_code`, `type_document_nom`, `confidentiel`, `nom_original`, `type_mime`, `taille`, `date_document`, `retire`, `motif_retrait`, `date_retrait`, `retire_par`, base fields; never the storage path or the hash. | The path is an internal detail. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D21 | New feature `features/agents/` with route `/agents/pieces` ("Pièces des agents", menu under Agents): an agent picker (AutoComplete on matricule and name over `/api/agents/`), then the component `DocumentsPanel.vue` taking an agent id. **(asked)** | 2.10 mounts the same panel on the summary page; this route goes away or redirects then. |
| D22 | The panel: table of type, original name, document date, size, upload date and author; "Afficher les pièces retirées" toggle; "Ouvrir" (new tab, inline), "Télécharger", "Retirer" (dialog with the reason); "Ajouter une pièce" dialog with the type (open types the user may read), the optional date and PrimeVue `FileUpload` with progress. Buttons hidden without the permission. Size and format checked in the browser too, with the same French messages; the API stays the authority. | `tech-stack.md`: immediate feedback, errors next to the field. |

### Demo data

| # | Decision | Reason |
| --- | --- | --- |
| D23 | `create_demo_agents` adds a few small generated PDFs and PNGs (built in code, no binary in the repository) for some agents, one of a confidential demo type, one retired; `create_demo_document_types` marks the demo medical certificate and identity card confidential with their groups; `create_demo_parametres` adds `taille_max_piece = 10`. Idempotent. | Covers every shape of the panel. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| `Q37` (new) — which document types are confidential, and for whom. | Demo: certificat médical for Social, its chef and Direction RH; pièce d'identité for Gestion de carrière, Administration du personnel, their chefs and Direction RH. |
| `Q38` (new) — virus scanning of uploads. | None in SyRH; noted in `docs/deployment.md` as a deployment choice. |
| The original file name is visible in the audit log to every Agents audit reader, confidential types included. | Accepted for now; revisit if `Q37` says names are sensitive. |
| Backup and safekeeping of `SYRH_DOCUMENT_KEYS`: a lost key loses every document. | Documented in `docs/deployment.md`; decided with the production deployment. |

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
| D24 | The permissions are `AGENT_DOCUMENT_EDIT_PERMISSIONS` in `roles.py`, not `DOCUMENT_EDIT_PERMISSIONS`. Holding them gives Administration du personnel and its chef staff status: they read the documents admin page. | `DOCUMENT_EDIT_PERMISSIONS` already names the document types' permissions (phase 1.5). |
| D25 | "A confidential type names a group" (D13) has no database constraint: a many-to-many is saved after its row. It is checked by `TypeDocument.check_groupes()`, from the admin form and the API serializer; group changes are audited through `set_groupes()` and the admin's `save_related()`. The Référentiels screen shows nothing new: the flag and groups are edited in Django admin (or the API); a successor carries them over. | Neither `full_clean()` nor a check constraint can see the groups before they are saved. |
| D26 | The duplicate rule (D6) is a partial unique constraint (`retire = false`): once retired, the same file can be uploaded again, for instance with the right type. | Otherwise a wrong upload could never be corrected with the same scan. |
| D27 | A retired row needs a reason and a date; `retire_par` may stay empty (scripts, demo data). | Same as the authors of every row (`tech-stack.md`). |
| D28 | The API adds `cree_par_nom` and `retire_par_nom` (D20) for the panel; uploading a confidential type the user cannot read answers `400` on `type_document`. | The panel shows who added and retired a piece (D22). |
| D29 | The file is chosen with a French "Choisir un fichier" button opening a hidden native input, not PrimeVue `FileUpload`; progress comes from `upload()` in `shared/utils/http.ts` (XMLHttpRequest). | The native button speaks the browser's language; `FileUpload`'s own type and size checks show its own messages, not the server's. `fetch` reports no upload progress. |
| D30 | The menu gets a separate entry "Pièces des agents" after "Agents". | The side menu has no sub-entries. |
| D31 | A test run (`manage.py test`) gets a generated key and a temporary document directory. Demo documents need no "no key" branch: system check `core.E002` stops the command first. | Tests never need a real key. |
| D32 | The test server's nginx accepts 50 Mo bodies (was 20 Mo); `docs/deployment.md` adds `SYRH_DOCUMENT_KEYS` and `SYRH_DOCUMENT_ROOT=/var/lib/syrh/documents`, to set before the next `update.sh`. | Otherwise the server would refuse to start, or nginx would refuse uploads under the parameter's limit. |
