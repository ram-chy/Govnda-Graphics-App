# PHASE 08 OWNER DECISION WORKSHEET

| Field | Value |
| --- | --- |
| Document | PHASE_08_OWNER_DECISION_WORKSHEET.md |
| Phase | 8A decision worksheet; 8B authorization recorded later |
| Version | 1.1 (all decisions and specification approved 2026-11-22; Phase 8B implementation authorized 2026-11-22) |
| Date | 2026-11-22 |
| Status | DECISIONS RESOLVED — Phase 8B implementation authorized 2026-11-22 and completed 2026-11-23; owner review pending |
| Related | AUTHENTICATION_SPECIFICATION.md, AUTHORIZATION_MATRIX.md, USER_ACCOUNT_WORKFLOWS.md, SESSION_AND_IDLE_LOCK_SPECIFICATION.md, OPEN_DECISIONS.md |

This worksheet lists every unresolved Phase 8A decision. Each item is **OPEN** until the owner answers; a recommendation is a planning option only and is **not** an approval. This worksheet does not duplicate the approved decisions in `AUTHENTICATION_SPECIFICATION.md` and `AUTHORIZATION_MATRIX.md`.

## 1. Decision process

1. **One essential question at a time.** Ask the owner one decision (starting with `P8A-01`); wait for the answer before asking the next.
2. **No assumed defaults.** An unanswered item must not be implemented as a recommendation or provisional default.
3. **Record the outcome.** For each decided item, capture: decision ID, approved option, owner, date, and the documents/rules affected. Then update `docs/OPEN_DECISIONS.md`.
4. **Traceability.** Existing identifiers (`Q-xx`, `AQ-xx`, `SQ-xx`, `B6-xx`) keep their meanings; new Phase 8A items use `P8A-xx`.
5. **Gate.** Phase 8B implementation was to start only after explicit owner authorization. The specification, matrix, Phase 7D acceptance, hashing-parameter review, and final scrypt values were recorded (see `PHASE_08_IMPLEMENTATION_READINESS.md` and `Reports/PHASE_07D_ACCEPTANCE.md`). That authorization was given 2026-11-22 and implementation completed 2026-11-23.

## 2. Decision index and approved-vs-open status

| ID | Topic | Status | Blocks |
| --- | --- | --- | --- |
| P8A-01 | Account identity rules | **RESOLVED 2026-11-22** | Schema identity fields, login, duplicate rules, user management |
| P8A-02 | Password policy | **RESOLVED 2026-11-22** | Password validation, throttling, expiry |
| P8A-03 | User administration & role assignment strategy | **RESOLVED 2026-11-22** | Admin safeguards, deactivate-only, role cardinality |
| P8A-04 | Accountant/Reviewer permission scope | **RESOLVED 2026-11-22 — strictly read-only** | — |
| P8A-05 | Viewer permission scope | **RESOLVED 2026-11-22 — low-privilege read-only** | — |
| P8A-06 | Operator module-specific sensitive permissions | **RESOLVED 2026-11-22** | — |
| P8A-07 | Session and locking edge cases | **RESOLVED 2026-11-22** | — |
| P8A-08 | Administrative recovery procedure | **RESOLVED 2026-11-22** | — |
| Q-22 (visibility) | Audit visibility and future event scope | **RESOLVED 2026-11-22** | — |
| B6-10 | Approval policies and thresholds | **RESOLVED 2026-11-22 — no approvals in v1** | — |

Already approved by the Phase 8A owner instruction (not decisions to re-ask): multiple local accounts; no cloud/remote auth; RBAC with exactly four role names; Owner/Admin full access; Operator baseline create/edit with listed denials; manual Owner/Admin password recovery; distinct password-change and reset audit events; 15-minute configurable idle lock with password unlock and lock/unlock audit events; service-layer permission enforcement; centralized permission definitions; explicit first-run owner creation with no seed user.

## 3. Account identity — `P8A-01`

**Decision log — 2026-11-22, Owner (all sub-questions answered; `P8A-01` CLOSED):** login identity = **Username only**. Email is an optional contact field and is therefore **not mandatory**. Uniqueness is **case-insensitive** (`Ram`/`RAM`/`ram` treated as the same username). Username rename is **Owner/Admin-only** (users cannot rename themselves).

| Question | Options | Status | Affects |
| --- | --- | --- | --- |
| What identifies a user at login? | Username only / email only / both | **DECIDED: Username only** (2026-11-22) | `users` fields, login screen, audit labels |
| Is email mandatory? | Yes / No | **DECIDED: No** (optional contact field) | Onboarding and schema nullability |
| How is uniqueness enforced? | Case-sensitive / case-insensitive | **DECIDED: Case-insensitive** (2026-11-22) | Constraints, duplicate validation |
| Can usernames be changed? | Yes / No / Admin-only | **DECIDED: Admin-only rename** (2026-11-22) | Edit workflow, `user.edit_identity` |

## 4. Password policy — `P8A-02`

**Decision log — 2026-11-22, Owner (`P8A-02` CLOSED):** minimum password length = **8 characters**; complexity requires **at least one uppercase letter, one lowercase letter, and one digit**; failed logins trigger a **temporary cooldown after 5 consecutive attempts for 15 minutes** (audited); users may change their own password **at any time** after verifying the current one (no forced first-login change); passwords **do not expire**. No symbol requirement and no permanent/manual-unlock lockout.

| Question | Options | Status |
| --- | --- | --- |
| Minimum length? | 8 / 10 / 12 / owner value | **DECIDED: 8 characters** (2026-11-22) |
| Complexity requirements? | None / mixed case+digit / symbol too | **DECIDED: uppercase + lowercase + digit** (2026-11-22) |
| Failed-login throttling / temporary lockout? | None / N attempts then cooldown / manual unlock | **DECIDED: temporary cooldown** (2026-11-22) |
| Cooldown threshold (failed attempts before cooldown)? | 3 / 5 / other | **DECIDED: 5 attempts** (2026-11-22) |
| Cooldown duration? | 5 / 15 / 30 minutes | **DECIDED: 15 minutes** (2026-11-22) |
| Password change policy? | Any time / admin-forced on first login | **DECIDED: Any time** (2026-11-22) |
| Password expiration? | Yes / No | **DECIDED: No expiration** (2026-11-22) |

Status: `P8A-02` is resolved (min 8 characters; uppercase + lowercase + digit; 5-attempt/15-minute cooldown; changes any time; no expiration). These approved rules may now be applied.

## 5. User administration — `P8A-03`

**Decision log — 2026-11-22, Owner:** multiple Owner/Admin accounts **are allowed** on one installation (for continuity); each admin's sensitive actions remain individually audited. An Owner/Admin **may deactivate another Owner/Admin**, with an audited event. The **last active Owner/Admin may not be deactivated (or downgraded)**; at least one active admin must always remain. User accounts are **deactivated only, never deleted** (preserves audit attribution). Each user holds **exactly one role**. All `P8A-03` sub-questions are answered; `P8A-03` is CLOSED.

| Question | Options | Status |
| --- | --- | --- |
| Multiple Owner/Admin accounts? | Yes / No | **DECIDED: Yes** (2026-11-22) |
| Can an Owner/Admin disable another Owner/Admin? | Yes / No | **DECIDED: Yes, with audit** (2026-11-22) |
| Can the last active Owner/Admin be disabled? | Yes / No | **DECIDED: No — keep at least one active admin** (2026-11-22) |
| Delete users or only deactivate? | Delete allowed / deactivate only | **DECIDED: Deactivate only** (2026-11-22) |
| Role cardinality per user? | Exactly one role / multiple roles | **DECIDED: Exactly one role** (2026-11-22) |

## 6. Accountant/Reviewer — `P8A-04`

**Decision log — 2026-11-22, Owner:** Accountant/Reviewer may **view all financial records and reports** (including all financial reports). The owner then decided **no create/edit of any records** — this role is viewing-only. The owner then decided **no approval or posting authority** for this role (no approval authority for this role; `B6-10` resolved with no approvals in v1). The owner then decided **full customer/supplier balance details are visible**. The owner then decided **sensitive business settings are hidden** from this role. The owner then decided **no explicit review/verify action**. `P8A-04` is CLOSED: the role is strictly read-only — view all financial records/reports and full balances; no create/edit, approval/posting, review/verify action, or sensitive settings. `B6-10` is now resolved with no approvals in v1, confirming this role has no approval authority. The proposed denials (no user/role/settings management, no restore/relocate, no audit modification) are still **not confirmed** as approved restrictions.

| Question | Options | Status |
| --- | --- | --- |
| Exact viewing permissions | All financial vs selected records | **DECIDED: All financial records and reports** (2026-11-22) |
| Exact create/edit permissions | None / specific record types | **DECIDED: None — viewing only** (2026-11-22) |
| Approval and posting authority | None / own records / all | **DECIDED: None** (2026-11-22; confirmed by `B6-10` — no approvals in v1) |
| Access to customer/supplier balances | Yes / No / summary only | **DECIDED: Yes — full balance details** (2026-11-22) |
| Access to financial reports | Yes / No / selected reports | **DECIDED: Yes — all financial reports** (2026-11-22, covered by viewing decision) |
| Access to sensitive business settings | Yes / No | **DECIDED: No — hidden** (2026-11-22) |
| Review/verify as a distinct action | Yes / No | **DECIDED: No — viewing only** (2026-11-22) |

## 7. Viewer — `P8A-05`

**Decision log — 2026-11-22, Owner:** Viewer may see **all modules in read-only mode**. The owner then decided **financial amounts and reports are hidden** from Viewer, that **export is not permitted**, that **print is not permitted**, and that **sensitive information is restricted**. `P8A-05` is CLOSED: a low-privilege read-only role — all modules view-only, with financial figures, sensitive information, export, and print unavailable.

| Question | Options | Status |
| --- | --- | --- |
| View all modules or selected modules? | All / selected | **DECIDED: All modules, read-only** (2026-11-22) |
| Financial amounts and reports visible? | Yes / No | **DECIDED: No — hidden** (2026-11-22) |
| Export permitted? | Yes / No | **DECIDED: No** (2026-11-22) |
| Print permitted? | Yes / No | **DECIDED: No** (2026-11-22) |
| Sensitive information restricted? | Yes / No | **DECIDED: Yes — restricted** (2026-11-22) |

No approval may be inferred from the role name "Viewer."

## 8. Operator — `P8A-06`

The baseline (create/edit day-to-day records; no user/role/settings management, restore, relocation, or audit modification) is **approved**.

**Decision log — 2026-11-22, Owner:** Operator may create/edit records in **all day-to-day operational modules** (e.g. sales, purchases, inventory, parties, expenses), not accounting/financial records.

| Question | Status |
| --- | --- |
| Module-specific create/edit scope | **DECIDED: all day-to-day operational modules** (2026-11-22) |
| Delete and cancel permissions | **DECIDED: No** (2026-11-22) |
| Approval/posting restrictions (also `B6-10`) | **DECIDED: No** (2026-11-22) |
| Export and print permissions | **DECIDED: No** (2026-11-22) |

`P8A-06` is CLOSED: Operator may create/edit in all day-to-day operational modules only; no delete/cancel, approve/post, or export/print. Create/edit does not imply any of those permissions. `B6-10` is resolved: no approvals or thresholds in v1.

## 9. Session and locking — `P8A-07`

| Question | Options | Status |
| --- | --- | --- |
| What counts as activity? | Proposal in session spec | **DECIDED: deliberate interaction with app window** (2026-11-22) |
| Does timeout apply while modal dialogs are open? | Continues / pauses | **DECIDED: Continues** (2026-11-22) |
| Do background operations continue while locked? | Continue / suspend | **DECIDED: approved split** (2026-11-22) — headless maintenance continues; data-surfacing workers suspended; no writes for locked user |
| Can users switch accounts without restarting? | Logout+login / hot switch | **DECIDED: Logout + login only** (2026-11-22); no hot switch |
| What happens when closed while locked? | Fresh login next launch (proposed) | **DECIDED: Fresh login next launch** (2026-11-22) |
| How do settings changes affect an existing session? | Proposal in session spec | **DECIDED: approved proposed rules** (2026-11-22) |

The 15-minute default, configurability, password unlock, and lock/unlock audit events are **approved** and are not re-asked.

## 10. Recovery — `P8A-08`

**Decision log — 2026-11-22, Owner (`P8A-08` CLOSED):** for an administrative reset, an Owner/Admin **enters a new password (with confirmation) in an explicit dialog**; no generated temporary password. If all Owner/Admin credentials are unavailable, a **documented offline owner procedure** is followed — no in-app backdoor or recovery key.

| Question | Options | Status |
| --- | --- | --- |
| Exact administrative reset procedure | Dialog-set new password / generated temporary password, both audited | **DECIDED: Admin enters a new password with confirmation in an explicit dialog** (2026-11-22) |
| Behavior when all Owner/Admin credentials are unavailable | Documented offline/owner procedure / other | **DECIDED: Documented offline owner procedure** (2026-11-22); no in-app backdoor/recovery key |

Manual Owner/Admin recovery (not self-service, no email/OTP) and distinct reset audit events are **approved**.

## 11. Related open items from the existing register

- `Q-22` (audit visibility): owner decided 2026-11-22 that **only Owner/Admin accounts may view audit history** (`audit.view`). Retention is indefinite and approved; no cleanup is allowed. The owner then decided audit history may be **exported by Owner/Admin only**, with each export recording an `audit.exported` event. The owner then decided to record **all significant business, security, and admin events**: sensitive/admin actions, authentication and account-lifecycle events, audit view/export events, and business record changes (create/edit/delete, approval/posting, financial adjustments). Existing historical rows (actor `system/unauthenticated`) remain unchanged. `Q-22` is CLOSED.
- `B6-10` (approval policies/thresholds): **RESOLVED 2026-11-22** — owner chose **no approval workflow and no amount thresholds in v1**. No actions require approval; no role has approval/posting authority; Owner/Admin performs sensitive actions directly with auditing.

## 12. Recommended decision order

1. `P8A-01` account identity — **RESOLVED 2026-11-22**.
2. `P8A-02` password policy — **RESOLVED 2026-11-22**.
3. `P8A-03` user administration & role strategy — **RESOLVED 2026-11-22**.
4. `P8A-08` recovery — **RESOLVED 2026-11-22**.
5. `P8A-04`, `P8A-05`, and `P8A-06` role scopes — **RESOLVED 2026-11-22**.
6. `P8A-07` session edge cases — **RESOLVED 2026-11-22**.
7. `Q-22` audit visibility — **RESOLVED 2026-11-22**.

8. `B6-10` approval policies and thresholds — **RESOLVED 2026-11-22**.

9. All owner decisions are resolved. The owner **explicitly approved the complete Phase 8A specification and authorization matrix on 2026-11-22** (documentation approval only, not implementation authorization). The owner also approved the hashing design on 2026-11-22 (Argon2id via `argon2-cffi`, with `hashlib.scrypt` fallback). The final parameter review is complete (Argon2id accepted; corrected scrypt fallback `N=2**17, r=8, p=1` approved 2026-11-22). Phase 7D owner acceptance was recorded 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`). Phase 8B still requires explicit owner authorization.
