# PHASE 06 — BUSINESS REQUIREMENTS, WORKFLOWS & MODULE PLANNING

## Project

Gobindas Graphics Business Management System

## Phase Objective

Define the complete business requirements, operational workflows, module
boundaries, business rules, and functional specifications for the application.

This is a **planning and documentation phase only**.

Do not implement business modules, create database tables, write migrations, or
introduce new business functionality during this phase.

The objective is to establish an approved business blueprint before
implementation begins.

---

## 1. Mandatory Initial Inspection

Before doing anything:

1. Inspect the entire existing project structure.
2. Read:
   - `docs/BLUEPRINT.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DATABASE_SCHEMA.md`
   - `docs/UI_UX_BLUEPRINT.md`
   - `docs/BACKUP_STRATEGY.md`
   - `docs/DEVELOPMENT_ROADMAP.md`
   - `docs/SECURITY_AND_DATA_PROTECTION.md`
   - `README.md`
3. Read all available phase reports from Phase 1 through Phase 5.
4. Inspect the current application navigation and placeholder pages.
5. Inspect existing domain, application, repository, infrastructure, and UI
   boundaries.
6. Inspect Git status and recent history.

Preserve all existing project decisions and completed work.

Do not reset, clean, overwrite, delete, or modify unrelated work.

Do not commit, amend, rebase, or push anything.

## 2. Confirmed Technical and Product Constraints

The following decisions are already approved. Do not reopen or replace them
without explicit owner approval.

### Application architecture

- Native Windows desktop application.
- Python.
- PySide6 / Qt 6 Widgets.
- SQLite.
- SQLAlchemy 2.
- Alembic.
- Pydantic and application/domain validation.
- Decimal-based financial calculations.
- Integer minor-unit (paise) monetary persistence.
- PyInstaller.
- Inno Setup.

### Architecture

Use the existing modular monolith:

- Presentation: PySide6 views and ViewModels.
- Application: services and use cases.
- Domain: entities and business rules.
- Infrastructure: SQLAlchemy, SQLite, backup, exports, logging, and file
  storage.

Business rules must remain independent of PySide6.

Keep the architecture straightforward. Avoid unnecessary abstractions and
overengineering.

### Data and backup

- Offline-first application.
- User-selected data/database location.
- SQLite database.
- Existing backup, restore, and relocation infrastructure.
- No cloud dependency.
- No multi-computer database sharing.

### Financial conventions

- Default currency: INR.
- Currency code: INR.
- Currency symbol: ₹.
- Two decimal places.
- Indian number grouping.
- Decimal calculations and integer paise persistence.
- Never use float for financial calculations.

### UI/UX

- Native Qt Widgets.
- Calm green-based Light Mode.
- Professional Dark Mode.
- Clean, minimal, easy-to-use interface.
- Avoid excessive green.
- Use semantic colors for status and feedback.

Do not redesign or replace the completed Phase 5 UI foundation.

## 3. Business Requirements Discovery

Study the project's purpose and identify the business operations that need to be
supported by Gobindas Graphics.

Do not assume that a graphics business follows a generic retail, bookshop, or
manufacturing workflow.

Identify potential operational areas and classify each as:

- Confirmed by existing project documentation.
- Proposed for owner consideration.
- Requires owner clarification.
- Not included in the current scope.

Investigate relevant areas such as:

- Customer management.
- Supplier management.
- Product and service catalogue.
- Quotation and estimates.
- Customer orders and job booking.
- Job/work order management.
- Production or service execution, if applicable.
- Delivery and dispatch.
- Invoicing and billing.
- Payment collection.
- Expenses.
- Purchases.
- Inventory and stock, if applicable.
- Business reports.
- User access and permissions.
- Business settings.

These are discovery topics, not approved requirements. Do not implement or mark
them as confirmed merely because they appear in this list.

## 4. Define Business Workflows

For each confirmed or proposed workflow, document:

1. Workflow purpose.
2. Actors and responsibilities.
3. Starting point.
4. Required information.
5. Main steps.
6. Possible status transitions.
7. Validation rules.
8. Business restrictions.
9. Failure and cancellation scenarios.
10. Related workflows.
11. Expected outputs and reports.

Use workflow diagrams where they genuinely improve understanding.

For every workflow, distinguish confirmed business rules from assumptions and
open questions.

Do not invent document numbering formats, tax calculations, pricing rules, stock
deduction rules, payment allocation rules, or approval policies.

## 5. Define Module Boundaries

Prepare a proposed module architecture.

For each module, specify:

- Purpose.
- Responsibilities.
- Main entities.
- Inputs and outputs.
- Dependencies on other modules.
- Permissions it may require.
- Reports it may produce.
- Important business rules.
- Dependencies that must be implemented first.

Identify shared functionality that should be reused without coupling unrelated
modules.

Avoid creating unnecessary modules or abstractions.

## 6. Document Business Data Requirements

For each proposed entity, document its functional data requirements.

Include:

- Business purpose.
- Required information.
- Optional information.
- Relationships.
- Validation requirements.
- Unique-value requirements, if confirmed.
- Lifecycle and status requirements.
- Deletion and archival expectations.
- Audit/history requirements.

Do not create actual database migrations or SQLAlchemy models.

Do not decide database columns or constraints solely from assumptions.

Where information is missing, record the question for owner approval.

## 7. Financial and Operational Rules

Identify financial and operational rules that require explicit decisions.

Investigate:

- Quotation pricing.
- Discounts.
- Taxes and applicable tax configuration.
- Advance payments.
- Partial payments.
- Outstanding balances.
- Refunds and cancellations.
- Credit sales, if applicable.
- Purchase payments.
- Expense recording.
- Inventory valuation and stock movement, if applicable.
- Profit and revenue reporting.

Do not assume the business uses any particular tax registration, tax rate,
accounting method, or stock valuation method.

For each rule, document the alternatives, consequences, and information required
to make a decision.

Do not silently select an alternative.

## 8. User Access and Permissions Planning

Prepare a proposed access-control model.

Identify possible user roles and their responsibilities.

For each proposed role, document:

- What it can view.
- What it can create.
- What it can update.
- What it can delete or cancel.
- What requires approval.
- What financial information it can access.

This is a proposal only.

Do not implement authentication, user management, roles, or permissions during
Phase 6.

## 9. Reporting Requirements

Identify useful business reports based on the proposed workflows.

For each report, document:

- Business purpose.
- Required source data.
- Filters.
- Date ranges.
- Grouping and totals.
- Export requirements.
- Whether it is operational or financial.

Do not fabricate dashboard metrics or introduce fake sample data.

Do not define reports that depend on unapproved business rules.

## 10. Phase Prioritization

Create a recommended implementation roadmap.

Separate the proposed modules into:

- Essential foundation.
- Core business operations.
- Financial operations.
- Inventory or production operations, if applicable.
- Reporting.
- Advanced functionality.

Identify dependencies and recommend an implementation order.

The roadmap must be realistic for a standalone offline Windows application.

Do not start implementation in this phase.

## 11. Required Documentation Deliverables

Create the following documents in `docs/`:

1. `BUSINESS_REQUIREMENTS.md`
   - Product scope.
   - Business objectives.
   - Confirmed requirements.
   - Proposed requirements.
   - Out-of-scope items.

2. `BUSINESS_WORKFLOWS.md`
   - Workflow descriptions.
   - Actors.
   - Process steps.
   - Status transitions.
   - Workflow diagrams where appropriate.

3. `MODULE_SPECIFICATIONS.md`
   - Module responsibilities.
   - Boundaries.
   - Dependencies.
   - Proposed entities.
   - Inputs and outputs.

4. `BUSINESS_RULES.md`
   - Confirmed rules.
   - Proposed rules.
   - Unresolved decisions.
   - Financial and operational restrictions.

5. `REPORTING_REQUIREMENTS.md`
   - Proposed reports.
   - Required data.
   - Filters and calculations.
   - Export requirements.

6. `OPEN_DECISIONS.md`
   - Every question requiring owner clarification.
   - Why the decision matters.
   - Available alternatives.
   - Consequences of each alternative.
   - Recommended option, if justified.
   - Whether the decision blocks implementation.

Update `docs/DEVELOPMENT_ROADMAP.md` to reflect Phase 6 completion and the
proposed next phases.

Do not overwrite unrelated documentation or remove historical information.

## 12. Owner Review Is Mandatory

Do not treat proposed requirements as approved requirements.

At the end of the phase, provide a concise owner-review summary containing:

- Confirmed requirements.
- Proposed modules.
- Recommended workflow order.
- Important business-rule decisions.
- Questions that require my answers.
- Decisions that block implementation.
- Recommended Phase 7 scope.

Present questions clearly and group related questions logically.

Do not begin Phase 7 automatically.

Wait for my review and explicit approval.

## 13. Testing and Verification

Because this is a documentation-only phase:

- Do not introduce code changes.
- Do not modify the database.
- Do not run migrations.
- Do not run seeders.
- Do not create sample business records.
- Do not modify application behavior.

Verify:

- All required documentation files exist.
- No contradictory business rules were introduced.
- Confirmed and proposed requirements are clearly separated.
- Existing architecture and technical decisions remain intact.
- Roadmap is consistent with the new documents.
- Existing project files and Git state are preserved.

## 14. Phase Report

Create:

`Reports/PHASE_06_REPORT.md`

Include:

- Phase number and title.
- Completion date.
- Initial project inspection.
- Documentation created and updated.
- Business areas investigated.
- Confirmed requirements.
- Proposed requirements.
- Unresolved decisions.
- Recommended module implementation order.
- Verification results.
- Deviations and limitations.
- Phase 7 recommendation.

## 15. Strict Restrictions

- No business-module implementation.
- No database schema changes.
- No migrations.
- No SQLAlchemy model changes.
- No authentication implementation.
- No seeders or sample data.
- No new dependencies.
- No cloud services.
- No architectural replacement.
- No destructive file operations.
- No Git commit or push.
- Do not silently invent business workflows or policies.

## Completion Criteria

Phase 6 is complete only when the documentation is internally consistent, all
assumptions are clearly identified, unresolved owner decisions are documented,
and the detailed report is saved.

**STOP after Phase 6. Wait for owner review and explicit authorization before
starting Phase 7.**
