# Phase 10 — Product & Service Catalogue Management

## Objective

Implement a simple Product & Service Catalogue for Gobindas Graphics Business
Management System.

The application is intended for a small business's daily operations and
accounting. Keep this module practical, minimal and easy to maintain.

## 1. Mandatory Repository Inspection

Before making changes:

- Inspect Git status and preserve all existing modifications.
- Read `docs/OPEN_DECISIONS.md`.
- Read `docs/BUSINESS_REQUIREMENTS.md`.
- Read `docs/MODULE_SPECIFICATIONS.md`.
- Read `docs/BUSINESS_RULES.md`.
- Read `docs/DATABASE_SCHEMA.md`.
- Read `docs/AUTHORIZATION_MATRIX.md`.
- Inspect Phase 9 implementation and `Reports/PHASE_09_REPORT.md`.
- Inspect existing database, migration, audit and UI patterns.

Do not assume proposed requirements are owner-approved.

## 2. Scope

Implement only:

### Product Management

- Create products.
- View and edit products.
- Search and list products.
- Activate/deactivate products.
- Detect possible duplicates and request confirmation before saving.

### Service Management

- Create services.
- View and edit services.
- Search and list services.
- Activate/deactivate services.
- Detect possible duplicates and request confirmation before saving.

### Catalogue UI

- Dedicated Products and Services navigation entries.
- Simple listing and search.
- Create/edit forms.
- Clear validation and duplicate warnings.
- Include/exclude inactive records.
- Consistent existing Light and Dark themes.

Reuse existing UI components and patterns wherever possible.

## 3. Business Rules and Owner Decisions

First inspect the existing documentation for approved decisions concerning:

- Product and service fields.
- Product/service classification.
- Categories and units, if approved.
- Pricing fields and their meaning.
- Duplicate detection policy.
- Required fields and validation.
- Permissions and lifecycle rules.

Use only explicitly approved requirements.

Do not invent:

- Tax rates or tax calculations.
- Purchase or selling workflows.
- Stock quantities or inventory valuation.
- Opening stock.
- Product variants or complex attributes.
- Barcode functionality.
- Multiple price lists.
- Discounts or commission calculations.

If an essential decision is still unresolved, stop before implementation and
report only the exact missing decision. Do not create another extensive
specification phase.

## 4. Database and Architecture

Follow the existing modular-monolith architecture:

- Domain validation and business rules.
- Application services.
- Repository layer.
- SQLAlchemy models.
- Alembic migration.
- PySide6 views and ViewModels.

Use the existing database transaction, audit and authorization mechanisms.

Keep product and service records appropriately distinguishable. Do not introduce
unnecessary abstraction or complex inheritance.

Never modify historical migrations.

## 5. Authorization and Audit

Follow `docs/AUTHORIZATION_MATRIX.md`.

- Enforce authorization in application services.
- Do not rely only on hidden UI controls.
- Use only approved permission keys.
- Record create, update, activate and deactivate events in the existing
  append-only audit system.
- Do not implement hard deletion unless explicitly approved.

## 6. Testing

Add focused tests for:

- Product creation and editing.
- Service creation and editing.
- Validation and duplicate detection.
- Duplicate confirmation.
- Search and inactive filtering.
- Activation/deactivation.
- Role-based authorization.
- Audit events.
- Migration upgrade and data preservation.
- Regression of Phase 1–9 functionality.

Run the complete pytest suite and Ruff.

Use isolated temporary databases. Never perform destructive testing against the
owner's business database.

## 7. Documentation and Report

Update only genuinely affected documentation.

Create:

`Reports/PHASE_10_REPORT.md`

Include:

- Implemented features.
- Approved fields and rules used.
- Files changed.
- Database migration details.
- Authorization and audit behavior.
- Automated test and Ruff results.
- Outstanding manual Windows checks.
- Known limitations.
- Git status.

## 8. Strict Boundaries

- No inventory management.
- No stock movement.
- No purchase or sales transactions.
- No invoices or payments.
- No accounting calculations.
- No tax implementation.
- No sample data or seeders.
- No unnecessary dependencies.
- No commits or pushes.
- Do not overwrite unrelated files.
- Preserve existing business data and historical audit records.

## 9. Completion

Implement the approved catalogue functionality, run tests, update documentation
and prepare the report.

If a required owner decision is missing, stop and report the specific blocker
without expanding the scope.

After completion, stop and wait for owner review.

**Guiding principle: A small, dependable product and service catalogue—not an
enterprise ERP inventory system.**
