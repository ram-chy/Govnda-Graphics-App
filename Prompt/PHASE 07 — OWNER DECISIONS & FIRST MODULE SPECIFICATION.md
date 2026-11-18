# PHASE 07 — OWNER DECISIONS & FIRST MODULE SPECIFICATION

## Project

Gobindas Graphics Business Management System

## Phase Objective

Resolve the business decisions that block implementation and prepare an
owner-approved functional specification for the first business module.

**This is a planning and approval-gate phase. Do not implement business
functionality.**

Phase 6 produced the business requirements and workflow documentation. However,
those requirements remain proposed or clarification-dependent until the owner
explicitly approves them.

Your job is to organize the outstanding decisions, explain their consequences,
and prepare the first module specification for owner approval.

---

## 1. Mandatory Initial Inspection

Before starting:

1. Inspect the project structure and Git status.
2. Read all Phase 1–6 reports.
3. Read these documents completely:
   - `docs/BUSINESS_REQUIREMENTS.md`
   - `docs/BUSINESS_WORKFLOWS.md`
   - `docs/MODULE_SPECIFICATIONS.md`
   - `docs/BUSINESS_RULES.md`
   - `docs/REPORTING_REQUIREMENTS.md`
   - `docs/OPEN_DECISIONS.md`
   - `docs/DEVELOPMENT_ROADMAP.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DATABASE_SCHEMA.md`
   - `docs/SECURITY_AND_DATA_PROTECTION.md`
4. Preserve existing decisions, terminology, and historical records.
5. Identify every decision that blocks the first business module.

Do not assume that a proposal in Phase 6 has been approved.

## 2. Create an Owner Decision Worksheet

Create:

`docs/PHASE_07_OWNER_DECISION_WORKSHEET.md`

Organize the questions into logical groups.

At minimum, address the following decision IDs from Phase 6:

### A. Tax and financial rules

- Q-03: Tax model.
- Q-08: Discounts and rounding.
- Q-09: Credit, payments, allocation, and balances.
- Q-13 / Q-14: Document corrections and related restrictions.

Explain each available approach, its impact, and which future modules depend on
it.

Do not choose tax rates, tax registration assumptions, or financial policies.

### B. Users and permissions

- Q-04 / AQ-05: User and role model.

Explain the implications of:

- Single-user application.
- Multiple local users with role-based access.
- Other possible access models documented in the project.

Do not implement authentication or permissions.

### C. Catalogue and pricing

- Q-07 / B6-01: Service catalogue and pricing basis.

Clarify whether the business needs:

- Products.
- Services.
- Both.
- Custom job-based pricing.
- Quantity/unit-based pricing.
- Other pricing methods.

Do not assume that a graphics business uses a standard retail catalogue.

### D. Document numbering

- Q-10: Document numbering.

Identify the documents requiring numbering and the decisions needed for each
format.

Do not invent or approve numbering prefixes or sequences.

### E. Job and work-order scope

- B6-02: Job/work-order scope.

Clarify whether customer work requires job cards, work orders, production
stages, job costing, or other workflow controls.

Do not assume that all these features are required.

### F. Inventory

- B6-07: Inventory applicability.

Clarify whether the business manages:

- Physical stock.
- Consumables and raw materials.
- Finished goods.
- Services without stock.
- A combination of these.

Explain the consequences for purchasing, sales, stock movement, valuation, and
reporting.

Do not introduce inventory functionality without owner approval.

### G. Business profile

- B6-09: Business profile fields.

Identify the information required for business identity, invoices, quotations,
and reports.

Keep mandatory and optional fields separate.

Do not invent legal or tax registration requirements.

### H. Master data

- B6-13: Master-data fields and duplicate policy.

Clarify the required fields and duplicate-handling expectations for customers,
suppliers, products, and services.

Do not create final database columns until the owner approves the functional
field lists.

## 3. Questionnaire Quality Requirements

For every decision:

1. Show the decision ID.
2. Explain the business question in plain language.
3. Explain why it matters.
4. Present realistic alternatives.
5. Explain the consequences of each alternative.
6. Identify dependent modules and workflows.
7. Give a recommendation only when supported by project requirements.
8. Mark the decision as:
   - BLOCKING
   - NON-BLOCKING
   - OPTIONAL
9. Provide a clear owner-answer field.
10. Allow the owner to select "Not decided yet".

Do not combine unrelated decisions into one question.

Do not use technical jargon where a business explanation is more appropriate.

## 4. First Module Selection

Evaluate the proposed implementation order from Phase 6.

The initial proposed order was:

1. Business settings and party masters.
2. Catalogue.
3. Confirmed job/quotation workflow, if approved.
4. Sales invoices and customer payments.
5. Purchases and supplier payments.
6. Expenses.
7. Inventory, only if confirmed.
8. Accounting/read models and reports.
9. Audit visibility, attachments, and users/roles, if approved.

Recommend the safest first implementation module based on dependencies and
approved requirements.

Do not assume the first module is automatically approved.

If essential decisions remain unresolved, explain why implementation must wait.

## 5. First Module Functional Specification

Once the owner provides answers, the first module specification must document:

- Module purpose.
- Scope and out-of-scope items.
- Actors and permissions.
- User workflows.
- Functional requirements.
- Field-level requirements.
- Validation rules.
- Duplicate handling.
- Status and lifecycle rules.
- Search and filtering.
- Deletion and archival behavior.
- Audit requirements.
- Error handling.
- UI screens and navigation.
- Service/use-case responsibilities.
- Repository responsibilities.
- Domain rules.
- Testing scenarios.
- Dependencies on other modules.

The specification must be consistent with the existing modular-monolith
architecture.

Do not write implementation code during Phase 7.

## 6. Required Documentation

Create:

1. `docs/PHASE_07_OWNER_DECISION_WORKSHEET.md`
2. `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`
3. `docs/PHASE_07_IMPLEMENTATION_READINESS.md`

Update `docs/OPEN_DECISIONS.md` only to improve traceability and status
tracking. Do not mark an unanswered decision as approved.

Update `docs/DEVELOPMENT_ROADMAP.md` to reflect Phase 7 planning and the
approval gate.

## 7. Strict Technical Restrictions

This phase is documentation and owner-review preparation only.

Do not:

- Create database tables.
- Create migrations.
- Create SQLAlchemy models.
- Implement business modules.
- Implement authentication.
- Implement roles or permissions.
- Add seeders or sample business data.
- Add dependencies.
- Change existing application behavior.
- Modify backup, restore, relocation, or database infrastructure.
- Change existing database contents.
- Commit, amend, rebase, reset, clean, or push Git changes.

Do not overwrite unrelated files.

## 8. Verification

Verify:

- All three required documents exist.
- Every blocking decision from Phase 6 is represented.
- Decision IDs are preserved.
- No unanswered decision is marked approved.
- No proposed requirement is represented as confirmed.
- First-module dependencies are clearly explained.
- Existing architecture and technical decisions remain intact.
- Git status confirms no unrelated changes were overwritten.

Because this phase is documentation-only, do not claim code tests passed unless
they were actually executed.

## 9. Phase Report

Create:

`Reports/PHASE_07_REPORT.md`

Include:

- Phase number and title.
- Initial inspection.
- Documents created and updated.
- Decisions reviewed.
- Blocking and non-blocking decisions.
- Recommended first module.
- Implementation readiness assessment.
- Verification results.
- Limitations.
- Owner actions required.

## 10. Stop Condition

At the end, present the owner decision worksheet clearly.

Do not proceed to Phase 8 or implement the first module.

Wait for the owner to answer the questions and explicitly approve the first
module specification.

**Phase 7 is complete only when the decision worksheet, first-module
specification, implementation-readiness document, and phase report are prepared.
Owner approval remains a separate mandatory gate.**
