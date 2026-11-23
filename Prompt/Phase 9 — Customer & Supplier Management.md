# Phase 9 — Customer & Supplier Management

## Objective

Implement the first essential operational master-data module for Gobindas
Graphics Business Management System: **Customer Management and Supplier
Management**.

This is a small-business application. Keep the implementation practical,
minimal, reliable and easy to use. Do not turn it into a large ERP system.

## 1. Record Phase 8B Acceptance

Before starting Phase 9:

- Update `Reports/PHASE_08B_REPORT.md`.
- Add a short Owner Acceptance section.
- Record that the owner personally tested the Windows application and formally
  accepted Phase 8B on 2026-11-23.
- Do not create a separate Phase 8C.
- Do not alter historical test results or claim additional verification.

## 2. Mandatory Inspection

Inspect the current repository and Git status before changing anything.

Read:

- `docs/DEVELOPMENT_ROADMAP.md`
- `docs/OPEN_DECISIONS.md`
- `docs/BUSINESS_REQUIREMENTS.md`
- `docs/BUSINESS_WORKFLOWS.md`
- `docs/MODULE_SPECIFICATIONS.md`
- `docs/BUSINESS_RULES.md`
- `docs/AUTHORIZATION_MATRIX.md`
- `docs/DATABASE_SCHEMA.md`
- Existing Phase 8B implementation and report
- Existing Business Profile, audit, database and UI implementations

Preserve all existing user changes, uncommitted files, application data and
historical records.

## 3. Scope

The intended module contains:

### Customer Management

- Create customer records.
- View customer details.
- Edit customer records.
- Search and list customers.
- Activate/deactivate customers if supported by approved business rules.
- Prevent unsafe deletion of records referenced by other business records.

### Supplier Management

- Create supplier records.
- View supplier details.
- Edit supplier records.
- Search and list suppliers.
- Activate/deactivate suppliers if supported by approved business rules.
- Prevent unsafe deletion of records referenced by other business records.

### User Interface

- Native PySide6 interface.
- Consistent with the existing green Light Mode and professional Dark Mode.
- Simple forms, clear validation messages and useful empty states.
- Reuse existing UI components and feedback patterns.
- No unnecessary dashboard widgets or decorative complexity.

## 4. Critical Business Rules

Before implementing:

1. Check whether decisions B6-13-A/B/C and all relevant customer/supplier field
   requirements have explicit owner approval.
2. Check approved duplicate-handling, mandatory-field, validation, deletion and
   archival rules.
3. Use existing approved specifications rather than inventing new ones.
4. Do not silently treat proposed or provisional defaults as approved.
5. Do not add tax, credit limits, opening balances, payment terms, pricing, or
   other financial behavior unless explicitly approved and required for this
   module.
6. Do not implement invoices, quotations, purchases, payments, inventory or
   accounting transactions in this phase.

**If essential field definitions or business rules remain unapproved, stop
before implementation.** Do not create another large planning phase. Report only
the exact unresolved decisions that prevent safe implementation, with concise
questions for the owner.

## 5. Architecture and Implementation

If the requirements are approved, implement a complete vertical slice using the
existing architecture:

- Domain entities and validation.
- Application services/use cases.
- Repository interfaces and SQLAlchemy implementations.
- Alembic migration.
- PySide6 views and ViewModels.
- Centralized authorization checks in application services.
- Audit integration using the existing append-only audit system.

Maintain the existing modular-monolith boundaries:

- Domain must not depend on PySide6 or SQLAlchemy.
- Business rules belong in the domain/application layers, not UI widgets.
- Database operations must use the existing transaction conventions.
- Use the existing error handling and diagnostic correlation IDs.
- Follow the approved authorization matrix exactly.

Use only the existing approved roles and permissions. Do not invent additional
roles or grant permissions to solve implementation convenience.

## 6. Database and Data Safety

- Use Alembic for schema changes.
- Never modify historical migrations.
- Never bypass the existing migration and safety-backup mechanisms.
- Preserve Business Profile, authentication, session, audit, backup and restore
  functionality.
- Do not change database-location or backup architecture.
- Do not use the owner's live database for destructive tests.
- Test migrations and data operations using isolated temporary databases.
- Do not create sample customers or suppliers in the real database.

## 7. Testing

Add tests for:

- Customer creation, editing, searching and validation.
- Supplier creation, editing, searching and validation.
- Duplicate handling according to approved rules.
- Activation/deactivation if implemented.
- Deletion protection and references.
- Authorization for each approved role.
- Audit event creation and append-only protection.
- Migration upgrade and existing-data preservation.
- Regression of Business Profile, authentication, backup and restore.

Run the complete test suite and Ruff. Report actual results only.

## 8. Documentation and Report

Update only the documentation that genuinely needs updating.

Create:

`Reports/PHASE_09_REPORT.md`

Include:

- Scope implemented.
- Approved business rules used.
- Files created and modified.
- Database migration details.
- Authorization and audit behavior.
- Test and lint results.
- Known limitations.
- Manual Windows checks required.
- Git status.
- Confirmation that no live business data was modified.

## 9. Strict Project Boundaries

- Keep this phase limited to Customer and Supplier Management.
- No additional modules.
- No speculative features.
- No unnecessary abstractions or dependencies.
- No sample data or seeders.
- No commits or pushes.
- Do not delete or overwrite unrelated files.
- Do not change existing business rules without explicit approval.
- Do not expand the roadmap unnecessarily.

## 10. Completion

If all required owner-approved decisions exist, implement and test the module.

If a required decision is missing, stop and report the exact blocker without
generating a large new specification.

After completing the implementation and report, stop and wait for the owner's
review.

**Primary principle: Build only what a small business genuinely needs. Prefer a
simple, dependable solution over unnecessary enterprise complexity.**
