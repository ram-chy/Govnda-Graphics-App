# REPORTING REQUIREMENTS — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | REPORTING_REQUIREMENTS.md |
| Version | 1.0 |
| Date | 2026-11-18 |
| Status | Phase 6 planning output — business reports are proposed and blocked by owner decisions |
| Scope | Reporting objectives, report catalogue, definitions, exports, dashboard metrics, data integrity, permissions |
| Related | BUSINESS_REQUIREMENTS.md, BUSINESS_WORKFLOWS.md, MODULE_SPECIFICATIONS.md, BUSINESS_RULES.md, OPEN_DECISIONS.md |

## 0. Status labels

- **[CONFIRMED]** — implemented technical status/reporting capability or confirmed convention.
- **[PROPOSED]** — planning requirement only; not approved for implementation.
- **[BLOCKED]** — cannot be reliably defined until referenced business rules/modules are approved.
- **[CONDITIONAL]** — applies only if the related business area is approved.
- **[OUT OF SCOPE]** — not part of the current product scope.

No business report may be implemented with invented metrics, sample data, or silently chosen accounting/tax/stock rules.

## 1. Reporting principles

- [CONFIRMED] All reports are local and offline; no report requires network access.
- [CONFIRMED] Money is displayed in INR with ₹, 2 decimals, and Indian digit grouping.
- [CONFIRMED] Money calculations use `Decimal`; integer paise is the persistence representation.
- [CONFIRMED] Fiscal-year context is April–March.
- [CONFIRMED] The current dashboard must remain honest: it reports verified foundation facts only and no business metrics.
- [PROPOSED] Business reports should be derived from stored source documents and postings, not independent totals entered by users.
- [PROPOSED] A report must not be shown as available until its source module and rules are implemented.
- [PROPOSED] Reports must state applied filters, date range, business name, generation date, and currency on printed output.
- [PROPOSED] Exported files must not silently overwrite existing files.
- [PROPOSED] Report totals must reconcile to the underlying detail rows and source documents.

## 2. Reporting objectives

### 2.1 Confirmed technical objectives

- Show honest application/database/backup status without implying business data exists.
- Provide users with verified data-protection information, not decorative widgets.
- Keep status understandable with text, shape, and accessible names.

### 2.2 Proposed business objectives

- Help the owner see what was sold, credited, collected, purchased, paid, and spent.
- Show open customer and supplier balances where credit is approved.
- Provide printable/exportable documents for operational use.
- Provide item/service, customer, supplier, expense, and job-level summaries where applicable.
- Provide financial summaries only to the approved accounting depth.
- Support decision-making without pretending to be statutory accounting or tax filing.

## 3. Report catalogue

### 3.1 Confirmed technical reports/views

| ID | Report/view | Purpose | Source | Filters/grouping | Output | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RPT-T-01 | Dashboard foundation status | Show verified app/database/backup state | Config, DB metadata, backup service | None required | UI cards | [CONFIRMED] |
| RPT-T-02 | Backup history/status | Show verified backup records and last result | Backup metadata/sidecars | Managed/manual/all if approved | UI list/details | [CONFIRMED] |
| RPT-T-03 | Application diagnostics view | Correlate errors by ID for support | Diagnostics/logging | Correlation ID/date if approved | Log/detail view | [PROPOSED] |

### 3.2 Proposed operational reports

| ID | Report | Business purpose | Source modules | Filters | Grouping/totals | Output | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RPT-O-01 | Customer list | Find and review customers | Customers | Status, search text | None or status counts | Screen, PDF, Excel | [PROPOSED] |
| RPT-O-02 | Customer statement | Show transactions and balance for one customer | Customers, invoices, payments | Customer, date range | Running balance if approved | Screen, PDF, Excel | [BLOCKED] Q-09, Q-16 |
| RPT-O-03 | Supplier list | Find and review suppliers | Suppliers | Status, search text | None or status counts | Screen, PDF, Excel | [PROPOSED] |
| RPT-O-04 | Supplier statement | Show purchases/payments/balance for one supplier | Suppliers, purchases, payments | Supplier, date range | Running balance if approved | Screen, PDF, Excel | [BLOCKED] Q-09, Q-16 |
| RPT-O-05 | Catalogue list | Review services/products | Catalogue | Status, category, search | Category totals/counts if approved | Screen, PDF, Excel | [PROPOSED] |
| RPT-O-06 | Sales register | List invoices in a period | Sales | Date range, customer, status | Invoice totals, tax/discount if approved | Screen, PDF, Excel | [BLOCKED] Q-03, Q-08, Q-10, Q-14 |
| RPT-O-07 | Sales by item/service | Understand service/product mix | Sales, catalogue | Date range, item/category | Quantity, amount, item subtotals | Screen, PDF, Excel | [BLOCKED] Q-07, `BR-01` |
| RPT-O-08 | Payment collection register | Review money received | Payments, customers | Date range, customer, method | Method totals, grand total | Screen, PDF, Excel | [BLOCKED] Q-09 |
| RPT-O-09 | Purchase register | List supplier bills in a period | Purchases | Date range, supplier, status | Bill totals, tax/discount if approved | Screen, PDF, Excel | [BLOCKED] Q-03, Q-10, Q-14 |
| RPT-O-10 | Supplier payment register | Review money paid | Supplier payments | Date range, supplier, method | Method totals, grand total | Screen, PDF, Excel | [BLOCKED] Q-09 |
| RPT-O-11 | Expense register | Review business expenses | Expenses | Date range, category, payee, method | Category/subtotal/grand total | Screen, PDF, Excel | [BLOCKED] Q-15, Q-24 |
| RPT-O-12 | Expense by category | Summarize spend by category | Expenses | Date range, category | Category totals, percentages if approved | Screen, PDF, Excel | [BLOCKED] Q-15 |
| RPT-O-13 | Job/work list | Track open or completed work | Jobs if approved | Status, customer, due date | Status counts if approved | Screen, PDF, Excel | [CONDITIONAL] `B6-02`, `B6-03` |
| RPT-O-14 | Quotation status | Review estimates | Quotations if approved | Status, customer, date | Status/value totals if approved | Screen, PDF, Excel | [CONDITIONAL] Q-13 |
| RPT-O-15 | Stock ledger | Track inventory movements | Inventory if approved | Item, date, movement type | Quantity/value balance if approved | Screen, PDF, Excel | [CONDITIONAL] Q-05, Q-06 |
| RPT-O-16 | Stock summary | Current stock position | Inventory if approved | Item/category, location if approved | Quantity/value totals | Screen, PDF, Excel | [CONDITIONAL] Q-05, Q-06 |
| RPT-O-17 | Attachment index | List linked supporting files | Attachments if approved | Entity, category, date | Counts if approved | Screen only initially | [CONDITIONAL] Q-24 |

### 3.3 Proposed financial reports

| ID | Report | Business purpose | Source modules | Filters | Grouping/totals | Output | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RPT-F-01 | Receivables summary | Amounts owed by customers | Invoices, payments, customers | As-of date, customer, aging buckets if approved | Customer totals, grand total | Screen, PDF, Excel | [BLOCKED] Q-09, Q-15 |
| RPT-F-02 | Payables summary | Amounts owed to suppliers | Purchases, payments, suppliers | As-of date, supplier | Supplier totals, grand total | Screen, PDF, Excel | [BLOCKED] Q-09, Q-15 |
| RPT-F-03 | Profit and loss summary | Basic income and expense view | Sales, purchases, expenses, inventory if applicable | Date range/fiscal period | Category totals, net result | Screen, PDF, Excel | [BLOCKED] Q-03, Q-05, Q-15, `BR-27` |
| RPT-F-04 | Trial balance | Account-style balances | Approved ledger/read models | As-of date | Debit/credit totals | Screen, PDF, Excel | [BLOCKED] Q-15 |
| RPT-F-05 | Cash/book summary | Cash/bank movement overview | Payments, expenses, purchases if approved | Date range, method | Opening/movements/closing if approved | Screen, PDF, Excel | [BLOCKED] Q-09, Q-15, Q-16 |
| RPT-F-06 | Tax summary | Tax collected/paid if applicable | Invoices, purchases, expenses | Date range, tax category | Tax component totals | Screen, PDF, Excel | [BLOCKED] Q-03 |

These reports are definitions of possible needs only. They are not approved report specifications.

## 4. Dashboard metrics

### 4.1 Confirmed dashboard behavior

- [CONFIRMED] Current dashboard shows verified foundation facts only.
- [CONFIRMED] No sample customers, sales, balances, or charts may be introduced.
- [CONFIRMED] Theme, status colors, and layout already exist and must not be redesigned by business module work.

### 4.2 Proposed dashboard metrics

| ID | Metric | Definition required before implementation | Status |
| --- | --- | --- | --- |
| DASH-P-01 | Sales today/month | Posted invoice basis, tax inclusive/exclusive, void handling | [BLOCKED] Q-03, Q-08, Q-14 |
| DASH-P-02 | Cash collected today/month | Payment posting and allocation rules | [BLOCKED] Q-09 |
| DASH-P-03 | Receivables total | Derived vs stored balance, as-of date, credit terms | [BLOCKED] Q-09, Q-16 |
| DASH-P-04 | Payables total | Supplier balance definition, as-of date | [BLOCKED] Q-09 |
| DASH-P-05 | Expenses this month | Category scope, posting rules, tax treatment | [BLOCKED] Q-15 |
| DASH-P-06 | Open jobs | Job lifecycle and status meanings | [CONDITIONAL] `B6-02`, `B6-03` |
| DASH-P-07 | Stock value | Valuation method and negative-stock policy | [CONDITIONAL] Q-05, Q-06 |
| DASH-P-08 | Backup status | Last verified backup and scheduler result | [CONFIRMED] |

Only `DASH-P-08` is based on implemented data. All business metrics must remain hidden or honestly unavailable until their definitions are approved.

## 5. Report definition requirements

Every approved business report must define:

1. **Purpose and owner.** Why it exists and who may run it.
2. **Source documents.** Exact source modules and whether drafts are included.
3. **Date basis.** Document date, posting date, payment date, or due date; date ranges are inclusive/exclusive.
4. **Fiscal context.** Use April–March year unless the approved report explicitly says otherwise.
5. **Filters.** Customer, supplier, item/category, status, payment method, date range, and other approved fields.
6. **Grouping.** Row grouping and sort order.
7. **Totals.** What is summed, what is excluded, and how voids/credits/adjustments affect totals.
8. **Money formatting.** INR, ₹, 2 decimals, Indian grouping, `Decimal` arithmetic.
9. **Quantity formatting.** Approved unit and decimal scale.
10. **Print layout.** A4 initially [PROVISIONAL]; page numbers, header/footer, repeated headings.
11. **Export behavior.** PDF and Excel options; safe filenames; no silent overwrite.
12. **Permission behavior.** Who can view/export and what happens when denied.
13. **Audit behavior.** Whether report generation is recorded, if approved.
14. **Tests.** Golden totals, empty data, filters, void treatment, and long-description wrapping.

## 6. Export and print requirements

- [CONFIRMED] Existing approved libraries for output are `reportlab` (PDF) and `openpyxl` (Excel).
- [CONFIRMED] Output remains local; no upload or cloud export.
- [PROPOSED] A4 portrait is the initial print format for most reports; landscape may be used for wide registers if approved.
- [PROPOSED] Paper size must be configurable per report only if owner approves Q-17/AQ-06.
- [PROPOSED] Print/PDF output must include business profile, report title, date range, filters, currency, and page numbers.
- [PROPOSED] Excel output must use text-safe handling for leading `=`, `+`, `-`, and `@` in user-entered strings to reduce formula injection risk.
- [PROPOSED] Export filenames must be deterministic and safe but must not overwrite existing files silently.
- [PROPOSED] Export must use `Decimal`-derived values, not binary floats or UI-formatted strings.
- [PROPOSED] Empty reports must state “No records found” with applied filters and must not invent totals or sample rows.
- [PROPOSED] Long-running exports use the existing task/progress feedback pattern.

## 7. Data integrity and reconciliation

- [PROPOSED] Report totals must reconcile to detail rows.
- [PROPOSED] Invoice reports must reconcile to sales register and payment allocation reports once those rules exist.
- [PROPOSED] Receivables/payables must reconcile to posted documents and approved adjustments.
- [PROPOSED] Inventory reports, if applicable, must reconcile the movement ledger to stock summary.
- [PROPOSED] Financial reports must state their basis: invoice issue, payment, job completion, or other approved rule.
- [PROPOSED] Reports must not include drafts unless explicitly stated.
- [PROPOSED] Voided/cancelled records must be represented consistently or excluded consistently, according to approved rule.
- [PROPOSED] Report query code belongs in application/read-model services; UI widgets only display results.

## 8. Access control

- [CONFIRMED] No role system exists in Phase 6.
- [REQUIRES OWNER CLARIFICATION] Whether users/roles are needed at all (Q-04).
- [PROPOSED] Viewer roles, if approved, should see restricted report sets.
- [PROPOSED] Export/print actions should be separately permissioned from view-only access.
- [PROPOSED] Audit/report access to sensitive owner information must be explicitly decided.

## 9. Report implementation order

[PROPOSED] after owner approval:

1. Technical/dashboard status reports already implemented; no changes in Phase 6.
2. Basic master lists: customers, suppliers, catalogue.
3. Transaction registers: sales, purchases, payments, expenses.
4. Balance reports: receivables and payables.
5. Summary reports: expense-by-category, sales-by-item/service, job/stock reports if applicable.
6. Financial summaries: profit and loss, trial balance/cash book if Q-15 is enabled.
7. Dashboard business metrics only after source report definitions are stable.

## 10. Tests required before any report is implemented

- INR formatting and Indian grouping.
- Decimal total precision and paise conversion.
- Date-range boundaries and fiscal-year boundaries.
- Empty result behavior.
- Draft inclusion/exclusion.
- Void/cancellation treatment.
- Filter combinations.
- Permission denial behavior if roles are approved.
- PDF/Excel generation with long names, special characters, and user-entered strings.
- No silent overwrite behavior.
- Reconciliation against source document totals.

## 11. Owner decisions needed

Report implementation is blocked until the owner settles:

- Q-03 tax model.
- Q-04 users/roles and report permissions.
- Q-05/Q-06 inventory scope and valuation if stock reports are needed.
- Q-08 discounts.
- Q-09 credit, payments, and balances.
- Q-08 discounts and rounding.
- Q-10 numbering.
- Q-14 returns/voids/refunds.
- Q-15 accounting depth.
- Q-16 opening balances/imports.
- Q-17/AQ-06 print formats.
- `B6-01` pricing basis.
- `B6-02`–`B6-04` job/delivery scope.
- `B6-10` approval policies (resolved 2026-11-22 — no approvals in v1).
- `B6-12` dashboard metric definitions.
