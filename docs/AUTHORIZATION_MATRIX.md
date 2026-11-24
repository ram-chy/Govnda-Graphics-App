# AUTHORIZATION MATRIX — Roles, Permissions, and Decision Status

| Field | Value |
| --- | --- |
| Document | AUTHORIZATION_MATRIX.md |
| Phase | 8A specification; 8B implementation |
| Version | 1.0 (owner-approved specification 2026-11-22); 8B implementation note added 2026-11-23 |
| Date | 2026-11-22 |
| Status | SPECIFICATION APPROVED 2026-11-22 — IMPLEMENTED IN PHASE 8B, owner review pending |
| Related | AUTHENTICATION_SPECIFICATION.md, PHASE_08_OWNER_DECISION_WORKSHEET.md, PHASE_08_IMPLEMENTATION_READINESS.md, OPEN_DECISIONS.md |

This matrix separates **approved** permissions from **proposed** permissions and **owner decisions**. A permission marked PROPOSED or OWNER DECISION must not be implemented as approved. No code, schema, or permission check was created in Phase 8A; Phase 8B implemented only the `A`-marked permissions.

## Phase 8B implementation status (authoritative)

Only `A`-marked keys are defined in `app.domain.auth.PermissionKey`. Proposed (`P`) and open (`O`) permissions are deliberately absent and are denied by default. `auth.login` is an unauthenticated entry point and is intentionally absent from all role grants. Owner/Admin receives every approved role-grantable permission; Operator, Accountant/Reviewer, and Viewer receive only `auth.logout`, `auth.unlock`, and `auth.password_change_self`. Authorization is enforced at the service layer through `AuthorizationService.require(...)` and re-reads the live role/status from the database on each check; UI visibility is advisory only. `audit.modify` is denied to every role.

## 1. Legend

| Mark | Meaning |
| --- | --- |
| `A` | Approved by the Phase 8A owner instruction. |
| `P` | Proposed by this specification; requires owner approval before implementation. |
| `O` | Open owner decision; no default may be treated as approved. |
| `D` | Denied to this role under approved rules. |
| `N/A` | Not applicable. |

An empty or `O` cell is never a grant.

## 2. Approved role names

| Role key | Display name | Status |
| --- | --- | --- |
| `owner_admin` | Owner/Admin | `A` |
| `operator` | Operator | `A` |
| `accountant_reviewer` | Accountant/Reviewer | `A` (role name; view-all-financial grant added 2026-11-22) |
| `viewer` | Viewer | `A` (role name only) |

No additional roles may be added without owner approval.

## 3. Permission catalogue

Permissions are centralized keys, not role-name comparisons. Each sensitive application service operation must call `AuthorizationService.require(permission_key)`.

### 3.1 Authentication and session permissions

| Permission key | Description | Status | Audit event |
| --- | --- | --- | --- |
| `auth.login` | Attempt authentication | `A` (unauthenticated entry point) | `auth.login_succeeded` / `auth.login_failed` |
| `auth.logout` | End current session | `A` | `auth.logout` |
| `auth.unlock` | Unlock locked session with password | `A` | `auth.unlock` |
| `auth.password_change_self` | Change own password | `A` | `auth.password_changed` |
| `auth.reauth_sensitive` | Re-authenticate for destructive operation | `P` — security doc recommends; exact use pending | sensitive operation audit event |

### 3.2 User and role administration

| Permission key | Description | Status | Audit event |
| --- | --- | --- | --- |
| `user.create` | Create local user account | `A` for Owner/Admin capability | `auth.user_created` |
| `user.edit_identity` | Edit identity fields | `A` — Owner/Admin-only username rename (`P8A-01`, 2026-11-22); email is optional contact data | `auth.user_updated` |
| `user.activate` | Activate user account | `A` for Owner/Admin capability | `auth.user_activated` |
| `user.deactivate` | Deactivate user account | `A` for Owner/Admin capability | `auth.user_deactivated` |
| `user.delete` | Delete user account | `D` — deactivate only (`P8A-03`, 2026-11-22); not an approved permission | No event |
| `user.reset_password` | Administrative password reset | `A` for Owner/Admin | `auth.password_reset_admin` |
| `user.assign_role` | Assign or change user role | `A` for Owner/Admin | `auth.role_assigned` |
| `permission.change` | Change role-permission assignments | `A` for Owner/Admin | `auth.permission_changed` |
| `user.view` | View user list and non-secret account fields | `P` | `auth.user_viewed` if approved |

### 3.3 Application administration

| Permission key | Description | Status | Audit event |
| --- | --- | --- | --- |
| `settings.application.update` | Change application-wide settings | `A` for Owner/Admin; denied to others | `admin.settings_changed` |
| `backup.create` | Create manual backup | `P` — Owner/Admin full access approved; Operator/others pending | `backup.created` |
| `backup.restore` | Restore a backup | `A` for Owner/Admin; `D` for Operator and Accountant/Reviewer | `backup.restored` |
| `database.relocate` | Relocate business database | `A` for Owner/Admin; `D` for Operator and Accountant/Reviewer | `admin.database_relocated` |
| `schedule.update` | Change scheduled backup settings | `P` — treat as application-wide settings | `admin.schedule_changed` |
| `upgrade.run` | Run maintenance schema upgrade | `P` — sensitive admin action | `admin.upgrade_run` |

### 3.4 Business Profile

| Permission key | Description | Status | Audit event |
| --- | --- | --- | --- |
| `business_profile.view` | View active profile and history | `P` | `business_profile.history_viewed` (existing) |
| `business_profile.edit` | Create/update profile, replace logo | `P` | existing `business_profile.created/updated/logo_changed` |

The existing Business Profile audit behavior must not be weakened. Actor attribution for future events changes from `system/unauthenticated` to the authenticated actor; historical rows remain unchanged.

### 3.5 Audit

| Permission key | Description | Status | Audit event |
| --- | --- | --- | --- |
| `audit.view` | View audit history | `A` for Owner/Admin only (`Q-22`, 2026-11-22); `D` for all other roles | none required |
| `audit.export` | Export audit history | `A` for Owner/Admin only (`Q-22`, 2026-11-22); `D` for all other roles | `audit.exported` |

**Recorded event scope (`Q-22`, 2026-11-22):** all significant business, security, and admin events — sensitive/admin actions, authentication and account-lifecycle events, audit view/export events, and business record changes (create/edit/delete, approval/posting, financial adjustments). Existing historical rows (actor `system/unauthenticated`) remain unchanged; retention is indefinite and append-only.
| `audit.modify` | Update or delete audit history | `D` for every role, including Owner/Admin | Not permitted |

Append-only retention is absolute for supported application operations. “Owner/Admin has full access” does not include mutating audit history; that would violate indefinite append-only retention.

### 3.6 Future business modules

No create, edit, delete, cancel, approve, post, export, or print permission for sales, purchases, inventory, expenses, accounting, or reports is approved by Phase 8A. Catalogue master-data permissions are approved for Phase 10 only as documented in §3.8; no catalogue pricing/stock/tax/transaction behavior is approved. Other module permissions depend on unresolved decisions such as Q-03, Q-06, Q-09, and Q-15 and must be specified per module in a later phase. `B6-10` is resolved (no approvals or thresholds in v1) and grants no approval/posting authority to any role.

### 3.7 Party master data (Phase 9, owner-approved 2026-11-23)

Applies to Customer and Supplier master records only. No financial amounts, transactions, balances, export, print, approval, or posting behavior is included in Phase 9.

| Permission key | Description | Status | Audit event |
| --- | --- | --- | --- |
| `party.view` | View/search/list customer and supplier details | `A` (2026-11-23) | optional view audit not required |
| `party.create` | Create customer/supplier record | `A` (2026-11-23) | `party.created` |
| `party.edit` | Edit customer/supplier fields, including activate/deactivate (Option 2A) | `A` (2026-11-23) | `party.updated` / `party.activated` / `party.deactivated` |
| `party.delete` | Hard delete customer/supplier | `D` — deactivate only in Phase 9; referenced records must never be unsafely deleted | Not permitted |

Role grants (Phase 9): Owner/Admin=`party.view,party.create,party.edit`; Operator=`party.view,party.create,party.edit`; Accountant/Reviewer=`party.view`; Viewer=`party.view`. Export/print/cancel/approve/post remain denied for all roles.

### 3.8 Catalogue master data (Phase 10, owner-approved 2026-11-24)

Applies to Product and Service catalogue master records only. No inventory/stock, variants, barcodes, multiple price lists, tax, discounts/commissions, transactions, invoices, payments, or accounting behavior is included in Phase 10.

| Permission key | Description | Status | Audit event |
| --- | --- | --- | --- |
| `catalogue.view` | View/search/list product and service catalogue records | `A` (2026-11-24) | optional view audit not required |
| `catalogue.create` | Create product/service catalogue record | `A` (2026-11-24) | `catalogue.created` |
| `catalogue.edit` | Edit catalogue fields, including activate/deactivate | `A` (2026-11-24) | `catalogue.updated` / `catalogue.activated` / `catalogue.deactivated` |
| `catalogue.delete` | Hard delete catalogue record | `D` — deactivate only in Phase 10; referenced records must never be unsafely deleted | Not permitted |

Role grants (Phase 10): Owner/Admin=`catalogue.view,catalogue.create,catalogue.edit`; Operator=`catalogue.view,catalogue.create,catalogue.edit`; Accountant/Reviewer=`catalogue.view`; Viewer=`catalogue.view`. Export/print/cancel/approve/post remain denied for all roles.

## 4. Role matrix — approved baseline only

### 4.1 Owner/Admin — approved

Full access to every application module and operation, including user management, role and permission management, application settings, business records, financial records, backup and restore, database relocation, and sensitive administrative operations. Sensitive operations must be audited.

Exception: `audit.modify` remains denied to all roles because audit history is append-only.

### 4.2 Operator — approved baseline

| Capability | Status |
| --- | --- |
| Create and edit day-to-day business records | `A` |
| Create/edit scope = all day-to-day operational modules (e.g. sales, purchases, inventory, parties, expenses), not accounting/financial records | `A` (`P8A-06`, 2026-11-22) |
| Delete or cancel records | `D` (`P8A-06`, 2026-11-22) |
| Approve or post records | `D` (`P8A-06`, 2026-11-22) |
| Export or print data | `D` (`P8A-06`, 2026-11-22) |
| Manage users, roles, or permissions | `D` |
| Manage application-wide settings | `D` |
| Restore backups | `D` |
| Relocate database | `D` |
| Modify or delete audit history | `D` |

`P8A-06` is CLOSED (2026-11-22): Operator's only data-changing permission is create/edit in day-to-day operational modules. `B6-10` is resolved: no approvals or thresholds in v1, so Operator has no approval/posting authority.

### 4.3 Accountant/Reviewer — role name approved; strictly read-only scope approved

**Approved (`A`, `P8A-04`, 2026-11-22):**
- View **all financial records and reports**, including all financial reports.
- View full customer and supplier balance details.

**Denied (`D`, `P8A-04`, 2026-11-22):**
- Create/edit of any records.
- Approval and posting of any records.
- Any explicit review/verify action (marking a record reviewed or verified).
- View sensitive business settings.

The following proposed denials are **not yet confirmed as approved restrictions** (still `P` / `O`):
- Cannot manage users, roles, or application-wide settings.
- Cannot restore backups or relocate the database.
- Cannot modify or delete audit history.

`B6-10` is resolved: no approvals or thresholds in v1. This role changes no data and has no approval authority.

### 4.4 Viewer — role name approved; low-privilege read-only scope approved

**Approved (`A`, `P8A-05`, 2026-11-22):** view **all modules in read-only mode**.

**Denied (`D`, `P8A-05`, 2026-11-22):** view financial amounts and reports; access sensitive information; export; print. This role changes no data.

| Capability | Status |
| --- | --- |
| View all modules read-only | `A` (2026-11-22) |
| View financial amounts and reports | `D` (2026-11-22) |
| Export | `D` (2026-11-22) |
| Print | `D` (2026-11-22) |
| Access sensitive business settings / sensitive information | `D` (2026-11-22) |
| Modify or delete audit history | `D` |

## 5. Service-layer enforcement rules

1. Every sensitive service method begins with an explicit `AuthorizationService.require(...)` call.
2. UI navigation and controls may hide unavailable actions but must not be the enforcement point.
3. Failed authorization raises a domain/application authorization error with a safe message and records a sensitive-action denial audit event if the owner approves denial auditing.
4. Role assignment changes take effect immediately for subsequent service calls.
5. User deactivation immediately invalidates that user's in-memory session.
6. Locked sessions fail authorization for all non-unlock operations regardless of role.
7. Centralized permission definitions are the single source of truth; do not hardcode role strings in views, view models, repositories, or migrations.

## 6. Owner approval gate

The owner explicitly approved this matrix and the complete Phase 8A specification on 2026-11-22 (documentation approval only). That approval covered:

- the permission catalogue and each `P` item intended for v1,
- Accountant/Reviewer scope (`P8A-04`) — approved 2026-11-22,
- Viewer scope (`P8A-05`) — approved 2026-11-22,
- Operator module-specific sensitive permissions (`P8A-06`) — approved 2026-11-22,
- audit visibility (`Q-22`) — approved 2026-11-22,
- approval policies and thresholds (`B6-10`) — approved 2026-11-22 (no approvals or thresholds in v1).

All worksheet decisions are resolved and this complete matrix/specification is approved. Phase 7D owner acceptance was recorded 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`), the hashing-parameter review was completed, and the final scrypt fallback values were approved 2026-11-22 (`AUTHENTICATION_SPECIFICATION.md` §3.1.1). The owner explicitly authorized Phase 8B implementation on 2026-11-22; this matrix now also records the implemented boundary: only `A`-marked keys are implemented and `P`/`O` permissions remain denied by default pending owner approval. Owner review/acceptance of the implementation remains pending; see `Reports/PHASE_08B_REPORT.md`.
