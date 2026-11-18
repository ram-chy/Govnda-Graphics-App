# PHASE 06 REPORT — BUSINESS REQUIREMENTS, WORKFLOWS & MODULE PLANNING

| Field | Value |
| --- | --- |
| Phase | Phase 06 |
| Title | Business Requirements, Workflows & Module Planning |
| Completion date | 2026-11-18 |
| Status | Documentation complete; owner review pending; Phase 7 not started |
| Branch/worktree state | Branch `main`; documentation changes are uncommitted; no commit, amend, reset, rebase, or push performed |
| Related brief | `Prompt/PHASE 06 — BUSINESS REQUIREMENTS, WORKFLOWS & MODULE PLANNING.md` |
| Related report style | `Reports/PHASE_05_REPORT.md` |

---

## 1. Phase number and title

Phase 06 — Business Requirements, Workflows & Module Planning.

This phase produced the business blueprint for future implementation. It was documentation-only: no business module, database table, migration, seed/sample data, authentication, cloud service, or unrelated code change was made.

## 2. Completion date

Documentation was completed on **2026-11-18**.

## 3. Initial inspection performed

The Phase 6 brief required inspection before documentation. The following were inspected:

- Repository root structure: `.git/`, `.gitignore`, `alembic.ini`, `app/`, `docs/`, `migrations/`, `opencode.json`, `Prompt/`, `pyproject.toml`, `README.md`, `Reports/`, `requirements-dev.txt`, `requirements.txt`, `scripts/`, `tests/`.
- Master documentation: `README.md`, `docs/BLUEPRINT.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE_SCHEMA.md`, `docs/UI_UX_BLUEPRINT.md`, `docs/BACKUP_STRATEGY.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/SECURITY_AND_DATA_PROTECTION.md`.
- Phase reports: `Reports/PHASE_01_REPORT.md` through `Reports/PHASE_05_REPORT.md`, plus the historical `Reports/PHASE_05_PENDING.md` reference.
- Current navigation and placeholders:
  - `app/ui/main_window.py` owns `NAVIGATION_GROUPS` and page routing.
  - Real views exist for Dashboard and Backup.
  - Sales, Purchases, Inventory, Customers, Suppliers, Expenses, Accounting, Reports, and Settings remain `PlaceholderView` pages.
  - `app/ui/components/sidebar.py` emits `navigation_requested`; it does not know views or services.
  - `app/ui/components/placeholder_view.py` provides the generic unavailable-page message.
- Layer boundaries:
  - `app/core`, `app/domain`, `app/infrastructure`, `app/services`/application layer, and `app/ui` structure.
  - `app/core/exceptions.py` error hierarchy.
  - Existing import-boundary and architecture rules from `ARCHITECTURE.md`.
- Git state:
  - Branch `main`, previously up to date with `origin/main`.
  - Phase 6 prompt file was untracked and was preserved unchanged.
  - No commits or history-changing operations were performed.

## 4. Files created

Documentation:

- `docs/BUSINESS_REQUIREMENTS.md`
- `docs/BUSINESS_WORKFLOWS.md`
- `docs/MODULE_SPECIFICATIONS.md`
- `docs/BUSINESS_RULES.md`
- `docs/REPORTING_REQUIREMENTS.md`
- `docs/OPEN_DECISIONS.md`
- `Reports/PHASE_06_REPORT.md` (this file)

## 5. Files modified

- `docs/DEVELOPMENT_ROADMAP.md`
  - Header updated to version 1.4 and 2026-11-18.
  - Status changed to Phase 6 planning complete, owner review pending, Phase 7 not started.
  - Phase map and dependency table updated; historical conditional-auth phase preserved and relabelled as deferred/formerly Phase 6.
  - New Phase 6 documentation section added with deliverables, DoD, gate, and recommended Phase 7 scope.
  - Phase 7 and Phase 8 prerequisites added.
  - Immediate next step updated for Phase 6 completion.

The untracked Phase 6 prompt file was not modified.

## 6. Business areas investigated

The following operational areas were classified in `BUSINESS_REQUIREMENTS.md`:

| Area | Classification |
| --- | --- |
| Customer management | [PROPOSED] |
| Supplier management | [PROPOSED] |
| Product and service catalogue | [PROPOSED] |
| Quotation and estimates | [REQUIRES OWNER CLARIFICATION] |
| Customer orders | [REQUIRES OWNER CLARIFICATION] |
| Job/work order management | [REQUIRES OWNER CLARIFICATION] |
| Production/service execution | [REQUIRES OWNER CLARIFICATION] |
| Delivery and dispatch | [REQUIRES OWNER CLARIFICATION] |
| Invoicing and billing | [PROPOSED] |
| Payment collection | [PROPOSED] |
| Expenses | [PROPOSED] |
| Purchases | [PROPOSED] |
| Inventory and stock | [REQUIRES OWNER CLARIFICATION] |
| Business reports | [PROPOSED] |
| User access and permissions | [REQUIRES OWNER CLARIFICATION] |
| Business settings | [PROPOSED] |
| Audit trail | [PROPOSED] |
| Import from existing records | [REQUIRES OWNER CLARIFICATION] |
| Barcode scanning | [REQUIRES OWNER CLARIFICATION] |
| Bengali/bilingual UI | [REQUIRES OWNER CLARIFICATION] |

No existing business workflow was assumed merely because a navigation placeholder exists.

## 7. Confirmed requirements captured

Confirmed requirements were limited to existing approved/implemented facts:

- Windows desktop, offline-first, Python, PySide6, SQLite, SQLAlchemy 2, Alembic, Pydantic.
- Modular-monolith layering; domain independent of PySide6.
- INR, ₹, 2 decimals, Indian digit grouping; `Decimal` calculations and integer paise storage.
- Indian fiscal year, 1 April to 31 March.
- User-selected local data root; no cloud, no network API, no multi-computer live database sharing.
- Verified backup, guarded restore, relocation, and pre-upgrade safety-backup gate.
- Phase 5 light/dark UI foundation; no redesign.
- Honest dashboard and placeholders; no fake data.
- No business tables, business data, or business modules currently implemented.
- Posted financial records are not silently hard-deleted, as a schema/design principle.

## 8. Proposed requirements captured

Proposed requirements were grouped into:

- Business profile and settings.
- Customer and supplier master data.
- Product/service catalogue.
- Job/work-order handling, only if confirmed.
- Quotations/estimates, only if confirmed.
- Sales invoices and customer payments.
- Purchases and supplier payments.
- Expenses.
- Conditional inventory.
- Conditional accounting/read models.
- Operational and financial reporting.
- Conditional attachments, audit history, and user roles.

All proposed items are clearly marked and are not implementation approvals.

## 9. Workflows documented

`BUSINESS_WORKFLOWS.md` documents:

### Confirmed implemented workflows

- First-launch setup.
- Startup classification and recovery gate.
- Manual and scheduled backup.
- Restore with safety backup and rollback.
- Database relocation.
- Pre-upgrade safety-backup gate.

### Proposed or clarification-dependent workflows

- Business profile setup.
- Customer and supplier onboarding/maintenance.
- Product/service catalogue maintenance.
- Job intake/work-order handling.
- Quotation/estimate handling.
- Sales invoice creation.
- Customer payment receipt.
- Purchase bill recording.
- Supplier payment recording.
- Expense recording.
- Stock receipt, issue, and adjustment.
- Cancellation, void, return, or refund.
- Period-end review and reporting.
- Attachment capture/retrieval.
- Audit-history review.

Each workflow was documented with purpose, actors, start condition, required information, steps, status transitions, validation/restrictions, failure/cancellation behavior, related workflows, outputs, and open decisions.

## 10. Module boundaries and shared functionality

`MODULE_SPECIFICATIONS.md` documents:

- Current confirmed foundation modules.
- Proposed business modules and their responsibilities.
- Proposed dependency map with no intended circular dependencies.
- Shared services: validation, document numbering, audit, attachments, permissions, export, search/select, and posting.
- Functional data requirements by business data area.
- Module prerequisites and recommended implementation order.

Module rules remain in application/domain layers, not UI widgets.

## 11. Business rules captured

`BUSINESS_RULES.md` separates:

- Ten confirmed rules.
- Provisional defaults that are explicitly not approvals, including invoice numbering, rounding, weighted-average valuation, service/units defaults, “not in v1” assumptions, English UI, A4 print, no barcode, no in-app encryption, and negative-stock blocking.
- Thirty-five rule areas with alternatives, consequences, information needed, and decision references.
- A proposed role permission matrix.
- Approval policy planning.
- Rule implementation and testing requirements.

No open rule was silently selected.

## 12. Reporting requirements captured

`REPORTING_REQUIREMENTS.md` documents:

- Confirmed technical/dashboard status reporting behavior.
- Proposed operational and financial report catalogue.
- Dashboard metrics and why each business metric is currently blocked.
- Report definition requirements.
- PDF/Excel/print behavior using existing approved libraries.
- Data integrity and reconciliation requirements.
- Access-control implications.
- Report implementation order and tests.

No fake metric, sample row, or unapproved financial definition was introduced.

## 13. Open decisions requiring owner review

`OPEN_DECISIONS.md` captures all decisions requiring owner confirmation or acknowledgment, including:

- Existing IDs `Q-01` through `Q-26`.
- Architecture IDs `AQ-01` through `AQ-08`.
- Security IDs `SQ-01` through `SQ-03`.
- New Phase 6 IDs `B6-01` through `B6-13`.

Key blocking decisions for Phase 7+ include:

- Q-03 tax model.
- Q-04 / AQ-05 user and role model.
- Q-07 / B6-01 service catalogue and pricing basis.
- Q-08 discounts and rounding.
- Q-09 credit, payments, allocation, and balances.
- Q-10 document numbering.
- Q-13 / Q-14 document and correction scope.
- B6-02 job/work-order scope.
- B6-07 inventory applicability.
- B6-09 business profile fields.
- B6-13 master-data fields and duplicate policy.

Recommendations are labelled as recommendations only; provisional defaults are not treated as decisions.

## 14. Recommended module implementation order

[PROPOSED] after owner approval:

1. Business settings and party masters.
2. Catalogue.
3. Confirmed job/quotation workflow, if approved.
4. Sales invoices and customer payments.
5. Purchases and supplier payments.
6. Expenses.
7. Inventory only if confirmed.
8. Accounting/read models and reports.
9. Audit visibility, attachments, and users/roles if approved.

This order reduces rework by resolving numbering, tax, posting, and valuation decisions before dependent modules are built.

## 15. Verification results

### 15.1 Documentation presence

Verified with file lookup that all required Phase 6 documents and the updated roadmap exist:

- `docs/BUSINESS_REQUIREMENTS.md`
- `docs/BUSINESS_WORKFLOWS.md`
- `docs/MODULE_SPECIFICATIONS.md`
- `docs/BUSINESS_RULES.md`
- `docs/REPORTING_REQUIREMENTS.md`
- `docs/OPEN_DECISIONS.md`
- `docs/DEVELOPMENT_ROADMAP.md`

### 15.2 Git verification

Observed working-tree state before this report file was created:

```text
 M docs/DEVELOPMENT_ROADMAP.md
?? "Prompt/PHASE 06 \342\200\224 BUSINESS REQUIREMENTS, WORKFLOWS & MODULE PLANNING.md"
?? docs/BUSINESS_REQUIREMENTS.md
?? docs/BUSINESS_RULES.md
?? docs/BUSINESS_WORKFLOWS.md
?? docs/MODULE_SPECIFICATIONS.md
?? docs/OPEN_DECISIONS.md
?? docs/REPORTING_REQUIREMENTS.md
```

- Branch: `main`.
- Roadmap diff: 75 insertions, 31 deletions.
- No code, migration, table, seed data, or configuration file was changed.
- No commit, amend, rebase, reset, clean, or push was performed.

### 15.3 Documentation consistency checks

- Confirmed/proposed/clarification/out-of-scope labels are used throughout.
- Provisional defaults are repeatedly marked as not approved.
- The roadmap preserves the historical auth phase rather than deleting it.
- No business rule from an open question was silently selected.
- No report definition depends on an approved metric that does not exist.
- No business data was added to dashboard/placeholder documentation.

### 15.4 Lint and test commands

The project's historical verification commands are Ruff and pytest. Attempts were made in this environment, but they could not be completed:

- `./.venv/Scripts/python.exe -m ruff check app tests` — not runnable because no `.venv/Scripts/python.exe` exists in this shell/workspace.
- `python --version` — Windows Python Store alias was returned; no usable `python` command.
- `py --version` — Python `3.14.7` launcher is available.
- `py -m ruff --version` — failed: `No module named ruff`.
- `py -m pytest --version` — failed: `No module named pytest`.
- `where ruff` and `where pytest` — not found on PATH.

Because Phase 6 changed documentation only, these unavailable checks do not invalidate the documentation deliverables. They are recorded as an environment limitation, not as passed checks.

## 16. Deviations from approved documentation

1. **The roadmap's historical “Phase 6 = authentication” label was superseded.** The Phase 6 brief explicitly made Phase 6 a business-planning phase. The old auth content was preserved under a historical/deferred heading instead of being deleted.
2. **The roadmap phase map was renumbered conceptually.** Business planning is now Phase 6; authentication remains conditional and must be renumbered if approved.
3. **No code-level verification was possible in this shell.** Ruff and pytest are unavailable to the current interpreter environment; this is recorded rather than hidden.
4. **No business rules were finalized.** Where existing documents contained defaults, they were preserved as provisional, not promoted to decisions.

No deviations were made to data-protection behavior, database schema, application code, or existing business data.

## 17. Known limitations

- The application still has no business data, business tables, business modules, or approved detailed field lists.
- Many operational workflows remain clarification-dependent, especially jobs, quotations, delivery, inventory, returns, and user access.
- Dashboard business metrics remain intentionally unavailable.
- Real Windows visual/DPI walkthroughs and Phase 4 operational drills from earlier phases remain outstanding release-verification tasks.
- This phase did not ask the owner to decide open questions; it documents them for review.

## 18. Phase 7 readiness assessment

**Documentation readiness:** complete. The required Phase 6 documents exist and classify confirmed, proposed, clarification-dependent, and out-of-scope items.

**Architecture readiness:** unchanged and intact. Module boundaries, shared-service planning, and rule placement preserve the existing layered architecture.

**Business readiness:** not yet approved. Owner review is required before implementation.

**Recommended Phase 7 entry condition:** owner confirms the minimum prerequisite set in `OPEN_DECISIONS.md` §7 and explicitly approves the first module's field list, validation rules, and workflow.

## 19. Work stop condition

Work stops here pending owner review and explicit authorization. No Phase 7 implementation should begin from this report alone.
