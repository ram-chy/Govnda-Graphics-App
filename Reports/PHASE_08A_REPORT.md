# PHASE 08A REPORT — Authentication, Local User Accounts, Roles & Permissions Specification

## 1. Phase overview

Phase 8A is a **requirements finalization and technical specification** phase for authentication and authorization. It is documentation only. No application source, database schema, migration, login, password hashing, user management, permission check, audit change, seed user, backup change, or owner database change was made.

The owner explicitly approved the complete Phase 8A specification and authorization matrix and resolved all decisions on 2026-11-22 (documentation approval only). The owner also approved the hashing design (Argon2id via `argon2-cffi`, scrypt fallback). The final parameter security review was completed 2026-11-22 (`AUTHENTICATION_SPECIFICATION.md` §3.1.1): Argon2id values accepted; the deficient starting scrypt values were replaced by owner-approved `N=2**17, r=8, p=1` with explicit `maxmem`. The owner then accepted Phase 7D on 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`), clearing B-1. The gate is still **NOT READY FOR IMPLEMENTATION**: Phase 8B must not begin until the owner confirms the scrypt values and explicitly authorizes Phase 8B.

## 2. Mandatory inspection performed

All mandatory pre-implementation inspection steps from the Phase 8A prompt were completed before writing any document:

1. Repository structure and Git status inspected (`git status`, `git log`).
2. Master architecture and security documentation read (`ARCHITECTURE.md`, `SECURITY_AND_DATA_PROTECTION.md`, `DATABASE_SCHEMA.md`, `BLUEPRINT.md`, `UI_UX_BLUEPRINT.md`).
3. All Phase 7 reports read; Phase 7D checked explicitly (see §4).
4. Current database schema and migration head inspected: head is `0003_business_profile_requirements`; no auth-related tables exist.
5. Existing audit event implementation inspected: `audit_events` table, `system/unauthenticated` actor, append-only ORM guard and SQLite triggers, indefinite retention.
6. Application startup, session lifecycle, configuration, and data-path management inspected (`app/main.py`, `app/app_context.py`, `app/core/config.py`, `app/core/paths.py`, `app/services/database_runtime.py`). No authentication session exists; `QSettings` stores only window/navigation state.
7. Business Profile integration and UI components inspected (`BusinessProfileView`, `MainWindow`, profile service/repository and tests).
8. `OPEN_DECISIONS.md` and `DEVELOPMENT_ROADMAP.md` reviewed.

No existing work was overwritten. Uncommitted/untracked work from earlier phases was preserved.

## 3. Prerequisite discrepancy — Phase 7D (recorded, then cleared by owner)

The Phase 8A prompt requires reading Phase 7D acceptance records if available and recording a discrepancy if absent. The discrepancy below was recorded truthfully when no acceptance existed; no Phase 7D verification report was fabricated.

- At Phase 8A preparation: **no `Reports/PHASE_07D_REPORT.md` existed** and no acceptance record existed in the repository.
- `Reports/PHASE_07C_REPORT.md` stated Business Profile was **owner-acceptance pending**; its owner acceptance checklist was unchecked.
- This was recorded as blocker **B-1** in `PHASE_08_IMPLEMENTATION_READINESS.md` and in `OPEN_DECISIONS.md`.
- **Later on 2026-11-22:** the owner stated **"Phase 7D accepted"** and confirmed it should be recorded as written owner acceptance/waiver. `Reports/PHASE_07D_ACCEPTANCE.md` records that statement and clears B-1. No Phase 7D technical verification is claimed, and the Phase 7C report findings remain unchanged.

## 4. Documentation created

Seven required documents were created:

| Document | Purpose |
| --- | --- |
| `docs/AUTHENTICATION_SPECIFICATION.md` | Local auth design, password hashing proposal, core operations, actor attribution, architecture placement. |
| `docs/AUTHORIZATION_MATRIX.md` | Centralized permission catalogue and role matrix with `A`/`P`/`O`/`D` status markers. |
| `docs/USER_ACCOUNT_WORKFLOWS.md` | First-run owner creation, login/logout, password change/reset, user/role administration workflows. |
| `docs/SESSION_AND_IDLE_LOCK_SPECIFICATION.md` | Session state, idle timer, lock/unlock, background tasks, settings effects. |
| `docs/PHASE_08_OWNER_DECISION_WORKSHEET.md` | All open decisions with IDs, options, recommendations, and one-question-at-a-time process. |
| `docs/PHASE_08_IMPLEMENTATION_READINESS.md` | Readiness verdict **NOT READY**, blockers, prerequisites, and future Phase 8B scope. |
| `Reports/PHASE_08A_REPORT.md` | This report. |

Two existing documents were updated:

| Document | Update |
| --- | --- |
| `docs/OPEN_DECISIONS.md` | Recorded Phase 8A confirmed decisions, the Phase 7D discrepancy, and new open `P8A-xx` decision IDs. |
| `docs/DEVELOPMENT_ROADMAP.md` | Added a Phase 8A planning/specification-only status; explicitly does **not** claim authentication is implemented. |

## 5. Decisions already confirmed (owner-approved)

Carried accurately from the Phase 8A owner instruction and prior documentation:

- Multiple **local user accounts** belong to the local installation.
- **No cloud/remote authentication**, web server, OTP, email recovery, or web auth framework.
- **Role-based access control** with exactly four approved role names: Owner/Admin, Operator, Accountant/Reviewer, Viewer. No new roles without owner approval.
- **Owner/Admin** full access to all modules and operations including user/role/permission management, settings, business/financial records, backup/restore, relocation, and sensitive admin operations; sensitive operations audited.
- **Operator** baseline: create/edit day-to-day records; cannot manage users/roles/settings, restore, relocate, or modify/delete audit history. Delete/cancel/approve/post must be defined separately per module.
- **Password recovery** manually managed by Owner/Admin; no self-service/email/OTP recovery.
- Password changes and administrative resets are **distinct audit events**.
- **Idle lock after 15 minutes**, configurable, password required to unlock, lock/unlock events recorded.
- **Service-layer permission enforcement** and **centralized permission definitions**; UI hiding is not authorization.
- **Explicit first-run owner creation** with password confirmation and no default/seed user.
- Existing audit infrastructure, indefinite retention, and Business Profile audit behavior are preserved.

## 6. Unresolved owner decisions

All are recorded in `PHASE_08_OWNER_DECISION_WORKSHEET.md` and `OPEN_DECISIONS.md`. None may be treated as approved:

| ID | Topic |
| --- | --- |
| `P8A-01` | Account identity: username, email, or both; uniqueness/case; email mandatory; username changes (**RESOLVED 2026-11-22 — see §11**) |
| `P8A-02` | Password policy: length, complexity, failed-login throttling, change policy, expiration (**RESOLVED 2026-11-22 — see §11**) |
| `P8A-03` | User administration: multiple admins, disabling admins/last admin, delete vs deactivate, role cardinality (**RESOLVED 2026-11-22 — see §11**) |
| `P8A-04` | Accountant/Reviewer permission scope (**RESOLVED 2026-11-22 — see §11**) |
| `P8A-05` | Viewer permission scope (**RESOLVED 2026-11-22 — see §11**) |
| `P8A-06` | Operator module-specific sensitive permissions (**RESOLVED 2026-11-22 — see §11**) |
| `P8A-07` | Session/locking edge cases (**RESOLVED 2026-11-22 — see §11**) |
| `P8A-08` | Administrative reset procedure and all-credentials-unavailable recovery (**RESOLVED 2026-11-22 — see §11**) |
| `Q-22` | Audit visibility and future event scope (**RESOLVED 2026-11-22 — see §11**) |
| `B6-10` | Approval policies and thresholds (**RESOLVED 2026-11-22 — no approvals in v1 — see §11**) |

Permission items in the authorization matrix marked `P` (proposed) or `O` (open) — including Business Profile permissions, manual backup, schedule/upgrade actions, and user view — are likewise not approved.

## 7. Recommended authentication architecture

- **Layered placement:** domain types and password value object; application services (`AuthenticationService`, `AuthorizationService`, `SessionService`, user/password services); infrastructure repositories and hasher; presentation screens — preserving the existing modular-monolith boundaries.
- **Password storage:** Owner approved 2026-11-22: Argon2id via `argon2-cffi` with calibrated parameters and `hashlib.scrypt` fallback if the new dependency is rejected. Self-describing hash strings, per-password random salt, constant-time verification, no secret logging. Final parameter review completed 2026-11-22: Argon2id values accepted and corrected scrypt fallback `N=2**17, r=8, p=1` approved (`B-4` cleared).
- **RBAC:** centralized permission keys resolved by an `AuthorizationService`; every sensitive service method checks `require(permission_key)`. No scattered role-name comparisons; UI hiding is advisory only.
- **Actor attribution:** new events use a non-secret actor from the session; pre-authentication events use `system/unauthenticated`; historical rows unchanged. All events use the append-only `audit_events` table with indefinite retention.
- **Session:** authenticated user ID, role snapshot, timestamps, lock state, and privileged re-auth state are in-memory only; no persisted session token. `QSettings` is not reused for auth state.
- **Data:** future Alembic migration adds user/role/permission tables after head `0003_business_profile_requirements`; no change to existing tables or audit data. Idle timeout may live in validated config.
- **Scope:** a small-business desktop design — not a generic enterprise IAM platform; fully offline with no network listener.

## 8. Implementation blockers

| ID | Blocker |
| --- | --- |
| B-1 | Owner accepted Phase 7D on 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`); gate cleared. |
| B-2 | Owner approval of the complete specification and authorization matrix granted 2026-11-22 (documentation only); gate cleared. |
| B-3 | All owner decisions (`P8A-01`–`P8A-08`, `Q-22`, `B6-10`) resolved since this report (see §11); gate cleared. |
| B-4 | Hashing design/algorithm/dependency owner-approved 2026-11-22; final parameter review complete and corrected scrypt fallback `N=2**17, r=8, p=1` approved; gate cleared. |

Full detail and the prerequisite checklist are in `PHASE_08_IMPLEMENTATION_READINESS.md`.

## 9. Verification of Phase 8A scope restrictions

| Requirement | Result |
| --- | --- |
| Existing owner decisions preserved accurately | PASS — §5 and the specification/matrix documents. |
| Proposed permissions distinguished from approved | PASS — `A`/`P`/`O`/`D` markers used throughout. |
| No unanswered permission treated as approved | PASS — open items excluded from grants; gated in readiness doc. |
| Documentation agrees with existing architecture | PASS — inspected implementation before writing. |
| No application code or database files modified | PASS — no source/schema/migration/database file changed. |
| Git status recorded before and after | PASS — §10. |
| No commit, push, stage, or history rewrite | PASS. |

## 10. Git status

Status at the end of Phase 8A:

```text
## main...origin/main
 M docs/DEVELOPMENT_ROADMAP.md
 M docs/OPEN_DECISIONS.md
?? "Prompt/Phase 7C — Business Profile Acceptance & Windows Integration Verification.md"
?? "Prompt/Phase 8A — Authentication, Local User Accounts, Roles & Permissions Specification.md"
?? Reports/PHASE_07C_REPORT.md
?? Reports/PHASE_08A_REPORT.md
?? docs/AUTHENTICATION_SPECIFICATION.md
?? docs/AUTHORIZATION_MATRIX.md
?? docs/PHASE_08_IMPLEMENTATION_READINESS.md
?? docs/PHASE_08_OWNER_DECISION_WORKSHEET.md
?? docs/SESSION_AND_IDLE_LOCK_SPECIFICATION.md
?? docs/USER_ACCOUNT_WORKFLOWS.md
```

No files staged. No commits made. No pushes made. No Git history rewritten. Uncommitted/untracked work from earlier phases preserved.

## 11. Owner decisions — all resolved

The one-question-at-a-time process in `PHASE_08_OWNER_DECISION_WORKSHEET.md` ran to completion on 2026-11-22; no Phase 8A owner question remains pending. The first decision in that process was:

> **`P8A-01` — Account identity: should a user log in with a username, an email address, or both?**

**`P8A-01` is RESOLVED (all owner answers 2026-11-22), recorded in `OPEN_DECISIONS.md`, the worksheet, and affected specification documents:** login identity = **username only**; email is an optional contact field and therefore not mandatory; username uniqueness is **case-insensitive**; username rename is **Owner/Admin-only**.

`P8A-02` is **RESOLVED** (owner decisions 2026-11-22, recorded in `OPEN_DECISIONS.md`, the worksheet, and affected specification documents): **minimum length = 8 characters**, **complexity = uppercase + lowercase + digit**, **failed logins trigger a temporary cooldown after 5 attempts for 15 minutes**, **users may change their own password at any time** after verifying the current one, and **passwords do not expire**. Under `P8A-03`, owner decided 2026-11-22: **multiple Owner/Admin accounts are allowed**. An Owner/Admin **may deactivate another Owner/Admin**, with an audited event. The **last active Owner/Admin may not be deactivated (or downgraded)**, so at least one active admin always remains. User accounts are **deactivated only, never deleted** (preserving audit attribution). Each user holds **exactly one role**. This closes `P8A-03`. Under `P8A-08`, owner decided 2026-11-22: an Owner/Admin **enters a new password with confirmation in an explicit dialog** for a reset (no generated temporary password). If all Owner/Admin credentials are unavailable, a **documented offline owner procedure** is followed (no in-app backdoor or recovery key). This closes `P8A-08`. Under `P8A-04`, owner decided 2026-11-22: Accountant/Reviewer may **view all financial records and reports**. No other permission is granted by that answer. The owner then decided **no create/edit of any records** — viewing only. The owner then decided **no approval or posting authority** for this role (no approval authority for this role; `B6-10` resolved with no approvals in v1). The owner then decided **full customer/supplier balance details are visible** to this role. The owner then decided **sensitive business settings are hidden** from this role. The owner then decided **no explicit review/verify action**, making the role strictly read-only. This closes `P8A-04`. Under `P8A-05`, owner decided 2026-11-22: Viewer may see **all modules in read-only mode**. The owner then decided **financial amounts and reports are hidden** from Viewer, that **export is not permitted**, that **print is not permitted**, and that **sensitive information is restricted**. This closes `P8A-05` as a low-privilege read-only role. Under `P8A-06`, owner decided 2026-11-22: Operator may create/edit records in **all day-to-day operational modules**, not accounting/financial records. The owner then decided **no delete or cancel**, **no approval or posting** (no approval authority for this role; `B6-10` resolved with no approvals in v1), and **no export or print**. This closes `P8A-06`. Under `P8A-07`, owner decided 2026-11-22: only **deliberate interaction with the application window** resets the idle timer; internal timers, background work, log writes, redraws, and OS activity outside the app do not. The owner then decided the idle timeout **continues during modal dialogs** (an untouched dialog still locks). The owner then approved the **background-work split** (headless maintenance continues; data-surfacing workers suspended; no writes for a locked user). The owner then decided **no hot switching** — logout + login only (a 'Switch user' shortcut may perform that same sequence). The owner then decided that **closing while locked ends the session and the next launch shows a fresh login** (no resume-locked-session path). The owner then approved the proposed settings-change rules (idle timeout at next activity reset; role/status and permission changes at next authorization check; deactivation invalidates the session; password change/reset invalidates privileged re-auth state). This closes `P8A-07`. Under `Q-22`, owner decided 2026-11-22: **only Owner/Admin accounts may view audit history**. The owner then decided audit history may be **exported by Owner/Admin only**, with each export recording an `audit.exported` event. The owner then decided to record **all significant business, security, and admin events** — sensitive/admin actions, authentication and account-lifecycle events, audit view/export events, and business record changes (create/edit/delete, approval/posting, financial adjustments); existing historical rows (`system/unauthenticated`) remain unchanged. This closes `Q-22`. Under `B6-10`, owner decided 2026-11-22: **no approval workflow and no amount thresholds in v1**; no actions require approval, no role has approval/posting authority, and Owner/Admin performs sensitive actions directly with auditing. This closes `B6-10`. All owner decisions are resolved; the complete specification/authorization matrix and hashing design are approved. Phase 7D owner acceptance was subsequently recorded on 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`), clearing B-1. The final hashing-parameter review is now complete (`AUTHENTICATION_SPECIFICATION.md` §3.1.1): Argon2id values accepted and corrected scrypt fallback `N=2**17, r=8, p=1` approved. Phase 8B implementation must not begin until the owner explicitly authorizes it. The owner then **explicitly approved the complete Phase 8A specification and authorization matrix on 2026-11-22** — documentation approval only, not implementation authorization. The owner also approved the hashing design (Argon2id/`argon2-cffi`, scrypt fallback; final parameter review completed 2026-11-22; corrected scrypt fallback approved). Phase 7D owner acceptance is recorded in `Reports/PHASE_07D_ACCEPTANCE.md` (B-1 cleared); explicit Phase 8B authorization remains before implementation.

## 12. Next steps after owner response

1. `P8A-01` answers have been recorded in `OPEN_DECISIONS.md`, the worksheet, and affected documents (2026-11-22).
2. `P8A-02` answers have been recorded in `OPEN_DECISIONS.md`, the worksheet, and affected documents (2026-11-22).
3. `P8A-03` answers recorded (multiple admins allowed; admin may disable another with audit; last active admin protected; deactivate only; exactly one role per user).
4. All decisions are resolved and explicit owner approval of the complete specification and authorization matrix was granted 2026-11-22 (B-2, B-3 cleared).
5. B-1 and B-4 are cleared (owner acceptance and completed review/approval, 2026-11-22). Still required before Phase 8B: explicit owner authorization.
