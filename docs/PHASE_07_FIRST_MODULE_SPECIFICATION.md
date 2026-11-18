# PHASE 07 FIRST MODULE SPECIFICATION — Business Settings / Business Profile

| Field | Value |
| --- | --- |
| Document | PHASE_07_FIRST_MODULE_SPECIFICATION.md |
| Version | 1.0 |
| Date | 2026-11-18 |
| Status | Draft for owner approval; NOT approved for implementation |
| Recommended first module | Business Settings — Business Profile only |
| Source | Phase 6 proposed order and architecture/database constraints |
| Related | PHASE_07_OWNER_DECISION_WORKSHEET.md, PHASE_07_IMPLEMENTATION_READINESS.md, OPEN_DECISIONS.md, ARCHITECTURE.md, DATABASE_SCHEMA.md |

## 0. Approval warning

This specification is prepared for the owner review gate. It is not implementation authorization. The recommended module is not automatically approved.

Implementation must wait until:

1. The owner answers the blocking decisions in `PHASE_07_OWNER_DECISION_WORKSHEET.md`.
2. The owner approves this specification, including the field list and validation rules.
3. The implementation-readiness document records the gate as passed.

No code, migration, table, model, dependency, sample data, or application behavior change is part of Phase 7.

## 1. First module selection

### 1.1 Recommendation

**Recommended first module:** Business Settings — Business Profile only.

This is the safest first slice because it:

- has no dependency on tax calculation, discounts, payment allocation, numbering, inventory, accounting, or report definitions;
- does not require customer/supplier duplicate rules;
- does not require catalogue/pricing decisions;
- can be delivered as one vertical slice through domain, application service, repository, ViewModel, and Settings UI;
- prepares identity information needed later by printed documents and reports without requiring those documents in the same slice.

### 1.2 Why not another module first

| Candidate | Why it is riskier |
| --- | --- |
| Customers/Suppliers | Requires `B6-13` field and duplicate approval, plus `B6-11` archival/historical display behavior. |
| Catalogue | Requires `Q-07 / B6-01` product/service scope and pricing basis; a standard retail catalogue must not be assumed. |
| Jobs/Work Orders | Requires `B6-02`, possibly `B6-03`, `B6-04`, quoting, revenue timing, attachments, and delivery rules. |
| Sales invoices | Requires `Q-03`, `Q-08`, `Q-09`, `Q-10`, `Q-13`, `Q-14`, and printed-document decisions. |
| Purchases/Payments | Requires tax, numbering, allocation, payable/receivable, and correction rules. |
| Inventory | Requires `B6-07`, `Q-05`, `Q-06`, and posting rules. |
| Reports/Dashboard | Requires source modules and approved metric/report definitions. |
| Users/Roles/Audit visibility | Requires `Q-04 / AQ-05`, `B6-10`, `Q-22`, and affects every module. |

### 1.3 Conditional nature

Even the recommended module is blocked until the owner approves the profile fields (`B6-09`). If the owner includes tax identifiers, logo/attachment metadata, printed document output, or visible audit history, additional decisions become blocking.

## 2. Module purpose

Provide a safe way to record the business identity used later in invoices, statements, reports, and other printed or exported documents, without inventing legal, tax, or financial requirements.

The first slice stores information only. It does not generate business documents.

## 3. Scope

### 3.1 In scope

- View current business profile status.
- Create a business profile when none exists.
- Edit an existing business profile.
- Save and reload the profile from the local application data store.
- Validate only owner-approved mandatory fields.
- Show clear empty, incomplete, complete, validation-error, and save-failure states.
- Preserve the existing navigation model by replacing only the Settings placeholder when implementation is authorized.
- Follow the existing light/dark theme, accessible feedback, and component conventions.

### 3.2 Out of scope

- Customers, suppliers, catalogue, jobs, quotations, invoices, purchases, expenses, payments, inventory, accounting, and reports.
- Tax calculation, tax rates, tax registration assumptions, and statutory validation.
- Document numbering (`Q-10`).
- Print/PDF/Excel output (`Q-17`, `AQ-06`).
- Logos/images or attachment storage unless `Q-24` is explicitly approved.
- User accounts, login, roles, permissions, approvals, or idle lock (`Q-04`, `AQ-05`, `B6-10`, `SQ-01`).
- Audit history UI or retention implementation (`Q-22`).
- Importing data (`Q-16`, `B6-08`).
- Backup, restore, relocation, migration, or database-infrastructure changes.
- Sample or seed business data.

## 4. Actors and permissions

| Actor | Current status | Responsibility |
| --- | --- | --- |
| Local user | [CONFIRMED] operating assumption | View and edit the single business profile. |
| Owner/Admin | [PROPOSED] only if Q-04 approves roles | Would control profile fields and sensitive changes. |
| Operator/Accountant/Viewer | [PROPOSED] only if Q-04 approves roles | Would require explicit permissions before implementation. |

- [CONFIRMED] Phase 7 does not implement authentication or permissions.
- [CONFIRMED] UI hiding/disabling must not be the only enforcement point if roles are later approved.
- [CONFIRMED] If Q-04 remains single-user, no actor identity is stored for profile changes.

## 5. User workflows

### WF-FM-01 — View profile status

1. User opens Settings.
2. The view asks the ViewModel to load the profile.
3. The view shows one of:
   - no profile yet;
   - profile incomplete, naming missing mandatory fields;
   - profile complete, showing a non-sensitive summary.
4. If loading fails, show an actionable error with correlation/reference information.

### WF-FM-02 — Create profile

1. User opens the empty profile form.
2. User enters owner-approved fields.
3. Validation runs on save, not on every keystroke for mandatory-field errors.
4. On success, save, reload, and show complete/incomplete status.
5. On failure, keep entered values visible and show field-level and general errors.

### WF-FM-03 — Edit profile

1. User opens the existing profile.
2. User changes one or more fields.
3. Validation runs on save.
4. On success, save atomically and return the updated profile.
5. On failure, retain the edited values and show errors without corrupting the saved profile.

### WF-FM-04 — Cancel or leave with unsaved changes

- Proposed behavior: confirm before discarding unsaved edits.
- Owner approval of this UX behavior is not required unless it conflicts with the existing UI blueprint; keep consistent with existing dialog conventions.

## 6. Functional requirements

| ID | Requirement | Status |
| --- | --- | --- |
| FM-F-01 | Load the current business profile or explicitly report that none exists | [PROPOSED] |
| FM-F-02 | Create one business profile for this installation | [PROPOSED] |
| FM-F-03 | Edit the existing business profile | [PROPOSED] |
| FM-F-04 | Validate only owner-approved mandatory fields | [PROPOSED; blocked by B6-09] |
| FM-F-05 | Save through an application service, not directly from the view | [CONFIRMED architecture constraint] |
| FM-F-06 | Expose field-level errors to the ViewModel/view without business logic in widgets | [CONFIRMED architecture constraint] |
| FM-F-07 | Keep INR/fiscal conventions from existing configuration; do not duplicate them in the profile | [CONFIRMED] |
| FM-F-08 | Provide empty, loading, saving, complete, incomplete, and failure states | [PROPOSED] |
| FM-F-09 | Do not generate documents from this module | [PROPOSED] |
| FM-F-10 | Do not create sample data during setup or first run | [CONFIRMED] |

## 7. Field-level requirements

These are functional fields for owner review, **not database columns**. Exact storage definitions are deferred until implementation is approved.

| Field | Purpose | Mandatory / optional | Owner decision | Notes |
| --- | --- | --- | --- | --- |
| Business name | Identity on documents/reports | Pending | B6-09-A | Do not infer legal entity type. |
| Address | Business address on documents | Pending | B6-09-A | Single line or structured fields require owner input. |
| Phone | Contact detail | Pending | B6-09-A/B6-13 policy alignment | Format not yet defined. |
| Email | Contact detail | Pending | B6-09-A | Format validation only if approved. |
| Logo | Branding on printed documents | Pending | B6-09-B + Q-24 | Out of scope unless attachment/storage policy approved. |
| Tax identifier | Tax-related identity | Pending | B6-09 + Q-03 | Do not add or validate unless owner confirms tax requirement. |
| Registration number | Legal/business identity | Pending | B6-09 | Do not invent legal requirement. |
| Bank details | Payment instructions on documents | Pending | B6-09 | Sensitive; must not be logged. |
| Footer message | Document footer text | Pending | B6-09-B | May include owner-specified text only. |
| Website/social handle | Optional identity | Pending | B6-09-B | Not required by any current module. |

## 8. Validation rules

- [PROPOSED] Mandatory validation applies only to fields selected as mandatory in `B6-09-A`.
- [PROPOSED] Optional fields may be blank.
- [PROPOSED] Empty mandatory values must produce field-level messages.
- [PROPOSED] Email format validation, if any, must be approved with the field list.
- [PROPOSED] Phone format validation, if any, must be approved; do not assume a country-specific format beyond the app's INR/India context.
- [CONFIRMED] No float money fields exist in this module.
- [CONFIRMED] No tax-rate validation is performed.
- [CONFIRMED] No legal/registration validation is performed.
- [CONFIRMED] Validation belongs in the domain/application layer, not in PySide6 widgets.

## 9. Duplicate handling

- [PROPOSED] One active business profile per installation.
- [PROPOSED] Creating a second profile while one exists is blocked rather than silently overwriting.
- [PROPOSED] Multi-profile support is out of scope.
- Owner confirmation required: [ ] One profile only  [ ] Multiple profiles needed  [ ] Not decided yet.

## 10. Status and lifecycle rules

Proposed lifecycle:

```text
No profile → Incomplete → Complete → Edited (still complete/incomplete) → Archived/Replaced
```

- **No profile:** expected first-use state.
- **Incomplete:** mandatory approved fields are missing.
- **Complete:** mandatory approved fields pass validation.
- **Edited:** same record after a save; completeness is recalculated.
- **Archived/Replaced:** out of scope unless `B6-11` approves historical display behavior.

Status labels are illustrative and require owner approval.

## 11. Search and filtering

- [PROPOSED] No search is required for a single-profile module.
- [PROPOSED] No list view is required.
- If multiple profiles are approved, search/filtering requirements must be specified in a revised module specification.

## 12. Deletion and archival behavior

- [CONFIRMED] No posted business records exist yet, but the project rule prohibits silent hard-deletion of posted records.
- [PROPOSED] The active profile cannot be hard-deleted through the first module UI.
- [PROPOSED] Replacement/history behavior depends on `B6-11`.
- [PROPOSED] If no archive behavior is approved, edits update the single profile and prior values are not shown as history.
- Owner confirmation required: [ ] Single record, no history  [ ] Keep replacement history  [ ] Not decided yet.

## 13. Audit requirements

- [CONFIRMED] No audit module exists.
- [CONFIRMED] No authentication actor exists unless Q-04 is approved.
- [PROPOSED] First module does not implement visible audit history.
- [PROPOSED] If Q-22 approves audit recording, record profile create/update events with correlation ID and a neutral actor label such as “local user”.
- [PROPOSED] Do not log sensitive field values such as bank details.
- Owner confirmation required: [ ] No visible audit  [ ] Record events only  [ ] Visible history  [ ] Not decided yet.

## 14. Error handling

- Use the existing `AppError` hierarchy and diagnostic correlation IDs.
- Show actionable messages:
  - profile not found is an empty state, not an error;
  - validation failure lists affected fields;
  - load/save failure distinguishes local storage failure from validation failure;
  - permission-denied is out of scope until roles exist.
- Never show raw tracebacks, SQL, file paths beyond intended profile context, or sensitive values.
- Preserve unsaved edits when save fails.
- Keep destructive confirmation patterns unchanged; this module has no destructive action.

## 15. UI screens and navigation

### 15.1 Navigation

- [CONFIRMED] Current `Settings` navigation entry is a placeholder.
- [PROPOSED] Replace only that placeholder with a Business Profile view when implementation is approved.
- [CONFIRMED] Navigation ownership remains in `app/ui/main_window.py`.
- [CONFIRMED] Sidebar remains a signal-emitting component with no business knowledge.

### 15.2 Settings / Business Profile view

Proposed elements:

- page title and short explanation;
- profile status badge (empty/incomplete/complete);
- form for owner-approved fields;
- Save and Cancel/Reset buttons;
- field-level error text;
- non-modal success feedback;
- modal error only when a user decision is required;
- scroll area for long content;
- accessible names for all fields and status labels;
- existing light/dark QSS tokens only.

### 15.3 Empty state

Text must state that no business profile exists and that profile details are used only for future documents/reports. It must not claim documents are available.

## 16. Service and use-case responsibilities

Proposed application-service responsibilities:

| Use case | Responsibility |
| --- | --- |
| `LoadBusinessProfile` | Return current profile or a not-found result; never create defaults silently. |
| `SaveBusinessProfile` | Validate through domain rules, call repository, and return result/errors. |
| `GetProfileCompletion` | Calculate completeness from approved mandatory fields. |
| `ResetProfileDraft` | Clear unsaved view model state without touching stored data. |

Rules:

- [CONFIRMED] Application services own transaction boundaries.
- [CONFIRMED] Application services call domain rules; they do not implement widget behavior.
- [PROPOSED] Return structured results rather than raising for expected validation failures.
- [CONFIRMED] Long-running work is not expected in this module; no new task workflow is required.

## 17. Repository responsibilities

Proposed repository responsibilities:

- load the stored profile or report none;
- persist a validated profile;
- preserve data on failed writes;
- expose no business validation;
- avoid leaking persistence types to the UI;
- support future migration only after approval and safety-backup rules are satisfied.

Repository responsibilities explicitly excluded:

- deciding which fields are mandatory;
- inventing default values;
- creating sample records;
- creating database migrations in Phase 7;
- modifying backup/restore/relocation infrastructure.

## 18. Domain rules

Proposed domain rules:

| ID | Rule | Status |
| --- | --- | --- |
| FM-DR-01 | A profile is complete only when all owner-approved mandatory fields are non-empty and valid | [PROPOSED; blocked by B6-09-A] |
| FM-DR-02 | Optional fields may be blank | [PROPOSED] |
| FM-DR-03 | Saving a profile must not change currency, locale, fiscal-year, or backup configuration | [CONFIRMED] |
| FM-DR-04 | No tax or legal validation is performed unless Q-03/B6-09 approves it | [CONFIRMED] |
| FM-DR-05 | One active profile per installation unless owner approves multiple profiles | [PROPOSED] |
| FM-DR-06 | Sensitive values must not appear in logs | [CONFIRMED security constraint] |

## 19. Dependencies on other modules

| Dependency | Type | Current status | Effect |
| --- | --- | --- | --- |
| Existing config/paths/errors | Technical | [CONFIRMED] | Reuse existing infrastructure; do not change it. |
| Existing shell/theme/components | Technical | [CONFIRMED] | Use current UI foundation; no redesign. |
| B6-09 profile fields | Business | [BLOCKING] | Must be answered before field-level implementation. |
| Q-03 tax model | Business | CONDITIONAL | Required only if tax identifiers/fields are included. |
| Q-24 attachments | Business | CONDITIONAL | Required only if logo/file storage is included. |
| Q-17 / AQ-06 print formats | Business | NOT REQUIRED | No document output in first slice. |
| Q-04 / AQ-05 users/roles | Business | NOT REQUIRED | No permissions in first slice. |
| Q-22 audit visibility | Business | CONDITIONAL | Required only if audit is included. |
| B6-11 archival behavior | Business | BLOCKING if history/replacement is included | Decide single-record vs history before implementation. |
| Q-10 numbering | Business | NOT REQUIRED | This module assigns no document numbers. |

## 20. Testing scenarios

Tests are required when implementation is authorized. Planned scenarios:

1. Load with no stored profile → empty state, no error.
2. Load with incomplete profile → status and missing mandatory fields.
3. Load with complete profile → complete status and correct field values.
4. Save with all mandatory fields → success and reload.
5. Save with missing mandatory field → field-level error, no stored change.
6. Save with invalid optional email, if email validation is approved → field-level error.
7. Save with bank/contact details → logs contain no sensitive values.
8. Save failure → previous saved profile remains intact; unsaved edits remain visible.
9. Create while a profile exists → blocked or handled according to approved duplicate rule.
10. Theme switching → form and status remain readable in light/dark themes.
11. Accessibility → all fields, status, and buttons have accessible names.
12. Navigation → Settings placeholder replaced only after approval; other placeholders unchanged.
13. Domain boundary test → domain rules do not import PySide6/SQLAlchemy/Alembic.
14. No-sample-data test → first launch does not create business profile data.
15. If audit is approved → profile events recorded and sensitive values redacted.

## 21. Acceptance criteria draft

The first module is complete only when:

- owner-approved fields and validation rules are implemented;
- profile can be created, viewed, edited, saved, and reloaded;
- empty/incomplete/complete/error states are covered;
- no document, table outside the approved slice, migration outside the approved safety process, seed data, auth, or sample data is added;
- domain rules and tests run without PySide6;
- existing Phase 1–5 tests remain green;
- UI is accessible and uses existing theme tokens;
- documentation is updated to match implemented behavior;
- owner acceptance is recorded.

## 22. Owner approval checklist

Owner must explicitly approve or correct each item:

- [ ] Recommended first module: Business Settings — Business Profile only.
- [ ] Mandatory field list from B6-09-A.
- [ ] Optional field list from B6-09-B.
- [ ] Exclusion of tax fields unless Q-03 requires them.
- [ ] Exclusion of logo/attachments unless Q-24 is approved.
- [ ] One profile per installation.
- [ ] Single-record/no-history or approved archival behavior.
- [ ] No audit UI in first slice, or approved audit requirements.
- [ ] No document output, numbering, customers, suppliers, catalogue, or transactions in first slice.
- [ ] This specification is approved for implementation.

Owner name: ____________________

Signature / written approval: ____________________

Date: ____________________
