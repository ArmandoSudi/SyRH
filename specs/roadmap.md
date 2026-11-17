# Roadmap

High-level implementation order, in very small phases. Each phase is a slice that can be built,
tested and committed on its own, usually backend model + API + tests, then a screen.

Order follows the data flow: foundations, then the agent record, then Carrière, Administration
du personnel, Rémunération, Social, Formation. Each module feeds the next.

Requirement IDs refer to [`docs/cahier-des-charges-sirh-arptc.md`](../docs/cahier-des-charges-sirh-arptc.md).
`Qn` refers to [`docs/questions-ouvertes.md`](../docs/questions-ouvertes.md): a phase marked with
a question needs that answer, or builds the rule as a parameter.

Tick a phase when it is merged.

## Milestone 0 — Foundations

- [x] **0.1 Scaffold** — Django + DRF, Vue + Vite, PostgreSQL, health check, initial commit.
- [x] **0.2 Login** — session login, logout and "current user" endpoints with CSRF; login page;
  route guard that redirects anonymous users.
- [x] **0.3 App shell and design system** — PrimeVue with the French locale; light and dark
  themes; layout with side menu and top bar; demo dashboard and design guide page
  (see [`design.md`](design.md)).
- [x] **0.4 Roles** — one group per profile of section 3 of the spec; permissions exposed to the
  frontend; menu filtered by role.
- [ ] **0.5 Base models** — abstract base with created/updated timestamps and author, shared by
  all business models.
- [ ] **0.6 Audit log** — record author, time, old and new value on every write; read-only screen
  for auditors (`TRA-10`).

## Milestone 1 — Reference data

Small tables first, each with model, constraints, admin, API and tests.

- [ ] **1.1 Organisation** — sites, directions, départements, services, bureaux, as a tree.
- [ ] **1.2 Classification** — catégories, grades, échelons.
- [ ] **1.3 Fonctions** — job functions.
- [ ] **1.4 Contract types** — CDI, CDD, stage, journalier.
- [ ] **1.5 Document types** — the supporting documents each event requires.
- [ ] **1.6 Exit and suspension reasons** — with a "counts toward seniority" flag (`Q2`, `Q3`).
- [ ] **1.7 Banks** — name, code (`REM-28`).
- [ ] **1.8 General parameters** — dated key/value settings: child age limit (25), maximum
  children, retirement age (65), career length (30).
- [ ] **1.9 Reference data screens** — one generic list/edit screen for administrators.

## Milestone 2 — Agent record (MVP)

The MVP goal: one reliable, historised agent record.

- [ ] **2.1 Agent identity** — model with unique matricule, never reused (`SOC-01`, `Q5`).
- [ ] **2.2 Contact details** — address, phone, email, emergency contact.
- [ ] **2.3 Contract** — type, hiring date, probation, end date.
- [ ] **2.4 Position history** — dated rows for service, function, grade, échelon, with no
  overlap (`SOC-02`, `SOC-03`).
- [ ] **2.5 Bank account** — bank and account number per agent.
- [ ] **2.6 Document storage** — upload, store and serve scanned documents behind authentication
  (`TRA-03`).
- [ ] **2.7 Documents on events** — attach a document to an event; block validation without it
  (`SOC-04`).
- [ ] **2.8 Agent list** — search by matricule, name, service, grade, function, status (`SOC-06`).
- [ ] **2.9 Agent creation form** — hiring entry by Gestion de carrière (`CAR-01`, `CAR-02`).
- [ ] **2.10 Agent summary page** — identity, current position, computed age and seniority,
  full timeline (`SOC-05`, `SOC-07`).
- [ ] **2.11 Validation workflow** — draft, submitted, validated, rejected with reason; the
  author cannot validate (`TRA-01`). Settle `Q20` to `Q26` (approval circuits) first.
- [ ] **2.12 Wife** — recorded on a marriage certificate; refused for a female agent's husband
  (`ADM-12`).
- [ ] **2.13 Children** — recorded on a birth certificate, with the configurable maximum
  (`ADM-13`, `ADM-17`).
- [ ] **2.14 End of dependant status** — death, divorce, child reaching 25 (`ADM-15`, `Q1`).
- [ ] **2.15 Data import** — load existing agents and dependants from a spreadsheet
  (`REP-02`).

**MVP checkpoint**: Gestion de carrière and Administration du personnel keep every agent's file
in SyRH.

## Milestone 3 — Gestion de carrière

- [ ] **3.1 Promotions** — old and new grade, effective date, decision reference (`CAR-06`).
- [ ] **3.2 Transfers and function changes** (`CAR-08`).
- [ ] **3.3 Interim assignments** — post, replaced holder, dates (`CAR-09`).
- [ ] **3.4 Suspensions** — mise en disponibilité (2 years, one renewal) and détachement, with
  return to service (`Q4`).
- [ ] **3.5 Seniority** — computed from hiring date, honouring the seniority flag of suspensions
  (`CAR-10`, `Q3`).
- [ ] **3.6 Exit** — reason, effective date, document; agent deactivated everywhere, never
  deleted (`CAR-16`, `CAR-19`).
- [ ] **3.7 Retirement forecast** — agents reaching 30 years or 65 years, by year (`CAR-14`,
  `CAR-15`).
- [ ] **3.8 Sanctions and distinctions** (`CAR-11`).

## Milestone 4 — Alerts

- [ ] **4.1 Alert engine** — scheduled job that computes upcoming deadlines.
- [ ] **4.2 Career alerts** — end of probation, end of contract, retirement at 12/6/3 months,
  end of suspension, end of interim.
- [ ] **4.3 Dependant alerts** — child approaching 25.
- [ ] **4.4 Notifications** — in-app list, then email (`TRA-04`).

## Milestone 5 — Administration du personnel

- [ ] **5.1 Absence types** — reference data, with their effect on pay.
- [ ] **5.2 Absences** — entry with supporting document and validation (`ADM-02`, `ADM-03`).
- [ ] **5.3 Annual leave** — entitlement, taken, balance (`ADM-04`).
- [ ] **5.4 Maternity and sickness** — periods flagged for the transport rule (`ADM-05`,
  `ADM-06`, `Q8`).
- [ ] **5.5 Attendance import** — from the time clock (`ADM-01`, `Q14`).
- [ ] **5.6 Overtime** — entry with prior authorisation, classified by rate band (`ADM-09`,
  `ADM-10`).
- [ ] **5.7 Monthly attendance report** (`ADM-08`).
- [ ] **5.8 Interns** — separate register, end-of-internship alert, certificate (`ADM-19`,
  `ADM-20`).
- [ ] **5.9 Day labourers** — separate register, days worked (`ADM-21`).

## Milestone 6 — Rémunération

- [ ] **6.1 Pay items** — configurable gains, deductions, contributions (`REM-01`, `Q10`).
- [ ] **6.2 Pay scales** — dated amounts, optionally per grade (`REM-23`, `REM-24`, `Q7`,
  `Q11`).
- [ ] **6.3 Pay period** — open, in progress, closed; closed periods are immutable (`REM-10`).
- [ ] **6.4 Base salary** — days worked × daily rate (`REM-25`).
- [ ] **6.5 Seniority bonus** (`REM-26`, `Q6`).
- [ ] **6.6 Housing and transport** — with transport withheld during sickness and maternity
  (`REM-27`).
- [ ] **6.7 Family allowances** — from validated dependants.
- [ ] **6.8 Deductions** — CNSS, IPR on base salary only, union dues (`REM-03`, `Q9`).
- [ ] **6.9 Variable items intake** — pull validated absences, overtime, interims and promotions
  into the period (`REM-02`).
- [ ] **6.10 Payroll run** — compute every agent for a period; simulation before closing
  (`REM-09`).
- [ ] **6.11 Payslip PDF** — bilingual, per the model in section 7.6 (`REM-29` to `REM-31`).
- [ ] **6.12 Control report** — month-over-month variance per agent, each linked to its cause;
  unexplained variances block closing (`REM-12` to `REM-17`).
- [ ] **6.13 Bank transfer file** — one Excel file per bank (`REM-20`, `Q16`).
- [ ] **6.14 Retroactive adjustments** (`REM-06`).
- [ ] **6.15 Advances and loans** (`REM-05`).
- [ ] **6.16 Final settlement** on exit (`REM-08`).
- [ ] **6.17 Payroll registers and statutory reports** (`REM-19`, `REM-21`).
- [ ] **6.18 Parallel run** — two months compared with the official payroll before switching
  over.

## Milestone 7 — Social

- [ ] **7.1 Hospitals and providers** — reference data (`SOC-M-07`, `Q13`).
- [ ] **7.2 Tariff grid** — dated versions, import from Excel or CSV (`SOC-M-08` to `SOC-M-10`).
- [ ] **7.3 Care vouchers** — issued only to active agents and validated dependants
  (`SOC-M-01`, `SOC-M-02`).
- [ ] **7.4 Voucher printing** — with verification code (`SOC-M-03`).
- [ ] **7.5 Voucher lifecycle** — issued, used, invoiced, expired, cancelled (`SOC-M-04`).
- [ ] **7.6 Invoice entry and import** — line by line (`SOC-M-11`).
- [ ] **7.7 Invoice control** — match lines to vouchers and to the tariff grid; list anomalies
  (`SOC-M-12` to `SOC-M-14`).
- [ ] **7.8 Dispute statement and amount payable** (`SOC-M-15`, `SOC-M-16`).
- [ ] **7.9 Medical consumption reports** (`SOC-M-17`).
- [ ] **7.10 Ceilings and agent share** (`SOC-M-05`, `Q12`).

## Milestone 8 — Formation

- [ ] **8.1 Training catalogue and providers** (`FOR-03`).
- [ ] **8.2 Sessions and participants** (`FOR-04`).
- [ ] **8.3 Results and certificates** — shown in the agent's record (`FOR-05`, `FOR-07`).
- [ ] **8.4 Absence link** — training is not counted as unjustified absence (`FOR-06`).
- [ ] **8.5 Training plan and budget** (`FOR-01`, `FOR-02`, `FOR-09`).
- [ ] **8.6 Training statistics** (`FOR-10`).

## Milestone 9 — Cross-cutting and go-live

- [ ] **9.1 Document templates** — certificates and decisions generated from editable templates
  (`TRA-09`, `CAR-20`).
- [ ] **9.2 List builder and exports** — PDF and Excel (`TRA-06`, `TRA-07`).
- [ ] **9.3 Dashboard** — headcount, payroll mass, absenteeism, medical spend (`TRA-08`).
- [ ] **9.4 Hardening** — two-factor authentication, session timeout, account lockout
  (`NF-01`, `NF-02`).
- [ ] **9.5 Backups and restore test** (`NF-07`).
- [ ] **9.6 Production deployment** on ARPTC servers.
- [ ] **9.7 User training and manuals**.

## Later

- Agent self-service portal.
- Annual evaluations (`CAR-12`) and promotion eligibility lists (`CAR-13`).
- Other social benefits (`SOC-M-19`).

## Working rules

- One phase, one branch, one reviewable change.
- A phase is done when its tests pass and the quality gates in
  [`tech-stack.md`](tech-stack.md) are green.
- If a phase turns out larger than a few days, split it here before continuing.
- Reorder freely within a milestone; do not start a milestone before the one it depends on.
