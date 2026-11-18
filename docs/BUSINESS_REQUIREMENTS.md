# BUSINESS REQUIREMENTS — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | BUSINESS_REQUIREMENTS.md |
| Version | 1.0 |
| Date | 2026-11-18 |
| Status | Phase 6 planning output — proposed business blueprint; owner review pending |
| Scope | Product scope, business objectives, requirement classification, proposed and out-of-scope items |
| Related | BLUEPRINT.md, ARCHITECTURE.md, DATABASE_SCHEMA.md, UI_UX_BLUEPRINT.md, BUSINESS_WORKFLOWS.md, MODULE_SPECIFICATIONS.md, BUSINESS_RULES.md, REPORTING_REQUIREMENTS.md, OPEN_DECISIONS.md |

## 0. Status labels

- **[CONFIRMED]** — already recorded in approved project documentation or implemented by Phases 1–5.
- **[PROPOSED]** — a planning recommendation for owner consideration; not approved for implementation.
- **[REQUIRES OWNER CLARIFICATION]** — a decision is needed before a reliable requirement can be written.
- **[OUT OF SCOPE]** — explicitly excluded from the current product scope or current phase.
- Existing `Q-xx`, `A-xx`, and `AQ-xx` identifiers retain their meanings from `docs/BLUEPRINT.md`, `docs/DATABASE_SCHEMA.md`, and `docs/ARCHITECTURE.md`. New Phase 6 discovery identifiers use `B6-xx`.

A **[PROPOSED]** requirement must not be treated as approved merely because it appears in this document.

## 1. Purpose of this document

This document defines the business scope of Gobindas Graphics Business Management System before any business module is implemented. It separates confirmed product constraints from operational areas that are merely proposed or still unclear. It is a planning output of Phase 6 only.

## 2. Product scope

### 2.1 Confirmed product context

- **[CONFIRMED]** The product is a standalone, offline-first Windows desktop application for Gobindas Graphics, described in existing documentation as a small graphics/printing business (`BLUEPRINT.md` §1.1).
- **[CONFIRMED]** The exact service catalogue of the business is not confirmed (`BLUEPRINT.md` §1.1, Q-07).
- **[CONFIRMED]** The application runs without a browser, server, network API, cloud account, or web dashboard.
- **[CONFIRMED]** The application uses one local SQLite database selected by the user at first launch.
- **[CONFIRMED]** The database path is absolute, explicit, and never defaulted, guessed, silently switched, or created on startup by normal GUI use.
- **[CONFIRMED]** No multi-computer sharing of the live SQLite database is supported; UNC and mapped network locations are refused.
- **[CONFIRMED]** Backup, restore, relocation, and scheduled backup infrastructure exist and must be preserved.
- **[CONFIRMED]** The current build has no business tables, business records, seed data, authentication, business profile, customers, suppliers, products, sales, purchases, inventory, accounting, expenses, or reports.
- **[CONFIRMED]** Current navigation contains real Dashboard and Backup surfaces; Sales, Purchases, Inventory, Customers, Suppliers, Expenses, Accounting, Reports, and Settings are honest `PlaceholderView` pages defined by `NAVIGATION_GROUPS` in `app/ui/main_window.py`.

### 2.2 Confirmed technical and financial constraints

| ID | Requirement | Status |
| --- | --- | --- |
| BR-C-01 | Python, PySide6/Qt Widgets, SQLAlchemy 2, Alembic, Pydantic, SQLite | [CONFIRMED] |
| BR-C-02 | Modular monolith: presentation, application services, domain, infrastructure | [CONFIRMED] |
| BR-C-03 | Business rules remain independent of PySide6 | [CONFIRMED] |
| BR-C-04 | Decimal-based calculations; integer paise persistence; no float for money | [CONFIRMED] |
| BR-C-05 | Default currency INR, symbol ₹, 2 decimals, Indian grouping | [CONFIRMED] Q-01 |
| BR-C-06 | Fiscal year starts 1 April (April–March) | [CONFIRMED] Q-11, `DATABASE_SCHEMA.md` §5 |
| BR-C-07 | Alembic is the only schema-change mechanism; baseline `0001_baseline` has no application tables | [CONFIRMED] |
| BR-C-08 | Normal startup never migrates automatically; maintenance upgrades require the verified safety-backup gate | [CONFIRMED] |
| BR-C-09 | Backups use the SQLite Online Backup API and are verified before publish | [CONFIRMED] |
| BR-C-10 | Restore is staged, verified, lock-protected, and rollback-aware | [CONFIRMED] |
| BR-C-11 | Light and dark UI foundation is complete and must not be redesigned | [CONFIRMED] |
| BR-C-12 | Status uses text, shape, and accessible names; no color-only meaning | [CONFIRMED] |

## 3. Business objectives

### 3.1 Confirmed objectives from existing product documentation

- **[CONFIRMED]** Run natively on Windows without a server or browser (G-01).
- **[CONFIRMED]** Work fully offline (G-02).
- **[CONFIRMED]** Keep business data under the owner's control (G-03).
- **[CONFIRMED]** Protect data against loss and corruption using verified backups and guarded restore (G-04).
- **[CONFIRMED]** Be fast and pleasant for daily data entry (G-05).
- **[CONFIRMED]** Survive future growth through a modular monolith and versioned schema (G-06).
- **[CONFIRMED]** Be installable without Python knowledge through PyInstaller and Inno Setup (G-07; packaging remains a later roadmap item).

### 3.2 Proposed business-specific objectives

- **[PROPOSED]** Record the businesses customers and suppliers actually deal with, without assuming a generic retail workflow.
- **[PROPOSED]** Record graphics/printing jobs or work orders if the owner confirms that job tracking is needed.
- **[PROPOSED]** Issue invoices and record payments against the correct customer, job, or document, subject to owner decisions.
- **[PROPOSED]** Record purchases and supplier payments, subject to owner decisions.
- **[PROPOSED]** Record expenses with enough classification for basic profitability reporting.
- **[PROPOSED]** Track inventory or consumables only if the owner confirms that stock is held and must be managed.
- **[PROPOSED]** Produce operational and financial reports that reconcile to stored business documents.
- **[PROPOSED]** Preserve audit history for financially significant actions, with retention and visibility to be decided.

## 4. Business area classification

| Area | Classification | Rationale / next action |
| --- | --- | --- |
| Customer management | [PROPOSED] | Eventual v1 scope in `BLUEPRINT.md` §5.1; fields, numbering, balances, and statements require approval before implementation. |
| Supplier management | [PROPOSED] | Eventual v1 scope in `BLUEPRINT.md` §5.1; fields and balance rules require approval. |
| Product and service catalogue | [PROPOSED] | Eventual v1 scope; exact services, units, and pricing basis are unresolved (Q-07, B6-01). |
| Quotation and estimates | [REQUIRES OWNER CLARIFICATION] | Provisional default is “not in v1” (Q-13). Owner must confirm whether quotations exist before invoicing. |
| Customer orders | [REQUIRES OWNER CLARIFICATION] | Not defined in approved documentation. Could be part of job booking if the owner confirms. |
| Job/work order management | [REQUIRES OWNER CLARIFICATION] | Likely relevant to a graphics business, but no lifecycle, fields, statuses, or approval rules exist. |
| Production or service execution | [REQUIRES OWNER CLARIFICATION] | Only applicable if the business tracks internal stages such as design, proofing, printing, finishing, or dispatch. |
| Delivery and dispatch | [REQUIRES OWNER CLARIFICATION] | Delivery notes/order notes are part of Q-13 default “not in v1”; delivery tracking not otherwise confirmed. |
| Invoicing and billing | [PROPOSED] | `BLUEPRINT.md` §6.3 describes daily sales entry as provisional; tax, discount, credit, and return rules are open. |
| Payment collection | [PROPOSED] | Sales payments and customer balances are in the proposed entity map; allocation and overpayment rules are open. |
| Expenses | [PROPOSED] | Eventual v1 scope; categories, payment methods, attachments, and posting effects need approval. |
| Purchases | [PROPOSED] | `BLUEPRINT.md` §6.4 describes provisional purchase entry; supplier payment and return rules need approval. |
| Inventory and stock | [REQUIRES OWNER CLARIFICATION] | Assumption A-11 allows goods and services, but a graphics business may not need stock control. Confirm scope before designing valuation or negative-stock rules. |
| Business reports | [PROPOSED] | Eventual v1 scope; report definitions and metric rules require approval. No fake metrics may be introduced. |
| User access and permissions | [REQUIRES OWNER CLARIFICATION] | Q-04 is open. Authentication and roles are conditional and are not part of Phase 6 implementation. |
| Business settings | [PROPOSED] | Eventual v1 scope; profile fields, numbering defaults, and financial defaults require approval. |
| Audit trail | [PROPOSED] | Listed as eventual v1 scope, but event list, retention, visibility, and actor model are not approved. |
| Import from existing records | [REQUIRES OWNER CLARIFICATION] | Q-16 is open. No importer may be built without a confirmed source, mapping, and validation policy. |
| Barcode scanning | [REQUIRES OWNER CLARIFICATION] | Q-23 default is no; no barcode workflow is confirmed. |
| Bengali/bilingual UI | [REQUIRES OWNER CLARIFICATION] | Q-20 default is English only; no localization requirement is confirmed. |

## 5. Confirmed requirements

### 5.1 Technical requirements

All constraints in `Prompt/PHASE 06 — BUSINESS REQUIREMENTS, WORKFLOWS & MODULE PLANNING.md` §2 are **[CONFIRMED]** and must not be reopened without explicit owner approval. They include the stack, modular-monolith layering, offline-first data control, INR financial conventions, and the completed Phase 5 UI foundation.

### 5.2 Implemented system workflows

The following workflows are **[CONFIRMED]** as implemented and verified by automated tests in Phases 1–5:

1. First-launch setup with `SETUP_REQUIRED`, `RECOVERY_REQUIRED`, and `READY` startup classification.
2. Data-root validation, additive folder scaffolding, database creation through `MigrationManager.create_database()`, and atomic configuration persistence.
3. Blocking recovery for missing drive, corrupt config, incomplete config, invalid database identity, or unsupported revision.
4. Verified manual and scheduled backups using the SQLite Online Backup API.
5. Backup history, sidecar metadata, verification status, and retention for managed automatic backups.
6. Staged restore with eligibility checks, safety backup, runtime shutdown, replacement, reopen verification, and rollback.
7. Verified database relocation with atomic config update and preservation of the old data root.
8. Pre-upgrade safety-backup gate for maintenance schema changes; normal startup still refuses unsafe schema states.

These are data-protection workflows, not business transaction workflows.

### 5.3 Confirmed business conventions

- **[CONFIRMED]** Default currency is INR with 2 decimal places and Indian grouping.
- **[CONFIRMED]** Money must be calculated with `Decimal` and persisted as integer minor units (paise); `float` is prohibited.
- **[CONFIRMED]** Fiscal year start is 1 April.
- **[CONFIRMED]** Business data remains local and under the owner's chosen folder location.
- **[CONFIRMED]** Posted financial records must not be silently hard-deleted; this is a documented schema principle in `DATABASE_SCHEMA.md` §1, although the exact void/cancellation workflow remains unapproved.

## 6. Proposed requirements

### 6.1 Master data (proposed)

- Create, view, search, edit, and deactivate customers and suppliers.
- Maintain product/service records with categories, units, active status, and optional price defaults.
- Store business profile information needed for printed documents and reports.
- Preserve history when a master record is referenced by a financial document; prefer deactivation over deletion.

All field lists, duplicate rules, and validation messages require owner approval before implementation.

### 6.2 Job and service operations (proposed, requires clarification)

- Record a customer job or work request if the owner confirms the need.
- Capture the work description, linked customer, dates, status, and related documents.
- Link estimates, invoices, attachments, and delivery information to the job where applicable.
- Do not assume manufacturing, retail, or bookshop workflow stages.

Lifecycle stages and permissions are unresolved (`B6-02`, `B6-03`, `B6-04`).

### 6.3 Sales and billing (proposed)

- Select a customer or walk-in customer, subject to approval.
- Add products/services or job lines with quantity, unit price, discounts, and tax, if applicable.
- Calculate totals using approved domain rules.
- Issue an invoice and optionally print/export it.
- Record customer payments and show outstanding balances.

Pricing, discounts, tax, numbering, credit sales, partial payments, refunds, and cancellations are **not** approved (`Q-03`, `Q-08`, `Q-09`, `Q-10`, `Q-14`, `B6-05`, `B6-08`).

### 6.4 Purchases (proposed)

- Record supplier bills and bill lines.
- Record supplier payments and outstanding payables.
- Link purchases to inventory or expenses only after the owner confirms posting rules.

Purchase returns, supplier payment allocation, and tax treatment are unresolved.

### 6.5 Expenses (proposed)

- Record business expenses with date, category, payee, amount, payment method, reference, notes, and optional attachment metadata.
- Classify expenses for basic profitability reporting.
- Preserve receipts/attachments according to the approved attachment policy.

Expense account mapping and accounting depth are unresolved (`Q-15`, `Q-24`).

### 6.6 Inventory (conditional proposal)

- Track stock movements only if the owner confirms that goods/consumables are held.
- Maintain an append-only stock movement ledger if inventory is in scope.
- Define valuation, negative-stock behavior, opening stock, and adjustments only after owner decisions.

No stock posting rule may be selected by implication from a generic retail or manufacturing workflow (`Q-05`, `Q-06`, `B6-07`).

### 6.7 Reporting (proposed)

- Provide operational reports for transactions, parties, and stock if those modules are implemented.
- Provide financial reports for receivables, payables, expenses, profit and loss, and trial balance according to the approved accounting depth.
- Provide PDF and Excel export using the existing approved libraries.
- Define dashboard metrics only after report definitions are approved.

No report definition may depend on an unapproved rule such as a tax model, valuation method, or revenue-recognition policy.

### 6.8 Business settings (proposed)

- Maintain business identity fields for documents.
- Maintain numbering configuration per document type and fiscal year.
- Maintain financial defaults once approved.
- Keep machine configuration outside the business database as already implemented; any database-backed business settings require a separate approved decision.

### 6.9 Audit and history (proposed)

- Record financially significant actions in an append-only audit trail.
- Link audit events to correlation IDs from diagnostic logs.
- Make audit history visible for a record where permissions allow.
- Define retention, redaction, and actor identity before implementation (`Q-04`, `Q-22`).

## 7. User access and permissions

- **[REQUIRES OWNER CLARIFICATION]** Whether the application needs login and roles (Q-04).
- **[CONFIRMED]** Phase 6 must not implement authentication, user management, roles, or permissions.
- **[PROPOSED]** A future access model may include Owner/Admin, Operator, Accountant/Reviewer, and Viewer roles.
- **[PROPOSED]** All permission checks, if approved, belong in application services, not only in the UI.
- **[OUT OF SCOPE FOR PHASE 6]** Login screens, password storage, user tables, session handling, and permission enforcement.

Detailed role permissions are proposed in `MODULE_SPECIFICATIONS.md` and `BUSINESS_RULES.md` and require owner approval.

## 8. Out-of-scope items

### 8.1 Product non-goals from `BLUEPRINT.md` §2.2

- [OUT OF SCOPE] Cloud synchronization, remote API, mobile client, or web dashboard.
- [OUT OF SCOPE] Simultaneous multi-computer use of one SQLite file over a network share.
- [OUT OF SCOPE] Multi-company or multi-tenant operation.
- [OUT OF SCOPE] Full statutory accounting certification or tax filing.
- [OUT OF SCOPE] Payroll, manufacturing/MRP, CRM campaigns, e-commerce integration.
- [OUT OF SCOPE] Custom report designer.
- [OUT OF SCOPE] Built-in SQLite encryption unless separately approved under Q-18.

### 8.2 Phase 6 restrictions

- [OUT OF SCOPE] Any business-module implementation.
- [OUT OF SCOPE] Database migrations, tables, columns, or SQLAlchemy models.
- [OUT OF SCOPE] Sample or seed business data.
- [OUT OF SCOPE] Authentication implementation.
- [OUT OF SCOPE] New dependencies, cloud services, or architectural replacement.

## 9. Assumptions requiring confirmation

| ID | Assumption in existing docs | Current status | Consequence if wrong |
| --- | --- | --- | --- |
| A-01 | One business, one currency, one database per installation | [CONFIRMED] for v1 constraints | Multi-company would change configuration and schema |
| A-02 | Single active user at a time | [CONFIRMED] operating assumption; login still open | Multi-user would require concurrency and auth redesign |
| A-03 | Currency needs 2 decimal places | [CONFIRMED] INR | Storage scale and rounding would change |
| A-04 | Quantities up to 3 decimals, unit prices up to 4 | [PROPOSED] schema scale | Invoice math and storage scale would change |
| A-06 | English UI sufficient for v1 | [REQUIRES OWNER CLARIFICATION] Q-20 | Localization layer required |
| A-10 | No statutory audit/certification requirement for v1 | [PROPOSED] | Accounting depth and controls would increase |
| A-11 | Products can be goods and services | [PROPOSED] Q-07 | Inventory posting rules need a type flag; confirm relevance |
| A-12 | A4 PDF sufficient initially | [PROPOSED] Q-17/AQ-06 | Thermal/receipt printing adds a device layer |

## 10. Owner review gates

Implementation of any business module requires owner approval of:

1. The specific field list and validation rules for that module.
2. The workflow and all status transitions.
3. Any numbering scheme for numbered documents.
4. Posting effects on inventory and accounting, if applicable.
5. Report and export requirements.
6. Rules tests and reconciliation expectations.
7. The resolved open decisions in `OPEN_DECISIONS.md` that block that module.

No Phase 7 work starts automatically after Phase 6.
