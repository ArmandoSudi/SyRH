# Tree reference data screens — requirements

Roadmap phase **1.10 Tree reference data screens**: editing in SyRH the reference tables that
have parents and children, and carrying children over when their parent changes at a date. Last
phase of Milestone 1.

Branch: `feature/tree-reference-screens`. Plan: [`plan.md`](plan.md). Merge criteria:
[`validation.md`](validation.md).

## Context

- Phase 1.9 made the six flat lists editable in SyRH: `EditionMixin` (create, correct, close and
  open a successor), `ModelPermission`, `ModelRulesSerializerMixin`, the generic `EditionDialog`,
  `ActionsLigne` and `useEdition`. It left seven tables in Django admin.
- The seven tables and their rules (phases 1.1, 1.2, 1.5, 1.6):
  - `Site`: one open head office at a time; cannot close while units on it stay open;
  - `UniteOrganisationnelle`: a tree (direction > département > service > bureau); its type,
    parent and site never change; it sits within its parent's period; a parent cannot close
    while children stay open;
  - `Categorie` > `Grade` > `Echelon`: each child within its parent's period; the parent never
    changes; same closing rule;
  - `TypeDocument` > `PieceRequise`: a requirement's event and type never change; a document type
    cannot close while requirements, exit reasons or suspension types pointing to it stay open.
- So today a parent with open children cannot be replaced at a date: renaming a direction means
  closing and re-adding its whole subtree by hand. The real reorganisations, reforms and renames
  the history rules were built for (organisation D8, classification D11) need that to be one act.
- Editors: Administrateur système, Gestion de carrière and its Chef de service, with the Django
  permissions already granted (`REFERENTIELS_EDIT_PERMISSIONS`).

## Scope

### In scope

1. **Write endpoints** on the seven tables, on 1.9's `EditionMixin`.
2. **Carrying children over**: replacing a parent at a date closes its open children on that
   date and reopens copies under the successor, down the whole subtree, in one transaction.
3. **A preview** of how many rows a replacement carries over, shown before saving.
4. **Dialog extensions**: choosing a parent among the valid open rows; fixed fields read-only.
5. **Edit actions on the Sites, Organisation, Classification and Pièces justificatives tabs**,
   including "add under this row" in the trees and a list of document types to edit.
6. **User guide**: editing the trees, with screenshots.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Moving a unit to another parent or site without replacing it | Not possible by design: the parent and site are fixed; a move is a replacement of the unit under its new parent |
| Carrying units over when a site is replaced | Not planned (D6) |
| Deleting a row | Never (principle 8) |
| Removing the tables from Django admin | Not planned: admin stays as a fallback |
| Undoing a replacement | Correct the rows by hand; the audit log shows what was done |

## Decisions

Decisions marked **(asked)** were confirmed with the product owner before writing this spec; the
others follow from the cahier des charges, `missions.md`, `tech-stack.md` and phases 1.1 to 1.9.

### Write API

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **All seven tables** (`sites`, `unites`, `categories`, `grades`, `echelons`, `types-document`, `pieces-requises`) get 1.9's three writes: `POST` creates, `PATCH` corrects, `POST {id}/successeur/` closes on `date_effet` and opens a successor. `PUT` and `DELETE` answer `405`. **(asked)** | Milestone 1 ends with every reference table editable in SyRH. |
| D2 | The model rules are the rules (1.9 D5): fixed fields (a unit's type, parent and site; a grade's catégorie; an échelon's grade; a requirement's event and type) are refused on `PATCH` by the models' own check, with their French messages. A successor may have other values for them: it is a new row. | One copy of each rule; a move or a reclassification is a replacement. |
| D3 | Permissions as in 1.9 (`add` to create, `change` to correct, both to replace), with the existing editors. | Nothing changes in who edits what. |

### Carrying children over

| # | Decision | Reason |
| --- | --- | --- |
| D4 | **Replacing a parent carries its open children over.** For each child still open after `date_effet`: close it on that date and create a copy (same values, the parent pointing to the new row, opening on `date_effet`), then do the same for that child's own children. All of it, the parent's closing and its successor included, is one transaction: any refused row cancels everything, and the errors come back. **(asked)** | A rename or reform is one act for the user and leaves no gap, no overlap and no orphan. |
| D5 | **The relations carried over**: a unit's sub-units; a catégorie's grades and their échelons; a grade's échelons; a document type's requirements, exit reasons and suspension types (the last two re-pointed to the new type). Each viewset declares its relations; the walk is generic. | The parent and child relations the models already check. |
| D6 | **Sites are not carried over**: replacing or closing a site stays refused while units on it remain open after the date (the existing rule). | A unit has both a parent and a site; carrying both at once would copy a unit twice. Sites rarely change; a unit that moves site is replaced under the new one. |
| D7 | **A child that opens on or after `date_effet`** under the old parent makes the replacement refused, with a message naming it. | It would have to be moved, not copied; the user corrects or closes it first. |
| D8 | **Closing** a parent ("Fermer") stays refused while children are open after the date, with the model's message naming them. | Closing a direction with its services open is a mistake, not a shortcut. |
| D9 | **A preview**: `GET {id}/suite/?date_effet=` returns how many rows a replacement on that date carries over, by kind ("3 départements, 9 services, 4 bureaux"), and the children that would block it (D7). The dialog shows it before saving and asks to confirm when the count is not zero. | The user sees the size of the act before doing it. |
| D10 | Every closed and created row is written with the signed-in user as author and audited like any other change. | The audit log shows the whole act, row by row. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D11 | **Parent fields** are a select of the valid open parents at today: the catégories for a grade, the grades for an échelon, the document types for a requirement, the units of a higher level for a unit (with the sites for its site). The server validates anyway. | Fewer refusals; the server stays the judge. |
| D12 | **Sites tab**: "Ajouter" and the row menu, as the flat lists. | Same pattern as 1.9. |
| D13 | **Organisation tree**: "Ajouter une direction" above the tree; on each unit's row, the menu plus "Ajouter une sous-unité" (parent and site prefilled, type the next level down). | Most units are added under another. |
| D14 | **Classification tree**: "Ajouter une catégorie" above; on a catégorie's row "Ajouter un grade"; on a grade's row "Ajouter un échelon" (next number prefilled); the row menu on each. | Same idea, one level at a time. |
| D15 | **Pièces justificatives**: on an event's row "Ajouter une pièce exigée" (event prefilled); the row menu on each requirement; and a **"Types de pièce"** table under the tree, with "Ajouter" and the row menu, at the tab's date. | Document types have no row of their own in the event tree; they need a list to be edited. |
| D16 | "Remplacer à une date" on a parent shows the preview of D9 once the date is chosen ("Les 12 lignes rattachées suivront : …") and, if rows block it, lists them and disables saving. | D9. |
| D17 | After a save, the tree reloads at the tab's date, keeping the rows the user had opened (the store's expanded keys; new keys for copied rows are opened like their originals). | The user stays where they were. |

### Documentation

| # | Decision | Reason |
| --- | --- | --- |
| D18 | `docs/user-guide.md`: "Change the reference data" covers the trees (adding under a row, replacing a parent and what follows it, why closing a parent is refused) with screenshots; "Who changes the reference data" no longer sends users to Django admin. `docs/user-guide.html` is rebuilt. | The guide describes what users do. |
| D19 | `tech-stack.md`: every reference table is written through the API. | `tech-stack.md` changes with the stack. |

## Open points

None new.

## Found during implementation

| # | Decision | Reason |
| --- | --- | --- |
