# PHASE 08 IMPLEMENTATION READINESS

| Field | Value |
| --- | --- |
| Document | PHASE_08_IMPLEMENTATION_READINESS.md |
| Phase | 8A readiness gate; 8B authorization recorded later |
| Version | 1.1 (owner approval recorded 2026-11-22; Phase 8B implementation authorization recorded 2026-11-22) |
| Date | 2026-11-22 |
| Status | **Historical: NOT READY at the end of Phase 8A** — explicit Phase 8B authorization was later given 2026-11-22 and implementation completed 2026-11-23 |
| Related | AUTHENTICATION_SPECIFICATION.md, AUTHORIZATION_MATRIX.md, USER_ACCOUNT_WORKFLOWS.md, SESSION_AND_IDLE_LOCK_SPECIFICATION.md, PHASE_08_OWNER_DECISION_WORKSHEET.md, Reports/PHASE_08A_REPORT.md |

This document records the readiness gate for Phase 8B (authentication implementation) as it stood at the end of Phase 8A. Phase 8A produced **specification only**; no code, schema, migration, seed user, or database change was made. The historical verdict was **NOT READY**: B-1 and B-4 were cleared, but explicit implementation authorization was still pending. **Update 2026-11-23:** the owner explicitly authorized Phase 8B on 2026-11-22, and the implementation is recorded in `Reports/PHASE_08B_REPORT.md`. The verdict statements below are retained as the Phase 8A gate record and are superseded by that authorization.

## 1. Readiness verdict

| Gate | Result | Detail |
| --- | --- | --- |
| Specification documents complete | PASS | Seven Phase 8A deliverables created (see report). |
| Existing decisions preserved | PASS | Approved decisions carried from Phase 8A owner instruction and prior docs. |
| Proposed vs approved clearly separated | PASS | `A` / `P` / `O` / `D` markers used across all documents. |
| No unanswered permission treated as approved | PASS | Open permissions are marked `O` and excluded from the role matrix grants. |
| Architecture consistency | PASS | Design follows modular-monolith layering and existing audit/config constraints. |
| Phase 7D acceptance record present | **PASS** | Owner accepted Phase 7D on 2026-11-22; recorded in `Reports/PHASE_07D_ACCEPTANCE.md`. No Phase 7D verification report was invented. |
| Owner approval of complete specification + authorization matrix | **PASS** | Explicitly approved 2026-11-22 (approval documentation only, not implementation authorization). |
| Owner decisions on open items resolved | **PASS** | `P8A-01`–`P8A-08`, `Q-22`, and `B6-10` all resolved (2026-11-22). |
| No code/database changes in Phase 8A | PASS | Verified in `Reports/PHASE_08A_REPORT.md`. |
| Hashing parameters owner-approved | **PASS** | Argon2id accepted; corrected scrypt `N=2**17, r=8, p=1` approved 2026-11-22 after security review (`AUTHENTICATION_SPECIFICATION.md` §3.1.1). |
| Migration approach confirmed | **PASS** | New tables only, Alembic revision after `0003_business_profile_requirements`, no downgrade with audit data (§3 item 5). |
| Service-layer test requirement confirmed | **PASS** | Authorization and lock enforcement tested at the service layer, not only via UI (§3 item 6). |

**Overall at end of Phase 8A: NOT READY FOR IMPLEMENTATION.** All six prerequisites in §3 were cleared, but Phase 8B had to wait for explicit implementation authorization. On 2026-11-22 the owner was asked to authorize Phase 8B; the historical Phase 8A record captured the block at that point. **Superseded 2026-11-22:** the owner then explicitly authorized Phase 8B, and that implementation was completed 2026-11-23.

## 2. Blockers

### B-1 — Phase 7D owner acceptance (**cleared 2026-11-22**)

The Phase 8A prompt requires reading Phase 7D acceptance records if available and recording a prerequisite discrepancy if none exists. That discrepancy was recorded here and in `Reports/PHASE_08A_REPORT.md` §3 when no Phase 7D acceptance existed; no verification report was invented.

- The owner then stated **"Phase 7D accepted"** on 2026-11-22 and confirmed it should be recorded as written owner acceptance/waiver.
- `Reports/PHASE_07D_ACCEPTANCE.md` records that statement. No `Reports/PHASE_07D_REPORT.md` was created and no Phase 7D technical verification is claimed.
- `Reports/PHASE_07C_REPORT.md` findings and its unchecked owner checklist remain unchanged as the historical verification record.
- Impact: the owner-accepted Business Profile baseline now exists; the B-1 prerequisite discrepancy is closed.
- This clears B-1 only. It does not authorize Phase 8B implementation.

### B-2 — Complete specification approved (2026-11-22; gate cleared)

The owner explicitly approved the complete Phase 8A specification and authorization matrix (all seven deliverables) on 2026-11-22. This is approval of the documentation only — it does not authorize Phase 8B implementation. B-1 is cleared by owner acceptance and B-4 is cleared by the completed review plus owner approval of the final scrypt values; explicit Phase 8B authorization remains outstanding.

### B-3 — Owner decisions (**all resolved 2026-11-22; gate cleared**)

`P8A-01` (account identity) is **resolved** (2026-11-22): username only, optional email, case-insensitive uniqueness, Owner/Admin-only rename. `P8A-02` (password policy) is **resolved** (2026-11-22): min 8 characters, uppercase + lowercase + digit, 5-attempt/15-minute cooldown, change any time, no expiration. `P8A-03` (user administration) is **resolved** (2026-11-22): multiple Owner/Admin accounts allowed; an admin may disable another admin (audited); the last active admin cannot be deactivated; users are deactivated only (never deleted); exactly one role per user. `P8A-08` (recovery) is **resolved** (2026-11-22): an Owner/Admin enters a new password in an explicit dialog; a documented offline owner procedure handles total admin lockout (no in-app backdoor). `P8A-04` (Accountant/Reviewer) is **resolved** (2026-11-22): strictly read-only — full financial record/report and balance viewing; no create/edit, approval/posting, review/verify action, or sensitive settings. `P8A-05` (Viewer) is **resolved** (2026-11-22): low-privilege read-only — all modules view-only, with financial figures and sensitive information hidden and no export or print. `P8A-06` (Operator) is **resolved** (2026-11-22): create/edit in all day-to-day operational modules only; no delete/cancel, approve/post, or export/print. `P8A-07` (session edge cases) is **resolved** (2026-11-22): only deliberate interaction with the application window resets the idle timer and the timeout continues during modal dialogs; headless background maintenance continues while locked while data-surfacing workers are suspended and no task writes for a locked user; users may not hot-switch accounts (logout + login only, with an optional 'Switch user' shortcut); closing while locked ends the session and the next launch shows a fresh login; settings-change rules are approved (idle timeout at next activity reset; role/status and permission changes at next authorization check; deactivation invalidates the session; password change/reset invalidates privileged re-auth state). `Q-22` (audit visibility) is **resolved** (2026-11-22): only Owner/Admin may view audit history and export it (with an `audit.exported` event), and all significant business, security, and admin events are recorded (sensitive/admin actions, authentication and account-lifecycle events, audit view/export, and business record changes). Existing historical rows (`system/unauthenticated`) remain unchanged; retention is indefinite and append-only. `B6-10` (approval policies) is **resolved** (2026-11-22): no approval workflow and no amount thresholds in v1; no role has approval/posting authority and Owner/Admin performs sensitive actions directly with auditing. All owner decisions are resolved. No default, recommendation, or proposed permission may be implemented as approved until the complete specification is explicitly approved.

### B-4 — Hashing review complete; final parameters owner-approved (**gate cleared**)

The owner approved 2026-11-22: **Argon2id via `argon2-cffi`** (`time_cost = 3`, `memory_cost = 65536` KiB, `parallelism = 1`, `hash_len = 32`, 16-byte random salt, PHC string), with **`hashlib.scrypt` as the fallback**. No dependency was added in Phase 8A.

Final parameter security review completed 2026-11-22 (recorded in `AUTHENTICATION_SPECIFICATION.md` §3.1.1, against the OWASP Password Storage Cheat Sheet):

- **Argon2id values are acceptable unchanged**; benchmark on target hardware during Phase 8B (target under one second).
- The originally proposed scrypt fallback `n=2**14, p=1` was **below the cited OWASP minimum** (`p=5` at that `N`).
- The owner approved the corrected final fallback on 2026-11-22: **`N=2**17`, `r=8`, `p=1`, `dklen=32`, 16-byte salt, explicit `maxmem` above 128 MiB** (~0.365 s locally). Argon2id values remain unchanged.
- B-4 is cleared. Target-hardware benchmarking remains a Phase 8B implementation acceptance check.

## 3. Prerequisites to clear before Phase 8B

1. Owner acceptance of Business Profile (Phase 7D record or documented waiver) — **cleared 2026-11-22** (`Reports/PHASE_07D_ACCEPTANCE.md`).
2. Owner approval of the complete Phase 8A specification and authorization matrix — **cleared 2026-11-22**.
3. Owner answers to all `P8A-xx` items, `Q-22`, and `B6-10` (recorded in `OPEN_DECISIONS.md`) — **cleared**.
4. Owner approval of hashing design/algorithm/dependency and final parameters — **cleared 2026-11-22** (review complete; corrected scrypt values approved).
5. Confirmation of the future migration approach — **confirmed 2026-11-22**: new tables only (users/roles/permissions), a new Alembic revision after the current head `0003_business_profile_requirements`, no changes to existing tables or historical audit rows, and no downgrade path once audit data exists (forward-only migration). This is a planning confirmation only; no migration or schema change was made in Phase 8A.
6. Confirmation that all service-layer authorization and lock enforcement is tested, not only UI visibility — **confirmed 2026-11-22**: every permission and lock rule gets a service-layer test so protected operations are rejected even if the UI is bypassed; UI tests verify presentation only. This is a planning confirmation only; no tests were added in Phase 8A.

## 4. What Phase 8B will require (once unblocked)

For planning only, not approved:

- New Alembic migration adding user/role/permission tables (no changes to existing tables or audit data).
- Domain types, repositories, password hasher, and application services in the existing layer structure.
- Native PySide6 screens for login, first-run owner creation, user management, password change/reset, locked/unlock, and access-denied feedback.
- Centralized permission definitions and service-layer enforcement.
- Authentication audit events using the existing append-only `audit_events` table; historical rows unchanged.
- Tests for every permission, workflow, and lock behavior; Ruff and full pytest passing before any phase gate.

## 5. Scope discipline reminder

Phase 8A did **not** modify application source, schema, migrations, audit infrastructure, Business Profile behavior, backup/restore, the owner's database, or Git history. The owner explicitly approved the specification and matrix on 2026-11-22 and accepted Phase 7D on 2026-11-22, clearing B-1. Phase 8B nevertheless remains prohibited until the owner explicitly authorizes it; the owner was asked on 2026-11-22 and explicitly chose to keep implementation blocked. The hashing-parameter review is complete, the final scrypt values are approved, and the algorithm/dependency decision is cleared.
