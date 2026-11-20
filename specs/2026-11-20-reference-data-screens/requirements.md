# Reference data screens — requirements

Roadmap phase **1.9 Reference data screens**: editing the reference data in SyRH itself instead
of Django admin. This phase covers the **six flat lists**; the tables with parents and children
move to a new phase **1.10**. **(asked)**

Branch: `feature/reference-data-screens`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Phases 1.1 to 1.8 built thirteen reference tables. Each is edited in Django admin by its
  editors and shown read-only on the "Référentiels" screen; every spec named phase 1.9 as the one
  that brings editing into the app.
- Every rule already lives in the models: database constraints, and `clean()` / `save()` with
  French messages per field. Django admin shows them; the API can reuse them unchanged.
- The editors differ by table: Administrateur système, Gestion de carrière and its Chef de
  service for most; Rémunération, its Chef de service and the administrator for banks (banks
  D12). The Django permissions (`add_…`, `change_…`) say who; `/api/auth/me/` already returns
  them to the client.
- History: a change is recorded by closing the current row on a date and opening a successor;
  a typing error is corrected in place; nothing is deleted (principle 3, principle 8).
- Writes from the SPA already work for the password change: session cookie and the
  `X-CSRFToken` header (`shared/utils/http.ts`). `apps.core.mixins.AuthorMixin` stamps the
  author of a row and of its audit entry.
- The roadmap's working rules: split a phase that is larger than a few days.

## Scope

### In scope

1. **Write endpoints** on the six flat lists: fonctions, types de contrat, banques, motifs de
   sortie, types de suspension, paramètres. Create, correct, and close-and-succeed; no delete.
2. **One generic edit dialog** on the frontend, driven by a field description per table.
3. **Edit actions on the existing tabs**, shown only to the users allowed to edit that table.
4. **Roadmap**: a new phase 1.10 for the other tables.
5. **User guide**: how to add, correct, replace and close a row, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Editing sites, organisation units, catégories, grades, échelons, document types and required documents | New roadmap phase **1.10 Tree reference data screens** |
| Removing the reference tables from Django admin | Not planned: admin stays as a fallback for the administrator |
| Deleting a row | Never (principle 8) |
| Validation circuits (entry, validation, integration) on reference data | Not asked for; `TRA-01` is about data that affects pay, phase 2.11 |
| Editing several rows at once, imports | Not asked for |
| Changing who edits which table | Permissions stay as phases 1.3 to 1.8 set them |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phases 1.1 to 1.8.

### What this phase covers

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **The six flat lists only**: `Fonction`, `TypeContrat`, `Banque`, `MotifSortie`, `TypeSuspension`, `Parametre`. **(asked)** | They share one shape (a row with its own dates, no children); the tree tables need parent pickers and cascading period checks, a second piece of work. |
| D2 | `roadmap.md` gains **1.10 Tree reference data screens** (sites, organisation, classification, document types and required documents), after 1.9 in Milestone 1. | The working rule on phase size; Milestone 1 ends with all reference data editable in the app. |

### Write API

| # | Decision | Reason |
| --- | --- | --- |
| D3 | **Three operations** on each of the six endpoints: `POST /` creates a row; `PATCH /{id}/` corrects one (any field the model lets change, closing date included, which closes the row with no successor); `POST /{id}/successeur/` closes the row on `date_effet` and opens a successor from that date with the fields sent, in one transaction. `PUT` and `DELETE` answer `405`. | The three ways history is kept (create, correct a typing error, record a change at a date), and nothing else. |
| D4 | **Successor rules**: only a row with no closing date can be succeeded; `date_effet` is after its opening date; the successor starts from the old row's values, overridden by the fields sent (the code may stay the same). If the successor is invalid, nothing is saved and the errors come back on its fields. | A change at a date leaves no gap and no overlap; a refused successor must not leave the old row closed. |
| D5 | **The model rules are the rules**: the serializer calls `full_clean()` and returns its `ValidationError` as a `400` with the field names, and `non_field_errors` for the rest. No rule is copied into the serializer. | One copy of each rule; the same French messages as in Django admin. |
| D6 | **Permissions**: reading keeps `HasModuleAccess("referentiels")`; `POST` needs the model's `add` permission, `PATCH` its `change` permission, `successeur` both. Others get `403`. | The Django permissions already say who edits what (Rémunération for banks, the others elsewhere). |
| D7 | The writer is the author: `cree_par` / `modifie_par` and the audit entries carry the signed-in user, through `AuthorMixin`. | The audit log says who changed what. |
| D8 | **Fields that never change** stay locked through the API, by the model's own rule: a parameter's key (general parameters D7). Every other field of the six tables can be corrected. | Same behaviour as Django admin. |
| D9 | The write responses return the saved row in the read serializer's shape; `successeur` returns the successor, with `201`. | The client updates its list without guessing. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D10 | **Who sees the actions**: the "Ajouter" button and the row actions appear only for a user holding the table's `add` / `change` permission, read from `/api/auth/me/`. Others see the tab as today. | No button that would answer `403`. |
| D11 | **Actions per row** (a menu at the end of the row): **Corriger** (edit in place), **Remplacer à une date** (close and open a successor), **Fermer** (set the closing date). A closed row offers only Corriger. **Ajouter** above the table opens an empty form. | The three history operations, named in the users' words. |
| D12 | **One generic dialog** (`EditionDialog.vue`) renders a form from a field description per table (`components/edition/champs.ts`): text, yes/no, choice, number, date, document type (a select of open document types). Each field shows its label, its help text where the model has one, and the server's error under it; errors without a field show at the top. | Six tables, one form; the messages come from the server (D5). |
| D13 | "Remplacer à une date" shows the fields prefilled with the current values and a required "Date d'effet"; "Fermer" asks only for the closing date. After a save, the dialog closes, the tab reloads its list at its current date, and a short confirmation shows ("Fonction enregistrée."). | The user sees the result where they were. |
| D14 | The dialog works with the keyboard (focus on the first field, Escape cancels, Enter saves) and fits at 375 px. | Same standard as the rest of the app. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D15 | `docs/user-guide.md` gets a "Change the reference data" subsection: add, correct, replace at a date, close, with screenshots of the dialog; "Who changes the reference data" says editing is now done in SyRH for the six lists, Django admin for the others until 1.10. `docs/user-guide.html` is rebuilt. | The guide describes what users do. |
| D16 | `tech-stack.md`: the `referentiels` lines say the six flat lists are editable through the API. | `tech-stack.md` changes with the stack. |

## Open points

None new. The open questions on the real lists (`Q29` to `Q34`) are answered by entering the data,
which this phase makes possible in the app.

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
