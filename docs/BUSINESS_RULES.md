# BUSINESS RULES — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | BUSINESS_RULES.md |
| Version | 1.0 |
| Date | 2026-11-18 |
| Status | Phase 6 planning output — confirmed rules separated from alternatives; owner approval required |
| Scope | Confirmed conventions, provisional defaults, open business rule alternatives, approval policies, proposed permission planning |
| Related | BUSINESS_REQUIREMENTS.md, BUSINESS_WORKFLOWS.md, MODULE_SPECIFICATIONS.md, REPORTING_REQUIREMENTS.md, OPEN_DECISIONS.md |

## 0. Rule status labels

- **[CONFIRMED RULE]** — already approved/implemented convention; safe to treat as a rule.
- **[PROVISIONAL DEFAULT]** — documented fallback or recommendation only; **not owner approval** and not implementation authority.
- **[OPEN RULE]** — alternatives exist; owner decision required.
- **[PROPOSED RULE]** — planning proposal that requires approval before implementation.
- **[OUT OF SCOPE]** — must not be implemented in current product scope.
- `BR-xx` IDs identify rule areas in this document. Existing `Q-xx`, `A-xx`, and `AQ-xx` IDs retain their meanings from project documentation.

No open rule may be selected silently during implementation.

## 1. Confirmed rules

| ID | Rule | Status | Source |
| --- | --- | --- | --- |
| BR-C-01 | Default currency is INR, symbol ₹, 2 decimal places, Indian digit grouping | [CONFIRMED RULE] | Q-01, Phase 1 report, UI/UX blueprint |
| BR-C-02 | Money uses `Decimal` in application/domain logic and integer paise in persistence; `float` is prohibited | [CONFIRMED RULE] | BLUEPRINT §4.3, DATABASE_SCHEMA §1 |
| BR-C-03 | Fiscal year is 1 April to 31 March | [CONFIRMED RULE] | Q-11, DATABASE_SCHEMA §5, Phase 1 report |
| BR-C-04 | Application is offline-first with a local user-selected database; no cloud/network dependency | [CONFIRMED RULE] | BLUEPRINT §2.1/§4.2, ARCHITECTURE |
| BR-C-05 | One local SQLite database per installation with no multi-computer sharing | [CONFIRMED RULE] | BLUEPRINT §2.1, Phase 4 report |
| BR-C-06 | Posted financial records must not be silently hard-deleted | [CONFIRMED RULE] | DATABASE_SCHEMA §1 |
| BR-C-07 | Alembic is the only schema-change mechanism; normal startup never migrates | [CONFIRMED RULE] | DATABASE_SCHEMA, Phase 4 report |
| BR-C-08 | Backups must be verified before publish; restore must be staged and rollback-aware | [CONFIRMED RULE] | BACKUP_STRATEGY, Phase 4 report |
| BR-C-09 | UI status must not rely on color alone | [CONFIRMED RULE] | UI_UX_BLUEPRINT, Phase 5 report |
| BR-C-10 | PySide6 must not be imported by domain modules | [CONFIRMED RULE] | ARCHITECTURE, tests |

## 2. Provisional defaults that are not approvals

| Item | Provisional/default text in existing docs | Status | Owner decision |
| --- | --- | --- | --- |
| Invoice numbering | `INV-YYYY-000001` suggested in Q-10 | [PROVISIONAL DEFAULT] | Q-10 |
| Rounding | Half-up / `ROUND_HALF_UP` suggested in Q-08 | [PROVISIONAL DEFAULT] | Q-08 |
| Inventory valuation | Weighted average suggested in Q-05 | [PROVISIONAL DEFAULT] | Q-05 |
| Quantity scale | Up to 3 decimals; unit price up to 4 decimals in A-04 | [PROVISIONAL DEFAULT] | A-04 |
| Quotation/order/delivery notes | Provisional default “not in v1” in Q-13 | [PROVISIONAL DEFAULT] | Q-13 |
| Authentication | No login/roles unless owner approves | [PROVISIONAL DEFAULT] | Q-04 |
| Language | English only in Q-20 | [PROVISIONAL DEFAULT] | Q-20 |
| Print format | A4 PDF sufficient in AQ-06/Q-17 | [PROVISIONAL DEFAULT] | Q-17, AQ-06 |
| Barcode scanning | No in Q-23 | [PROVISIONAL DEFAULT] | Q-23 |
| Encryption | Not built into v1; full-disk encryption suggested in Q-18 | [PROVISIONAL DEFAULT] | Q-18 |
| Stock negative quantity | Block negative stock as a common default, but not owner-confirmed | [PROVISIONAL DEFAULT] | Q-06 |

## 3. Financial and operational rule alternatives

### 3.1 Pricing, quotations, and jobs

| ID | Rule area | Status | Alternatives / consequences | Information needed | Decision ref |
| --- | --- | --- | --- | --- | --- |
| BR-01 | Product/service catalogue and price basis | [OPEN RULE] | Fixed price list; quantity × rate; area/page/hour/unit-based; custom quote only; or combinations. The chosen basis affects catalogue fields, invoice lines, quotes, and reports. | Exact services offered, units, whether rates vary by customer/date/size, examples of past jobs | Q-07, A-11, `B6-01` |
| BR-02 | Whether quotations/estimates exist | [OPEN RULE] | No quotations; optional quotations; mandatory quotation before job/invoice. Affects job workflow, numbering, and reporting. | Whether customers ask for written estimates and whether estimates must be tracked | Q-13 |
| BR-03 | Quotation validity and conversion | [OPEN RULE] | No expiry; fixed days; custom per quote; one-time conversion; multiple revisions. Affects status rules and audit history. | Validity period, revision policy, acceptance evidence | Q-13, `B6-02` |
| BR-04 | Job/work-order lifecycle | [OPEN RULE] | No job tracking; simple open/closed; multi-stage design/proof/print/finish/delivery. Affects UI, statuses, permissions, reports. | Whether work progress is tracked and which stages are real | `B6-02`, `B6-03` |
| BR-05 | Delivery/dispatch tracking | [OPEN RULE] | No delivery note; manual note reference; delivery status on job; separate dispatch document. | Whether the business delivers, who signs/receives, required fields | Q-13, `B6-04` |

### 3.2 Discounts, tax, and invoice calculations

| ID | Rule area | Status | Alternatives / consequences | Information needed | Decision ref |
| --- | --- | --- | --- | --- | --- |
| BR-06 | Discounts | [OPEN RULE] | No discounts; line-level; document-level; both; fixed amount or percentage; discount before/after tax. Affects calculation order and reports. | Whether discounts are offered, who may grant them, calculation order | Q-08 |
| BR-07 | Tax model | [OPEN RULE] | No tax; single inclusive tax; GST-like split; multiple tax components; exempt categories. Affects invoice math, reports, profile fields. | Registration status, tax names/rates, inclusive/exclusive pricing, document requirements | Q-03 |
| BR-08 | Rounding and precision | [OPEN RULE] | `ROUND_HALF_UP` or another mode; line-level vs document-level rounding; 2/3/4 decimal intermediates. Must use `Decimal`. | Tax/discount examples and expected totals | Q-08, A-04 |
| BR-09 | Document numbering | [OPEN RULE] | Prefix per type, per fiscal year, per branch (branch out of scope), or continuous; reset policy; concurrency-safe allocation. | Required formats for invoice, quote, bill, payment, expense | Q-10 |
| BR-10 | Posted invoice mutability | [PROPOSED RULE] | Draft may be edited; posted document should only be corrected via void/credit/adjustment. Protects audits and balances. | Whether owner wants amendments on original document | Q-14 |

### 3.3 Sales, credit, and receivables

| ID | Rule area | Status | Alternatives / consequences | Information needed | Decision ref |
| --- | --- | --- | --- | --- | --- |
| BR-11 | Credit sales | [OPEN RULE] | Cash-only; credit allowed with due date; customer-specific credit terms; credit limits. Affects receivables/aging. | Whether customers buy on credit and standard terms | Q-09 |
| BR-12 | Partial payments | [OPEN RULE] | Full payment only; multiple partial payments; payment against specific invoice; payment against customer balance. | How customers actually pay and how receipts are recorded | Q-09 |
| BR-13 | Advance payments | [OPEN RULE] | No advances; advance against customer; advance against job; advance against invoice. Affects balances and reports. | Whether advances are taken before work/delivery | Q-09, `B6-08` |
| BR-14 | Payment allocation | [OPEN RULE] | Manual allocation; FIFO; allocation by due date; customer-level unallocated receipt. Affects statements and aging. | Required allocation behavior and correction process | Q-09 |
| BR-15 | Overpayments and refunds | [OPEN RULE] | Block overpayment; keep as customer credit; refund workflow; adjust future invoice. | Whether refunds/credits occur and approval needed | Q-09, Q-14 |
| BR-16 | Outstanding balance definition | [OPEN RULE] | Derived from documents; stored balance updated on posting; both with reconciliation. Derived is less duplication but may need performance work later. | Required statement/balance behavior and performance expectations | Q-09, Q-15 |
| BR-17 | Returns, voids, and cancellations | [OPEN RULE] | Void draft only; void posted with reason; credit note; refund; negative invoice. Affects tax/reports/stock. | Real cancellation/return scenarios and required document | Q-14 |

### 3.4 Purchases, expenses, and inventory

| ID | Rule area | Status | Alternatives / consequences | Information needed | Decision ref |
| --- | --- | --- | --- | --- | --- |
| BR-18 | Purchase workflow | [OPEN RULE] | Direct bill entry; purchase order then bill; goods receipt then bill. Affects documents and approvals. | Whether purchase orders/receipts are used | `B6-06` |
| BR-19 | Supplier payment allocation | [OPEN RULE] | Specific bill; supplier balance; FIFO; advance. Affects payables and statements. | How suppliers are paid | Q-09 |
| BR-20 | Purchase returns | [OPEN RULE] | No returns; supplier credit note; stock reversal; refund. Affects payables and stock if applicable. | Whether purchase returns occur | Q-14 |
| BR-21 | Expense categories and methods | [OPEN RULE] | Fixed category list; user-defined categories; account mapping; payment methods cash/bank/UPI/cheque. Affects reports. | Actual expense categories and payment methods | Q-15, Q-24 |
| BR-22 | Inventory applicability | [OPEN RULE] | No stock tracking; consumables only; goods for resale; both. A graphics business may not need full stock control. | Whether stock is held, counted, or valued | Q-05, `B6-07` |
| BR-23 | Inventory valuation | [OPEN RULE] | Weighted average; FIFO; standard cost; no valuation. Affects profit reports and stock ledger complexity. | Owner-selected valuation policy | Q-05 |
| BR-24 | Negative stock | [OPEN RULE] | Block; allow with warning; allow with approval. Affects validation and adjustments. | Whether stock can go negative in practice | Q-06 |
| BR-25 | Stock adjustment approval | [OPEN RULE] | No manual adjustments; owner approval; reason required; threshold. Affects audit and controls. | Who may adjust stock and why | Q-05, `B6-10` |

### 3.5 Accounting, reporting, and data intake

| ID | Rule area | Status | Alternatives / consequences | Information needed | Decision ref |
| --- | --- | --- | --- | --- | --- |
| BR-26 | Accounting depth | [OPEN RULE] | Simple transaction summaries; double-entry-style ledger; statutory-ready accounting (out of scope). Affects reports and validation. | What owner needs to see and reconcile | Q-15 |
| BR-27 | Revenue/profit recognition | [OPEN RULE] | On invoice issue; on payment; on job completion; on delivery. Affects sales and profit reports. | Business practice for recognizing sales | Q-15, `B6-03` |
| BR-28 | Opening balances and imports | [OPEN RULE] | Start fresh; enter opening balances manually; import from spreadsheets. Affects migration/import tools and validation. | Existing data format, cutover date, data quality | Q-16, `B6-08` |
| BR-29 | Report periods | [OPEN RULE] | Daily/monthly/fiscal-year/custom ranges; comparison periods. Affects query layer and filters. | Required reporting cadence | Q-17, `B6-12` |
| BR-30 | Dashboard metrics | [OPEN RULE] | Sales today/month, receivables, payables, stock value, expenses, job counts. Definitions depend on posting rules. | Which numbers owner wants on the dashboard | `B6-12` |

### 3.6 Administrative and supporting rules

| ID | Rule area | Status | Alternatives / consequences | Information needed | Decision ref |
| --- | --- | --- | --- | --- | --- |
| BR-31 | User access | [OPEN RULE] | Single unrestricted local user; simple login; named roles with permissions. Affects schema, UI, audit actor, and tests. | Number of people using the app and need for separation | Q-04 |
| BR-32 | Approval thresholds | [OPEN RULE] | No approvals; discounts/voids require approval; amount-based thresholds. Affects workflows and roles. | Which actions are sensitive and who approves | `B6-10` |
| BR-33 | Audit trail | [OPEN RULE] | No audit; financial events only; all create/update/delete events. Affects storage, performance, and visibility. | Events to record, retention, who can view | Q-22 |
| BR-34 | Attachments | [OPEN RULE] | No attachments; file links; copies inside data root; hashes and previews. Affects backup size and privacy. | Need to store receipts/artwork/proofs and policy | Q-24, AQ-04 |
| BR-35 | Language and document format | [OPEN RULE] | English only; Bengali; bilingual; A4 only; A4 plus receipt/thermal. Affects UI and export design. | Owner/user language needs and paper formats | Q-20, Q-17, AQ-06 |

## 4. Proposed role permission matrix

[PROPOSED] only. No user/role module is implemented in Phase 6. If Q-04 remains “single local user”, this matrix remains out of scope.

| Action | Owner/Admin | Operator | Accountant/Reviewer | Viewer |
| --- | --- | --- | --- | --- |
| View dashboard and allowed lists | Yes | Yes | Yes | Yes |
| Create/edit customers, suppliers, catalogue | Yes | Yes | No | No |
| Create draft invoices/quotations/jobs | Yes | Yes | No | No |
| Post invoices/purchases/payments | Yes | Conditional | Conditional | No |
| Change price, apply discount, set credit terms | Yes | Conditional/approval | Conditional/approval | No |
| Record payments | Yes | Yes | Conditional | No |
| Void/cancel/return/refund posted records | Yes | Approval required | Approval required | No |
| Adjust stock | Yes | Approval required | Conditional | No |
| Approve sensitive actions | Yes | No | Conditional | No |
| View reports | Yes | Yes | Yes | Restricted set |
| Export/print reports | Yes | Yes | Yes | Conditional |
| View audit history | Yes | Conditional | Conditional | No |
| Change business settings/numbering defaults | Yes | No | No | No |
| Perform backup/restore/relocation | Yes | Backup only | No | No |
| Manage users/roles | Yes | No | No | No |

All permission checks, if approved, belong in application services. UI hiding/disabling is only a usability aid.

## 5. Approval policy planning

[PROPOSED] approval rules require owner decisions before implementation.

| Action needing possible approval | Why it matters | Possible approvers | Current status |
| --- | --- | --- | --- |
| Discount above limit | Revenue leakage and pricing control | Owner/admin, reviewer | [OPEN RULE] `B6-10` |
| Void posted invoice/bill | Changes reported revenue/payables | Owner/admin | [OPEN RULE] Q-14 |
| Refund/credit note | Cash and tax/report effect | Owner/admin, reviewer | [OPEN RULE] Q-14 |
| Bad debt/write-off | Receivables and profit effect | Owner/admin | [OPEN RULE] Q-15 |
| Stock adjustment | Inventory valuation effect | Owner/admin | [OPEN RULE] Q-05/Q-06 |
| Expense above threshold | Cash control | Owner/admin | [OPEN RULE] `B6-10` |
| Opening balance entry | Starting financial position | Owner/admin | [OPEN RULE] Q-16 |
| Change numbering configuration | Document traceability | Owner/admin | [OPEN RULE] Q-10 |
| Restore over current database | Destructive technical action | Owner/admin | [CONFIRMED] existing safety workflow governs execution; human authorization policy still to confirm |

## 6. Rule implementation requirements

- [CONFIRMED] Business rules must live in `app/domain` or application services, never only in widgets.
- [CONFIRMED] Rule tests must use plain Python/pytest without PySide6.
- [CONFIRMED] All money calculations must use `Decimal`; persistence must convert to integer paise.
- [PROPOSED] Each approved rule should have a stable `BR-xx` ID, an owner decision reference, examples, and boundary tests.
- [PROPOSED] Rule changes must be reviewed against reports and stored historical documents before release.
- [PROPOSED] Any rounding, tax, discount, or allocation rule requires golden-value tests with representative invoices/payments.
- [PROPOSED] Unapproved rules must fail closed: the affected feature remains unavailable rather than choosing a default silently.

## 7. Owner decisions required before business-rule implementation

The owner must settle, at minimum:

1. `BR-01` exact services/units/pricing basis.
2. `BR-02`–`BR-05` quotation, job, and delivery workflows.
3. `BR-06`–`BR-09` discounts, tax, rounding, and numbering.
4. `BR-11`–`BR-17` credit, payments, balances, returns, and cancellations.
5. `BR-18`–`BR-25` purchase, expense, and inventory behavior.
6. `BR-26`–`BR-30` accounting/report definitions and dashboard metrics.
7. `BR-31`–`BR-35` access, approvals, audit, attachments, and localization/print format.

Until then, these rules are planning inputs only.
