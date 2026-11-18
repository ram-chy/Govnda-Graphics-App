# PHASE 05 REPORT — UI/UX REFINEMENT & APPLICATION POLISH

| Field | Value |
| --- | --- |
| Phase | Phase 05 |
| Title | UI/UX Refinement & Application Polish |
| Completion date | 2026-11-17 |
| Status | Implementation complete; owner review pending |
| Branch/worktree state | Uncommitted working-tree changes; no commit, amend, reset, rebase, or push performed |
| Related brief | `Prompt/PHASE 05 — UX REFINEMENT & APPLICATION POLISH.md` |
| Historical note | `Reports/PHASE_05_PENDING.md` is preserved unchanged as a historical pending-state report |

---

## 1. Phase number and title

Phase 05 — UI/UX Refinement & Application Polish.

This phase refined the existing PySide6 Qt Widgets desktop application. It did
not introduce business modules, a new backup implementation, a database schema
change, authentication, cloud services, seed data, or Phase 6 work.

## 2. Completion date

Implementation and documentation were completed on **2026-11-17**.

## 3. UI audit findings

The audit was performed before implementation by inspecting the shell, theme
system, dashboard, backup view, dialogs, ViewModels, configuration, and existing
tests. Key findings were:

1. **Theme infrastructure existed but QSS was only partly tokenized.** The
   palettes were centralized, but the stylesheet still contained hardcoded font
   sizes, paddings, borders, and control heights. Dialogs, toasts, status badges,
   and native dialog controls were not fully styled.
2. **Shell chrome was usable but not polished.** Window size and minimum size
   were hardcoded in `MainWindow`; geometry/state and the selected page were not
   restored; status-bar labels lacked accessible names; no latest-backup status
   was visible in the shell.
3. **The dashboard had stale and uneven presentation.** It used three separate
   information cards and a "Next phase" message that still described Phase 4. It
   had no explicit empty state explaining the absence of business records.
4. **Backup UI was functional but dense.** Location details were built with a
   manual grid; history had no empty state; unverified entries were greyed with a
   hard-coded `Qt.GlobalColor.gray`; Restore was visually dangerous but not
   isolated in tab order or given an explicit accessible action name.
5. **Failures were over-modalized.** A failed history read emitted
   `operation_failed`, which the view displayed as a modal error even though no
   user decision was required. Task Scheduler status was queried synchronously
   before opening the settings dialog.
6. **Feedback patterns were incomplete.** There was no reusable toast, status
   badge, or empty-state component. Success, warning, error, and background-task
   presentation were inconsistent across screens.
7. **Dialog conventions varied.** Button defaults, tab order, field labels,
   tooltips, and accessible names were inconsistent. The fatal error dialog's
   correlation reference was not directly selectable/copyable.
8. **Responsive coverage was thin.** The dashboard and backup pages had no
   scroll areas for long content or wrapped paths, and dialog sizes were fixed
   rather than clamped to the available screen.
9. **Accessibility basics were incomplete.** Important status labels and trees
   lacked accessible names/descriptions. `QTreeWidgetItem` in the pinned PySide6
   version does not expose `setAccessibleName()`, so a compatible approach was
   required.
10. **High-DPI policy existed but was not visually verified.** `app/main.py`
    already used Qt's supported `PassThrough` rounding policy, but real Windows
    visual walkthroughs at 100%, 125%, and 150% had not been performed.

## 4. Implementation summary

Phase 5 completed a focused presentation-layer refinement:

- Expanded the token module and rebuilt the QSS generator so all visual lengths
  are token-derived and unit-explicit.
- Refined the main window, navigation status, status bar, backup status, window
  session persistence, and `F5` refresh shortcut.
- Reworked the dashboard to show only verified facts and an explicit empty state
  for unavailable business data.
- Reworked the backup view to provide clear empty, unavailable, busy, verified,
  and failure states with safe action gating.
- Added a small set of reusable controls and feedback components.
- Standardized dialog sizing, defaults, tab order, accessible names, and async
  scheduler status.
- Added 20 Phase 5 programmatic tests and updated existing shell tests for
  isolated `QSettings`.
- Updated the four required documents and created this report.

No Phase 1–4 service, repository, domain, migration, backup-core, restore,
relocation, scheduler, or retention logic was changed. No database file, schema,
or content was modified by this phase.

## 5. Files created

Presentation and tests:

- `app/ui/components/controls.py`
- `app/ui/components/feedback.py`
- `tests/test_phase05_ui.py`

Documentation/report:

- `Reports/PHASE_05_REPORT.md` (this file)

## 6. Files modified

Code and tests:

- `app/core/constants.py`
- `app/ui/components/__init__.py`
- `app/ui/components/sidebar.py`
- `app/ui/dialogs/backup_settings_dialog.py`
- `app/ui/dialogs/error_dialog.py`
- `app/ui/dialogs/recovery_dialog.py`
- `app/ui/dialogs/restore_confirmation_dialog.py`
- `app/ui/dialogs/setup_wizard.py`
- `app/ui/main_window.py`
- `app/ui/themes/qss.py`
- `app/ui/themes/tokens.py`
- `app/ui/viewmodels/backup_viewmodel.py`
- `app/ui/views/backup_view.py`
- `app/ui/views/home_view.py`
- `tests/test_main_window.py`

Documentation:

- `docs/UI_UX_BLUEPRINT.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_ROADMAP.md`
- `README.md`

`Reports/PHASE_05_PENDING.md` was intentionally not modified or removed.

## 7. Design system details

- `app/ui/themes/tokens.py` now defines the complete token set: light/dark
  palettes, chart palettes, font families and weights, typography scale,
  spacing scale (4–40 px), radii, border/focus widths, control and table-row
  heights, shell dimensions, icon sizes, and dialog/wizard dimensions.
- `app/ui/themes/qss.py` renders one `string.Template` stylesheet from those
  tokens. `build_stylesheet()` substitutes palette, metrics, and typography
  values; no positive CSS length is emitted without `px`.
- Tests assert that generated QSS contains no unresolved `$` placeholders, no
  `pxpx`, and no unitless positive lengths for common length properties.
- QSS now covers primary/secondary/danger/disabled/focus button states,
  navigation selection and focus, cards, semantic status badges with distinct
  border shapes, toasts, inputs, trees/tables, headers, scroll bars, tooltips,
  progress bars, check boxes, message boxes, wizard headers/footers, and paths.
- `ThemeManager` continues to apply the stylesheet at runtime and synchronises
  `QPalette`, including the highlight color, so native dialogs follow the active
  theme.
- Font fallback is `Segoe UI Variable Text` → `Segoe UI` → `Tahoma` →
  `sans-serif`; path/numeric text uses `Cascadia Mono` → `Consolas` →
  `monospace`.

## 8. Light Mode changes

Light Mode retains the approved calm green direction:

- App background `#F6F7F5`, surface `#FFFFFF`, alternating surface `#EEF2EE`.
- Primary accent `#1F7A4D`, hover `#18643F`, pressed `#124E31`.
- Soft borders `#DDE3DD` / `#C3CCC5`; selected surface `#E3F1E8`.
- Semantic colors: success `#2E7D32`, warning `#B26A00`, error `#B3261E`,
  information `#1D6FB8`, focus `#2F8F63`.

Changes in Phase 5 were structural rather than a palette redesign: token values
are now applied consistently to dialogs, status indicators, toasts, inputs,
tables, and scroll bars, and the green accent remains limited to actions,
selection, and brand/status meaning rather than washing the whole interface.

## 9. Dark Mode changes

Dark Mode retains the approved professional layered surfaces:

- App background `#121614`, surface `#1A201D`, alternating surface `#232B27`.
- Primary accent `#4CAF82`, hover `#5CBF90`, pressed `#3E9A71`.
- Borders `#313B35` / `#44524A`; selected surface `#243B30`.
- Semantic colors remain distinguishable: success `#66BB6A`, warning `#E0A64A`,
  error `#EF6B62`, information `#64A9E8`, focus `#6FD3A2`.
- `on.primary` is `#0E1512` so text on the lighter green accent stays readable.

Phase 5 added dark-aware styling for the same surfaces and controls listed in
§8, plus Qt palette synchronisation so `QMessageBox` and native picker controls
do not appear as bright outliers.

## 10. Application shell changes

`app/ui/main_window.py` now:

- uses `METRICS.window_default_width/height` and
  `METRICS.window_minimum_width/height` instead of literals;
- accepts an injected `QSettings` instance, making session tests isolated;
- restores `window/geometry`, `window/state`, and `navigation/current`;
- ignores saved geometry when it does not fit a connected screen and centres the
  window on the primary screen instead;
- saves geometry, state, and current navigation on an accepted close, after the
  existing backup-shutdown close guard;
- exposes `F5` through `QShortcut(QKeySequence.StandardKey.Refresh, self)` and
  calls `refresh()` on the active view when available;
- adds accessible names to the status bar and database, backup, currency,
  local-only, and version labels;
- shows the latest verified backup time from `BackupSnapshot`, with a tooltip
  naming the backup file, and handles unavailable/no-verified-backup states;
- uses named status-message duration constants in `app/core/constants.py`.

The sidebar spacing now uses `METRICS.space_1`. Navigation destinations and
routes were not changed.

## 11. Dashboard changes

`app/ui/views/home_view.py` now:

- uses a `QScrollArea` with a resizable content widget and token margins;
- shows a `StatusBadge` of "Verified and ready" or "Setup required";
- replaces three uneven information cards with one `DetailCard` named
  "Environment" containing version, currency, formatting example, data location,
  and database file when configured;
- keeps the "Business database" explanation based only on startup verification;
- replaces the stale "Next phase" card with an `EmptyState` explaining that
  business records are unavailable and that summary values appear only after the
  relevant modules and approved report definitions are released;
- removes the old `_info_card()` helper and hardcoded `KpiValue` styling.

No fake revenue, profit, sales, customer, inventory, expense, or chart data was
added. No chart is rendered because no approved metric definition exists.

## 12. Dialog and workflow improvements

- **Setup wizard:** token-based `set_dialog_size()`, labeled path field with a
  buddy, right-elided review tree with full-path tooltips and an accessible name,
  consistent `make_button()` usage, deliberate tab order, token-based minimum
  widths, and a focused recovery action on initialization/persistence failure.
- **Recovery dialog:** token sizing, `DetailCard` for preserved paths, Retry
  focused and default, Exit separated in tab order with the accessible name
  "Exit without changing any business data", and unchanged four-action semantics
  (Retry / Locate existing data / Start new setup / Exit).
- **Restore confirmation:** token sizing, `DetailCard` for the selected backup,
  Cancel as the default action, an explicit destructive accessible name naming
  the backup file, and unchanged mandatory confirmation and safety-backup text.
- **Backup settings:** token sizing, accessible field names, `Ctrl+S` on
  **Save schedule**, and a `set_task_status()` method updated through an
  asynchronous `task_status` signal so the dialog opens immediately.
- **Fatal error dialog:** selectable correlation reference plus a **Copy
  reference** button; technical details remain behind **Show details**.

`QTreeWidgetItem.setAccessibleName()` is unavailable in the pinned PySide6
version, so tree-level accessible names/descriptions and item tooltips are used
instead. No dialog workflow permission or data-safety step was removed.

## 13. Backup UI improvements

`app/ui/views/backup_view.py` now:

- uses a scroll area, `DetailCard`, `StatusBadge`, `make_button()`, and
  `show_toast()`;
- provides an explicit empty state when no backup records exist and an
  unavailable state with a reason when the data root cannot be read;
- disables manual backup and refresh while an operation is busy, with an
  accessible progress bar;
- keeps Restore enabled only for a selected `VERIFIED` record;
- adds tooltips for history rows, an accessible history-tree name/description,
  and palette-derived muted text instead of `Qt.GlobalColor.gray`;
- uses a deliberate tab order: Back up now → Refresh → Schedule settings →
  history → Restore → Move database;
- shows success as a status badge plus a transient toast;
- treats history read failures as a non-modal warning via the new
  `BackupViewModel.read_failed` signal;
- keeps decision-required failures modal via `QMessageBox.critical`;
- queries Task Scheduler asynchronously when **Schedule settings** is opened;
- shows a wait cursor during destination validation for relocation.

`BackupViewModel` gained `read_failed`, `task_status`, and `load_task_status()`
without changing backup, restore, relocation, or retention services.

## 14. Reusable components

| Component | File | Responsibility |
| --- | --- | --- |
| `StatusBadge` / `apply_status()` | `app/ui/components/feedback.py` | Semantic text, shape, tone property, accessible name |
| `EmptyState` | `app/ui/components/feedback.py` | Text-only title/detail empty state |
| `Toast` / `show_toast()` | `app/ui/components/feedback.py` | Non-modal, four-second, max-two, click-to-dismiss feedback |
| `DetailCard` | `app/ui/components/controls.py` | Consistent caption/value rows with selectable values |
| `make_button()` | `app/ui/components/controls.py` | Primary/secondary/danger variants with accessible names |
| `set_dialog_size()` | `app/ui/components/controls.py` | Token sizing clamped to 90% of the available screen |

These were exported through `app/ui/components/__init__.py`. Existing
`Sidebar`, `TopBar`, `SectionCard`, and `PlaceholderView` components were kept.
No large abstraction framework was introduced.

## 15. DPI and display scaling results

**Automated/programmatic results:**

- `app/main.py` retains
  `QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)`.
  No global font or widget scaling multiplier was added.
- Offscreen smoke runs were executed with `QT_QPA_PLATFORM=offscreen` and
  `QT_SCALE_FACTOR` values `1`, `1.25`, and `1.5`. Each exited `0`, logged
  `Main window shown`, and contained no `CRITICAL` entries or `Traceback`.
- These checks verify startup and widget construction only. They are **not**
  visual DPI verification.

**Real Windows results:** no real Windows visual walkthrough at 100%, 125%, or
150% was performed in this environment. See §20 for exact manual instructions.

## 16. Accessibility improvements

- Added accessible names to the status bar and all permanent status labels.
- Added accessible names to schedule fields, recovery buttons, restore buttons,
  setup path field, review tree, history tree, and progress bar.
- Set explicit strong focus policies on generated buttons.
- Added explicit tab order in the shell's backup view and in recovery, restore,
  setup, and backup-settings dialogs.
- Made the safe action the default/focused action where applicable: Retry in
  recovery, Cancel in restore, Save schedule in backup settings, and a recovery
  action on setup failure.
- Kept semantic meaning available through text and border shape, not color
  alone.
- Kept the destructive restore action visually distinct, tooltipped, named, and
  separated in tab order.
- Added a **Copy reference** action to the fatal error dialog.

Keyboard activation was exercised programmatically for `F5` and button defaults.
A full keyboard-only walkthrough and Windows screen-reader verification were not
performed and remain manual release tasks.

## 17. Performance considerations

- No long-running work was moved onto the GUI thread. Backup, restore,
  relocation, and startup catch-up continue to use the existing task runner.
- The Task Scheduler query was moved off the dialog-open path through
  `load_task_status()`/`task_status`, so opening backup settings no longer waits
  on scheduler I/O.
- Stylesheets are generated once per theme application; semantic style changes
  repolish only the affected badge.
- Navigation views remain lazily created and cached by the existing `QStackedWidget`
  pattern; Phase 5 did not introduce repeated page reconstruction.
- `QScrollArea` replaces fixed-height growth for dashboard and backup content,
  avoiding unnecessary layout pressure when paths wrap.
- The only additional refresh trigger is one backup reload after an accepted
  schedule update; existing refresh/operation flows were otherwise preserved.
- No profiling, 10k-row table benchmark, or long-session memory measurement was
  performed. The table benchmark is not applicable yet because no `DataTable`
  or business list screen exists.

## 18. Automated tests executed

Commands run from the repository root with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q tests/test_phase05_ui.py
.\.venv\Scripts\python.exe -m pytest -q
```

Additional programmatic smoke checks were executed by
`tests/test_phase05_ui.py::test_programmatic_smoke_at_scale_factors` with
`QT_SCALE_FACTOR` values `1`, `1.25`, and `1.5`, using isolated `APPDATA`,
`LOCALAPPDATA`, and a mutex name unique to each run. These use the real
`python -m app.main --smoke-test` entry point against a temporary database, but
they are offscreen programmatic checks, not visual or Windows integration tests.

Coverage areas in `tests/test_phase05_ui.py`:

- tokenized QSS completeness and palette synchronization;
- status, empty-state, detail-card, button, dialog-sizing, and toast components;
- shell session persistence, accessible shell labels, and `F5` refresh;
- backup history, empty/unavailable/busy states, restore gating, and feedback;
- ViewModel read-failure and asynchronous task-status signals;
- dialog defaults, accessible names, and task-status updates;
- programmatic smoke at three scale factors.

`tests/test_main_window.py` was updated to inject a temporary `QSettings` file so
shell tests do not read or write developer/global settings.

## 19. Exact test results

| Command | Exact result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m ruff check app tests` | `All checks passed!` |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_phase05_ui.py` | `20 passed in 7.53s` (final rerun) |
| `.\.venv\Scripts\python.exe -m pytest -q` | `448 passed in 30.09s` (final rerun) |
| Programmatic scale smoke, `QT_SCALE_FACTOR=1` | Exit code `0`; `Main window shown`; no `CRITICAL` or `Traceback` |
| Programmatic scale smoke, `QT_SCALE_FACTOR=1.25` | Exit code `0`; `Main window shown`; no `CRITICAL` or `Traceback` |
| Programmatic scale smoke, `QT_SCALE_FACTOR=1.5` | Exit code `0`; `Main window shown`; no `CRITICAL` or `Traceback` |

The full-suite count includes all Phase 1–4 regression tests. No tests were
weakened or skipped to obtain these results.

## 20. Actual Windows visual tests performed

**None.** No real Windows desktop session, manual visual walkthrough, or Windows
screen-reader check was performed in this environment. The offscreen smoke checks
in §18 must not be treated as visual verification.

Exact manual verification instructions, to be completed on Windows 10/11 with a
dedicated temporary data root and a temporary test database:

1. Set Windows display scaling to **100%**, then launch the application from the
   virtual environment or release build.
2. Inspect the main window, sidebar, dashboard, status bar, backup view, setup
   wizard, recovery dialog, backup-settings dialog, restore-confirmation dialog,
   tables, buttons, inputs, and progress indicator.
3. Confirm there is no clipped text, overlapping controls, inaccessible button,
   unusably small click target, or unnecessary horizontal scrolling at
   **1280 × 720**, maximized, and restored sizes.
4. Navigate using the keyboard only; confirm visible focus, logical tab order,
   `F5` refresh, and keyboard activation of primary actions.
5. Repeat steps 2–4 at **125%** and **150%** scaling. Record screenshots and any
   defect for owner review.
6. If display scaling changes while the app is closed, relaunch and repeat the
   checks. Live scaling-change handling is not claimed by this phase.
7. Use a temporary data root only. Never point these checks at the user's actual
   business database.

These checks are required before release sign-off; they are not reported as
passed here.

## 21. Phase 4 operational verification results

The Phase 4 report stated that automated verification passed but real Windows
integration checks were not executed. Those checks were **not executed again in
Phase 5**, and Phase 5 did not change the underlying protection logic. None of
the items below is claimed as verified.

| Required check | Result | Manual instruction |
| --- | --- | --- |
| Manual backup through the real GUI | Not executed | In the Backup view of a temporary installation, choose **Back up now** and confirm the completion toast/status. |
| Backup history and metadata verification | Not executed | Inspect the new entry in `Backups/Manual` and its JSON sidecar; confirm `VERIFIED`, created time, size, schema revision, and SHA-256 checksum match the UI. |
| Real Windows Task Scheduler registration and query | Not executed | Enable the daily schedule in Backup settings, then run `schtasks /Query /TN "GobindasBMS\DailyBackup" /V /FO LIST` and confirm the task and action path. |
| Scheduled runner while the app is closed | Not executed | Close the GUI and run `.\.venv\Scripts\python.exe -m app.tools.backup --scheduled --config "%APPDATA%\GobindasBMS\config.json"`; confirm exit code `0` and a new verified automatic backup. |
| Restore with application restart | Not executed | Select a verified backup in the temporary installation, accept the explicit confirmation, and confirm the app closes, restarts, reopens the restored database, and leaves a verified safety backup. |
| Database relocation | Not executed | Use **Move database...** with a second temporary data root; confirm the destination database verifies, `config.json` updates atomically, and the old database/data root is preserved. |
| Missing-drive recovery | Not executed | Make the temporary data root unavailable, launch, confirm the blocking recovery dialog with Retry / Locate / New setup / Exit, then reconnect and use Retry; confirm no fallback database is created. |
| Rollback behavior in a safe test environment | Not executed | On a disposable database, induce a controlled failure after the safety backup is created and confirm the original database and configuration remain usable. |
| Manual drill in `docs/BACKUP_STRATEGY.md` | Not executed | Follow the documented drill exactly against a temporary database and record each pass/fail with timestamps and log extracts. |

Mocked and automated tests establish code behavior only; they do not establish
real Windows integration success.

## 22. Known limitations

- No real Windows visual/DPI walkthrough was performed.
- No real Windows backup/restore/relocation/scheduler integration drill was
  performed in this phase.
- The sidebar icon-rail collapse target is not implemented; no approved SVG icon
  family exists. Existing textual navigation is retained.
- Dashboard KPI cards and charts are intentionally absent because no approved
  business metric definitions exist.
- `DataTable`, form primitives, skeleton loading, KPI/chart cards, and a
  development component gallery remain deferred to owning phases.
- Toast accessible names exist, but no screen-reader live-region announcement is
  emitted.
- Live display-scaling changes while the application is running are not handled;
  Qt's `PassThrough` policy and layouts are used instead.
- Splitter-position persistence is documented as a target but no splitter exists
  in the current shell.
- Form validation UX and unsaved-changes guards remain future work because no
  editable business forms exist yet.
- No performance profiling or large-table benchmark was run.

## 23. Outstanding issues

- Owner review of the UI, `docs/UI_UX_BLUEPRINT.md`, and this report.
- Complete the Windows visual/DPI checklist in §20 at 100%, 125%, and 150%.
- Complete the Phase 4 real Windows operational checklist in §21 on a dedicated
  temporary database before relying on those flows as release-verified.
- Decide whether an approved icon set and icon-rail collapse are needed in a
  later phase.
- Define component and metric requirements for `DataTable`, form primitives,
  KPI cards, and charts in their owning phases.
- Add live-region announcements and a formal screen-reader pass during Phase 11
  accessibility hardening.

No known defect blocks the automated test suite or the current Phase 5 build.

## 24. Deviations from approved documentation

1. **Roadmap demo deliverables were superseded.** The older roadmap text called
   for a demo list/form with fake in-memory data. The authoritative Phase 5 brief
   explicitly forbids fake data and new business modules, so the dashboard uses
   verified facts and an honest empty state instead. The roadmap was updated to
   record this.
2. **Icon-rail collapse was not implemented.** `UI_UX_BLUEPRINT.md` §2.2 lists a
   48 px icon rail below 1360 px. Phase 5 retained the full-width sidebar
   because no approved SVG icon set exists. The blueprint now marks this as
   target-only.
3. **Charts/KPI cards were not implemented.** The blueprint's dashboard picture
   is a future target. Phase 5 added reusable structure and an empty state, not
   fabricated metrics.
4. **Toast live-region announcement was not added.** Toasts have semantic
   accessible names, four-second dismissal, click-to-dismiss, and max-two
   stacking, but no screen-reader live-region event.
5. **`QTreeWidgetItem` accessible-name workaround.** The pinned PySide6 version
   does not support `setAccessibleName()` on `QTreeWidgetItem`; tree-level
   accessible names/descriptions and tooltips are used instead.
6. **Real Windows verification remains outstanding.** The Phase 5 brief's
   "where possible" DPI walkthrough and Phase 4 checkpoint could not be performed
   in this environment. They are documented as not executed in §20 and §21.

No deviations were made to Phase 1–4 data-protection behavior or database schema.

## 25. Phase 6 readiness assessment

**Technical readiness:** the presentation foundation is ready for review. The
shell, themes, feedback components, dialog conventions, and backup UI states are
consistent and covered by automated tests. Architecture boundaries remain intact;
the full suite passes with 448 tests and Ruff is clean.

**Governance readiness:** Phase 6 must not start automatically. Owner review of
this report and explicit authorization are required. Authentication, roles,
users, business master data, and all later business phases remain unstarted.

**Release-readiness gap:** real Windows visual/DPI checks and the Phase 4 manual
backup integration drill remain outstanding. They do not block completion of
Phase 5 implementation, but they must be completed and recorded before the
affected behavior is treated as release-verified.

Work stops here pending owner review and explicit authorization.
