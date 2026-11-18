# PHASE 07 IMPLEMENTATION READINESS — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | PHASE_07_IMPLEMENTATION_READINESS.md |
| Version | 1.0 |
| Date | 2026-11-18 |
| Status | NOT READY for implementation; owner decision and approval gate pending |
| Recommended first module | Business Settings — Business Profile only |
| Related | PHASE_07_OWNER_DECISION_WORKSHEET.md, PHASE_07_FIRST_MODULE_SPECIFICATION.md, DEVELOPMENT_ROADMAP.md, OPEN_DECISIONS.md |

## 1. Readiness conclusion

**The project is not ready to implement the first business module.**

Phase 7 successfully prepared the decision worksheet, first-module specification, and approval gate. However, the owner has not yet answered the blocking decisions or explicitly approved the first-module specification.

No Phase 8 work may begin. No business functionality may be implemented from this document alone.

## 2. Technical baseline

| Area | Status | Assessment |
| --- | --- | --- |
| Offline Windows desktop foundation | Complete | Preserved; no changes made. |
| Python/PySide6 shell and theme | Complete | Suitable foundation for the Settings view. |
| Config/path/error infrastructure | Complete | Reusable by the first module; no changes required. |
| Database and Alembic foundation | Complete | Baseline only; no business tables exist. |
| Backup/restore/relocation | Complete | Preserved; no changes made. |
| Domain layer boundaries | Complete | Ready for new business rules if kept framework-independent. |
| Application/service layer pattern | Complete | Ready for a profile use-case slice. |
| UI feedback components | Complete | Ready for empty/error/status states. |
| Business tables/models/migrations | Absent | Correct for Phase 7; implementation requires a later approved gate. |
| Authentication/roles | Absent | Correct unless Q-04/AQ-05 changes the first module scope. |
| Sample business data | Absent | Correct; none may be added. |

## 3. First-module readiness matrix

| Gate | Required evidence | Current status | Result |
| --- | --- | --- | --- |
| First module selected | Safest module identified from dependencies | Business Profile recommended | PASS as planning recommendation only |
| Module specification prepared | All required spec sections documented | `PHASE_07_FIRST_MODULE_SPECIFICATION.md` created | PASS as draft |
| Owner field approval | B6-09-A mandatory fields answered | Not answered | FAIL |
| Optional field approval | B6-09-B optional fields answered | Not answered | FAIL |
| Duplicate/profile-count decision | One profile vs multiple profiles answered | Not answered | FAIL |
| Archival/historical display | B6-11 answered if history/replacement is included | Not answered conditionally | FAIL if history included |
| Tax-field boundary | Q-03 answered if tax identifiers are included | Not answered; recommended exclusion pending owner approval | CONDITIONAL |
| Attachment boundary | Q-24 answered if logo/file storage is included | Not answered; recommended exclusion pending owner approval | CONDITIONAL |
| Audit boundary | Q-22 answered if visible audit is included | Not answered; recommended exclusion pending owner approval | CONDITIONAL |
| Role boundary | Q-04/AQ-05 answered if role permissions are included | Not answered; recommended exclusion pending owner approval | CONDITIONAL |
| First-module spec approval | Owner explicitly approves spec | Not approved | FAIL |
| Architecture compatibility | Spec follows modular-monolith boundaries | Documented | PASS |
| Technical restrictions | No code/schema/migration/data changes in Phase 7 | Preserved | PASS |

Overall result: **NOT READY**.

## 4. Blocking decisions for the recommended first module

| ID | Question | Why it blocks the first module | Worksheet location |
| --- | --- | --- | --- |
| B6-09-A | Which profile fields are mandatory? | Determines validation and completion status. | Group G1 |
| B6-09-B | Which profile fields are optional? | Determines the form and stored information. | Group G2 |
| B6-13 profile-count extension | One profile or multiple profiles? | Determines duplicate handling and repository behavior. | Section 9 of first-module spec; related to B6-13 |
| B6-11 | How should historical/replaced profile data display? | Required only if history or replacement behavior is included. | Group I1 |
| Module spec approval | Is the draft specification approved? | Owner authorization is mandatory before implementation. | First-module spec §22 |

Conditional blockers:

| ID | Condition that makes it blocking |
| --- | --- |
| Q-03 | Owner includes tax identifiers or tax-dependent fields. |
| Q-24 | Owner includes logo or attachment-style file storage. |
| Q-17 / AQ-06 | Owner includes printed document output in the first slice. |
| Q-22 | Owner includes visible audit history in the first slice. |
| Q-04 / AQ-05 | Owner includes users, roles, or role-based permissions in the first slice. |

## 5. Phase 6 minimum owner-review set

These decisions remain open in `OPEN_DECISIONS.md` and must be answered or marked “Not decided yet” in the worksheet:

1. Q-03 — tax model.
2. Q-04 — user/role model.
3. Q-07 / B6-01 — service catalogue and pricing basis.
4. Q-08 — discounts and rounding.
5. Q-09 — credit, payments, allocation, and balances.
6. Q-10 — numbering.
7. Q-13 / Q-14 — document and correction scope.
8. B6-02 — job/work-order scope.
9. B6-07 — inventory applicability.
10. B6-09 — business profile fields.
11. B6-13 — master-data fields and duplicate policy.

Some affect later modules more directly, but they remain part of the owner-review gate recorded in Phase 6.

## 6. Non-blocking decisions for this first slice

The following may remain open while the minimal Business Profile slice is implemented, provided the first module specification keeps them out of scope:

- Q-05 inventory valuation.
- Q-06 negative stock.
- Q-15 accounting depth.
- Q-16 imports/opening balances.
- Q-17 printed document formats.
- Q-18 / AQ-04 encryption.
- Q-19 / AQ-03 code signing.
- Q-20 language.
- Q-21 off-site backups.
- Q-23 barcode scanning.
- Q-24 attachments, if logo/file storage is excluded.
- Q-25 second automatic backup destination.
- Q-26 backup warning policy.
- AQ-02 installation scope.
- AQ-06 thermal receipts.
- SQ-01, SQ-02, SQ-03 security UX.
- B6-03, B6-04, B6-05, B6-06, B6-08, B6-10, B6-12.
- Q-22 audit history, if no visible audit is included.

## 7. Decision consequences by possible owner answer

| Owner answer | Effect on readiness |
| --- | --- |
| Approve minimal B6-09 field list, one profile, no history, no tax fields, no attachments, no audit UI, no roles, and sign the spec | First module becomes ready for a later implementation phase. |
| Mark B6-09 “Not decided yet” | First module remains blocked. |
| Include tax identifiers | Q-03 must be answered before implementation. |
| Include logo/file storage | Q-24 must be answered before implementation. |
| Include printed output | Q-17/AQ-06 must be answered before implementation. |
| Include visible audit history | Q-22 and possibly Q-04 must be answered before implementation. |
| Include roles/permissions | Q-04/AQ-05 and likely B6-10 must be answered; roadmap/auth phase must be renumbered. |
| Request customers/suppliers/catalogue as first module instead | Revised first-module specification and B6-13/Q-07 decisions are required. |

## 8. Architecture safety check

The recommended module specification preserves:

- Presentation, application service, domain, and infrastructure separation.
- No PySide6 imports in domain code.
- No SQLAlchemy/Alembic/sqlite3/filesystem IO in domain code.
- ViewModels using QtCore only, not QtWidgets.
- UI widgets free of business rules.
- Repository implementations free of business validity decisions.
- Application services owning use cases, validation calls, and transaction boundaries.
- Existing error handling and diagnostic correlation IDs.
- Existing task/feedback conventions.
- Modular-monolith vertical slice approach.
- No global mutable service locator.
- No silent defaults, sample data, or speculative module folders.

## 9. Data safety check

The recommended module does not require:

- new tables before a later approved implementation gate;
- new Alembic migration in Phase 7;
- changes to `0001_baseline`;
- automatic startup migration;
- changes to backup/restore/relocation;
- changes to the user-selected database path policy;
- changes to configuration storage;
- changes to existing business data, because none exists.

When implementation is later approved, Alembic must still be the only schema-change mechanism, and any maintenance migration must respect the verified safety-backup gate.

## 10. Owner action checklist

Before readiness can be re-assessed, the owner must:

1. Answer or mark “Not decided yet” for every item in the Phase 7 worksheet.
2. Confirm or correct the recommended first module: Business Profile only.
3. Approve the mandatory profile field list.
4. Approve the optional profile field list.
5. Confirm one profile per installation or request a revised specification.
6. Confirm exclusion of tax, attachment/logo, print, audit UI, roles, customers, suppliers, catalogue, and transactions from the first slice, or identify which must be added.
7. If history/replacement is included, answer B6-11.
8. Sign/approve `PHASE_07_FIRST_MODULE_SPECIFICATION.md`.
9. Request a readiness re-check.

## 11. Reassessment procedure

After owner answers are supplied:

1. Transfer answers from the worksheet into the decision register with owner, date, and approved option.
2. Update this readiness matrix from `FAIL`/`CONDITIONAL` to `PASS` only where evidence exists.
3. Revise the first-module specification if the owner changed scope.
4. Confirm no new dependency, schema, migration, or infrastructure change violates architecture/data rules.
5. Record explicit owner approval.
6. Only then plan the first implementation phase.

Until those steps occur, status remains **NOT READY**.
