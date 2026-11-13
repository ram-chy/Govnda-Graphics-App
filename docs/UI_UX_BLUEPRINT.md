# UI/UX BLUEPRINT — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | UI_UX_BLUEPRINT.md |
| Version | 1.0 |
| Date | 2026-11-12 |
| Status | Draft for review |
| Toolkit | PySide6 6.x, Qt Widgets, QSS |
| Related | BLUEPRINT.md, ARCHITECTURE.md |

## 1. Design intent

A calm, professional Windows business application that feels native, stays readable with dense data, and never makes the user fear losing data.

Principles:

1. **Clarity before decoration.** No gradients on content surfaces, no decorative animation, no visual noise.
2. **Green is an accent, not a theme wash.** Neutral surfaces dominate; green marks primary actions, selection, and brand identity.
3. **Data is the interface.** Tables and totals get the space; chrome stays thin.
4. **Predictable patterns.** Every list looks and behaves the same; every form validates the same way.
5. **Safe by default.** Destructive actions are explicit, confirmed, and reversible where possible.
6. **Keyboard-friendly.** A competent user can enter an invoice without touching the mouse.
7. **Honest states.** Loading, empty, error, offline, and missing-drive states are designed, not afterthoughts.

## 2. Application shell

### 2.1 Main window layout

```text
┌────────────────────────────────────────────────────────────────────────────┐
│  Top bar (56 px): page title · context actions · global search · theme/help │
├──────────────┬─────────────────────────────────────────────────────────────┤
│  Sidebar     │  Page header (title, subtitle, primary action)              │
│  (240 px)    │  ─────────────────────────────────────────────────────────  │
│              │  Optional filter bar                                        │
│  Dashboard   │  ┌───────────────────────────────────────────────────────┐  │
│  Sales       │  │ Content: cards, tables, forms, charts                 │  │
│  Purchases   │  │                                                       │  │
│  Inventory   │  │                                                       │  │
│  Customers   │  └───────────────────────────────────────────────────────┘  │
│  Suppliers   │                                                             │
│  Expenses    │                                                             │
│  Accounting  │                                                             │
│  Reports     │                                                             │
│  ─────────   │                                                             │
│  Settings    │                                                             │
│  Backup      │                                                             │
└──────────────┴─────────────────────────────────────────────────────────────┘
│  Status bar (24 px): database path indicator · last backup · sync/status   │
└────────────────────────────────────────────────────────────────────────────┘
```

- Default window: 1440 × 900, centered on the active screen.
- Minimum usable: 1280 × 720.
- Sidebar is fixed-width with a subtle right border; no floating cards over content.
- Top bar is a flat surface with a bottom border; it holds the page title and only page-relevant actions.
- Status bar shows, at minimum: database connection state, last successful backup age, and a discreet local-only indicator. It never shows raw file paths unless the user hovers/expands.

### 2.2 Navigation

- Sidebar groups: **Overview**, **Operations** (Sales, Purchases, Inventory), **Parties** (Customers, Suppliers), **Finance** (Expenses, Accounting, Reports), **System** (Settings, Backup, Users if enabled).
- One level of nesting only. No mega-menus, no tabs inside tabs.
- The active item uses a soft green surface and a 3 px left accent; hover uses a neutral tint.
- Collapsible to an icon rail (48 px) when the window is narrower than 1360 px, with tooltips.
- Badges show counts only where actionable (e.g., low-stock count); no vanity counters.
- Navigation state is restored on next launch (last module, window geometry, splitter positions).

### 2.3 Status bar

| Element | Behaviour |
| --- | --- |
| Database | Green dot + "Local database" or amber/red with reason; click opens details |
| Last backup | "Backed up 6h ago" / "Backup overdue" / "Drive unavailable"; click opens Backup |
| Theme | Optional quick toggle; also in Settings |
| Version | In About dialog, not always visible |

## 3. Screen inventory

Screens are created only when their module is approved. This is the target map, not an implementation order.

| Module | Screens |
| --- | --- |
| Setup | Welcome, data folder selection, validation result, restore-existing option, business profile |
| Dashboard | Single page with KPI cards, charts, recent activity |
| Sales | Invoice list, invoice editor, invoice detail/print, payment dialog, customer statement |
| Purchases | Bill list, bill editor, bill detail, supplier payment dialog |
| Inventory | Stock overview, movement ledger, adjustment editor, low-stock report |
| Customers | List, editor, detail with ledger/statement |
| Suppliers | List, editor, detail with ledger/statement |
| Products | List, editor, categories, units, price list |
| Expenses | List, editor, categories |
| Accounting | Chart of accounts, journal list, journal editor (if approved), trial balance |
| Reports | Report library, parameter panel, preview, export |
| Settings | Business profile, numbering, financial defaults, appearance, database location |
| Backup | Status, history, manual backup, restore, schedule settings |
| Users | User list, editor, roles (conditional) |
| System | Logs folder shortcut, about, diagnostics, integrity check |

## 4. Dashboard

### 4.1 Layout

```text
Page header: "Dashboard"  · date range chip · Refresh
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Sales today │ Sales MTD   │ Receivable  │ Payable     │
│ 12,400.00   │ 245,900.00  │ 38,250.00   │ 12,000.00   │
│ +8% vs yday │ 32 invoices │ 6 customers │ due in 7d   │
└─────────────┴─────────────┴─────────────┴─────────────┘
┌───────────────────────────────────┬─────────────────────┐
│ Sales trend (30 days)             │ Low stock           │
│ line/area chart                   │ compact list        │
├───────────────────────────────────┼─────────────────────┤
│ Top products                      │ Recent activity     │
│ horizontal bars                   │ invoices/payments   │
└───────────────────────────────────┴─────────────────────┘
```

- KPI cards: label, value (prominent), secondary context, optional trend. No more than six.
- Charts use the shared chart theme; max two series by default; no 3D, no pie charts with more than five slices.
- Every card has a defined empty state ("No sales in this period") and an error state with retry.
- Dashboard is read-only; clicking a card navigates to the filtered module.
- Data loads asynchronously; skeletons are preferred over a blocking spinner over the whole page.
- Dashboard never blocks startup: the shell appears first.

### 4.2 Metric definitions

Metric definitions must be approved with reports (Phase 10). Tentative:

- Sales today/MTD: posted invoices only, excluding voided.
- Receivable: sum of unpaid balances for active customers.
- Payable: sum of unpaid supplier bills.
- Low stock: goods with on-hand ≤ reorder level.
- Trend comparisons: same period previous day/month/year, clearly labelled.

## 5. List and table pattern

### 5.1 Structure

```text
Page header: "Sales invoices"                 [+ New invoice]
┌──────────────────────────────────────────────────────────────┐
│ Search…          Status: All ▾   From [date] To [date]  Reset│
├──────────────────────────────────────────────────────────────┤
│ #  Date       Customer        Total      Paid     Status    │
│ …                                                            │
├──────────────────────────────────────────────────────────────┤
│ 1–50 of 1,240            ‹ 1 2 3 … 25 ›      50 per page ▾  │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Rules

- Implement with `QTableView` + a custom `QAbstractTableModel`; do not build tables from `QTableWidget`.
- Server-side (SQL) filtering, sorting, and pagination. Debounce search 250–300 ms.
- Default page size 50; options 25/50/100/200.
- Sticky header, sortable columns with an explicit indicator, sensible default sort (usually date desc, then number desc).
- Numeric columns right-aligned with tabular figures; money includes currency only in headers, not every cell, unless ambiguity exists.
- Status is a text badge with a shape/icon, not color alone.
- Row double-click opens the record; Enter opens; context menu offers the same actions as the toolbar.
- Selection is single-row by default; multi-select only for batch exports or explicit bulk actions.
- Empty states: first-use vs filtered-empty are different messages, with a clear action ("Clear filters", "Create first invoice").
- Error state: inline banner over the table with retry; the rest of the shell stays usable.
- Never freeze the UI while counting; show "Loading…" and page totals when ready.
- Column widths and order persist per user per table (window state store).
- Do not show hidden/derived columns by default; provide a column chooser only for dense reports.

### 5.3 Row actions

- Primary action in the page header.
- Secondary actions in a row context menu and an overflow button; avoid icon-only actions without tooltips.
- Destructive actions are never the default button; documents are voided, not deleted.

## 6. Form pattern

### 6.1 Structure

- Form sections with a title and optional description; 24 px between sections.
- Labels above fields (not left-aligned) for readability at narrow widths; required fields marked with an asterisk and a legend.
- Two-column layout for short field pairs when width ≥ 1400 px; single column otherwise.
- Related sub-entities (invoice lines) use an editable grid below the header, not a separate page.
- Primary action bottom-right (**Save**, **Post invoice**), **Cancel** left of it. Dialog-level destructive action is separated.
- Autosave is not used for financial documents; drafts are explicit.

### 6.2 Validation

- Validate on blur for simple fields and on submit for cross-field rules.
- Error text sits directly below the field, red, with an error icon; the field border also changes.
- The first invalid field receives focus on submit; a summary banner appears if the error is off-screen.
- Messages are specific and actionable: "Payment cannot exceed the invoice balance of 1,250.00." Not "Invalid input."
- Server/domain errors map back to fields where possible; otherwise show a banner.
- Do not clear user input on error.
- Unsaved-changes guard on close/navigation: **Discard**, **Keep editing**.

### 6.3 Field behaviour

| Field type | Behaviour |
| --- | --- |
| Money | Right-aligned, accepts grouping, stores exact Decimal, shows currency suffix/code |
| Quantity | Up to 3 decimals, unit shown; no exponent notation |
| Date | Keyboard entry plus calendar popup; default today; no timezone surprises |
| Party lookup | Searchable combo with "create new" only where allowed |
| Product lookup | Search by name/SKU; shows stock and price context; does not auto-post stock |
| Notes | Multiline, bounded, no rich text |
| Checkbox | Only for true binary options; no tri-state |
| Attachment | File picker with type/size validation, shows filename and size |

## 7. Dialog pattern

- **Confirmation** (destructive): title, consequence sentence, **Cancel** (default) and a clearly labelled destructive action. Typing a confirmation phrase is reserved for restore/delete-database operations.
- **Editor dialogs**: max 90% of screen height, scroll body, fixed footer, 480–720 px wide. Full-page editors are preferred for invoices.
- **Informational**: one primary button, no ambiguous "OK/Cancel" for a single acknowledgement.
- **Progress**: modal only for blocking restore/migration; otherwise a non-modal status strip with cancel where safe.
- **Error**: what happened, what data is safe, what to do next, and a copyable correlation ID. Technical details behind "Show details".
- Escape closes non-destructive dialogs; pressing Escape during a save is ignored while the operation is in flight.
- Dialogs remember size only where useful; confirmation dialogs are fixed size.

## 8. Feedback and state patterns

| State | Pattern |
| --- | --- |
| Loading (short) | Inline spinner/skeleton in the affected area |
| Loading (long) | Progress bar + status text + cancel when safe |
| Success | Brief inline banner or toast; no modal for routine saves |
| Validation error | Field errors + summary banner |
| Unexpected error | Error dialog with correlation ID + retry/close |
| Empty | Illustration-free, concise text + primary action |
| Offline | Not applicable (app is offline); show no fake "cloud" status |
| Missing drive | Blocking page with path, reason, Retry, Locate, Exit |
| Backup overdue | Amber status-bar chip + dashboard notice, not a modal at every launch |
| Database locked | Short wait, then actionable message; never loop silently |

Toasts: bottom-right, 4 s, max two stacked, dismissible, announced to screen readers. No toast for errors that require a decision.

## 9. Design tokens

Qt Style Sheets have no variables, so tokens live in Python (`app/ui/themes/tokens.py`) and are substituted into QSS templates. Widgets that custom-paint read the same tokens.

### 9.1 Color — Light

| Token | Hex | Use |
| --- | --- | --- |
| `bg.app` | `#F6F7F5` | Window background |
| `bg.surface` | `#FFFFFF` | Cards, tables, dialogs |
| `bg.surfaceAlt` | `#EEF2EE` | Hover rows, section bands |
| `bg.selected` | `#E3F1E8` | Selected row/nav item |
| `border.default` | `#DDE3DD` | Borders, dividers |
| `border.strong` | `#C3CCC5` | Input borders |
| `text.primary` | `#1B231F` | Body, headings |
| `text.secondary` | `#5B6B62` | Labels, metadata |
| `text.disabled` | `#93A099` | Disabled |
| `primary` | `#1F7A4D` | Primary buttons, active accent |
| `primary.hover` | `#18643F` | Hover |
| `primary.pressed` | `#124E31` | Pressed |
| `on.primary` | `#FFFFFF` | Text on primary |
| `success` | `#2E7D32` | Paid/success |
| `warning` | `#B26A00` | Overdue/low stock |
| `danger` | `#B3261E` | Errors, destructive |
| `info` | `#1D6FB8` | Informational |
| `focus` | `#2F8F63` | Focus ring |

### 9.2 Color — Dark

| Token | Hex | Use |
| --- | --- | --- |
| `bg.app` | `#121614` | Window background |
| `bg.surface` | `#1A201D` | Cards, tables, dialogs |
| `bg.surfaceAlt` | `#232B27` | Hover rows |
| `bg.selected` | `#243B30` | Selected |
| `border.default` | `#313B35` | Borders |
| `border.strong` | `#44524A` | Input borders |
| `text.primary` | `#E8EEE9` | Body |
| `text.secondary` | `#A3B0A8` | Labels |
| `text.disabled` | `#6E7B73` | Disabled |
| `primary` | `#4CAF82` | Primary |
| `primary.hover` | `#5CBF90` | Hover |
| `primary.pressed` | `#3E9A71` | Pressed |
| `on.primary` | `#0E1512` | Text on primary |
| `success` | `#66BB6A` | Success |
| `warning` | `#E0A64A` | Warning |
| `danger` | `#EF6B62` | Danger |
| `info` | `#64A9E8` | Info |
| `focus` | `#6FD3A2` | Focus ring |

### 9.3 Typography

| Token | Value |
| --- | --- |
| Family | `Segoe UI Variable Text`, fallback `Segoe UI` |
| Numeric | `Cascadia Mono`, fallback `Consolas` for tabular figures in totals grids |
| Body | 13 px / 20 px line height |
| Small / meta | 12 px / 16 px |
| Label | 12 px, medium weight |
| Section title | 15 px, semibold |
| Page title | 20 px, semibold |
| KPI value | 26 px, semibold, tabular |
| Monospace | 12–13 px |

Never use more than three weights on one screen. Avoid all-caps for long labels; letter-spacing only for short section eyebrows if used.

### 9.4 Spacing, sizing, shape

| Token | Value |
| --- | --- |
| Space 1–8 | 4, 8, 12, 16, 20, 24, 32, 40 px |
| Control height | 32 px (compact 28 px) |
| Table row height | 34 px |
| Icon size | 16 px (nav 20 px) |
| Radius | 4 px inputs/badges, 6 px cards, 8 px dialogs |
| Border width | 1 px |
| Content padding | 24 px horizontal, 20 px vertical |
| Max form width | 760 px; centered in narrow windows |

### 9.5 Chart tokens

- Series palette: primary green, muted teal, warm sand, slate blue, muted terracotta.
- Grid lines at 8–12% opacity; no chart borders; labels in `text.secondary`.
- Tooltips show exact formatted values.
- Chart backgrounds always `bg.surface`; never transparent over patterns.
- Red/green are never the only encoding for positive/negative; use sign and labels.

## 10. Theme implementation

- Two QSS templates (`light.qss`, `dark.qss`) generated from tokens; runtime switch without restart.
- Follow the Windows app theme by default, with an explicit Light/Dark/System setting.
- Charts receive an explicit palette object; do not infer from widget palette.
- Custom delegates read tokens on `paint` so theme changes repaint correctly.
- PDFs and Excel exports always use the light/print palette regardless of UI theme.
- Test both themes for every screen before a module is done; include a screenshot check in review.

## 11. Responsive behaviour

This is a desktop app, but window sizes vary and DPI scaling can be high.

| Width | Behaviour |
| --- | --- |
| ≥ 1440 | Two-column forms; full KPI row; sidebar expanded |
| 1280–1439 | Single-column forms where needed; KPIs wrap 2×2; sidebar collapses to icons |
| < 1280 | Not supported below minimum; horizontal scroll only in tables |
| Height < 760 | Page scrolls; footer actions remain visible in editors |

- Use layouts, `QSizePolicy`, and minimum sizes; no absolute positioning.
- Long text ellipsizes with a tooltip; tables allow column resizing.
- Dialogs clamp to 90% of the available screen geometry.
- High DPI: enable Qt high-DPI scaling, use SVG icons where possible, test 150%/200%.
- Multi-monitor: restore geometry only if the screen still exists; otherwise center on the primary screen.

## 12. Accessibility and usability

- Contrast: body text and essential icons meet WCAG AA (4.5:1 normal text, 3:1 large text/UI components).
- Every interactive control has an accessible name; icon-only buttons have tooltips and accessible descriptions.
- Full keyboard operation: Tab order follows visual order; focus is always visible (2 px focus ring).
- Shortcuts: `Ctrl+N` new (context), `Ctrl+S` save, `Ctrl+F` search, `Ctrl+P` print/export, `F5` refresh, `Esc` close/cancel, `Delete` only with confirmation. Avoid overriding standard text-editing keys.
- Do not rely on color alone for status: badges include text; validation includes icons and messages.
- Tables expose headers and cell values to assistive technology; row count is announced on page changes where feasible.
- Respect Windows text scaling; avoid fixed-height labels that clip at 200%.
- Animations: no essential motion; if added, keep under 150 ms and allow disabling.
- Error messages are plain language, identify the field, and state the fix.
- Destructive actions state the exact object ("Void invoice INV-2026-000184") and consequence.
- Long operations are cancellable where no data is left half-written; otherwise the action is atomic and the UI says so.

## 13. Reusable component strategy

Components live in `app/ui/components/`; each has one responsibility, tokens for styling, and a small API.

| Component | Responsibility |
| --- | --- |
| `PageHeader` | Title, subtitle, primary/secondary actions |
| `AppButton` | Variants: primary, secondary, ghost, danger; busy state |
| `TextField` | Label, input, hint, error, required marker |
| `MoneyField` | Exact decimal input, formatting, currency context |
| `QuantityField` | Scale-aware quantity input with unit |
| `DateField` | Calendar + keyboard entry |
| `PartyPicker` | Debounced search, recent items, permission to create |
| `ProductPicker` | Search by name/SKU, stock/price context |
| `DataTable` | QTableView + model + empty/error/loading overlays |
| `FilterBar` | Search, date range, status, reset |
| `Pagination` | Page size, page navigation, total count |
| `StatusBadge` | Semantic status with text + icon |
| `KpiCard` | Label, value, secondary context, optional trend |
| `ChartCard` | Title, range control, chart, empty/error states |
| `SectionCard` | Grouped content with title and actions |
| `EmptyState` | Message + primary action |
| `Banner` | Inline info/warning/error with optional action |
| `ConfirmDialog` | Typed confirmation, destructive styling |
| `BusyOverlay` | Scoped progress with cancel when safe |
| `Toast` | Transient success/info notification |
| `FormSection` | Consistent form grouping and spacing |
| `Sidebar` | Navigation, groups, collapse state |
| `TotalsPanel` | Subtotal, discount, tax, total with tabular figures |

Rules:

- No module-specific styling inside a shared component; variants are explicit.
- Components emit intent signals; they do not call services.
- Components never contain business rules or money math beyond formatting.
- Shared components are documented with a small gallery/test screen in development builds (not shipped).

## 14. Icons and imagery

- Use one icon family (SVG, outline, 16/20 px) with consistent stroke width.
- No emoji as UI icons.
- Business logo appears on the login/setup and printed documents only; not in the working shell.
- Empty states use text, not decorative illustrations, to keep the app professional and light.

## 15. Content and terminology

- Prefer business words over technical words: "Sales invoices", not "Sales entities"; "Backup", not "Snapshot".
- Use sentence case for labels and buttons ("Save invoice", "Back up now").
- Currency formatting follows the business locale, but the stored/displayed precision is defined by DATABASE_SCHEMA.md.
- Dates display as `12 Nov 2026` in tables and `12/11/2026` in compact fields, chosen consistently per screen.
- Confirm dialogs use "Void" for financial documents and "Delete" only for safe drafts/attachments.
- Avoid "Error code" as the primary message; correlation IDs are secondary.

## 16. UI acceptance checklist

Before a screen is considered done:

- [ ] Both themes reviewed at 100% and 150% DPI.
- [ ] Keyboard-only path completes the primary task.
- [ ] Loading, empty, filtered-empty, error, and disabled states exist.
- [ ] Validation messages are specific and field-linked.
- [ ] Table sorts, filters, and pages without blocking the UI.
- [ ] Money/quantity values round-trip without formatting drift.
- [ ] Destructive action names the object and requires confirmation.
- [ ] Unsaved-changes guard works on navigation and close.
- [ ] No hard-coded colors, fonts, or spacing outside tokens.
- [ ] Screen-reader names exist for icon-only controls.
- [ ] Window geometry restores safely on a missing monitor.
- [ ] No English text is truncated at minimum window width without a tooltip.
