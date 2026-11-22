# Document storage — plan

Task groups for roadmap phase 2.6: storage, reference data, the model, permissions and admin, API,
screen, demo data, user guide and wrap-up. Decision numbers (`D1`...) refer to
[`requirements.md`](requirements.md). Each group ends with its tests passing and is committed on
its own. **(asked)**

## 1. Backend: encrypted storage

1. Add `cryptography` with `uv add`; record it in `tech-stack.md` (Files and documents).
2. Settings (D8, D9, D12): `SYRH_DOCUMENT_KEYS` and `SYRH_DOCUMENT_ROOT` through django-environ;
   `.env.example` entries with how to generate a key; `backend/var/` in `.gitignore`;
   `DATA_UPLOAD_MAX_MEMORY_SIZE` and `FILE_UPLOAD_MAX_MEMORY_SIZE` at 50 Mo. Tests use a
   generated key and a temporary root.
3. `apps/core/storage.py` (D7, D10): `EncryptedFileSystemStorage(FileSystemStorage)` — encrypts
   in `_save()` with the first key of a `MultiFernet`, decrypts in `open()`; `url()` raises (no
   public URL); `DocumentIndechiffrable` raised on `InvalidToken`.
4. System check `core.E002` (D8): no key, or a key that is not a valid Fernet key, outside tests.
5. Tests (`apps/core/test_storage.py`): round trip; bytes on disk differ from the clear file and
   do not start with `%PDF-`; a second key decrypts after rotation, an unknown key raises
   `DocumentIndechiffrable`; `url()` raises; the check reports a missing and a malformed key.

## 2. Backend: reference data

1. `TypeDocument` (D13): `confidentiel` and `groupes_autorises`; rule "a confidential type has at
   least one group" in the model, French message on `groupes_autorises`; admin form shows both
   (filter_horizontal). Migration in `referentiels`.
2. `Parametre` (D12): key `TAILLE_MAX_PIECE`, label "Taille maximale d'une pièce justificative",
   `Definition("Mo", 1, 50)`; the frontend mirror of `Cle` updated.
3. Demo commands (D23): confidential flags and groups on the demo types; `taille_max_piece = 10`.
4. Tests: the confidential rule from `full_clean()`; the parameter's bounds; the API of both
   tables exposes the new fields; demo commands idempotent.

## 3. Backend: the `Document` model

1. Model `Document(BaseModel)` in `apps/agents/models.py` with the fields of D1, the storage of
   group 1, `upload_to` building `documents/<yyyy>/<mm>/<uuid4>` (D4); ordering (D5);
   `default_permissions = NO_DELETE`; `__str__` with the label of D5.
2. `apps/agents/documents.py`: `detect_mime(head)` (D11); `clean_original_name(name)` (D4);
   `create_document(agent, type_document, uploaded_file, date_document, auteur)` which reads the
   limit (D12), checks emptiness, size and format, computes `taille` and `empreinte`, refuses a
   duplicate (D6) and saves, each failure a `ValidationError` on `fichier` or `type_document`.
3. Model rules (D2, D3, D17): type open on the upload day; fields fixed after creation except
   retirement; `retirer(motif, auteur)` sets the four fields once, refuses a second time and a
   short reason; `delete()` raises. `CheckConstraint`: retired rows have a reason, a date and an
   author; others have none.
4. Readable-by helper (D14): `Document.objects.lisibles_par(user)` — non-confidential types, or
   confidential types sharing a group with the user, everything for a superuser.
5. Migration `0008_document`.
6. Tests (`test_documents.py`): each detected format and each refusal (renamed `.exe`, HTML named
   `.pdf`, empty, over the limit read from the parameter, duplicate); path traversal and control
   characters in the original name; stored name is a UUID; closed type refused; metadata fixed;
   retirement once, reason required, the check constraint bypassing the model; `delete()` raises;
   `lisibles_par` for a member, a non-member and a superuser; audit of upload and retirement
   with label and author, and no file content in the entry.

## 4. Backend: permissions and Django admin

1. `roles.py` (D15): `DOCUMENT_EDIT_PERMISSIONS` (view, add, change on `document`) for Gestion de
   carrière, Administration du personnel and their chefs. Run `migrate` on the development
   database straight after.
2. `admin.py`: `DocumentAdmin` read-only (list: matricule, type, original name, date, retired;
   search on matricule and name; filter on type and retired), queryset through `lisibles_par`;
   no add (uploads go through the API so that every check runs), no delete.
3. Tests (`test_access.py`): permissions held by the four groups only, regranted after `migrate`,
   no delete; the admin list hides confidential documents from a non-member.

## 5. Backend: API

1. `DocumentSerializer` (D20) on `BaseModelSerializer`; `DocumentUploadSerializer` calling
   `create_document`.
2. `DocumentViewSet` nested under `/api/agents/<id>/documents/` (D18): list (`?retires=1`),
   create (multipart, `access_agents` + `add_document`), `fichier` action (D10, D19), `retrait`
   action (`change_document`). Queryset always through `lisibles_par`; the module check before
   the agent lookup.
3. Tests: list in order with every field, retired rows only with `?retires=1`; upload success
   returns `201` and the row; each upload refusal returns `400` with its message on the field;
   download inline and attachment, headers of D19, bytes equal to the uploaded file, accented
   name encoded; a confidential document absent from the list and `404` on download for a
   non-member, present for a member and Direction RH; retire `200`, second retire `400`;
   anonymous `401`; no Agents access `403`; readers without `add_document` get `403` on upload
   and retire; `PUT`/`PATCH`/`DELETE` `405`; undecryptable file `500` with a French message and
   no body bytes of the file; fixed query count on the list.

## 6. Frontend: the documents page

1. `features/agents/api/documents.ts`: typed `listDocuments`, `uploadDocument` (with progress,
   through `request()` or an `XMLHttpRequest` wrapper in `shared/utils/http.ts` that keeps the
   CSRF and `ApiError` behaviour), `retireDocument`, `documentUrl`.
2. `features/agents/components/DocumentsPanel.vue` (D22), `AddDocumentDialog.vue`,
   `RetireDocumentDialog.vue`; `features/agents/views/AgentDocumentsView.vue` with the agent
   picker (D21); `features/agents/routes.ts`; menu entry and `meta.permission` in
   `shared/utils/modules.ts`.
3. Client-side checks: extension and size against the parameter (read from the existing
   parameters API), French messages matching the API's.
4. Tests (Vitest): the panel lists, toggles retired rows, hides buttons without permissions,
   shows field errors from an `ApiError`, shows progress; the dialogs validate before sending.
5. Check the page in the light and dark themes and at its loading, empty and error states.

## 7. Backend: demo data

1. `create_demo_agents` (D23): small PDFs and PNGs generated in code, uploaded through
   `create_document`, one confidential, one retired; skipped when no key is set, with a warning.
2. Tests: rows pass the checks; a second run creates nothing and writes no audit entry; no
   author.

## 8. User guide

1. `docs/user-guide.md`: section "Pièces justificatives de l'agent" — find an agent, add a
   piece, open or download it, retire it, what confidential pieces are.
2. Screenshots through `docs/capture_screenshots.py` (light theme); rebuild `user-guide.html`.

## 9. Wrap-up

1. `tech-stack.md`: the `agents/` line names the documents; "Files and documents" names the
   encrypted storage, the key variables and `cryptography`. `docs/deployment.md`: the key, its
   backup, the document directory and its backup, virus scanning (`Q38`).
2. `docs/questions-ouvertes.md`: add `Q37` and `Q38`.
3. Run the manual walkthrough and the security checks in [`validation.md`](validation.md) on the
   scratch database.
4. Run all quality gates from [`tech-stack.md`](../tech-stack.md).
5. Record any decision changed on the way under "Found during implementation".
6. Tick **2.6 Document storage** in [`roadmap.md`](../roadmap.md).
7. Run `/changelog` on the branch.
