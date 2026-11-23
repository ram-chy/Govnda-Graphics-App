# Phase 8A — Authentication, Local User Accounts, Roles & Permissions Specification

## Role

Act as a Senior Software Architect, Windows Desktop Application Security
Engineer, Python/PySide6 Developer, and Database Architect.

Your task is to prepare the complete authentication and authorization
specification for the Gobindas Graphics Business Management System.

This is Phase 8A: requirements finalization and technical specification.

Do not begin implementation until the owner has explicitly approved the complete
specification.

## 1. Project Context

The application is a native Windows desktop application built with:

- Python
- PySide6 / Qt 6 Widgets
- SQLite
- SQLAlchemy 2
- Alembic
- Pydantic and application/domain validation

Architecture: modular monolith with Presentation, Application, Domain, and
Infrastructure layers.

The application is offline-first and runs locally on Windows.

Authentication must be implemented as a native desktop application feature, not
as a web authentication system.

Do not introduce Laravel, Next.js, React, Node.js, a web server, or remote
authentication services.

## 2. Mandatory Pre-Implementation Inspection

Before making changes:

1. Inspect repository structure and Git status.
2. Read the master architecture and security documentation.
3. Read all Phase 7 reports, including Phase 7D acceptance records if available.
4. Inspect the current database schema and migration head.
5. Inspect the existing audit event implementation.
6. Inspect application startup, session lifecycle, configuration, and data-path
   management.
7. Inspect Business Profile integration and existing UI components.
8. Review `docs/OPEN_DECISIONS.md` and the development roadmap.

Preserve all existing work and uncommitted changes.

If Phase 7D documentation has not yet been created, record this as a
prerequisite discrepancy. Do not invent an acceptance record.

## 3. Owner-Approved Authentication Decisions

Treat the following decisions as confirmed.

### Local user accounts

- The application supports multiple local user accounts.
- Accounts belong to the local installation.
- No cloud identity provider or remote authentication is required.
- The application must support role-based access control.

### Approved roles

1. Owner/Admin
2. Operator
3. Accountant/Reviewer
4. Viewer

Do not add new roles without owner approval.

### Owner/Admin

Owner/Admin has full access to every application module and operation,
including:

- User management.
- Role and permission management.
- Application settings.
- Business records.
- Financial records.
- Backup and restore.
- Database relocation.
- Sensitive administrative operations.

Sensitive operations must be audited.

### Operator

Approved baseline:

- Can create and edit day-to-day business records.
- Cannot manage users, roles, or permissions.
- Cannot manage application-wide settings.
- Cannot restore backups.
- Cannot relocate the database.
- Cannot modify or delete audit history.

Deletion, cancellation, approval, and other sensitive business operations must
be defined separately for each module.

Do not assume that create/edit permission implies delete, cancel, approve, or
post permission.

### Accountant/Reviewer

A proposed baseline exists but has not yet been approved:

- View financial records and reports.
- Create/edit permitted financial records.
- Review transactions.
- Verify financial information.
- Cannot manage users, roles, or application-wide settings.
- Cannot restore backups or relocate the database.
- Cannot modify or delete audit history.

Mark every unapproved permission as an owner decision.

### Viewer

The Viewer role exists as an approved role name, but its exact permissions have
not been approved.

Do not assume that Viewer means unrestricted read-only access to every module or
sensitive record.

Prepare a proposed permission model and request owner approval.

## 4. Password and Recovery Requirements

Approved decisions:

- Password recovery is manually managed by Owner/Admin.
- No self-service password recovery.
- No email-based recovery or OTP.
- Password resets must be recorded in audit history.
- Password changes and administrative resets must be distinguishable in audit
  events.

Specify secure password storage using an established password-hashing algorithm
with appropriate parameters.

Never store plaintext passwords.

Never log passwords or expose them in error messages.

Specify password verification, password change, administrative reset, and
session invalidation behavior.

Do not invent an account lockout policy or password complexity policy without
marking it as a proposed owner decision.

## 5. Idle Lock Requirements

Approved:

- Automatic lock after 15 minutes of inactivity.
- Configurable idle timeout.
- Password required to unlock.
- Relevant lock/unlock events recorded.

Specify:

- What counts as user activity.
- How the inactivity timer is reset.
- How the application enters locked state.
- How unlocking works.
- How background tasks behave while locked.
- Whether the active user can be switched.
- What happens when the application is closed while locked.
- How settings changes affect an existing session.

Security-sensitive screens must not remain accessible behind a locked overlay.

The implementation must not depend on a superficial overlay alone if other
application routes or dialogs remain accessible.

## 6. Authorization Architecture

Design a maintainable role-based access-control architecture.

Consider:

- Users.
- Roles.
- Permissions.
- Role-permission assignments.
- User status and activation.
- Current authenticated session.
- Authorization service.
- Central permission definitions.
- UI navigation visibility.
- Command/action authorization.
- Application service authorization.
- Database-level ownership and consistency.

The UI must not be the only authorization boundary.

Every sensitive application operation must enforce authorization in the
application/service layer.

Hiding a button or menu item is not sufficient authorization.

Avoid scattering hardcoded role-name comparisons throughout the application.

Prefer permission-based checks with centralized definitions.

Do not overengineer a generic enterprise IAM platform. Keep the design
appropriate for a standalone small-business desktop application.

## 7. First-Run Owner Account

Design the initial owner account creation flow.

Consider:

- First-run setup.
- Initial Owner/Admin account creation.
- Password confirmation.
- Duplicate account prevention.
- No hardcoded default password.
- Safe recovery if setup is interrupted.
- Prevention of an installation with no active Owner/Admin account.
- Behavior when the owner account is disabled or its password is forgotten.

Do not create a default account or seed user automatically.

The initial account must be created through an explicit setup workflow.

The exact username/email requirements must be presented for owner approval.

## 8. Audit Requirements

Use the existing append-only audit infrastructure.

Propose audit events for:

- Initial owner account creation.
- User creation.
- User activation/deactivation.
- Role assignment changes.
- Permission changes.
- Successful login.
- Failed login, where appropriate.
- Logout.
- Password change.
- Administrative password reset.
- Application lock.
- Application unlock.
- Sensitive administrative actions.

Audit records must not contain plaintext passwords, password hashes, or other
authentication secrets.

Preserve indefinite audit retention and append-only behavior.

Define behavior for events occurring before an authenticated user exists.

Do not modify or weaken the existing Business Profile audit behavior.

## 9. Database and Security Design

Propose the required database tables and relationships.

Consider:

- Users.
- Roles.
- Permissions.
- Role-permission assignments.
- User-role assignment strategy.
- Session-related state, if persistence is necessary.
- Authentication settings.
- Audit integration.

Explain which information should be persisted and which should remain in memory.

Use secure password-hashing storage.

Use database constraints and transactions where appropriate.

Do not add unnecessary schema complexity.

Do not create migrations or modify the existing schema in this phase.

## 10. UI/UX Specification

Design native PySide6 screens for:

- Login.
- First-run Owner/Admin creation.
- User management.
- Create/edit user.
- Role assignment.
- Password change.
- Administrative password reset.
- Locked application screen.
- Unlock screen.
- Access-denied feedback.

Preserve the accepted Phase 5 UI design:

- Calm green-based Light Mode.
- Professional Dark Mode.
- Minimal and easy-to-read interface.
- Keyboard accessibility.
- Consistent dialogs and feedback.
- No excessive use of semantic colors.

Do not implement screens yet.

## 11. Owner Decision Worksheet

Create a concise owner decision worksheet covering unresolved questions.

At minimum include:

### Account identity

- Username, email, or both.
- Username uniqueness and case sensitivity.
- Whether email is mandatory.
- Whether users can change their usernames.

### Password policy

- Minimum password length.
- Password complexity requirements.
- Failed-login throttling or temporary lockout.
- Password change policy.
- Whether password expiration is required.

### User administration

- Whether multiple Owner/Admin accounts are allowed.
- Whether Owner/Admin can disable another Owner/Admin.
- Whether the last active Owner/Admin can ever be disabled.
- Whether users can be deleted or only deactivated.

### Accountant/Reviewer

- Exact viewing permissions.
- Exact create/edit permissions.
- Approval and posting authority.
- Access to customer and supplier balances.
- Access to financial reports.
- Access to sensitive business settings.

### Viewer

- Whether Viewer can view all modules or only selected modules.
- Whether financial amounts and reports are visible.
- Whether export and print are permitted.
- Whether sensitive information is restricted.

### Operator

- Module-specific create/edit permissions.
- Delete/cancel permissions.
- Approval/posting restrictions.
- Export/print permissions.

### Session and locking

- Whether the timeout applies while modal dialogs are open.
- Whether background operations continue while locked.
- Whether users can switch accounts without restarting the application.

### Recovery

- Exact administrative reset procedure.
- Behavior when all Owner/Admin credentials are unavailable.

Ask one essential question at a time during the owner decision process. Do not
assume unanswered decisions.

## 12. Required Documentation

Create:

- `docs/AUTHENTICATION_SPECIFICATION.md`
- `docs/AUTHORIZATION_MATRIX.md`
- `docs/USER_ACCOUNT_WORKFLOWS.md`
- `docs/SESSION_AND_IDLE_LOCK_SPECIFICATION.md`
- `docs/PHASE_08_OWNER_DECISION_WORKSHEET.md`
- `docs/PHASE_08_IMPLEMENTATION_READINESS.md`
- `Reports/PHASE_08A_REPORT.md`

Update:

- `docs/OPEN_DECISIONS.md`
- `docs/DEVELOPMENT_ROADMAP.md`

Only update the roadmap to reflect that Phase 8A is planning/specification work.
Do not claim authentication is implemented.

## 13. Strict Scope Restrictions

Phase 8A is documentation and specification only.

Do not:

- Modify Python application source code.
- Modify database schema.
- Create migrations.
- Implement login.
- Implement password hashing.
- Implement user management.
- Implement role or permission checks.
- Modify Business Profile behavior.
- Modify audit infrastructure.
- Run seeders.
- Create sample users.
- Change backup or restore behavior.
- Change the owner's database.
- Commit, push, stage, or rewrite Git history.

Do not begin Phase 8B implementation without explicit owner approval of the
requirements and authorization matrix.

## 14. Verification

Verify:

- Existing owner decisions are preserved accurately.
- Proposed permissions are clearly distinguished from approved permissions.
- No unanswered permission is silently treated as approved.
- Documentation agrees with the existing architecture.
- No application code or database files were modified.
- Git status is recorded before and after.

## 15. Final Response

Report:

- Documentation created.
- Decisions already confirmed.
- Unresolved owner decisions.
- Recommended authentication architecture.
- Implementation blockers.
- Git status.
- Exact next owner decision required.

Stop after Phase 8A and wait for the owner.

**Priority: security, clarity, maintainability, and preserving existing business
data. Do not rush implementation.**
