# SESSION AND IDLE LOCK SPECIFICATION

| Field | Value |
| --- | --- |
| Document | SESSION_AND_IDLE_LOCK_SPECIFICATION.md |
| Phase | 8A specification; 8B implementation |
| Version | 1.0 (owner-approved specification 2026-11-22); 8B implementation note added 2026-11-23 |
| Date | 2026-11-22 |
| Status | SPECIFICATION APPROVED 2026-11-22 — IMPLEMENTED IN PHASE 8B, owner review pending |
| Related | AUTHENTICATION_SPECIFICATION.md, AUTHORIZATION_MATRIX.md, USER_ACCOUNT_WORKFLOWS.md, PHASE_08_OWNER_DECISION_WORKSHEET.md, UI_UX_BLUEPRINT.md |

This document specifies the approved in-memory session and automatic idle-lock behavior. It was specification-only in Phase 8A; Phase 8B implemented the `A`-marked behavior after explicit owner authorization. Status labels follow `AUTHORIZATION_MATRIX.md`: `A` (approved), `P` (proposed), `O` (open owner decision).

## Phase 8B implementation status (authoritative)

Implemented: a single in-memory session with no QSettings persistence; 15-minute default idle timeout configurable through `AppConfig.idle_timeout_seconds`; deliberate keyboard/mouse activity resets the timer while non-interaction events do not; application-modal lock screen requiring the locked-in user's password; timeout continues while modals are open; lock and unlock audit events; no hot switching; explicit exit control ends the session when locked; all service-layer authorization checks fail while locked. `MainWindow` installs the active idle monitor and lock flow; `app.ui.auth.session_guard.SessionGuard` provides a reusable equivalent component. Sensitive background work is gated by service-layer authorization; a dedicated data-surfacing worker suspension contract remains a follow-up as such workers are added.

## 1. Approved baseline

- Automatic lock after **15 minutes** of inactivity (`A`).
- The timeout is **configurable** (`A`).
- The **password of the locked-in user is required to unlock** (`A`).
- Lock and unlock events are recorded in audit history (`A`).
- Security-sensitive screens must not remain accessible behind a locked overlay; the implementation must not rely on a superficial overlay alone (`A`).

All `P8A-07` edge cases approved 2026-11-22: activity definition, modal-dialog timeout behavior, background-work split, logout+login-only switching, fresh-login-after-close, and settings-change effects. `P8A-07` is CLOSED.

## 2. Session state

Persisted (after a future approved migration; `A`):

- User account records, password hashes, account status, and role assignments.
- Authentication settings only if genuinely persistent.

In memory only (`A`):

| Field | Purpose |
| --- | --- |
| Authenticated user ID | Stable identity for actor attribution. |
| Identity label | Non-sensitive display label. |
| Role assignment snapshot | Permissions available to the session. |
| Login timestamp | Audit/session context. |
| Last-activity timestamp | Drives idle lock. |
| Lock state | Whether the session is currently locked. |
| Privileged re-authentication state | Temporary authorization for destructive actions (`P`). |

Not persisted (`A`): passwords, password hashes in config, session tokens, unlock tokens, or reset secrets. `QSettings` currently stores only window geometry and navigation; it must not be repurposed for authentication or session state.

## 3. What counts as user activity

Approved (`A`, `P8A-07`, 2026-11-22) — count as activity:

- Keyboard input and mouse interaction with the application.
- Navigation between screens and opening/closing views.
- Explicit interaction with dialogs and forms.

Approved (`A`, `P8A-07`, 2026-11-22) — **not** activity:

- Internal timers, background backup/catch-up work, log writes, or theme/rerender events.
- OS-level activity outside the application window.
- Network-less idle timers and scheduled runner processes.

The rationale is that idle lock protects an unattended application window, so only deliberate interaction with that window should postpone it.

## 4. Inactivity timer

Behavior (`A` unless noted):

1. The timer starts or resets when a session becomes authenticated or is unlocked (`A`).
2. Any qualifying activity resets the timer to the configured timeout (`A` — activity definition approved 2026-11-22).
3. When the elapsed inactive time reaches the configured timeout, the session enters the locked state (`A`).
4. The timer is in-process and in-memory; restarting the application requires a fresh login (`A`).
5. Default timeout is 15 minutes; the configurable value must be validated as a positive duration (`A`). Range limits and storage location (config vs database) are `O` (`P8A-07`).

## 5. Entering locked state

Steps (`A` unless noted):

1. Freeze the current in-memory session and record `auth.lock` with the locked-in user as actor (`A`).
2. Block **all** non-unlock routes: navigation, view creation, dialogs, view-model commands, and application service calls (`A`). Authorization checks must reject operations while locked regardless of role (`A`).
3. Present a native locked screen over the application that requests the locked-in user's password (`A`).
4. Do not expose business data, audit data, or settings behind the lock screen (`A`).

Security requirement (`A`): hiding or replacing the central widget is insufficient; lock enforcement must exist in the service/authorization layer so no alternate route can reach sensitive data.

## 6. Unlocking

1. The locked-in user enters their password (`A`).
2. Verify against the stored hash using constant-time comparison (`A`).
3. On success: resume the existing session (same user and role snapshot), reset the activity timer, record `auth.unlock`, and restore the prior view (`A`).
4. On failure: show a generic error, do not unlock, and apply the owner-approved throttling policy if any (`O` — `P8A-02`). No password is logged (`A`).
5. Unlocking does not create a new identity or a new session (`A`).

## 7. Background tasks while locked

Approved (`A`, `P8A-07`, 2026-11-22) — the proposed split is confirmed:

- Read-only/background maintenance such as the scheduled backup runner continues independently of GUI lock state, because it is a headless process and does not expose data through the locked UI.
- In-process background workers that could surface data through a dialog or view are suspended or queued until unlock.
- No background task may write business data on behalf of a locked user.

Suspending all background work (including headless maintenance) was **not approved**.

## 8. Modal dialogs and the idle timer

Approved (`A`, `P8A-07`, 2026-11-22): **the timeout continues during modal dialogs** — an open but untouched dialog still locks the app. Stronger unattended protection; may interrupt long data-entry dialogs. Pausing during modals was **not approved**.

## 9. Switching users

Approved (`A`, `P8A-07`, 2026-11-22): **no hot switching** — a user must explicitly log out (ending the session) and log in as the other user. This keeps actor attribution and permission snapshots unambiguous. A "Switch user" action that performs the same logout+login sequence is permitted. Hot switching was **not approved**.

## 10. Closing the application while locked

Approved (`A`, `P8A-07`, 2026-11-22):

- Closing while locked ends the in-memory session; no session is persisted (`A`).
- On the next launch the application shows the login screen (`A`).
- No "resume locked session" path exists; the user authenticates fresh (`A`).

## 11. Settings changes affecting an existing session

Approved (`A`, `P8A-07`, 2026-11-22):

- Changing the configured idle timeout takes effect on the current session at the next activity reset (not retroactively).
- Changing a user's role or status takes effect at the next service-layer authorization check; deactivation immediately invalidates the session (approved in `USER_ACCOUNT_WORKFLOWS.md`).
- Changing permission definitions takes effect immediately on subsequent checks.
- A password change or administrative reset invalidates privileged re-authentication state as specified in `USER_ACCOUNT_WORKFLOWS.md`.

## 12. UI integration

- Locked and unlock screens must follow `UI_UX_BLUEPRINT.md`: calm green Light Mode, professional Dark Mode, minimal readable layout, keyboard accessibility, consistent dialogs, and restrained semantic colors (`A`).
- Access-denied and failed-unlock feedback use the same consistent feedback components (`A`).
- Keyboard focus must move into the lock/unlock screen when locking, and back to the restored view on unlock (`P`).
- No screens are implemented in Phase 8A (`A`).
