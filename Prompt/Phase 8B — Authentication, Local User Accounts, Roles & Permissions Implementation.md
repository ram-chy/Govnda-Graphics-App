# Phase 8B — Authentication, Local User Accounts, Roles & Permissions Implementation

## 1. Objective

Implement the authentication and authorization system for **Gobindas Graphics
Business Management System**, following the owner-approved Phase 8A
documentation.

This is an implementation phase, not another requirements or planning phase.

The implementation must integrate with the existing Python, PySide6, SQLite,
SQLAlchemy 2, and Alembic modular-monolith architecture.

**Owner authorization:** Phase 8B implementation explicitly authorized on
2026-11-22.

## 2. Mandatory pre-implementation inspection

Before changing any file:

1. Inspect repository structure, current Git branch, Git status, and recent
   commit history.
2. Read the complete documents:
   - `docs/AUTHENTICATION_SPECIFICATION.md`
   - `docs/AUTHORIZATION_MATRIX.md`
   - `docs/USER_ACCOUNT_WORKFLOWS.md`
   - `docs/SESSION_AND_IDLE_LOCK_SPECIFICATION.md`
   - `docs/PHASE_08_IMPLEMENTATION_READINESS.md`
   - `docs/PHASE_08_OWNER_DECISION_WORKSHEET.md`
   - `docs/OPEN_DECISIONS.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DATABASE_SCHEMA.md`
   - `docs/SECURITY_AND_DATA_PROTECTION.md`
   - `docs/DEVELOPMENT_ROADMAP.md`
3. Read the Phase 7 and Phase 8 reports, including
   `Reports/PHASE_07D_ACCEPTANCE.md` and `Reports/PHASE_08A_REPORT.md`.
4. Inspect the current implementation of:
   - Application startup and `AppContext`
   - Database connection and migration management
   - SQLAlchemy models and repositories
   - Existing audit event infrastructure
   - Business Profile functionality
   - Main window, navigation, dialogs, themes and reusable controls
   - Configuration and data-path handling
   - Existing tests and fixtures
5. Verify the actual migration head. Expected current head:
   `0003_business_profile_requirements`.
6. Verify that the Phase 7D acceptance record exists and Phase 8A implementation
   readiness is clear.
7. Inspect the exact approved Argon2id parameters in
   `AUTHENTICATION_SPECIFICATION.md` §3.1.1.

Do not rely on this prompt as a replacement for the detailed approved
specifications.

If a required document is missing, contradictory, or does not authorize a
permission or behavior, stop and report the discrepancy before implementing that
part.

## 3. Architecture requirements

Preserve the existing modular-monolith boundaries.

### Domain layer

- User and role domain types.
- Password policy/value object.
- Authentication and authorization rules.
- Session-related domain concepts where appropriate.

### Application layer

Implement appropriately separated services, including:

- `AuthenticationService`
- `AuthorizationService`
- `SessionService`
- User account management service
- Password management service

Service methods must enforce authorization themselves.

### Infrastructure layer

- SQLAlchemy repositories.
- Password hashing and verification.
- SQLite/Alembic persistence.
- Audit event integration.
- Safe database transactions.

### Presentation layer

Native PySide6 screens, dialogs, and reusable UI components.

Business rules must not depend on PySide6.

Do not introduce a web server, REST API, browser-based authentication, remote
identity provider, or cloud authentication.

## 4. Database implementation

Create the necessary Alembic migration after the existing migration head.

Expected existing migration head:

`0003_business_profile_requirements`

Implement only the tables, constraints, and indexes required by the approved
specifications.

Requirements:

- Local user accounts.
- Exactly one role per user.
- Centralized role and permission definitions.
- Case-insensitive unique usernames.
- Optional email contact field.
- Active/deactivated account state.
- Secure password hash storage.
- Required timestamps and audit-related fields.
- Appropriate database constraints and indexes.

Use the existing SQLAlchemy and migration conventions.

### Critical database safeguards

- Never delete or recreate the existing database.
- Never reset the database.
- Never drop existing tables.
- Never rewrite existing Business Profile records.
- Never alter existing historical audit records.
- Never silently downgrade migrations.
- Do not create a default user or seed user.
- Do not create sample business data.

Preserve all existing Phase 1–7 data and functionality.

Use transactions and appropriate constraints to protect critical operations.

## 5. Password security

Implement the owner-approved password hashing design.

### Primary algorithm

Argon2id using `argon2-cffi`.

Use the exact approved Argon2id parameters from:

`docs/AUTHENTICATION_SPECIFICATION.md` §3.1.1

Do not invent or silently change those parameters.

### Fallback algorithm

Use Python's `hashlib.scrypt` with the approved values:

- `N = 2**17`
- `r = 8`
- `p = 1`
- Explicitly configured `maxmem`, sufficient for the selected parameters and
  verified against the target environment.

Use the exact fallback and self-describing hash format documented in the
approved specification.

### Security requirements

- Unique cryptographically secure random salt per password.
- Constant-time hash verification.
- No plaintext passwords in database, logs, exceptions, or configuration.
- Never expose password hashes through UI or normal application responses.
- Never log credentials.
- Verify password hashes before permitting login.
- Support safe hash algorithm identification and future migration.
- Handle missing or unsupported hash dependencies safely.

If Argon2id cannot be initialized and the approved fallback cannot be used
safely, fail closed. Never store plaintext passwords.

### Password policy

Implement the approved policy:

- Minimum 8 characters.
- At least one uppercase letter.
- At least one lowercase letter.
- At least one digit.
- No password expiration.
- Users may change their own password after verifying their current password.
- Administrative password reset requires an explicit dialog where Owner/Admin
  enters and confirms the new password.

Do not introduce unapproved complexity rules.

## 6. First-run owner creation

Implement the explicit first-run account creation workflow.

Requirements:

- If no active user account exists, application enters first-run setup.
- Display a native Owner/Admin creation screen.
- Require username, password, and password confirmation.
- Apply the approved password policy.
- Do not create any default or seeded account.
- Do not allow normal application access before the initial Owner/Admin account
  is successfully created.
- Ensure concurrent or repeated first-run attempts cannot create multiple
  initial owner accounts unexpectedly.
- Use a transaction to protect initial account creation.
- After successful creation, proceed to the normal login/session workflow.

The initial account must receive the approved Owner/Admin role.

Do not introduce an in-app backdoor or recovery key.

## 7. Login and authentication

Implement username-only login.

Requirements:

- Username is case-insensitive.
- Email is optional and is not a login identity.
- Username changes are Owner/Admin-only.
- Verify account status before granting access.
- Reject deactivated accounts.
- Generic authentication failure messages must not reveal whether a username
  exists.
- Do not persist authentication tokens or sessions.
- Do not reuse `QSettings` for authentication state.

### Failed-login throttling

Implement the approved rule:

- Five failed login attempts trigger a 15-minute cooldown.
- Enforce the cooldown consistently.
- Prevent simple application restarts from bypassing the policy if the approved
  specification requires persistent throttling.
- Use safe time handling.
- Avoid leaking account existence through different cooldown responses.

Record the appropriate authentication audit events without recording passwords
or sensitive credentials.

## 8. Role-based authorization

Implement centralized permission definitions and an `AuthorizationService`.

Every sensitive application service operation must enforce its required
permission.

The UI may hide or disable unavailable actions, but UI visibility must never be
treated as authorization.

Use permission keys and centralized authorization checks.

Do not scatter role-name comparisons throughout the application.

### Approved roles

Exactly four roles:

1. Owner/Admin
2. Operator
3. Accountant/Reviewer
4. Viewer

Do not add roles without owner approval.

### Owner/Admin

Full access to approved application functionality, including:

- User and role administration.
- Business settings.
- Business and financial records.
- Backup and restore.
- Database relocation.
- Sensitive administrative operations.
- Audit history visibility and export.

Sensitive operations must be audited.

### Operator

- Create and edit day-to-day operational records in approved operational
  modules.
- No accounting or financial record access beyond permissions explicitly
  approved in the authorization matrix.
- No delete or cancel.
- No approval or posting.
- No export or print.
- No user/role management.
- No sensitive settings administration.
- No restore or relocation.
- No audit-history modification.

### Accountant/Reviewer

- Strictly read-only.
- May view financial records and reports.
- May view full customer and supplier balance details.
- No record creation or editing.
- No approval or posting.
- No review/verify action.
- Sensitive business settings hidden.

### Viewer

- Read-only access to approved visible modules.
- Financial amounts and financial reports hidden.
- No export or print.
- Sensitive information restricted.
- No create, edit, delete, approval, or posting permissions.

### Permission matrix safeguard

Read the authorization matrix carefully.

Implement only permissions marked as owner-approved.

Do not automatically grant permissions marked `P` (proposed) or `O` (open).

Do not interpret a role's general description as authorization for an individual
operation.

If an operation has no approved permission, deny it by default.

## 9. User administration

Implement the approved local user-management workflow.

Requirements:

- Owner/Admin can create users.
- Owner/Admin can assign one approved role per user.
- Owner/Admin can edit permitted account details.
- Owner/Admin can deactivate users.
- Deactivated accounts must not authenticate.
- Accounts are deactivated, never deleted.
- Multiple Owner/Admin accounts are allowed.
- An Owner/Admin may deactivate another Owner/Admin, with an audit event.
- The last active Owner/Admin cannot be deactivated or downgraded.
- Prevent changes that would leave the installation without an active
  Owner/Admin.
- Username rename is Owner/Admin-only.
- Email remains optional.

Protect concurrent user-administration operations using database transactions
and appropriate consistency checks.

## 10. Password change and administrative reset

### Self-service password change

- Require current password verification.
- Require new password and confirmation.
- Enforce password policy.
- Audit successful password changes.
- Invalidate privileged re-authentication state as specified.

### Administrative reset

- Owner/Admin enters a new password and confirmation in an explicit dialog.
- Do not generate or display temporary passwords.
- Audit administrative reset separately from self-service password changes.
- Never reveal the new password after the operation completes.

### All-admin-credentials-unavailable recovery

Do not implement an in-app backdoor, hidden administrator account, or recovery
key.

Document the approved offline owner recovery procedure in the appropriate
documentation.

## 11. Session management and idle lock

Implement in-memory session management only.

The session should contain the necessary authenticated user identity, role
snapshot, timestamps, lock state, and privileged re-authentication state.

Do not persist active sessions or authentication tokens.

### Idle lock

- Default idle timeout: 15 minutes.
- Configurable according to the approved specification.
- Password required to unlock.
- Record lock and unlock audit events.
- Timeout continues during modal dialogs.
- Closing the application while locked ends the session.
- Next launch requires fresh login.

### Timer reset rule

Only deliberate interaction with the application window resets the idle timer.

Do not reset it for:

- Internal timers.
- Background work.
- Log writes.
- UI redraws.
- OS activity outside the application.

### Background work during lock

Follow the approved split:

- Headless maintenance may continue.
- Data-surfacing workers must be suspended.
- No writes may occur on behalf of the locked user.

### Settings changes during an active session

Follow the approved rules:

- Idle timeout changes take effect at the next activity reset.
- Role/status/permission changes take effect at the next authorization check.
- Deactivation invalidates the session.
- Password change/reset invalidates privileged re-authentication state.

No hot account switching. A Switch User shortcut, if implemented, must perform
logout followed by login.

## 12. Audit integration

Preserve the existing append-only `audit_events` implementation and indefinite
retention.

Integrate new authentication and administration events with the existing audit
service.

Record appropriate events for:

- Successful and failed authentication.
- Account creation.
- Account deactivation.
- Username changes.
- Role changes.
- Password changes.
- Administrative password resets.
- Session lock and unlock.
- Logout.
- Relevant authorization/security events.
- Sensitive administrative operations.

Use the authenticated session actor for authenticated events.

Use `system/unauthenticated` for pre-authentication events as specified.

Do not rewrite historical audit rows.

Do not weaken repository, ORM, or SQLite append-only protections.

Do not introduce audit deletion or modification functionality.

Only Owner/Admin may view or export audit history. If audit viewing/export
functionality is not already in scope for this implementation, implement the
required authorization boundaries and event recording without expanding the UI
into an unrelated audit-management module.

Audit export, if implemented, must record `audit.exported`.

## 13. Native PySide6 UI

Integrate authentication screens into the existing application shell.

Expected screens/dialogs, subject to the approved workflows:

- First-run Owner/Admin setup.
- Login.
- Session lock/unlock.
- User management.
- Create/edit user.
- Password change.
- Administrative password reset.
- Role assignment.
- Deactivation confirmation.

Follow existing UI conventions:

- Clean, minimal, professional desktop UI.
- Calm green-based Light Mode.
- Professional Dark Mode.
- Consistent spacing and typography.
- Reusable controls and feedback components.
- Keyboard navigation and visible focus.
- Accessible labels and validation messages.
- Clear loading and error states.

Do not redesign unrelated screens.

Do not break the existing Business Profile, dashboard, backup, restore, or
relocation interfaces.

### Application startup flow

Implement a clear startup state flow:

1. Database setup/recovery checks.
2. Database migration compatibility checks.
3. First-run account setup if no account exists.
4. Login if accounts exist and no authenticated session exists.
5. Main application shell after successful authentication.
6. Session lock when idle timeout is reached.

Never display protected business data before authentication.

Do not change the existing database-location recovery behavior.

## 14. Application integration and security

Review all existing service entry points and ensure authorization cannot be
bypassed by calling services directly.

Do not rely solely on disabled UI controls.

Ensure:

- No protected data appears on the login screen.
- Deactivated users cannot continue accessing protected functionality.
- Authorization failures are handled consistently.
- Background workers respect session-lock rules.
- Exceptions do not leak secrets.
- Database transactions roll back safely on failure.
- Existing business services remain independent of UI authorization logic.

Do not introduce unnecessary dependencies.

If adding `argon2-cffi`, update the dependency manifest and packaging
configuration appropriately.

Verify that the application can still be packaged for Windows.

## 15. Testing requirements

Add comprehensive automated tests using pytest.

Use isolated temporary databases and test configurations.

Never run destructive tests against the owner's configured business database.

### Authentication tests

- First-run owner creation.
- Duplicate username rejection, including case-insensitive duplicates.
- Login success.
- Wrong password.
- Deactivated account login rejection.
- Failed-login cooldown.
- Cooldown expiration.
- Password policy.
- Password change.
- Administrative password reset.
- Hash verification and algorithm identification.
- Missing hashing dependency behavior.
- No plaintext password persistence.

### Authorization tests

Test each approved role against every implemented permission.

Verify:

- Owner/Admin access.
- Operator restrictions.
- Accountant/Reviewer read-only restrictions.
- Viewer financial-data restrictions.
- Proposed/open permissions denied by default.
- Direct service calls cannot bypass authorization.
- Last active Owner/Admin protection.
- Deactivated-user session invalidation.

### Session tests

- Session creation and logout.
- Idle timeout.
- Modal-dialog timeout behavior.
- Deliberate interaction timer reset.
- Non-interaction events do not reset timer.
- Lock/unlock.
- Application close while locked.
- Fresh login on next launch.
- Background-work restrictions.
- Permission and role changes during active sessions.

### Audit tests

- Authentication event recording.
- Account lifecycle event recording.
- Password event separation.
- Session lock/unlock events.
- Actor attribution.
- Append-only protections remain intact.
- Historical audit rows unchanged.

### Regression tests

Run the full existing test suite.

Explicitly verify that these existing modules remain functional:

- Database setup and recovery.
- Migration management.
- Backup and restore.
- Database relocation.
- Business Profile.
- Business Profile version history.
- Business Profile audit history.
- Existing application startup behavior.

Run Ruff and all relevant static checks.

Do not claim tests passed unless they were actually executed.

## 16. Documentation updates

Update the relevant documentation to reflect the implemented system:

- `docs/AUTHENTICATION_SPECIFICATION.md`
- `docs/AUTHORIZATION_MATRIX.md`
- `docs/USER_ACCOUNT_WORKFLOWS.md`
- `docs/SESSION_AND_IDLE_LOCK_SPECIFICATION.md`
- `docs/SECURITY_AND_DATA_PROTECTION.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_ROADMAP.md`

Clearly distinguish implemented functionality from future or unimplemented
functionality.

Do not silently change owner-approved requirements.

## 17. Scope restrictions

This phase must not implement:

- Business modules not already approved.
- New accounting functionality.
- Approval workflows or amount thresholds.
- Cloud or remote authentication.
- Email or OTP recovery.
- Default or seeded user accounts.
- In-app recovery backdoors.
- Multi-company or multi-tenant functionality.
- New roles.
- Unapproved permissions.
- Audit deletion or editing.
- Unrelated UI redesign.
- Database reset or destructive migration.
- New backup/restore architecture.

Do not use this phase to implement unrelated roadmap items.

## 18. Git and data protection

- Preserve existing uncommitted and untracked work.
- Never discard, overwrite, or reformat unrelated files.
- Never stage files.
- Never commit or push.
- Never rewrite Git history.
- Never modify the owner's configured business database for testing.
- Never run destructive migration tests against the live database.
- Use isolated test databases.
- Do not change backup settings or scheduled tasks without explicit approval.

## 19. Completion report

Create:

`Reports/PHASE_08B_REPORT.md`

The report must include:

1. Phase overview and implementation scope.
2. Repository state before and after.
3. Architecture and implementation details.
4. Database migration and schema changes.
5. Authentication implementation.
6. Password hashing implementation and exact parameters used.
7. Role and permission implementation.
8. Session and idle-lock implementation.
9. Audit integration.
10. UI screens and workflows.
11. Tests executed and exact results.
12. Ruff/static-check results.
13. Regression results.
14. Known limitations and deferred items.
15. Manual Windows verification checklist.
16. Security considerations.
17. Git status and confirmation that no commits/pushes were made.
18. Owner review and acceptance status — leave pending until the owner reviews
    it.

## 20. Completion criteria

Phase 8B may be reported as implementation-complete only when:

- All approved authentication requirements are implemented.
- All four approved roles behave according to the authorization matrix.
- Service-layer authorization is enforced.
- First-run owner creation is safe.
- Password hashing and verification work correctly.
- Failed-login throttling works.
- Session locking follows the approved rules.
- Audit integration preserves append-only behavior.
- Existing Phase 1–7 functionality remains intact.
- Full automated tests pass.
- Ruff/static checks pass.
- Documentation and report are updated.

If a requirement cannot be completed safely, document it as incomplete instead
of claiming success.

Do not begin another phase automatically.

**Stop after Phase 8B implementation, verification, documentation, and report
creation. Wait for owner review and explicit next-phase instruction.**
