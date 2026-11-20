# PHASE 07 IMPLEMENTATION READINESS — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | PHASE_07_IMPLEMENTATION_READINESS.md |
| Version | 1.1 |
| Date | 2026-11-18; readiness reassessed 2026-11-20; corrected by Phase 7B on 2026-11-20 |
| Status | Phase 7B Business Profile correction implemented; all other business decisions remain open |
| Recommended first module | Business Settings — Business Profile only |
| Related | PHASE_07_OWNER_DECISION_WORKSHEET.md, PHASE_07_FIRST_MODULE_SPECIFICATION.md, DEVELOPMENT_ROADMAP.md, OPEN_DECISIONS.md |

## Phase 7B correction (authoritative)

Readiness is reassessed against the owner-approved Phase 7B prompt. The earlier text-only, single-record/no-history, no-logo, and no-audit conclusions below are superseded for this slice.

The implemented profile requires five mandatory text fields plus a validated managed logo, records immutable version snapshots, and writes durable audit events with `system/unauthenticated`. Migration `0003_business_profile_requirements` adds the required columns and profile/version/audit tables non-destructively. Backups can embed managed logo files in sidecar `managed_assets`; restore and relocation preserve `Logos/` and roll back on failure. No other business module or transaction behavior is authorized.

## 1. Readiness conclusion

**The project is ready to implement the minimal first business module only.**

Phase 7 prepared the decision worksheet, first-module specification, and approval gate. On 2026-11-20 the owner was shown the recommended minimal options and gave written continuation instructions, recorded in the worksheet and specification as delegated approval. The approved slice is: Business Profile only; business name mandatory; address, phone, email, website, registration number, and footer message optional; one profile per installation; single record with no history; no tax, logo/attachment, print, audit UI, roles, customers, suppliers, catalogue, or transactions.

All other decisions remain open. No other business module, table beyond the approved profile table, or transaction behavior is authorized by this reassessment.

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
| First module selected | Safest module identified from dependencies | Business Profile selected | PASS |
| Module specification prepared | All required spec sections documented | `PHASE_07_FIRST_MODULE_SPECIFICATION.md` approved for minimal slice | PASS |
| Owner field approval | B6-09-A mandatory fields answered | Business name only | PASS |
| Optional field approval | B6-09-B optional fields answered | Address, phone, email, website, registration number, footer message | PASS |
| Duplicate/profile-count decision | One profile vs multiple profiles answered | One profile per installation; second create blocked | PASS |
| Archival/historical display | B6-11 answered if history/replacement is included | Single record, no history | PASS |
| Tax-field boundary | Q-03 answered if tax identifiers are included | Tax fields excluded from approved slice | PASS for this slice |
| Attachment boundary | Q-24 answered if logo/file storage is included | Logo/attachments excluded from approved slice | PASS for this slice |
| Audit boundary | Q-22 answered if visible audit is included | No audit UI in approved slice | PASS for this slice |
| Role boundary | Q-04/AQ-05 answered if role permissions are included | No roles in approved slice | PASS for this slice |
| First-module spec approval | Owner explicitly approves spec | Approved by 2026-11-20 continuation instruction | PASS |
| Architecture compatibility | Spec follows modular-monolith boundaries | Documented | PASS |
| Technical restrictions | No code/schema/migration/data changes in Phase 7 | Preserved in Phase 7; implementation is a later phase | PASS |

Overall result: **READY for the minimal Business Profile slice only**.

## 4. Decisions resolved for the approved first module

| ID | Question | Approved answer | Worksheet location |
| --- | --- | --- | --- |
| B6-09-A | Which profile fields are mandatory? | Business name only. | Group G1 |
| B6-09-B | Which profile fields are optional? | Address, phone, email, website, registration number, footer message. | Group G2 |
| B6-13 profile-count extension | One profile or multiple profiles? | One profile per installation; second create blocked. | Group G3 |
| B6-11 | How should historical/replaced profile data display? | Single record, no history. | Group I1 |
| Module spec approval | Is the specification approved? | Approved for the minimal slice on 2026-11-20. | First-module spec §22 |

Excluded conditions (these would require new owner decisions if added later):

| ID | Condition that would reopen scope |
| --- | --- |
| Q-03 | Tax identifiers or tax-dependent fields. |
| Q-24 | Logo or attachment-style file storage. |
| Q-17 / AQ-06 | Printed document output. |
| Q-22 | Visible audit history. |
| Q-04 / AQ-05 | Users, roles, or role-based permissions. |

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

Completed for the approved minimal slice on 2026-11-20:

1. [x] Confirm the first module: Business Profile only.
2. [x] Approve the mandatory profile field list: business name.
3. [x] Approve the optional profile field list: address, phone, email, website, registration number, footer message.
4. [x] Confirm one profile per installation.
5. [x] Confirm exclusion of tax, attachment/logo, print, audit UI, roles, customers, suppliers, catalogue, and transactions from the first slice.
6. [x] Confirm single-record/no-history behavior.
7. [x] Approve `PHASE_07_FIRST_MODULE_SPECIFICATION.md`.

Remaining owner actions apply to later modules only and are recorded as open in `OPEN_DECISIONS.md`.

## 11. Reassessment procedure

The 2026-11-20 reassessment followed this procedure:

1. Transferred the approved first-module answers from the continuation instruction into the worksheet and decision register with date and scope.
2. Updated this readiness matrix from `FAIL`/`CONDITIONAL` to `PASS` only for the approved slice.
3. Kept excluded scope out of the first-module specification.
4. Confirmed the planned schema change is limited to the approved business-profile table and remains Alembic-only.
5. Recorded explicit owner approval in the worksheet and specification.

Status remains **READY** only for the approved minimal Business Profile slice.
