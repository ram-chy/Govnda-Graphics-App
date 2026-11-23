# USER ACCOUNT WORKFLOWS — Local Accounts, Roles & Passwords

| Field | Value |
| --- | --- |
| Document | USER_ACCOUNT_WORKFLOWS.md |
| Phase | 8A specification; 8B implementation |
| Version | 1.0 (owner-approved specification 2026-11-22); 8B implementation note added 2026-11-23 |
| Date | 2026-11-22 |
| Status | SPECIFICATION APPROVED 2026-11-22 — IMPLEMENTED IN PHASE 8B, owner review pending |
| Related | AUTHENTICATION_SPECIFICATION.md, AUTHORIZATION_MATRIX.md, SESSION_AND_IDLE_LOCK_SPECIFICATION.md, PHASE_08_OWNER_DECISION_WORKSHEET.md, PHASE_08_IMPLEMENTATION_READINESS.md |

This document specifies the approved lifecycle workflows for local user accounts. It was specification-only in Phase 8A; Phase 8B implemented the `A`-marked workflows after explicit owner authorization. Each step is labelled with its decision status using the legend in `AUTHORIZATION_MATRIX.md` — `A` (approved), `P` (proposed), `O` (open owner decision), `D` (denied). An `O` or `P` step must not be built as though approved.

## Phase 8B implementation status (authoritative)

Implemented `A` workflows: first-run owner creation; login and logout; create/edit/rename user; assign role; activate/deactivate with last-active-Admin protection; self-service password change with current-password verification; administrative password reset; and append-only audit events for each lifecycle change. Passwords are never displayed, logged, or persisted in plaintext. Roles are assigned from exactly four approved keys; there is no separate `user_roles` table. All steps remain service-layer enforced with advisory-only UI hiding.

## 1. General workflow rules

- All account data belongs to the local installation (approved `A`).
- Every workflow is executed through application services; views only collect input and display results (approved `A`).
- Authorization is permission-based and enforced in the service layer, never only by hiding a control (approved `A`).
- No workflow may display, log, or persist a plaintext password, password hash, salt, or reset secret (approved `A`).
- Every sensitive workflow writes an append-only audit event with a non-secret actor derived from the session (approved `A`).
- Account identity is fully resolved (`P8A-01`, 2026-11-22): **username only**, email optional (not mandatory), case-insensitive uniqueness, and Owner/Admin-only username rename. Password policy is fully resolved (`P8A-02`, 2026-11-22): minimum 8 characters, uppercase + lowercase + digit, 5-attempt/15-minute cooldown, changes any time, no expiration. `P8A-03` is resolved (2026-11-22): multiple Owner/Admin accounts allowed, admins may disable other admins (audited) but never the last active admin, deactivate-only (never delete), and exactly one role per user. `P8A-08` is resolved (2026-11-22): admin-entered new password in an explicit dialog, with a documented offline owner procedure for total admin lockout (no in-app backdoor). These decisions constrain several steps below.

## 2. First-run Owner/Admin account creation

Status: workflow shape approved `A`; account identity fully approved (`P8A-01`, 2026-11-22) — username with case-insensitive uniqueness, optional email, Owner/Admin-only rename.

Trigger:

- Application has a valid, migrated database but **zero active Owner/Admin accounts** and no account records indicating a completed first-run setup.

Steps:

1. The application enters a dedicated first-run setup state before the main window is available (`A`).
2. The setup screen collects the initial Owner/Admin username (`A`, `P8A-01`), an optional email address (`A`), a password, and a matching password confirmation (`A`).
3. Validate that password and confirmation match and that the password satisfies the approved policy (`A`): at least 8 characters with uppercase, lowercase, and digit (`P8A-02`).
4. Validate username uniqueness case-insensitively (approved `P8A-01`); duplicate-account prevention is required (`A`).
5. Within one database transaction, create the account, assign the `owner_admin` role, and store the password hash (`A`).
6. Write audit event `auth.owner_account_created` with actor `system/unauthenticated`, because no authenticated user exists yet (`A`). No secret is included in the payload.
7. Mark first-run setup complete, then present the login screen (`A`).

Safety rules:

- No hardcoded default password, seed user, or automatic account is ever created (`A`).
- If setup is interrupted before the transaction commits, no partial account is left; the first-run state is shown again on next launch (`A`).
- The workflow must never leave an installation with no active Owner/Admin account (`A`).
- Concurrent first-run attempts must be serialized so exactly one initial owner can be created (`P` — concurrency detail to be confirmed against local single-instance behavior).

## 3. Login

Status: mechanism approved `A`; identity resolution by username with case-insensitive matching approved (`P8A-01`, 2026-11-22); throttling (5 attempts/15-minute cooldown) approved (`P8A-02`, 2026-11-22).

1. Show the native login screen before the main window (`A`).
2. Collect the username (approved identity, `P8A-01`) and the password (`A`).
3. Resolve the account and verify the password hash using constant-time comparison (`A`).
4. On failure, show a generic message that does not reveal whether the identity exists (`A`). Optionally record `auth.login_failed` with identity label only, subject to the failed-login auditing decision (`O`).
5. On success, create the in-memory session described in `SESSION_AND_IDLE_LOCK_SPECIFICATION.md` (`A`), record `auth.login_succeeded` (`A`), and open the main window (`A`).

A deactivated account cannot log in (`A`). A user with no active role assignment cannot log in (`P` — confirm as part of `P8A-03`).

## 4. Logout

Status: approved `A`.

1. User selects Logout.
2. Clear the in-memory session, revoke privileged re-authentication state, and discard any lock state (`A`).
3. Record `auth.logout` (`A`).
4. Return to the login screen; do not close the application unless the user chooses to (`A`).

## 5. Self-service password change

Status: workflow approved `A`; password rules approved (`P8A-02`); post-change session behavior `O`.

1. Authenticated user supplies the current password, a new password, and confirmation (`A`).
2. Verify the current password before accepting the change (`A`).
3. Confirm new password and confirmation match and satisfy the approved `P8A-02` policy (`A`).
4. Store the new hash in the same transaction that writes `auth.password_changed` (`A`). The event must be distinguishable from an administrative reset (`A`).
5. Invalidate privileged re-authentication state (`A`). Whether the current session stays authenticated or requires re-login is `O`.

## 6. Administrative password reset

Status: Owner/Admin authority and distinct audit event approved `A`; procedure approved (`P8A-08`, 2026-11-22) — admin enters a new password with confirmation in an explicit dialog; no generated temporary password.

1. Only an actor with `user.reset_password` may start this workflow (`A`).
2. Administrator selects the target account and enters a new password (and confirmation) through an explicit dialog (`A`, `P8A-08`). The target's old password is never displayed, derived, or logged (`A`).
3. Store the new hash and write `auth.password_reset_admin` in one transaction (`A`). This event must be distinguishable from `auth.password_changed` (`A`).
4. Immediately invalidate the target account's in-memory session and privileged re-authentication state (`A`). If the target is the current user, require re-login (`A`).
5. The reset procedure is approved (`P8A-08`, 2026-11-22) as described above. If all Owner/Admin credentials are unavailable, a documented offline owner procedure is followed (`A`, `P8A-08`, 2026-11-22); there is no in-app backdoor or recovery key. No self-service, email, or OTP recovery exists (`A`).

## 7. Create user account

Status: Owner/Admin authority approved `A`; account identity fully approved (`P8A-01`), including Owner/Admin-only rename; role scope `P8A-04`/`P8A-05`/`P8A-06`.

1. Only an actor with `user.create` may start (`A`).
2. Collect a username (approved identity, `P8A-01`) and optional email, plus an initial password with confirmation (`A`).
3. Enforce duplicate-account prevention (`A`) and the approved password policy per `P8A-02` (`A`).
4. Assign **exactly one role** to each account (`A`, `P8A-03`, 2026-11-22). Multiple Owner/Admin accounts are approved (`A`, 2026-11-22).
5. Create the account, role assignment(s), and password hash in one transaction and write `auth.user_created` (and `auth.role_assigned` for role changes) (`A`).
6. New accounts are active by default unless deactivation is explicitly chosen (`P` — confirm in `P8A-03`).

## 8. Edit user identity, activate, and deactivate

Status: activation/deactivation authority approved `A`; Owner/Admin-only username rename approved (`P8A-01`), email optional contact data `A`; last-admin safeguard approved (`P8A-03`, 2026-11-22).

- Editing identity fields requires `user.edit_identity`. Username rename is Owner/Admin-only (`A`, `P8A-01`); email is optional contact data (`A`). The edit writes `auth.user_updated` (`A`).
- Deactivation requires `user.deactivate` and writes `auth.user_deactivated` (`A`). A deactivated user cannot log in; any active session for that user is invalidated immediately (`A`).
- Activation requires `user.activate` and writes `auth.user_activated` (`A`).
- An Owner/Admin may deactivate another Owner/Admin, with an audited event (`A`, `P8A-03`, 2026-11-22). The last active Owner/Admin may **not** be deactivated or downgraded; at least one active Owner/Admin must always remain (`A`, `P8A-03`, 2026-11-22). The workflow must prevent an installation with no active Owner/Admin (`A`).
- Users are **deactivated only, never deleted** (`A`, `P8A-03`, 2026-11-22), preserving audit attribution. `user.delete` is not an approved permission and must not be implemented.

## 9. Role and permission assignment

Status: Owner/Admin authority approved `A`; role permission scopes `O`/`P`.

1. Role assignment changes require `user.assign_role` and write `auth.role_assigned` (`A`).
2. Permission-definition changes require `permission.change` and write `auth.permission_changed` (`A`).
3. Only the four approved role names may be assigned (`A`). No new role may be created without owner approval (`A`).
4. Concrete permission sets for Accountant/Reviewer (`P8A-04`), Viewer (`P8A-05`), and Operator's module-specific sensitive actions (`P8A-06`) are not approved; the UI must not present them as fixed grants (`O`).
5. Role assignment changes take effect on the next service-layer authorization check (`A`). Whether an existing session's role snapshot refreshes immediately is `O` (`P8A-07`).

## 10. View user list and access-denied feedback

Status: proposed `P` / open `O`.

- A user list showing non-secret account fields is proposed for Owner/Admin (`user.view`, `P`). No password or hash is ever displayed (`A`).
- Access-denied feedback must be a safe, non-revealing message rendered by a consistent dialog (`A`); exact wording and whether denials are audited are `O`.
- Audit viewing (`audit.view`) is approved for Owner/Admin only under `Q-22` (2026-11-22); all other roles are denied. Audit export (`audit.export`) is approved for Owner/Admin only, with each export recording an `audit.exported` event (`Q-22`, 2026-11-22).

## 11. Audit event summary

| Event | Trigger | Actor | Status |
| --- | --- | --- | --- |
| `auth.owner_account_created` | First-run owner creation | `system/unauthenticated` | `A` |
| `auth.user_created` | Create user | Authenticated admin | `A` |
| `auth.user_updated` | Edit identity | Authenticated admin | `P` (field scope `O`) |
| `auth.user_activated` / `auth.user_deactivated` | Activation state change | Authenticated admin | `A` |
| `auth.user_deleted` | Delete user | — | `D` — no deletion workflow approved (`P8A-03`: deactivate only) |
| `auth.role_assigned` | Role assignment change | Authenticated admin | `A` |
| `auth.permission_changed` | Permission definition change | Authenticated admin | `A` |
| `auth.login_succeeded` | Successful login | Newly authenticated user | `A` |
| `auth.login_failed` | Failed login | `system/unauthenticated` or identity label | `O` (scope decision) |
| `auth.logout` | Explicit logout | Ending user | `A` |
| `auth.password_changed` | Self-service change | Authenticated user | `A` |
| `auth.password_reset_admin` | Administrative reset | Authenticated admin | `A` |
| `auth.lock` / `auth.unlock` | Idle lock / unlock | Locked-in / resumed user | `A` |

All events use the existing append-only `audit_events` table with indefinite retention. Historical Business Profile events (`system/unauthenticated`) remain unchanged.
