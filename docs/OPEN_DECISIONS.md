# OPEN DECISIONS — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | OPEN_DECISIONS.md |
| Version | 1.5 |
| Date | 2026-11-18; Phase 7B correction recorded 2026-11-20; Phase 7B-1 retention decision recorded 2026-11-21; Phase 8A specification and Phase 7D owner acceptance recorded 2026-11-22; Phase 8B implementation recorded 2026-11-23 |
| Status | Business Profile scope corrected by Phase 7B; audit retention approved by Phase 7B-1; Phase 8A specification, authorization matrix, decisions, and hashing design approved 2026-11-22; explicit Phase 8B implementation authorization given 2026-11-22 and implemented 2026-11-23 (owner review pending) |
| Scope | All decisions requiring owner confirmation before business implementation, plus resolved constraints and deferred technical decisions |
| Related | BUSINESS_REQUIREMENTS.md, BUSINESS_WORKFLOWS.md, MODULE_SPECIFICATIONS.md, BUSINESS_RULES.md, REPORTING_REQUIREMENTS.md, DEVELOPMENT_ROADMAP.md, PHASE_07_OWNER_DECISION_WORKSHEET.md, PHASE_07_IMPLEMENTATION_READINESS.md, AUTHENTICATION_SPECIFICATION.md, AUTHORIZATION_MATRIX.md, USER_ACCOUNT_WORKFLOWS.md, SESSION_AND_IDLE_LOCK_SPECIFICATION.md, PHASE_08_OWNER_DECISION_WORKSHEET.md, PHASE_08_IMPLEMENTATION_READINESS.md |

## Phase 7B correction (authoritative)

Phase 7B resolves the profile-specific parts of B6-09 and B6-11: one active profile plus immutable version history, with mandatory `business_name`, `address`, `phone`, `email`, `footer_message`, and `logo`, and optional `secondary_phone`, `website`, and `registration_number`. Profile logo rules are PNG/JPG/JPEG, at most 5 MB, content-validated, and stored under `Logos/` by safe relative reference.

Durable profile audit events are implemented with actor `system/unauthenticated` and no ordinary audit UI. Phase 7B-1 resolves the retention part of Q-22: audit history is retained indefinitely with no automatic cleanup. Q-22 was fully resolved under Phase 8A (2026-11-22): Owner/Admin-only view and audited export, with all significant business, security, and admin events recorded. General attachment decisions also remain open. Earlier entries saying business name alone was mandatory, history was excluded, or logo/audit were excluded are superseded for this slice only.

## Phase 8A authentication specification (authoritative status)

Phase 8A produced documentation only. It is **not an implementation approval** and made no code, schema, migration, seed-user, backup, or owner-database change. The owner approved the high-level directions below on 2026-11-22: multiple local accounts, no cloud/remote auth, RBAC with exactly four role names (Owner/Admin, Operator, Accountant/Reviewer, Viewer), Owner/Admin full access, the Operator create/edit baseline with its listed denials, manual Owner/Admin password recovery, distinct password-change and administrative-reset audit events, 15-minute configurable idle lock with password unlock and lock/unlock audit events, service-layer permission enforcement, centralized permission definitions, and explicit first-run owner creation with no seed user.

Those approvals are recorded in `docs/AUTHENTICATION_SPECIFICATION.md` and `docs/AUTHORIZATION_MATRIX.md`. All detailed `P8A-xx` decisions, `Q-22` audit visibility, and `B6-10` approval policies are now resolved (2026-11-22; see §9 below and `docs/PHASE_08_OWNER_DECISION_WORKSHEET.md`). The owner explicitly approved the complete Phase 8A specification and authorization matrix on 2026-11-22 (documentation approval only). The owner approved the hashing design on 2026-11-22: Argon2id via `argon2-cffi` with `hashlib.scrypt` fallback. Final parameter review completed 2026-11-22: Argon2id values accepted and corrected scrypt fallback `N=2**17, r=8, p=1` (explicit `maxmem`) approved. Phase 7D owner acceptance was recorded 2026-11-22 in `Reports/PHASE_07D_ACCEPTANCE.md`, clearing B-1. The owner then explicitly authorized Phase 8B implementation on 2026-11-22; Phase 8B was implemented 2026-11-23 and remains pending owner review.

Owner decisions recorded 2026-11-22 (**`P8A-01` is now CLOSED**): login identity = **username only**; email is an optional contact field (therefore not mandatory for an account); username uniqueness is **case-insensitive** (e.g. `Ram`/`RAM`/`ram` cannot coexist); **username rename is Owner/Admin-only** (users cannot rename themselves). This closes account identity. Under `P8A-02`, owner decided 2026-11-22: **minimum password length = 8 characters**; **complexity requires at least one uppercase letter, one lowercase letter, and one digit**; and **failed logins trigger a temporary cooldown after 5 consecutive attempts for 15 minutes** (audited); **users may change their own password at any time** after verifying the current one (no forced first-login change). **Passwords do not expire.** This closes `P8A-02`. Under `P8A-03`, owner decided 2026-11-22: **multiple Owner/Admin accounts are allowed** on one installation (each admin's sensitive actions remain individually audited). An Owner/Admin **may deactivate another Owner/Admin**, with an audited event. The **last active Owner/Admin may not be deactivated (or downgraded)** — at least one active admin must always remain. User accounts are **deactivated only, never deleted**, preserving audit attribution; each user holds **exactly one role**. This closes `P8A-03`. Under `P8A-08`, owner decided 2026-11-22: an Owner/Admin **enters a new password (with confirmation) in an explicit dialog** for the reset; no generated temporary password. If all Owner/Admin credentials are unavailable, a **documented offline owner procedure** is followed (no in-app backdoor or recovery key). This closes `P8A-08`. Under `P8A-04`, owner decided 2026-11-22: Accountant/Reviewer may **view all financial records and reports** (including all financial reports). This grants viewing only. The owner then decided: **no create/edit of any records** — viewing only. The owner then decided **no approval or posting authority** for this role (no approval authority for this role; `B6-10` resolved with no approvals in v1). The owner then decided **full customer/supplier balance details are visible** to this role. The owner then decided **sensitive business settings are hidden** from this role. The owner then decided **no explicit review/verify action** — the role is strictly read-only. This closes `P8A-04`. Under `P8A-05`, owner decided 2026-11-22: Viewer may see **all modules in read-only mode**. The owner then decided **financial amounts and reports are hidden** from Viewer (read-only navigation does not expose financial figures/reports), and that **export is not permitted** and **print is not permitted**. The owner then decided **sensitive information is restricted** from Viewer. This closes `P8A-05`. Under `P8A-06`, owner decided 2026-11-22: Operator may create/edit records in **all day-to-day operational modules** (e.g. sales, purchases, inventory, parties, expenses), not accounting/financial records. The owner then decided **no delete or cancel** for Operator, **no approval or posting** (no approval authority for this role; `B6-10` resolved with no approvals in v1), and **no export or print**. This closes `P8A-06`. Under `P8A-07`, owner decided 2026-11-22: only **deliberate interaction with the application window** (keyboard/mouse input, navigation, explicit dialog/form interaction) resets the idle timer; internal timers, background work, log writes, redraws, and OS activity outside the app do not. The owner then decided the idle timeout **continues during modal dialogs** (an untouched dialog still locks). The owner then approved the **background-work split**: headless maintenance (e.g. scheduled backup) continues; in-process workers that could surface data are suspended until unlock; no background task writes business data on behalf of a locked user. The owner then decided **no hot switching**: a user must log out (ending the session) and log in as the other user; a 'Switch user' shortcut may perform that same logout+login sequence, keeping actor attribution and permission snapshots unambiguous. The owner then decided that **closing while locked ends the session and the next launch shows a fresh login** (no resume-locked-session path). The owner then approved the proposed settings-change rules: idle-timeout changes apply at the next activity reset (not retroactively); role/status and permission-definition changes apply at the next service-layer authorization check (deactivation immediately invalidates the session); password change/reset invalidates privileged re-auth state. This closes `P8A-07`. Under `Q-22`, owner decided 2026-11-22: **only Owner/Admin accounts may view audit history** (`audit.view`). The owner then decided audit history may be **exported by Owner/Admin only**, with each export recording an `audit.exported` event. The owner then decided to record **all significant business, security, and admin events**: sensitive/admin actions, authentication and account-lifecycle events, audit view/export events, and business record changes (create/edit/delete, approval/posting, financial adjustments). Existing historical rows (actor `system/unauthenticated`) remain unchanged. This closes `Q-22`. Under `B6-10`, owner decided 2026-11-22: **no approval workflow and no amount thresholds in v1**. No actions require approval; sensitive actions are performed directly by Owner/Admin (with auditing), and no role has approval/posting authority. This closes `B6-10`.

Prerequisite discrepancy was recorded when no Phase 7D acceptance existed; the owner later accepted Phase 7D on 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`), clearing B-1. Phase 8B implementation authorization was then given explicitly by the owner on 2026-11-22. Decisions were handled one essential question at a time; `P8A-01`–`P8A-08`, `Q-22`, and `B6-10` are all resolved. The complete specification and authorization matrix were explicitly approved 2026-11-22. Hashing design approved 2026-11-22 (Argon2id/`argon2-cffi`, scrypt fallback); parameter review complete and corrected scrypt fallback approved 2026-11-22. Phase 8B was implemented 2026-11-23 and is documented in `Reports/PHASE_08B_REPORT.md`; owner acceptance remains pending.

## 0. Decision handling rules

- Existing `Q-xx`, `AQ-xx`, and `SQ-xx` identifiers keep their meanings from project documentation.
- New Phase 6 business-discovery identifiers use `B6-xx`.
- **[RESOLVED]** means already confirmed or implemented; do not reopen casually.
- **[PROVISIONAL DEFAULT]** means a documented fallback only; it is **not owner approval**.
- **[OPEN]** means no implementation should proceed in that area until the owner decides.
- **[DEFERRED]** means the decision is real but not required before initial business modules.
- Recommendations below are justified planning options only. They do not replace owner approval.
- Once decided, record the outcome in an ADR or decision log with: decision ID, approved option, owner, date, affected documents, and resulting `BR-xx` rule changes.

## 1. Resolved constraints

| ID | Question | Decision / current status | Impact |
| --- | --- | --- | --- |
| Q-01 | Currency and decimals | [RESOLVED] INR, ₹, 2 decimals, Indian grouping | Money formatting and storage confirmed |
| Q-02 | Multi-currency buying/selling | [RESOLVED for v1] No; INR only | Single-currency schema and calculations |
| Q-11 | Fiscal year start | [RESOLVED] 1 April, April–March | Periods, numbering, reports |
| Q-12 | Multiple branches/warehouses | [RESOLVED for v1] No | No branch/warehouse dimension in initial business modules |
| AQ-01 | Final Python build target | Phase 1 resolved CPython 3.14.6; final release target re-confirmed at packaging | Technical, deferred to packaging |
| AQ-07 | ReportLab version | [RESOLVED] 5.1.0 smoke-tested on Python 3.14.6 | PDF generation dependency |
| AQ-08 | pytest-qt adoption | [RESOLVED] Not adopted; offscreen Qt tests suffice | Test tooling |

## 2. Core business decisions blocking Phase 7+

| ID | Decision needed | Why it matters | Existing default / recommendation | Alternatives and consequences | Blocks | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q-03 | Tax model: none, inclusive, exclusive, GST-like components, rates, per line/invoice | Drives invoice math, document layout, purchase/expense handling, reports | Default says no tax in v1; recommend confirming with owner/accountant before billing modules | No tax is simplest but may not match legal/business need; multiple components need rate/rounding rules and stronger reports | Invoices, purchases, expenses, tax reports, P&L | [OPEN] |
| Q-04 | Single user vs multiple users with login/roles | Affects auth, permissions, audit actor, approval workflows, schema | Phase 8A: multiple local accounts with RBAC approved at high level 2026-11-22; all detailed `P8A-xx`, `Q-22`, and `B6-10` decisions resolved | Multi-user requires secure credentials, role tests, concurrency policy, and an approved specification | All modules if roles are needed; audit and approvals | [RESOLVED — Phase 8A specification/matrix approved 2026-11-22; Phase 8B implemented 2026-11-23, owner review pending] |
| Q-05 | Inventory valuation method | Affects stock value, COGS, profit reports | Default: weighted average (provisional); requires owner/accountant decision | FIFO, weighted average, standard cost, or no inventory valuation; changing later requires careful period handling | Inventory, purchase/sales stock postings, P&L | [OPEN] |
| Q-06 | Negative stock allowed? | Affects validation and adjustment workflow | Default: block by default; recommend blocking if stock is tracked | Allow with warning/approval requires audit and exception reports | Sales, inventory, returns | [OPEN] |
| Q-07 | Exact services/products and units | Affects catalogue, price basis, invoice lines, reports | Default: goods + services with units; exact catalogue unresolved | Fixed price, pieces, area, hours, rolls, custom quotes; each changes fields and calculations | Catalogue, invoices, pricing, item reports | [OPEN] |
| Q-08 | Discounts and rounding policy | Affects invoice totals and golden-value tests | Default: line discount, half-up rounding; provisional only | Line/document/both; fixed/percent; before/after tax; different rounding points | Invoices, quotations, tax reports | [OPEN] |
| Q-09 | Credit sales, partial payments, advances, payment methods, allocation, balances | Drives receivables/payables and statements | Default: yes credit; cash/bank/mobile; details unresolved | Full vs partial, invoice-specific vs customer-level allocation, advances, overpayments, refunds | Invoices, payments, statements, dashboard | [OPEN] |
| Q-10 | Document numbering and reset policy | Affects uniqueness, audit, fiscal-year handling | Default: `INV-YYYY-000001`, yearly reset; provisional only | Prefix per type, continuous vs yearly reset, separate sequences for quotes/bills/payments | All numbered documents | [OPEN] |
| Q-13 | Quotations, sales orders, delivery notes in v1? | Changes sales/job workflow scope | Default: not in v1; recommend confirming before job design | None, quotes only, orders only, delivery notes only, all; each adds documents/statuses | Jobs, quotations, delivery, reporting | [OPEN] |
| Q-14 | Sales/purchase returns, voids, refunds, credit notes | Affects posted records, stock, payments, tax, audit | Default: not in v1; provisional only | Void drafts only, credit notes, refunds, stock reversals, negative invoices | Corrections, returns, refunds, reports | [OPEN] |
| Q-15 | Accounting depth | Determines financial reports and reconciliation | Default: summary ledger first; recommend for v1 if statutory accounting is out of scope | Simple summaries, double-entry-style ledger, statutory-ready accounting; last is out of scope | Accounting, P&L, trial balance, reports | [OPEN] |
| Q-16 | Existing data to import | Affects cutover and validation tooling | Default: none; recommend starting fresh unless real data must be carried over | Manual opening balances only; spreadsheet import; legacy software import | Opening balances, import tooling, cutover | [OPEN] |
| Q-17 | Required print formats | Affects report/export design | Default: A4 invoice + statement; recommend A4 first | A4 only, receipt/thermal, custom sizes; thermal is AQ-06 | Invoice/statement/reports, packaging | [OPEN] |

## 3. New Phase 6 business-discovery decisions

| ID | Decision needed | Why it matters | Recommendation / provisional view | Alternatives and consequences | Blocks | Status |
| --- | --- | --- | --- | --- | --- | --- |
| B6-01 | Exact graphics/printing service catalogue and pricing basis | Prevents generic retail assumptions | No pricing basis may be assumed; owner examples required | Fixed service price, quantity × rate, area/page/hour/unit-based, custom quote; changes catalogue and invoice math | Catalogue, jobs, invoices, reports | [OPEN] |
| B6-02 | Whether job/work-order tracking is needed | A graphics business may need job-level traceability | Planning assumption only; no lifecycle approved | No jobs, simple open/closed, multi-stage workflow; each changes UI and permissions | Jobs module and job reports | [OPEN] |
| B6-03 | Internal service/production stages and completion rule | Defines when work is “done” and when revenue may be recognized | No stages approved; do not assume design/proof/print/finish | None, simple status, explicit stages; affects reports and approvals | Jobs, revenue reports, dashboard | [OPEN] |
| B6-04 | Delivery/dispatch tracking | Determines whether delivery notes/statuses are needed | No delivery workflow confirmed | No tracking, note reference, delivery status, separate dispatch document | Jobs, invoices, reports | [OPEN] |
| B6-05 | Walk-in customers and customer identity on sales | Affects customer master and sales validation | No policy approved | Always named customer, allow generic walk-in, per-invoice walk-in details; affects statements | Sales invoices and customer reports | [OPEN] |
| B6-06 | Purchase workflow: direct bill vs purchase order vs receipt | Affects purchase documents and approvals | No workflow approved | Direct bill is simplest; PO/receipt adds traceability and statuses | Purchases, inventory, approvals | [OPEN] |
| B6-07 | Whether inventory/consumables are in scope | A graphics business may not need stock control | Confirm before designing inventory | No stock, consumables only, goods for resale, both; affects schema and reports | Inventory, stock postings, stock reports | [OPEN] |
| B6-08 | Opening balances, advances, and cutover treatment | Determines starting balances and statement accuracy | Recommend entering reviewed opening balances only if history is needed; start fresh otherwise | No balances, manual opening balances, imported history; advances need separate decision | Payments, statements, P&L, reports | [OPEN] |
| B6-09 | Business profile fields for printed documents | Affects invoice/statement headers and compliance-looking output | Approved for the first module only: business name mandatory; address, phone, email, website, registration number, footer message optional; tax/logo/bank excluded | Tax fields still require Q-03; logo/file storage still requires Q-24 | Print/PDF documents | [APPROVED FOR FIRST MODULE ONLY — 2026-11-20 owner continuation instruction; broader document-header policy still open] |
| B6-10 | Approval policies and thresholds | Needed for discounts, voids, refunds, expenses, stock adjustments | Owner decided 2026-11-22: no approval workflow and no amount thresholds in v1; Owner/Admin performs sensitive actions directly with auditing; no role has approval/posting authority | — | Permissions, workflows, audit | [RESOLVED 2026-11-22] |
| B6-11 | Historical document display and master-record archival behavior | Needed to preserve history without hard deletes | First business-profile record is single-record/no-history; document display policy remains unapproved | Show original snapshot, show current master data, show both, hide voided records | Invoices, statements, audit, reports | [OPEN for documents; FIRST-MODULE PROFILE RULE APPROVED 2026-11-20] |
| B6-12 | Dashboard metric definitions | Prevents fake or misleading dashboard numbers | Keep business metrics hidden until source rules are approved | Sales, collections, receivables, payables, expenses, jobs, stock value | Dashboard business metrics | [OPEN] |
| B6-13 | Master-data required fields and duplicate policy | Needed before customer/supplier/catalogue implementation | Phase 9 (2026-11-23, owner approved as proposed): **Customers/Suppliers** required=`name`; optional=`phone,email,address,contact_person,notes,is_active`; duplicate rule=warn on possible duplicate, allow save after explicit confirmation; duplicate match=case-insensitive normalized name, also warn on matching phone for existing active record when phone provided; activate/deactivate=yes; delete=deactivate-only in normal UI (no hard delete). Phase 10 (2026-11-24, owner approved step-by-step): **Catalogue (Products/Services)** shared table with `kind=product|service`; required=`name`; optional=`description,unit,default_sale_price_minor(reference INR paise integer, no tax/discount/stock calculation),is_active`; category/code/SKU/managed masters not included in this slice; duplicate rule=warn on case-insensitive normalized name within same kind; save only after explicit confirmation; activate/deactivate=yes; delete=deactivate-only in normal UI (no hard delete); permissions=`catalogue.view/create/edit` with Owner/Admin+Operator view/create/edit and Accountant/Reviewer+Viewer view-only. Broader catalogue decisions (categories, codes/SKU, managed units, tax/pricing rules, stock/variants/barcodes) remain open. | Name-only, contact-required, tax-ID uniqueness, phone/email duplicate checks | Customers, suppliers, catalogue | [PARTIALLY RESOLVED — Phase 9 customers/suppliers approved 2026-11-23; Phase 10 catalogue minimal master slice approved 2026-11-24; broader catalogue decisions still OPEN] |

## 4. Security, data-protection, and packaging decisions

| ID | Decision needed | Why it matters | Existing default / recommendation | Alternatives and consequences | Blocks | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q-18 / AQ-04 | Encryption at rest / SQLCipher | Key recovery and restore risk; data safety expectations | No in-app encryption; recommend BitLocker + offline backup copy. AQ-04 open before schema freeze | OS-level encryption only; SQLCipher requires key management, migration/backup complexity | Packaging, security claims, future schema freeze | [OPEN / DEFERRED] |
| Q-19 / AQ-03 | Code-signing certificate | Installer SmartScreen warnings and trust | Default: no certificate; document SmartScreen handling | Purchase certificate and sign EXE/installer; affects packaging budget | Final packaging/release | [DEFERRED] |
| Q-20 | Bengali/bilingual UI | Affects UI labels, report headers, document templates, and tests | Default: English only; provisional | English only, Bengali, bilingual; affects translation and export layout | UI, reports, document output | [OPEN] |
| Q-21 | Off-site/second-device backup requirement | Disaster recovery expectation | Manual periodic copy recommended; no cloud requirement | Manual copy, external drive rotation, automatic second destination; no cloud in v1 | Backup UX, release guidance | [OPEN] |
| Q-22 | Audit visibility and future event scope | Accountability and who may see audit data | Retention is indefinite (Phase 7B-1); Owner/Admin-only view and audited export; all significant business, security, and admin events recorded (2026-11-22) | No retention period is allowed; historical `system/unauthenticated` rows unchanged | Audit module, permissions | [RESOLVED 2026-11-22] |
| Q-23 | Barcode scanning | Product/UI scope | Default: no | No scanning; manual code entry; scanner support; affects catalogue and sales UI | Catalogue/Sales enhancements | [DEFERRED] |
| Q-24 | Attachment types and size limits | Storage/backup size and safety | Default: PDF/JPG/PNG, 10 MB each; provisional | No attachments; file links; stored copies; type/size policy; backup inclusion | Attachments, receipts, artwork/proofs | [OPEN] |
| Q-25 | Automatic backups to second destination | Backup runner complexity and failure policy | Default: no; manual extra copy | Single destination; second local/external destination; affects failure semantics | Backup runner enhancements | [DEFERRED] |
| Q-26 | Warn/exit if no verified backup for N days | Backup discipline vs user interruption | Default: warn after 7 days; provisional | No warning; warn; block business entry; affects UX policy | Backup UX policy | [OPEN] |
| AQ-02 | Per-user or per-machine install | Installer and data-root defaults | Open for packaging | Per-user simpler; per-machine may need elevated install and shared program files | Final packaging | [DEFERRED] |
| AQ-05 | Authentication/roles in v1 | Duplicates Q-04 from architecture view | Phase 8A prepared the specification; high-level multiple-account RBAC direction approved 2026-11-22, aligned with Q-04 | Single user vs login/roles | All role-dependent modules | [RESOLVED — Phase 8B implemented 2026-11-23, owner review pending] |
| AQ-06 | Thermal receipt printing | Print layout and device handling | Open; A4 first default | A4 only; receipt printers; affects report/export design | Print/export phase | [DEFERRED] |
| SQ-01 | Idle-lock when no login is used | Physical security policy | Phase 8A approved 15-minute configurable idle lock with password unlock and lock/unlock audit events as part of local accounts; the no-login variant is superseded; edge cases `P8A-07` resolved 2026-11-22 | No lock; idle lock without login | Security UX | [RESOLVED — Phase 8B implemented 2026-11-23] |
| SQ-02 | Support-bundle export feature | Supportability vs privacy | Not in v1 | No bundle; sanitized diagnostics bundle | Support tooling | [DEFERRED] |
| SQ-03 | Password reset recovery procedure if auth | Only needed if Q-04/AQ-05 approves auth | Phase 8A approved manual Owner/Admin recovery (no self-service/email/OTP) with distinct change vs reset audit events; administrator-entered new-password procedure and documented offline owner procedure for total lockout decided (`P8A-08`) | Self-service reset, owner-managed reset, no auth | Auth implementation | [RESOLVED — audited admin reset implemented in Phase 8B; offline owner procedure remains documentation] |

## 5. Out-of-scope unless owner reopens product scope

| Area | Current status | Decision required to reopen |
| --- | --- | --- |
| Cloud sync / remote API / web client | [OUT OF SCOPE] | New product-scope decision and architecture review |
| Multi-computer live database sharing | [OUT OF SCOPE] | New concurrency/data architecture decision |
| Multi-company / multi-tenant | [OUT OF SCOPE] | New product-scope decision |
| Multi-branch / warehouse | [OUT OF SCOPE] | Reopen Q-12 |
| Payroll, MRP, CRM campaigns, e-commerce | [OUT OF SCOPE] | New product-scope decision |
| Statutory accounting/tax filing certification | [OUT OF SCOPE] | Reopen Q-03/Q-15 with compliance requirements |
| Custom report designer | [OUT OF SCOPE] | New product-scope decision |
| Barcode scanning | [DEFERRED] | Reopen Q-23 |
| Built-in SQLite/database encryption | [DEFERRED] | Reopen Q-18/AQ-04 with key-management plan |

## 6. Decision-to-module impact summary

| Decision group | Modules blocked |
| --- | --- |
| Q-03, Q-08, Q-10, B6-09 | Invoices, quotations, printable documents, tax/discount reports |
| Q-04, AQ-05, Q-22, B6-10 | Roles, approvals, audit visibility, protected reports |
| Q-05, Q-06, B6-07 | Inventory, stock postings, stock reports, P&L |
| Q-07, B6-01, B6-13 | Catalogue, pricing, customer/supplier masters, item reports |
| Q-09, B6-05, B6-08 | Payments, receivables, payables, statements, dashboard balances |
| Q-13, B6-02, B6-03, B6-04, B6-06 | Quotations, jobs, delivery, purchase-order workflow |
| Q-14, B6-11 | Voids, returns, refunds, corrections, historical display |
| Q-15, Q-16, B6-12 | Accounting, P&L, trial balance, imports/opening balances, dashboard |
| Q-17, AQ-06 | Print/PDF/Excel and receipt formats |
| Q-18, Q-21, Q-24, Q-25, Q-26, AQ-04 | Security claims, backup UX, attachments, packaging |

## 7. Minimum owner review for Phase 7

Before any business implementation starts, the owner should confirm at least:

1. Q-03 tax model.
2. Q-04 user/role model.
3. Q-07/B6-01 service catalogue and pricing basis.
4. Q-08 discounts and rounding.
5. Q-09 credit/payment/allocation behavior.
6. Q-10 numbering.
7. Q-13/Q-14 document and correction scope.
8. B6-02 job/work-order scope.
9. B6-07 inventory applicability.
10. B6-09 business profile fields.
11. B6-13 master-data fields and duplicate policy.

If any remain open, the next phase should limit itself to modules whose rules are fully decided.

## 8. Phase 7 traceability notes

- Phase 7 prepared `docs/PHASE_07_OWNER_DECISION_WORKSHEET.md`, `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`, and `docs/PHASE_07_IMPLEMENTATION_READINESS.md`.
- The 2026-11-20 continuation instruction approved only the minimal first-module scope recorded in §1/B6-09, G3, and I1. No other unanswered decision is approved, resolved, or downgraded by Phase 7 or Phase 7A.
- `Q-20` was added to this register for traceability because it is referenced in Phase 6 documents but was previously missing here. Its documented English-only default remains a provisional default, not owner approval.
- Worksheet traceability:
  - Group A: `Q-03`, `Q-08`, `Q-09`, `Q-13`, `Q-14`.
  - Group B: `Q-04`, `AQ-05`.
  - Group C: `Q-07`, `B6-01`.
  - Group D: `Q-10`.
  - Group E: `B6-02`.
  - Group F: `B6-07`.
  - Group G: `B6-09`.
  - Group H: `B6-13`.
  - Group I: `B6-11`, `Q-22` as first-module behavioral decisions.
  - Group J: remaining open/deferred decisions for full register coverage.
- ID namespace note: `BR-C-xx` is used locally in `BUSINESS_REQUIREMENTS.md` for confirmed technical constraints and in `BUSINESS_RULES.md` for confirmed business rules. When citing a `BR-C-xx` ID, include the document name to avoid ambiguity.
- First-module readiness was reassessed on 2026-11-20 after the owner's written continuation instruction. B6-09, one-profile/single-record/no-history behavior, B6-11 for the first profile slice, and the first-module specification are approved for that slice only.
- The continuation instruction did not approve Q-03, Q-04, Q-07/B6-01, Q-08, Q-09, Q-10, Q-13/Q-14, B6-02, B6-07, B6-13, or any other open decision. Those remain open for later modules. Phase 8A subsequently resolved Q-04 for authentication (multiple local accounts + RBAC, with all detailed `P8A-xx` decisions, `Q-22`, and `B6-10` approved 2026-11-22), but that does not approve unrelated open business decisions.

## 9. Phase 8A authentication decisions (new IDs)

These IDs were introduced by Phase 8A. Each is **OPEN** unless marked otherwise in the table; a recommendation in the worksheet is not an approval. Owner decisions are made one essential question at a time; `P8A-01` is resolved. Record each answer here with owner and date before implementation.

| ID | Decision | Status | Related existing ID |
| --- | --- | --- | --- |
| P8A-01 | Account identity: username, email, or both; uniqueness/case; mandatory email; username changes | [RESOLVED 2026-11-22 — username only; email optional/not mandatory; case-insensitive uniqueness; Owner/Admin-only rename] | Q-04, AQ-05 |
| P8A-02 | Password policy: length, complexity, failed-login throttling, change policy, expiration | [RESOLVED 2026-11-22 — min length 8; uppercase + lowercase + digit; cooldown after 5 attempts/15 min; change any time; no expiration] | Q-04 |
| P8A-03 | User administration: multiple admins, disabling other/last admin, delete vs deactivate, role cardinality | [RESOLVED 2026-11-22 — multiple admins allowed; admin may disable another (audited); last active admin cannot be deactivated; deactivate only, never deleted; exactly one role per user] | Q-04 |
| P8A-04 | Accountant/Reviewer exact permission scope (proposed baseline not approved) | [RESOLVED 2026-11-22 — strictly read-only: view all financial records/reports and full balances; no create/edit, approval/posting, review/verify action, or sensitive settings] | Q-04, B6-10 |
| P8A-05 | Viewer permission scope (role name approved, permissions not) | [RESOLVED 2026-11-22 — all modules visible read-only; financial amounts/reports and sensitive information hidden; no export or print] | Q-04 |
| P8A-06 | Operator module-specific sensitive permissions: create/edit scope, delete/cancel, approve/post, export/print | [RESOLVED 2026-11-22 — create/edit across all day-to-day operational modules; no delete/cancel, approval/posting, or export/print] | Q-04 |
| P8A-07 | Session/locking edge cases: activity definition, modal dialogs, background tasks, user switching, close while locked, settings effects | [RESOLVED 2026-11-22 — deliberate app-window interaction resets timer; modal timeout continues; background split; logout+login only; fresh login after close; settings rules approved] | SQ-01 |
| P8A-08 | Administrative reset procedure and behavior when all Owner/Admin credentials are unavailable | [RESOLVED 2026-11-22 — admin enters a new password with confirmation in an explicit dialog; no generated temporary password; documented offline owner procedure for total admin lockout; no in-app backdoor/recovery key] | SQ-03 |

Traceability: `docs/PHASE_08_OWNER_DECISION_WORKSHEET.md` documents all options and the one-question-at-a-time process; `docs/PHASE_08_IMPLEMENTATION_READINESS.md` records these decisions and the Phase 7D acceptance history (discrepancy recorded, then cleared by owner acceptance). `Q-22` is resolved (Owner/Admin-only audit view and audited export; all significant business, security, and admin events recorded) and `B6-10` is resolved (no approvals or thresholds in v1). The owner explicitly approved the complete Phase 8A specification and authorization matrix on 2026-11-22 (documentation only). Hashing design was approved 2026-11-22 (Argon2id/`argon2-cffi`, scrypt fallback); the final parameter review is complete and the corrected scrypt fallback was approved 2026-11-22. Phase 7D was accepted by the owner on 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`); Phase 8B remains gated by explicit owner authorization.
