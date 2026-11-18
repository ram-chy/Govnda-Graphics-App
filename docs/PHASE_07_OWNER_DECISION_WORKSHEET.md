# PHASE 07 OWNER DECISION WORKSHEET — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | PHASE_07_OWNER_DECISION_WORKSHEET.md |
| Version | 1.0 |
| Date | 2026-11-18 |
| Status | Draft for owner review; no decision is approved by this document |
| Purpose | Organize outstanding decisions, explain consequences, and prepare the approval gate for the first business module |
| Related | PHASE_07_FIRST_MODULE_SPECIFICATION.md, PHASE_07_IMPLEMENTATION_READINESS.md, OPEN_DECISIONS.md, BUSINESS_RULES.md |

## 0. How to use this worksheet

For every decision, choose one option and write the date. You may select **Not decided yet** for any item. A blank answer means **Not decided yet**.

Status meanings:

- **BLOCKING** — required before the first business module may be implemented. Some blocking items only affect later transaction modules; this is stated in the decision text.
- **NON-BLOCKING** — may remain open for the first module but must be resolved before the named later work begins.
- **OPTIONAL** — can remain unanswered without changing the current plan; record the answer only if the owner wants it captured.

Recommendation rules:

- A recommendation is included only where the existing project requirements support it.
- Provisional defaults in Phase 6 are **not approvals**.
- This worksheet does not choose tax rates, tax-registration assumptions, legal requirements, financial policies, numbering prefixes, or database columns.
- Answering “Keep documented default” means **approving that default for the named decision**, not merely acknowledging that it exists.

## 1. Decision summary

| Group | Decision IDs | Status | Short description |
| --- | --- | --- | --- |
| A — Tax and financial rules | Q-03, Q-08-A, Q-08-B, Q-09-A, Q-09-B, Q-09-C, Q-09-D, Q-13, Q-14 | BLOCKING | Tax, discounts, rounding, credit/payments, balances, document scope, corrections |
| B — Users and permissions | Q-04 / AQ-05 | BLOCKING | Single user vs local named users with roles |
| C — Catalogue and pricing | Q-07 / B6-01 (scope), Q-07 / B6-01 (pricing basis) | BLOCKING | Products, services, custom jobs, pricing method |
| D — Document numbering | Q-10-A, Q-10-B | BLOCKING | Which documents are numbered and how numbering behaves |
| E — Job/work-order scope | B6-02 | BLOCKING | Whether job cards, work orders, stages, costing, or other controls are needed |
| F — Inventory | B6-07 | BLOCKING | Services only, physical stock, consumables, finished goods, or combination |
| G — Business profile | B6-09-A, B6-09-B | BLOCKING | Mandatory and optional business identity fields |
| H — Master data | B6-13-A, B6-13-B, B6-13-C | BLOCKING | Required fields and duplicate handling for customers, suppliers, products/services |
| I — First-module behavioral details | B6-11, Q-22 | BLOCKING / NON-BLOCKING | Historical display/archival; audit expectations |
| J — Other tracked decisions | Q-05, Q-06, Q-15, Q-16, Q-17, Q-18/AQ-04, Q-19/AQ-03, Q-20, Q-21, Q-23, Q-24, Q-25, Q-26, AQ-02, AQ-06, SQ-01, SQ-02, SQ-03, B6-03, B6-04, B6-05, B6-06, B6-08, B6-10, B6-12 | Mostly NON-BLOCKING / OPTIONAL | Later modules, packaging, reporting, security UX, and discovery details |

---

## 2. Group A — Tax and financial rules

### A1. Q-03 — Tax model

- **Business question:** Does the business need tax on sales, purchases, expenses, invoices, and reports, or should v1 operate without tax?
- **Why it matters:** Tax rules change invoice calculations, printed documents, purchase entry, expense handling, report totals, and number of saved fields. Choosing incorrectly can make records hard to correct later.
- **Alternatives and consequences:**
  - **No tax in v1:** Simplest invoices and reports; no tax identifiers, tax components, or tax reports. If tax becomes required later, earlier documents cannot show it.
  - **Tax in v1:** Requires tax applicability rules, rate source, inclusive/exclusive pricing, per-line vs document-level calculation, and tax reports. Rates and registration assumptions must be supplied by the owner/accountant.
  - **Mixed model:** Some items/services taxed and others not; requires category rules and clear exemption handling.
- **Dependent modules/workflows:** Sales invoices, purchases, expenses, quotations if approved, invoice print, tax reports, profit and loss.
- **Recommendation:** No recommendation. The project only supports “no tax in v1” as a provisional default; it is not approval.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] No tax in v1  [ ] Tax in v1 — details to be supplied  [ ] Mixed model — details to be supplied  [ ] Not decided yet
- **Owner-provided details/rate source:** ____________________
- **Decision date / signed by:** ____________________

### A2. Q-08-A — Discount policy

- **Business question:** Are discounts given to customers, and if so, where are they entered?
- **Why it matters:** Discount placement affects totals, approval needs, audit history, and who can change prices.
- **Alternatives and consequences:**
  - **No discounts:** Simplest calculation; no discount fields or permission rules.
  - **Line discount only:** Discount applies to each item/service line; good for item-specific concessions; totals need line-level tests.
  - **Document-level discount only:** One discount applies to the whole bill; simpler but less detailed.
  - **Both line and document discount:** Most flexible; requires a defined order of calculation and stronger approval controls.
  - **Fixed amount or percentage:** Each needs different validation and reporting.
- **Dependent modules/workflows:** Sales invoices, quotations if approved, discount approvals, reports, dashboard totals.
- **Recommendation:** No recommendation beyond keeping the Phase 6 “line discount” default unapproved until the owner confirms it.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] No discounts  [ ] Line discount only  [ ] Document-level only  [ ] Both  [ ] Not decided yet
- **Discount type:** [ ] Fixed amount  [ ] Percentage  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### A3. Q-08-B — Rounding policy

- **Business question:** At what point should money be rounded, and which rounding method should be used?
- **Why it matters:** Small rounding differences affect invoice totals, tax/discount calculations, reports, and reconciliation.
- **Alternatives and consequences:**
  - **Round only final document total:** Fewer rounding points; line totals may not add exactly to displayed totals.
  - **Round each line, then total:** Easier to read; requires defined handling of intermediate values.
  - **Half-up rounding:** Provisional project default; must be explicitly approved.
  - **Another rounding method:** Owner/accountant must state the method; golden-value tests are required.
- **Dependent modules/workflows:** Invoices, purchases, tax calculations, discount calculations, reports, tests.
- **Recommendation:** No recommendation; the documented half-up default is provisional only.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Final total only  [ ] Each line then total  [ ] Half-up  [ ] Other: __________  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### A4. Q-09-A — Credit sales

- **Business question:** Are customers allowed to buy now and pay later?
- **Why it matters:** Credit sales create receivables, due dates, statements, follow-up needs, and balance reports.
- **Alternatives and consequences:**
  - **Cash-only:** No customer balance except unusual corrections; simple reports.
  - **Credit allowed for all customers:** Requires due dates and receivables reports.
  - **Credit allowed only for selected customers:** Requires customer-level credit settings and approval rules.
  - **Credit limits:** Adds more validation and owner policy decisions.
- **Dependent modules/workflows:** Invoices, customer payments, customer statements, receivables, dashboard balances.
- **Recommendation:** No recommendation; owner business practice must decide.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Cash-only  [ ] Credit for all  [ ] Credit for selected customers  [ ] Credit limits  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### A5. Q-09-B — Partial payments

- **Business question:** Can a customer pay part of an invoice and pay the rest later?
- **Why it matters:** Partial payments require outstanding balances and payment-by-payment tracking.
- **Alternatives and consequences:**
  - **Full payment only:** Simple; no partial balance tracking.
  - **Multiple partial payments allowed:** Requires payment history and balance calculation rules.
  - **Payment allowed against a customer balance rather than one invoice:** More flexible; statement rules become more complex.
- **Dependent modules/workflows:** Customer payments, invoices, statements, receivables.
- **Recommendation:** No recommendation.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Full payment only  [ ] Partial payments allowed  [ ] Customer-level payment only  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### A6. Q-09-C — Advances

- **Business question:** Can the business receive money before the job, service, or invoice is completed?
- **Why it matters:** Advances affect customer balances, job status, invoice settlement, and refund behavior.
- **Alternatives and consequences:**
  - **No advances:** Simpler balances.
  - **Advance against customer:** Shows as customer credit; allocation later must be defined.
  - **Advance against job:** Requires job tracking and job/customer balance rules.
  - **Advance against invoice:** Requires a draft/proforma document or equivalent reference.
- **Dependent modules/workflows:** Jobs if approved, invoices, customer payments, refunds/corrections, reports.
- **Recommendation:** No recommendation.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] No advances  [ ] Against customer  [ ] Against job  [ ] Against invoice/draft  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### A7. Q-09-D — Payment allocation and balances

- **Business question:** When money is received or paid, which document does it reduce, and how should balances be shown?
- **Why it matters:** Allocation rules determine statements, aging, totals, and whether an overpayment is blocked, credited, or refunded.
- **Alternatives and consequences:**
  - **Manual allocation to a specific invoice/bill:** Clear audit trail; more data entry.
  - **Oldest-first automatic allocation:** Faster; may not match customer expectations.
  - **Customer/supplier-level balance only:** Simple entry; less precise statement detail.
  - **Overpayment blocked:** Prevents ambiguity; may annoy users.
  - **Overpayment kept as credit:** Requires future adjustment/refund rules.
- **Dependent modules/workflows:** Customer payments, supplier payments, statements, receivables/payables, refunds, reports.
- **Recommendation:** No recommendation.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Manual allocation  [ ] Oldest-first  [ ] Balance only  [ ] Overpayment blocked  [ ] Overpayment as credit  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### A8. Q-13 — Supporting sales documents

- **Business question:** Which documents, if any, are needed before or after a sales invoice: quotations, customer orders, or delivery notes?
- **Why it matters:** Each document adds a workflow, status rules, numbering, printing, and report definitions.
- **Alternatives and consequences:**
  - **Invoices only:** Smallest scope; no estimate or delivery tracking.
  - **Quotations only:** Adds estimate preparation and acceptance/conversion rules.
  - **Customer orders only:** Adds order confirmation and fulfillment tracking.
  - **Delivery notes only:** Adds dispatch/delivery evidence.
  - **Combination:** Requires explicit relationships between quote/order/job/invoice/delivery.
- **Dependent modules/workflows:** Jobs if approved, quotations, invoices, delivery, reports, numbering.
- **Recommendation:** Treat the documented “not in v1” default as pending, not approved; choose only documents that are actually used.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Invoices only  [ ] Quotations  [ ] Customer orders  [ ] Delivery notes  [ ] Combination: __________  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### A9. Q-14 — Corrections, returns, refunds, and cancellations

- **Business question:** How should mistakes, returns, and refunds be handled after a document has been recorded?
- **Why it matters:** Posted records must not be silently deleted. The correction method affects tax, stock, balances, audit, and reports.
- **Alternatives and consequences:**
  - **Draft-only correction:** Drafts can be changed; posted records are fixed. Simplest but inflexible.
  - **Void with reason:** Posted document remains visible as void; requires visibility rules.
  - **Credit note:** Good for sales returns; requires credit document and allocation rules.
  - **Refund:** Requires cash/bank treatment and approval policy.
  - **Reversal/adjustment:** General correction method; requires audit and report treatment.
- **Dependent modules/workflows:** Invoices, purchases, payments, expenses, stock if applicable, tax reports, audit.
- **Recommendation:** No recommendation; the documented “not in v1” default is provisional only.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Draft-only correction  [ ] Void with reason  [ ] Credit note  [ ] Refund  [ ] Reversal/adjustment  [ ] Not decided yet
- **Decision date / signed by:** ____________________

---

## 3. Group B — Users and permissions

### B1. Q-04 / AQ-05 — User and role model

- **Business question:** Will one person use the application without sign-in, or will several people use it with different permissions?
- **Why it matters:** This decision affects login screens, user records, permission checks, audit actor identity, approval workflows, and test scope. It can be added later only with careful design; it should not be invented in the first module.
- **Alternatives and consequences:**
  - **Single-user application:** No login, no roles, one local user. Simplest and matches the documented v1 default, but no separation of duties and audit cannot identify a named user.
  - **Multiple local users with role-based access:** Supports Owner/Admin, Operator, Accountant/Reviewer, and Viewer; requires credentials, role management, permission tests, and password recovery policy.
  - **Shared workstation with role switching but no named users:** Simpler than full login, but weak accountability and not suitable for sensitive approvals.
  - **Windows-account-based identity:** Uses the OS user; needs architecture/security review and is not currently implemented or designed.
  - **Related optional controls:** Idle lock (`SQ-01`), support-bundle export (`SQ-02`), and password-reset recovery (`SQ-03`) only apply if a login model is approved.
- **Dependent modules/workflows:** Every protected module; audit actor; approvals; reports; setup/admin screens; security review.
- **Recommendation:** Keep first module single-user only if the owner confirms that no role separation is needed; this is supported by the documented single-user default, but it still requires owner confirmation.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Single-user, no login  [ ] Multiple local users with roles  [ ] Shared workstation with role switching  [ ] Windows-account identity — needs review  [ ] Not decided yet
- **If roles approved, required roles:** [ ] Owner/Admin  [ ] Operator  [ ] Accountant/Reviewer  [ ] Viewer  [ ] Other: __________
- **Decision date / signed by:** ____________________

---

## 4. Group C — Catalogue and pricing

### C1. Q-07 / B6-01 — Product/service scope

- **Business question:** What does the business actually sell: products, services, custom jobs, or a combination?
- **Why it matters:** A graphics/printing business may not use a standard retail catalogue. The answer determines whether the first master-data slice needs product records, service records, or neither.
- **Alternatives and consequences:**
  - **Services only:** Catalogue stores repeatable services; no stock or product goods fields.
  - **Products only:** Catalogue stores sellable goods; may imply stock questions.
  - **Products and services:** Requires item type and different validation/posting behavior.
  - **Custom job-based work only:** Repeatable catalogue may be unnecessary; job scope description becomes central.
  - **Combination:** Requires clear rules for when an item is a service, a product, or a custom job.
- **Dependent modules/workflows:** Catalogue, jobs if approved, quotations if approved, invoices, purchases if applicable, item reports.
- **Recommendation:** No recommendation; do not assume a standard retail catalogue.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Services only  [ ] Products only  [ ] Products and services  [ ] Custom job-based work only  [ ] Combination: __________  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### C2. Q-07 / B6-01 — Pricing basis

- **Business question:** How is the price for a service/product/job normally worked out?
- **Why it matters:** Pricing basis determines fields, calculation rules, invoice lines, quotation lines, and reports.
- **Alternatives and consequences:**
  - **Fixed price per item/service:** Simple catalogued rate.
  - **Quantity × rate:** Needs units and quantity validation.
  - **Area/page/hour/unit-based pricing:** Needs measurement fields and conversion rules.
  - **Custom quote only:** Price is entered per job; catalogue may only store names/categories.
  - **Customer-specific rates:** Requires customer-level price rules and approval policy.
  - **Other method:** Owner must describe examples.
- **Dependent modules/workflows:** Catalogue, quotations, jobs, invoices, item/service reports.
- **Recommendation:** No recommendation until the owner provides real examples of past work and pricing.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Fixed price  [ ] Quantity × rate  [ ] Area/page/hour/unit  [ ] Custom quote only  [ ] Customer-specific rates  [ ] Other: __________  [ ] Not decided yet
- **Examples to attach:** ____________________
- **Decision date / signed by:** ____________________

---

## 5. Group D — Document numbering

### D1. Q-10-A — Documents requiring numbers

- **Business question:** Which business documents need their own visible reference number?
- **Why it matters:** Numbering affects uniqueness, search, printing, audit, and how users refer to documents.
- **Alternatives and consequences:**
  - **Invoices only:** Smallest scope.
  - **Invoices and quotations:** Requires two independent sequences.
  - **Invoices, quotations, purchase bills, and receipts:** More complete traceability; more rules.
  - **All business documents:** Adds sequences for expenses, delivery notes, orders, credits, and adjustments if those documents exist.
- **Dependent modules/workflows:** All transaction modules; reports; audit; print documents.
- **Recommendation:** Identify documents first; do not choose formats until the document list is approved.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Invoices only  [ ] Invoices + quotations  [ ] Invoices + quotations + purchase bills + receipts  [ ] All business documents  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### D2. Q-10-B — Number format and behavior

- **Business question:** For each approved document type, what numbering behavior is required: prefix, reset rule, uniqueness scope, and gap handling?
- **Why it matters:** Number format cannot be invented. It affects legal/business traceability and document search.
- **Alternatives and consequences:**
  - **Continuous sequence:** No yearly reset; simple uniqueness.
  - **Reset each fiscal year:** Requires year-aware allocation and careful restart rules.
  - **Prefix per document type:** Helps humans identify document type but must be owner-specified.
  - **Gaps allowed vs gap-free:** Gap-free numbering can be blocked by cancelled drafts or failed saves; rules must be explicit.
- **Dependent modules/workflows:** All numbered documents, reports, audit, correction/cancellation workflows.
- **Recommendation:** No recommendation; do not approve `INV-YYYY-000001` unless the owner explicitly selects it.
- **Status:** **BLOCKING**
- **Owner answer per document type:** ____________________
- **Prefix:** ____________________  **Reset:** [ ] Never  [ ] Fiscal year  [ ] Other: __________
- **Gaps:** [ ] Allowed  [ ] Not allowed  [ ] Not decided yet
- **Decision date / signed by:** ____________________

---

## 6. Group E — Job and work-order scope

### E1. B6-02 — Job/work-order controls

- **Business question:** Does customer work need job cards, work orders, production stages, job costing, delivery tracking, or other workflow controls?
- **Why it matters:** Adding job tracking creates a new core module and affects invoices, attachments, due dates, reports, and possibly revenue timing. It should not be assumed for every graphics business.
- **Alternatives and consequences:**
  - **No job tracking:** Invoices can be created directly; smallest scope.
  - **Simple job card:** Records customer, description, due date, and status; no detailed stages or costing.
  - **Work orders with stages:** Adds status transitions and responsibility tracking; requires owner-defined stages.
  - **Job costing:** Tracks estimated vs actual time/material/cost; significant design and reporting impact.
  - **Delivery/dispatch control:** Adds delivery status and possibly delivery notes.
  - **Combination:** Requires explicit lifecycle, fields, permissions, and report definitions.
- **Dependent modules/workflows:** Jobs, quotations if approved, invoices, attachments, reports, dashboard, revenue/profit rules.
- **Recommendation:** No recommendation; select only controls the business actually uses.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] No job tracking  [ ] Simple job card  [ ] Work orders with stages  [ ] Job costing  [ ] Delivery/dispatch control  [ ] Combination: __________  [ ] Not decided yet
- **If stages are required, list them:** ____________________
- **Decision date / signed by:** ____________________

---

## 7. Group F — Inventory

### F1. B6-07 — Inventory applicability

- **Business question:** Does the business manage physical stock, consumables/raw materials, finished goods, services only, or a combination?
- **Why it matters:** Inventory affects purchasing, sales postings, stock movements, valuation, negative-stock rules, reports, and profit calculation. Adding it without approval would create unnecessary complexity.
- **Alternatives and consequences:**
  - **Services only:** No stock ledger, no valuation, no stock reports; purchasing may still record expenses/bills.
  - **Physical stock for resale:** Requires receipts, issues, adjustments, stock balance, and likely valuation.
  - **Consumables/raw materials:** Requires usage tracking; may not need sale-price valuation.
  - **Finished goods:** Requires production/completion rules if goods are made in-house.
  - **Combination:** Requires category rules and separate posting behavior for stock and non-stock items.
- **Dependent modules/workflows:** Catalogue, purchases, sales, stock ledger, returns/corrections, valuation, stock reports, profit and loss.
- **Recommendation:** No recommendation; inventory must remain out of scope until the owner confirms it is needed.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Services only  [ ] Physical stock  [ ] Consumables/raw materials  [ ] Finished goods  [ ] Combination: __________  [ ] Not decided yet
- **Decision date / signed by:** ____________________

---

## 8. Group G — Business profile

### G1. B6-09-A — Mandatory business profile fields

- **Business question:** Which business identity details must be present before documents or reports can be produced?
- **Why it matters:** These fields appear in invoice/statement/report headers. Mandatory fields block document issue if missing, so they must be deliberately chosen.
- **Candidate mandatory fields:** Legal/business name; address; phone; email; logo; tax identifier; registration number; bank details; footer message.
- **Important:** Do not add tax or legal registration fields unless the owner confirms they are required. Tax identifiers depend on Q-03.
- **Dependent modules/workflows:** Business settings, invoice print, statement print, reports, first module validation.
- **Recommendation:** Approve only fields the owner needs on everyday documents; leave tax/registration fields out unless Q-03 and the owner require them.
- **Status:** **BLOCKING**
- **Owner answer — select mandatory fields:** [ ] Business name  [ ] Address  [ ] Phone  [ ] Email  [ ] Logo  [ ] Tax ID  [ ] Registration no.  [ ] Bank details  [ ] Footer message  [ ] Other: __________  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### G2. B6-09-B — Optional business profile fields

- **Business question:** Which business details should be stored but not required before documents are issued?
- **Why it matters:** Optional fields improve documents without blocking daily work.
- **Candidate optional fields:** Logo, secondary phone, email, website, tax ID, registration number, bank details, footer text, social/media handle.
- **Dependent modules/workflows:** Business settings, printed documents, reports.
- **Recommendation:** Keep decorative or rarely used details optional unless the owner says otherwise.
- **Status:** **BLOCKING**
- **Owner answer — select optional fields:** [ ] Logo  [ ] Secondary phone  [ ] Email  [ ] Website  [ ] Tax ID  [ ] Registration no.  [ ] Bank details  [ ] Footer message  [ ] Other: __________  [ ] Not decided yet
- **Decision date / signed by:** ____________________

---

## 9. Group H — Master data

### H1. B6-13-A — Customer fields and duplicate policy

- **Business question:** What information must be stored for each customer, and what should happen if two customer records look the same?
- **Why it matters:** Customer records are used on jobs, invoices, payments, and statements. Poor duplicate rules create incorrect balances and confusing history.
- **Alternatives and consequences:**
  - **Name only required:** Fast entry; high duplicate risk.
  - **Name + phone required:** Better identification; may exclude customers without phone.
  - **Name + address/contact required:** Stronger identity; slower entry.
  - **Tax ID/registration required:** Only if legally/business required; depends on Q-03 and owner policy.
  - **Duplicate handling:** Warn, block exact matches, require manual review, or allow with reason.
- **Dependent modules/workflows:** Customer master, jobs, invoices, payments, statements, reports.
- **Recommendation:** Require enough identification to avoid duplicate balances; do not add tax/legal identifiers unless required.
- **Status:** **BLOCKING**
- **Owner answer — required fields:** [ ] Name  [ ] Phone  [ ] Email  [ ] Address  [ ] Contact person  [ ] Tax ID  [ ] Registration no.  [ ] Other: __________  [ ] Not decided yet
- **Owner answer — duplicate policy:** [ ] Warn only  [ ] Block exact match  [ ] Manual review  [ ] Allow with reason  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### H2. B6-13-B — Supplier fields and duplicate policy

- **Business question:** What information must be stored for each supplier, and what should happen if two supplier records look the same?
- **Why it matters:** Supplier records affect purchase bills, payments, payables, and statements.
- **Alternatives and consequences:** Same alternatives as customers, applied to suppliers; tax identifiers depend on Q-03.
- **Dependent modules/workflows:** Supplier master, purchase bills, supplier payments, statements, reports.
- **Recommendation:** Require enough identification to avoid duplicate payables; do not add tax/legal identifiers unless required.
- **Status:** **BLOCKING**
- **Owner answer — required fields:** [ ] Name  [ ] Phone  [ ] Email  [ ] Address  [ ] Contact person  [ ] Tax ID  [ ] Registration no.  [ ] Other: __________  [ ] Not decided yet
- **Owner answer — duplicate policy:** [ ] Warn only  [ ] Block exact match  [ ] Manual review  [ ] Allow with reason  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### H3. B6-13-C — Product/service fields and duplicate policy

- **Business question:** What information must be stored for each product/service, and what should happen if two entries look the same?
- **Why it matters:** Catalogue entries are reused on invoices and reports. The answer depends on Q-07/B6-01 product/service scope and pricing basis.
- **Alternatives and consequences:**
  - **Name only:** Simple; duplicate risk.
  - **Name + code/reference:** Better search and printing; requires code uniqueness rule.
  - **Name + category + unit:** Needed for unit-based pricing and reports.
  - **Name + price basis/rate:** Needed only if fixed or catalogued pricing is approved.
  - **Duplicate handling:** Warn, block exact names/codes, manual review, or allow with reason.
- **Dependent modules/workflows:** Catalogue, quotations if approved, invoices, purchases if applicable, item reports.
- **Recommendation:** Keep fields minimal until Q-07/B6-01 pricing basis is answered.
- **Status:** **BLOCKING**
- **Owner answer — required fields:** [ ] Name  [ ] Code/reference  [ ] Category  [ ] Unit  [ ] Price/rate  [ ] Description  [ ] Item type  [ ] Other: __________  [ ] Not decided yet
- **Owner answer — duplicate policy:** [ ] Warn only  [ ] Block exact match/code  [ ] Manual review  [ ] Allow with reason  [ ] Not decided yet
- **Decision date / signed by:** ____________________

---

## 10. Group I — Additional first-module behavioral decisions

### I1. B6-11 — Historical display and archival behavior

- **Business question:** When a customer, supplier, or catalogue item is renamed or retired, should old documents show the old details or the current details?
- **Why it matters:** Documents must remain readable and trustworthy. This decision affects stored snapshots, list filtering, and archival behavior.
- **Alternatives and consequences:**
  - **Show current master details:** Simple storage; old documents may no longer reflect what was printed.
  - **Show original snapshot:** Accurate history; needs snapshot storage in documents.
  - **Show both:** Best traceability; more UI complexity.
  - **Hide retired records:** Cleaner lists; historical documents may need special lookup.
- **Dependent modules/workflows:** All master data and documents, statements, reports, audit/history.
- **Recommendation:** Do not hard-delete records used by history; decide how old documents should display before first module implementation.
- **Status:** **BLOCKING**
- **Owner answer:** [ ] Current details  [ ] Original snapshot  [ ] Both  [ ] Hide retired records  [ ] Not decided yet
- **Decision date / signed by:** ____________________

### I2. Q-22 — Audit expectations for the first module

- **Business question:** Should changes to business settings and master records be recorded and visible, and if so, for how long?
- **Why it matters:** Audit changes storage, UI, permissions, and retention. If no role model exists, audit cannot identify a named user.
- **Alternatives and consequences:**
  - **No visible audit:** Smallest scope; no history UI.
  - **Record financial/master changes only:** Useful baseline; actor may be “local user” unless Q-04 is approved.
  - **Record all create/update/delete/archive actions:** Stronger traceability; more storage and UI work.
  - **Owner-visible history:** Requires a history screen and retention policy.
- **Dependent modules/workflows:** All business modules, user/role model, reports, security review.
- **Recommendation:** For the first module, defer visible audit history unless the owner requires it; keep posted/business records non-deletable as already documented.
- **Status:** **NON-BLOCKING** for the first module if no audit visibility is included; **BLOCKING** if audit history is included in first-module scope.
- **Owner answer:** [ ] No visible audit  [ ] Record financial/master changes only  [ ] Record all significant changes  [ ] Owner-visible history  [ ] Not decided yet
- **Retention:** [ ] Indefinite  [ ] Fixed period: __________  [ ] Not decided yet
- **Decision date / signed by:** ____________________

---

## 11. Group J — Other tracked decisions

These decisions are not all required for the first module, but they remain in the Phase 6 decision register. Each row includes an owner-answer field and the **Not decided yet** option.

| ID | Plain-language question and why it matters | Realistic alternatives and consequences | Dependent modules/workflows | Recommendation | Status | Owner answer |
| --- | --- | --- | --- | --- | --- | --- |
| Q-05 | If stock is used, how is its value calculated? Wrong valuation changes stock value and profit. | Weighted average (provisional); FIFO; standard cost; no valuation. | Inventory, COGS, P&L, stock reports | No recommendation; needs owner/accountant input. | NON-BLOCKING unless B6-07 confirms stock | [ ] Weighted avg [ ] FIFO [ ] Standard cost [ ] No valuation [ ] Not decided yet |
| Q-06 | Can stock fall below zero? Affects sales validation and adjustments. | Block by default (provisional); allow with warning; allow with approval. | Sales, inventory, returns | No recommendation; block is safer if stock is real. | NON-BLOCKING unless stock in scope | [ ] Block [ ] Warning [ ] Approval [ ] Not decided yet |
| Q-15 | How much accounting detail is needed? Affects reports and reconciliation. | Summary ledger first (provisional); double-entry-style ledger; statutory-ready accounting is out of scope. | Accounting, expenses, reports | Summary ledger is supported by current docs but not owner-approved. | NON-BLOCKING for first module | [ ] Summary [ ] Double-entry style [ ] Not decided yet |
| Q-16 | Is existing data being brought in? Affects cutover and validation. | None (provisional); manual opening balances; spreadsheet import. | Opening balances, imports, reports | Start fresh is supported by current default but needs confirmation. | NON-BLOCKING for first module | [ ] None [ ] Manual balances [ ] Import [ ] Not decided yet |
| Q-17 | Which printed formats are needed? Affects document layout. | A4 invoice + statement (provisional); other formats; thermal receipt via AQ-06. | Invoices, statements, reports, exports | A4 first is supported by current docs but not approved. | NON-BLOCKING for first module | [ ] A4 invoice+statement [ ] Other [ ] Not decided yet |
| Q-18 / AQ-04 | Is encryption at rest required? Key recovery affects backups and support. | No in-app encryption + OS disk encryption (default); SQLCipher/in-app encryption with key management. | Security, packaging, backup/restore | No in-app encryption is documented but not approved. | OPTIONAL / DEFERRED | [ ] No in-app encryption [ ] In-app encryption [ ] Not decided yet |
| Q-19 / AQ-03 | Is a code-signing certificate available? Affects installer trust warnings. | No certificate + document warning; signed build. | Packaging/release | No recommendation. | OPTIONAL / DEFERRED | [ ] No certificate [ ] Signed build [ ] Not decided yet |
| Q-20 | Is English-only UI sufficient? Affects labels, reports, and test scope. | English only (default); Bengali; bilingual. | UI, reports, export templates | English only is documented but not approved. | NON-BLOCKING | [ ] English [ ] Bengali [ ] Bilingual [ ] Not decided yet |
| Q-21 | Is an off-site or second-device backup copy required? | Manual periodic copy (default); second local/external destination; no requirement. | Backup UX, release guidance | Manual copy is documented but not approved. | NON-BLOCKING | [ ] Manual copy [ ] Second destination [ ] No requirement [ ] Not decided yet |
| Q-23 | Is barcode scanning needed? | No (default); manual code entry with scanner-like input; dedicated scanning UI. | Catalogue, sales, inventory | No scanning is documented but not approved. | OPTIONAL / DEFERRED | [ ] No [ ] Manual code entry [ ] Dedicated scanning [ ] Not decided yet |
| Q-24 | Are receipts/artwork/proofs stored as attachments? Affects storage size and backup. | No attachments; PDF/JPG/PNG up to 10 MB (provisional); links to external files; other limits. | Jobs, invoices, expenses, attachments, backup | No recommendation. | NON-BLOCKING unless attachments in first module | [ ] No [ ] PDF/JPG/PNG 10 MB [ ] External links [ ] Not decided yet |
| Q-25 | Should automatic backups also write to a second destination? | No + manual copy (default); second destination with failure rules. | Backup runner, backup UX | No automatic second destination is documented but not approved. | OPTIONAL / DEFERRED | [ ] No [ ] Second destination [ ] Not decided yet |
| Q-26 | Should the app warn if no verified backup exists for N days? | No warning; warn after 7 days (default); block business entry. | Backup UX, daily use | Warning is documented but not approved. | NON-BLOCKING | [ ] No warning [ ] Warn after 7 days [ ] Block [ ] Not decided yet |
| AQ-02 | Is installation per-user or per-machine? | Per-user (preferred in docs); per-machine with elevated install. | Packaging | No recommendation. | OPTIONAL / DEFERRED | [ ] Per-user [ ] Per-machine [ ] Not decided yet |
| AQ-06 | Are thermal receipt printers needed? | A4 only (current); thermal receipt support later. | Reports, print/export | No recommendation. | NON-BLOCKING | [ ] A4 only [ ] Thermal needed [ ] Not decided yet |
| SQ-01 | Is idle-lock needed when no login is used? | Off (default); timed lock. | Security UX, Q-04 | No recommendation. | OPTIONAL / DEFERRED | [ ] Off [ ] Timed lock [ ] Not decided yet |
| SQ-02 | Is a support-bundle export feature needed? | Not in v1 (default); sanitized diagnostics bundle. | Support tooling | No recommendation. | OPTIONAL / DEFERRED | [ ] Not in v1 [ ] Sanitized bundle [ ] Not decided yet |
| SQ-03 | If login is approved, how is a lost password recovered? | Manual owner-managed audited reset (default); self-service reset. | Auth implementation, Q-04 | No recommendation. | OPTIONAL / DEFERRED | [ ] Manual audited reset [ ] Self-service [ ] Not decided yet |
| B6-03 | If jobs exist, are internal stages tracked? | No; open/closed only; owner-defined stages. | Jobs, reports, dashboard | No recommendation. | NON-BLOCKING until B6-02 approves jobs | [ ] No [ ] Open/closed [ ] Owner-defined stages [ ] Not decided yet |
| B6-04 | Is delivery/dispatch tracked? | No; job status only; delivery note; separate dispatch document. | Jobs, invoices, reports | No recommendation. | NON-BLOCKING until B6-02/Q-13 | [ ] No [ ] Job status [ ] Delivery note [ ] Dispatch document [ ] Not decided yet |
| B6-05 | Are walk-in customers allowed? | Always named customer; generic walk-in; per-invoice walk-in details. | Customers, sales invoices, statements | No recommendation. | NON-BLOCKING for first master module | [ ] Named only [ ] Generic walk-in [ ] Per-invoice details [ ] Not decided yet |
| B6-06 | Is a purchase-order workflow needed? | Direct bill entry; PO then bill; goods receipt then bill. | Purchases, inventory, approvals | No recommendation. | NON-BLOCKING for first module | [ ] Direct bill [ ] PO then bill [ ] Receipt then bill [ ] Not decided yet |
| B6-08 | How are opening balances, advances, and cutover handled? | Start fresh; manual reviewed balances; imported data. | Payments, statements, P&L, reports | Start fresh is supported by current default but needs confirmation. | NON-BLOCKING for first master module | [ ] Start fresh [ ] Manual balances [ ] Import [ ] Not decided yet |
| B6-10 | Are approvals or amount thresholds needed for sensitive actions? | No approvals (simplest); approval for voids/discounts/expenses; amount thresholds. | Roles, workflows, audit | No recommendation. | NON-BLOCKING for first module unless approvals included | [ ] No approvals [ ] Specific actions [ ] Thresholds [ ] Not decided yet |
| B6-12 | Which dashboard business metrics are required? | Sales, collections, receivables, payables, expenses, jobs, stock value; none yet. | Dashboard, reports | Keep hidden until metric definitions exist. | NON-BLOCKING | [ ] None yet [ ] Sales [ ] Collections [ ] Receivables [ ] Payables [ ] Expenses [ ] Jobs [ ] Stock value [ ] Not decided yet |

## 12. Owner sign-off

- I have answered or marked **Not decided yet** for every item above.
- I understand that provisional defaults are not approvals.
- I understand that implementation cannot begin until the first module specification is explicitly approved.

Owner name: ____________________

Signature / written approval: ____________________

Date: ____________________
