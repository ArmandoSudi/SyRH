# Mission

SyRH is the HR management system of the ARPTC (Autorité de Régulation de la Poste et des
Télécommunications du Congo). It follows every agent from hiring to exit and lets the five HR
services work from the same data instead of re-keying it between them.

Stakeholder input lives in [`docs/cahier-des-charges-sirh-arptc.md`](../docs/cahier-des-charges-sirh-arptc.md).
Unanswered business rules live in [`docs/questions-ouvertes.md`](../docs/questions-ouvertes.md).
Requirement IDs below (`SOC-01`, `CAR-06`, ...) refer to the cahier des charges.

## Who it serves

| Service | What it does in SyRH |
| --- | --- |
| Gestion de carrière | Creates the agent at hiring, records promotions, suspensions and exits |
| Administration du personnel | Records attendance, absences, overtime, dependants, interns, day labourers |
| Rémunération | Computes payroll from data validated by the other services, explains every pay variance |
| Social | Issues care vouchers and checks the hospital's monthly invoice against them |
| Formation | Records the training each agent receives |

Supporting roles: HR service heads (validation), HR management (approval, dashboards), internal
audit (read-only), system administrators (accounts and settings, no access to pay amounts).

## The agent lifecycle we cover

1. **Hiring** — record, contract, assignment, grade.
2. **Professional evolution** — promotions, interim assignments, seniority, training.
3. **Social evolution** — wife and children, on proof of a civil-status document.
4. **Day to day** — attendance, absences, overtime, medical care, monthly pay.
5. **Suspension** — mise en disponibilité (2 years, renewable once) and détachement.
6. **Exit** — death, resignation, or retirement at 30 years of career or 65 years of age,
   whichever comes first.

## MVP goal

**One reliable, historised agent record shared by all five services.**

The MVP is done when Gestion de carrière and Administration du personnel can keep the complete
file of every agent in SyRH — identity, contract, grade and position history, dependants,
supporting documents — and any service can trust it as the single source of truth.

Payroll, care vouchers and training are built afterwards, on top of that record. We would rather
ship a narrow system with a sound data model than a broad one whose data cannot be trusted.

## Principles

These decide trade-offs when the spec is silent.

1. **The database is the product.** Model the domain carefully before building screens. Every
   table has constraints that make invalid states unrepresentable where practical.
2. **One source of truth.** A fact is stored once, in the module that owns it. Other modules read
   it; nobody copies it.
3. **History is never overwritten.** Anything that evolves (grade, function, salary, assignment,
   civil status) is stored as dated records. An event has an effective date distinct from its
   entry date (`SOC-02`, `SOC-03`).
4. **No proof, no validation.** An event that rests on a document cannot be validated without the
   scanned document attached (`SOC-04`, `ADM-14`).
5. **Who enters does not validate.** Data that affects pay goes through entry, validation, then
   integration (`TRA-01`).
6. **Rules are parameters, not code.** Pay scales, age limits, durations, maximum number of
   children, banks and pay items are reference data that HR maintains (`REM-23`, `NF-12`).
7. **Everything is traceable.** Every create, update, validation and deletion is logged with
   author, time, old and new value (`TRA-10`).
8. **Nothing is physically deleted.** Agents who leave are deactivated and archived (`CAR-19`,
   `NF-13`).
9. **Least privilege.** A user sees only what their role needs. Salaries are visible to
   Rémunération and HR management only; care details to Social only (`SOC-M-20`).
10. **French first.** Interface, documents and domain vocabulary are in French; code and
    technical documentation are in English.

## Fixed business rules

Settled by stakeholders; do not re-open without them.

| Rule | Value |
| --- | --- |
| Proof for a wife | Marriage certificate |
| Husband of a female agent | Not a dependant |
| Proof for a child | Birth certificate |
| Child age limit | 25 years |
| Maximum number of children covered | Configurable parameter |
| Start of the 30-year career count | Hiring date at ARPTC |
| Détachement | Counts toward the 30 years |
| Mise en disponibilité | 2 years, renewable once; no pay or benefits |
| Pay currency and method | USD only, by bank transfer |
| Gross total on the payslip | Includes the seniority bonus |
| IPR tax base | Base salary only |
| Transport component | Not paid during sickness and maternity leave |
| Attendance | Comes from the existing time clock; absences are entered by Administration du personnel |
| Sites | All ARPTC sites |

## Out of scope

- General accounting and treasury: SyRH exports files, it does not keep the books.
- Recruitment before hiring: job postings, candidate selection.
- Medical records: only what is needed to check invoices.
- Agent self-service portal: planned for a later version.

## What success looks like

- An HR officer finds any agent and reads their full dated history on one screen.
- No service keeps a parallel spreadsheet for data SyRH owns.
- Any figure on a payslip can be traced to a validated event and its supporting document.
- Upcoming deadlines (end of probation, retirement, child turning 25, end of suspension) are
  flagged before they happen, not discovered after.
