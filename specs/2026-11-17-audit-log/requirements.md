# Audit log — requirements

Roadmap phase **0.6 Audit log**: record author, time, old and new value on every write; read-only
screen for auditors (`TRA-10`).

Branch: `feature/audit-log`. Plan: [`plan.md`](plan.md). Merge criteria: [`validation.md`](validation.md).

## Context

- `TRA-10`: for every creation, modification, validation and deletion, record the author, date,
  time, old and new value; the log cannot be modified.
- `NF-05`: a complete, timestamped, unalterable audit log, kept at least 10 years. The 10 years
  are a proposal not yet confirmed by the ARPTC (`Q18`).
- Section 3: the Auditeur / contrôle interne profile is read-only and reads the audit log.
- `missions.md`, principle 7: everything is traceable. Principle 9: least privilege. The Auditeur
  reads neither Paie nor Social (roles D26); the Administrateur système has no access to HR data
  or pay amounts.
- Phase 0.5 is merged: every business model inherits `BaseModel` (`date_creation`,
  `date_modification`, `cree_par`, `modifie_par`). The author is filled explicitly from the
  request by `AuthorMixin` and `BaseModelAdmin`, never by middleware or thread-locals (0.5 D7).
- Phase 0.4 deferred the audit of role and permission changes to this phase.
- No business table exists yet. Until milestone 1, only account and group changes reach the log.
- `tech-stack.md` lists "audit log implementation (library or custom)" as undecided. This phase
  decides it.

## Scope

### In scope

1. **Audit entries** in a new `apps.audit` app: one append-only table.
2. **Automatic capture for every `BaseModel` table**: creation, modification and deletion, with
   the old and new value of each changed field.
3. **Capture of account administration**: users, groups, group membership and permissions,
   changed through Django admin, the own-password endpoint or the group setup after `migrate`.
4. **Unalterable log**: the database refuses to update or delete an entry.
5. **Module of each entry**, so readers see only the entries of modules they can open.
6. **A new module, "Journal d'audit"**, with its access permission, opened by Auditeur,
   Direction RH and Administrateur système.
7. **Read-only API**: paginated list with filters, and entry detail.
8. **Read-only screen** "Journal d'audit": list, filters, detail of changed fields.

### Out of scope

| Item | Where it goes |
| --- | --- |
| Validation and rejection entries | Phase 2.11 Validation workflow adds the action |
| Sign-ins, sign-outs, failed sign-ins | Not planned for now (asked); phase 9.4 Hardening may add them |
| Logging what users read or consult | Not required by `TRA-10` |
| History tab on a record's own screen | The first record screen (2.10 Agent summary page) |
| Export of the log to Excel or PDF | Phase 9.2 List builder and exports |
| Purge or archiving of old entries | Not before the retention period is confirmed (`Q18`); nothing is purged |
| Protection against the database owner (separate database role, off-site copies) | Phases 9.4 Hardening, 9.5 Backups |
| Logging `createsuperuser` and `create_demo_users` | Installation and development tools; not logged |

## Decisions

Decisions marked **(asked)** were confirmed by the product owner on 2026-11-17. The others follow
from [`missions.md`](../missions.md), [`tech-stack.md`](../tech-stack.md) and the cahier des
charges.

### What is logged

| # | Decision | Reason |
| --- | --- | --- |
| D1 | The log covers **every `BaseModel` table and account administration** (users, groups, membership, permissions). Sign-ins are not logged. **(asked)** | `TRA-10` for business data; role changes were deferred here by phase 0.4. The screen has real entries before the first business table exists. |
| D2 | Actions in this phase: `creation`, `modification`, `suppression`. Phase 2.11 adds `validation` and `rejet`. | `TRA-10` lists all four kinds of event; validation does not exist yet. |
| D3 | An entry records: date and time, author (empty for system writes), action, table, row id, a text label of the row at that moment, its module, and the list of changed fields. | `TRA-10`. The label keeps the entry readable after the row changes or disappears. |
| D4 | Each changed field is stored as its name, its French label at that moment, the old value and the new value. A creation has only new values, a deletion only old values. | Readable by an auditor without knowing the code. |
| D5 | Values are stored as JSON: text, numbers and booleans as they are; dates and decimals as text; a foreign key as its id and label; a many-to-many change as the labels added and removed. | Old values must stay readable even if the referenced row changes later. |
| D6 | **Not logged as changes**: `date_modification`, `modifie_par`, `date_creation`, `cree_par` (the entry already holds the date and author) and `last_login` (it changes on every sign-in). | No noise; sign-ins are out of scope (D1). |
| D7 | **Password changes** are logged as a change of "mot de passe" with masked values, never the hash. | Traceable without exposing even a hash. |
| D8 | A save that changes no field writes no entry. | The log records changes, not saves. |

### How changes are captured

| # | Decision | Reason |
| --- | --- | --- |
| D9 | **Custom implementation, in Django**: no library and no database trigger for capture. **(asked)** | Keeps the author explicit, as phase 0.5 decided; the libraries find the author through middleware and thread-locals. |
| D10 | `BaseModel.save()` and `BaseModel.delete()` write the entry **in the same transaction** as the change. If the change is rolled back, so is its entry. | An entry exists exactly when the change exists. |
| D11 | The author of a creation is `cree_par`; of a modification, `modifie_par`, both set by the mixins (0.5). `BaseModel.delete()` takes an `auteur` argument; `AuthorMixin` and `BaseModelAdmin` pass the request user. | No new way of finding the author. |
| D12 | Old values are read from the database inside the save transaction, just before writing. | Correct even if the object in memory is stale. |
| D13 | On `BaseModel` tables, **`QuerySet.update()` and `QuerySet.delete()` raise an error**. Bulk changes use `update_audited(auteur, **values)`, which logs one entry per row, or delete row by row. `bulk_create` and `bulk_update` are not blocked; their callers log by hand (documented). | They bypass `save()` and `delete()`, which would leave silent gaps. |
| D14 | Deletions are rare (principle 8, `PROTECT` by default). Rows removed by an `on_delete=CASCADE` are not logged one by one; a `CASCADE` between business models must be justified in its phase's spec. | Keeps capture simple without hiding a real gap. |
| D15 | **Account administration** is captured explicitly: an audit mixin for the user and group admins (fields, group membership, permissions, the admin password form), the own-password endpoint, and `sync_groups()`, which logs the permissions it adds with an empty author. | `User` and `Group` are not `BaseModel` tables; these are the only paths that change them in production. |

### Unalterable log

| # | Decision | Reason |
| --- | --- | --- |
| D16 | A PostgreSQL trigger, created by migration, **refuses `UPDATE` and `DELETE`** on the audit table. The model also refuses to save an existing entry and has no `delete`. | `TRA-10`, `NF-05`: the log cannot be modified, not even by mistake in a shell. |
| D17 | `TRUNCATE` is not blocked: the test runner empties tables with it. Protection against the database owner comes with a separate database role in phase 9.4. | A table owner can always drop a trigger; a stronger guarantee needs roles, not code. |
| D18 | The author and table foreign keys use `PROTECT`. Nothing is ever purged in this phase. | An entry must never lose its author or table; retention is at least 10 years (`NF-05`, `Q18`). |
| D19 | The audit table is not registered in Django admin. | The screen is the only way to read it; admin would offer edit forms. |

### Who reads what

| # | Decision | Reason |
| --- | --- | --- |
| D20 | New module **`audit`**, labelled "Journal d'audit", with permission `accounts.access_audit`, given to **Auditeur, Direction RH and Administrateur système**. **(asked)** | Section 3 names the Auditeur; Direction RH supervises; the administrator answers for account changes. |
| D21 | Each entry carries the **module** of its table. A reader sees an entry only if they can open its module. Account administration entries carry the scope `comptes`, visible to every holder of `access_audit`. | Least privilege: the Auditeur never sees Paie or Social values; the Administrateur système sees account and Référentiels entries, never HR data. |
| D22 | Every concrete `BaseModel` subclass declares its module as a class attribute, `module = "referentiels"`. A system check fails at start-up if it is missing or unknown. | The module is known when the table is designed; forgetting it must not silently hide or leak entries. |
| D23 | An entry hidden from a reader answers `404` on the detail endpoint, as if it did not exist. | Does not reveal that a hidden entry exists. |

### API

| # | Decision | Reason |
| --- | --- | --- |
| D24 | `GET /api/audit/entrees/`: list, newest first, 50 per page. Filters: `date_debut`, `date_fin`, `auteur` (text matched on username, first and last name), `module`, `action`, `table`, and `table` + `objet` for one row's history. | Covers what an auditor searches for; the row filter prepares the future history tab. |
| D25 | `GET /api/audit/entrees/{id}/`: one entry with its changed fields. Writes answer `405`. | Read-only by construction. |
| D26 | Both endpoints use `HasModuleAccess("audit")`, then the module filter of D21. | `tech-stack.md`: access enforced in the API. |
| D27 | The author is returned as id and display name; a system write shows "Système". The table is returned as its French label. | Readers see people and tables, not ids. |
| D28 | Indexes on date, on table and row id, and on module and date. | `NF-08`: a screen in under 3 seconds as the log grows over 10 years. |

### Screen

| # | Decision | Reason |
| --- | --- | --- |
| D29 | Feature folder `audit`, route `/audit` with `meta.permission` from the shared module map, menu entry "Journal d'audit" under Administration. | Same rules as every module (phase 0.4). |
| D30 | A paginated table, loaded page by page from the API: date and time, author, action, module, table, row label. Filters: period, author, module (only the reader's modules), action. | Matches D24; nothing is loaded in full. |
| D31 | Clicking a row opens a side panel with each changed field: label, old value, new value. Masked values show as "••••••". | The old and new value is the point of `TRA-10`. |
| D32 | No button on the screen changes anything. Filters stay while the user moves around (Pinia). | Read-only; `tech-stack.md` keeps filters across navigation. |

### Decision recorded in tech-stack

| # | Decision | Reason |
| --- | --- | --- |
| D33 | `tech-stack.md`: the audit log is **custom** (`apps.audit`), removed from "Decisions not yet taken", and `audit` is added to the list of apps. | `tech-stack.md` changes in the same commit as the stack. |

## Open points

| Point | Assumption until answered |
| --- | --- |
| Retention period of the log (`Q18`: 10 years proposed, not confirmed) | Nothing is purged. |
