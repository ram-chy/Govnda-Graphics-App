# PHASE 05 — UI/UX REFINEMENT & APPLICATION POLISH

## Project

Gobindas Graphics Business Management System

## Objective

Refine the existing PySide6 desktop application into a polished, consistent,
professional Windows application.

This phase focuses on UI/UX quality, visual consistency, accessibility,
usability, DPI scaling, and application-wide interaction patterns.

Do not introduce new business functionality or redesign the existing backend
architecture.

The application must remain a genuine standalone Windows desktop application.

---

# 1. Existing technology stack

Preserve the existing stack:

- Python
- PySide6 / Qt Widgets
- SQLite
- SQLAlchemy 2
- Alembic
- Pydantic and existing validation
- PyQtGraph where appropriate
- pytest
- Ruff
- PyInstaller architecture compatibility

Do not introduce:

- React
- Next.js
- Electron
- Browser-based UI
- QML without a documented technical justification
- A web server
- A remote database

Use the existing native Qt Widgets architecture.

---

# 2. Mandatory pre-implementation inspection

Before modifying anything:

1. Read all master documentation in `docs/`.
2. Read all four previous phase reports.
3. Inspect the complete existing UI implementation.
4. Inspect the existing application shell, navigation, dashboard, themes,
   dialogs, ViewModels, and backup interface.
5. Inspect the current configuration and settings implementation.
6. Inspect all existing tests.
7. Inspect Git status, branches, and recent commit history.
8. Identify existing UI inconsistencies and usability problems.
9. Prepare a short UI audit before implementation.

Preserve all existing functionality.

Do not delete, overwrite, or replace existing files without understanding their
purpose.

Do not commit, amend, reset, rebase, or push Git changes.

Do not run seeders or create sample business data.

Do not change database schemas or database contents.

---

# 3. Phase 4 operational verification checkpoint

The Phase 4 report confirms that automated verification passed, but real Windows
integration tests were not executed.

Before relying on the affected features, inspect and document the following
operational checks:

- Manual backup through the real GUI.
- Backup history and metadata verification.
- Real Windows Task Scheduler registration and task query.
- Scheduled runner execution while the main application is closed.
- Restore with application restart.
- Database relocation.
- Missing-drive recovery.
- Rollback behavior where a safe test environment permits it.
- Manual drill documented in `docs/BACKUP_STRATEGY.md`.

Use a dedicated temporary test database and temporary data directory. Never
experiment with the user's actual business database.

If the current environment permits real Windows testing, perform and record it.

If it does not, clearly identify the unavailable tests and provide exact manual
verification instructions.

Do not claim that mocked tests establish real Windows integration success.

Do not modify working Phase 4 data-protection logic merely to improve its
appearance.

---

# 4. UI design direction

The overall visual direction must be:

**Clean, minimal, calm, professional, and easy on the eyes.**

## 4.1 Light Mode

Use a calm green-based Light Mode.

Requirements:

- Green as the primary brand/accent color.
- Soft neutral backgrounds.
- Clear content surfaces.
- Comfortable contrast.
- Subtle borders.
- Restrained shadows.
- Consistent spacing.
- Minimal visual noise.

Avoid excessive green backgrounds or unnecessary decorative elements.

Use semantic colors only for appropriate states:

- Success.
- Warning.
- Error.
- Information.

## 4.2 Dark Mode

Create a professional Dark Mode.

Requirements:

- Comfortable dark surfaces.
- Clearly distinguishable content panels.
- Readable text.
- Appropriate border contrast.
- Green accent used consistently.
- Semantic status colors remain distinguishable.
- Avoid pure-black backgrounds everywhere.

## 4.3 Consistency

Establish reusable design tokens for:

- Primary and secondary colors.
- Backgrounds and surfaces.
- Text hierarchy.
- Borders.
- Spacing.
- Corner radii.
- Typography.
- Control heights.
- Button variants.
- Status indicators.
- Dialog dimensions.

Use the existing theme architecture where possible.

Avoid scattered hardcoded styles throughout widgets.

---

# 5. Application shell refinement

Refine the existing main application window.

Inspect and improve:

- Sidebar navigation.
- Application header.
- Main content area.
- Status bar.
- Window title.
- Navigation selection state.
- Content margins.
- Panel alignment.
- Window resizing behavior.

Requirements:

1. Keep navigation easy to understand.
2. Make the selected navigation item obvious without excessive highlighting.
3. Maintain consistent icon sizes and alignment.
4. Ensure text does not clip at smaller window sizes.
5. Use consistent page headers and action placement.
6. Avoid unnecessary nested panels.
7. Preserve existing routes/views and functionality.
8. Provide useful empty states where data is not yet available.

Do not invent new business modules or navigation destinations.

Do not create fake working screens for modules that have not been implemented.

---

# 6. Dashboard refinement

Improve the existing dashboard presentation without inventing business data.

Requirements:

- Clear dashboard heading.
- Consistent content layout.
- Appropriate summary-card structure where existing data supports it.
- Existing database and location status presented clearly.
- Useful empty states for unavailable business information.
- Appropriate chart layout using existing data only.
- Consistent spacing and typography.
- No fake revenue, profit, sales, customer, inventory, or expense figures.

If there is insufficient real data for a chart, show a clear empty state instead
of fabricated values.

Keep dashboard components reusable for future modules.

Do not implement new reporting or accounting calculations in this phase.

---

# 7. Dialog and workflow refinement

Review and improve existing dialogs and workflows:

- First-launch setup wizard.
- Data-location validation.
- Recovery dialog.
- Backup settings dialog.
- Restore confirmation dialog.
- Other existing application dialogs.

Focus on:

- Clear titles.
- Short and understandable explanations.
- Consistent button placement.
- Proper default and cancel actions.
- Visible validation messages.
- Clear progress feedback.
- Proper error handling.
- Confirmation before destructive actions.
- Consistent spacing and sizing.

For the setup wizard:

- Keep the selected absolute data path visible.
- Make validation results easy to understand.
- Keep warnings distinguishable from errors.
- Preserve the existing explicit confirmation step.

For recovery:

- Clearly explain why the application cannot safely open the database.
- Preserve Retry, Locate existing data, Start new setup, and Exit behavior.
- Never encourage the user to create a replacement database accidentally.

For restore:

- Clearly identify the selected backup.
- Explain that current database contents will be replaced.
- Make the safety-backup protection understandable.
- Keep explicit confirmation mandatory.

Do not remove important technical information from error messages. Present the
main explanation clearly and retain useful diagnostic details where appropriate.

---

# 8. Backup management UI refinement

Improve the Phase 4 backup-management interface.

Preserve all existing backup functionality.

Refine:

- Backup history table/list.
- Backup type indicators.
- Verification status.
- File size formatting.
- Date and time formatting.
- Last successful backup information.
- Automatic schedule settings.
- Manual backup action.
- Restore action.
- Relocation action.
- Progress and failure feedback.

Requirements:

1. Make backup status understandable to a non-technical business user.
2. Distinguish verified, failed, missing, and unverified backups.
3. Make destructive operations visually clear.
4. Avoid presenting an unverified backup as restorable.
5. Keep operation progress visible.
6. Prevent repeated clicks from triggering conflicting operations.
7. Keep the UI responsive.
8. Preserve the global operation-lock behavior.

Do not weaken backup, restore, relocation, or retention protections.

Do not introduce a new backup implementation.

---

# 9. Reusable UI components

Review the existing reusable controls and create or refine components only where
useful.

Potential components:

- Primary button.
- Secondary button.
- Destructive button.
- Form field.
- Search field.
- Page header.
- Section header.
- Status indicator.
- Empty state.
- Loading/progress indicator.
- Confirmation dialog.
- Consistent table styling.
- Summary card.

Avoid building a large abstraction framework.

Components must be reusable and maintainable.

Do not duplicate existing components unnecessarily.

---

# 10. Typography, spacing, and icons

Establish a consistent typography hierarchy.

Requirements:

- Readable page titles.
- Clear section headings.
- Comfortable body text.
- Legible secondary text.
- Consistent button typography.
- Consistent input text.

Use an appropriate Windows-compatible font fallback strategy.

Use consistent spacing rather than arbitrary per-widget values.

Keep icons visually consistent.

Do not rely on color alone to communicate meaning.

Ensure important text remains readable in both themes.

---

# 11. Windows DPI and display scaling

Phase 1's 100% and 150% DPI visual walkthrough was previously outstanding.

Address this in Phase 5.

Test at:

- 100% display scaling.
- 125% display scaling.
- 150% display scaling.
- A smaller supported window size.
- A typical desktop resolution.

Check:

- Main window.
- Sidebar.
- Dashboard.
- Setup wizard.
- Recovery dialog.
- Backup management.
- Settings dialogs.
- Tables.
- Buttons.
- Input fields.
- Progress indicators.

Requirements:

- No clipped text.
- No overlapping controls.
- No inaccessible buttons.
- No unusably small click targets.
- No unnecessary horizontal scrolling.
- Appropriate resizing behavior.
- Proper high-DPI scaling configuration.

Use Qt-supported high-DPI behavior appropriate to the installed PySide6/Qt
version.

Do not use arbitrary global scaling hacks.

---

# 12. Accessibility and usability

Improve basic desktop accessibility.

Requirements:

- Logical keyboard navigation.
- Visible keyboard focus.
- Useful tab order.
- Appropriate accessible names for important controls.
- Keyboard activation for actions.
- Understandable validation messages.
- Sufficient contrast.
- Clear disabled states.
- Proper dialog focus behavior.

Ensure that the application remains usable without relying exclusively on mouse
interaction.

Do not sacrifice visual simplicity for unnecessary decoration.

---

# 13. Notifications and feedback

Standardize user feedback for:

- Successful operations.
- Validation failures.
- Warnings.
- Errors.
- Background tasks.
- Backup completion.
- Restore completion.
- Relocation completion.

Use the existing notification mechanism if one exists.

If it does not, implement a lightweight reusable native Qt notification pattern.

Avoid excessive popups.

Use confirmation dialogs only where user confirmation is genuinely necessary.

Critical failures must remain visible until acknowledged or otherwise safely
handled.

---

# 14. Responsive behavior

The application must behave appropriately when:

- The window is maximized.
- The window is resized.
- The window is restored.
- The display scaling changes.
- Content becomes longer.
- Tables contain many rows.
- Dialogs display validation errors.

Use Qt layouts and size policies properly.

Avoid fixed geometry unless a specific control requires it.

Do not assume every user has a large monitor.

---

# 15. Performance

UI refinement must not make the application slower.

Requirements:

- Avoid unnecessary widget recreation.
- Avoid expensive work on the GUI thread.
- Preserve background execution for long-running tasks.
- Avoid repeated full-table refreshes without need.
- Avoid excessive stylesheet recalculation.
- Keep scrolling and navigation responsive.

Do not move database or business logic into widgets.

---

# 16. Testing requirements

Add or update automated tests where appropriate.

Test:

- Theme switching.
- Theme persistence.
- Main window layout behavior.
- Navigation behavior.
- Dialog validation and button behavior.
- Keyboard navigation where testable.
- Empty states.
- Backup UI action states.
- Progress and error presentation.
- Existing Phase 1–4 regression behavior.

Run:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q
```

Perform application smoke tests.

Perform real Windows visual walkthroughs at 100%, 125%, and 150% DPI when
possible.

If a test cannot be performed, state that explicitly.

Do not weaken existing tests.

Do not claim visual verification based only on automated widget tests.

---

# 17. Documentation updates

Update:

- `docs/UI_UX_BLUEPRINT.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_ROADMAP.md`
- `README.md`

Document:

- Final design system.
- Light and Dark themes.
- Reusable UI components.
- Navigation structure.
- Dialog conventions.
- DPI behavior.
- Accessibility improvements.
- Remaining UI limitations.

Preserve historical documentation and previous phase reports.

Do not rewrite unrelated technical documentation.

---

# 18. Mandatory Phase 5 report

Create:

`Reports/PHASE_05_REPORT.md`

Include:

1. Phase number and title.
2. Completion date.
3. UI audit findings.
4. Implementation summary.
5. Files created.
6. Files modified.
7. Design system details.
8. Light Mode changes.
9. Dark Mode changes.
10. Application shell changes.
11. Dashboard changes.
12. Dialog and workflow improvements.
13. Backup UI improvements.
14. Reusable components.
15. DPI and display scaling results.
16. Accessibility improvements.
17. Performance considerations.
18. Automated tests executed.
19. Exact test results.
20. Actual Windows visual tests performed.
21. Phase 4 operational verification results.
22. Known limitations.
23. Outstanding issues.
24. Deviations from approved documentation.
25. Phase 6 readiness assessment.

Clearly distinguish automated test results from actual visual and Windows
integration verification.

Never invent successful results.

---

# 19. Acceptance criteria

Phase 5 is complete only when:

- The existing application has a consistent visual design.
- Light Mode is calm and green-based.
- Dark Mode is professional and readable.
- The main application shell is polished.
- Dashboard presentation uses only real available data.
- Existing dialogs and workflows are visually consistent.
- Backup management UI is clear and safe.
- Reusable components are appropriately organized.
- DPI scaling has been tested where possible.
- Basic keyboard accessibility is addressed.
- The UI remains responsive.
- Existing Phase 1–4 functionality remains intact.
- Ruff passes.
- The full test suite passes.
- Documentation is updated.
- `Reports/PHASE_05_REPORT.md` is complete.

---

# 20. Strict scope boundaries

Do not implement:

- Customers.
- Suppliers.
- Products.
- Purchases.
- Sales.
- Inventory.
- Expenses.
- Accounting.
- Authentication.
- User roles.
- Business profile fields.
- New database tables.
- Fake dashboard data.
- Cloud backup.
- Multi-computer database sharing.

These require separate approved phases and business requirements.

Do not start Phase 6 automatically.

---

# 21. Final execution rule

Work methodically.

Do not rush.

Preserve existing architecture and functionality.

Do not delete existing user data.

Do not run seeders.

Do not commit or push Git changes.

Do not silently modify database configuration.

After implementation:

1. Run all verification commands.
2. Review the final Git diff.
3. Check for accidental changes.
4. Complete the available visual and operational tests.
5. Update documentation.
6. Save `Reports/PHASE_05_REPORT.md`.
7. Summarize the results and outstanding limitations.

**STOP after Phase 5. Wait for the owner's review and explicit authorization
before beginning Phase 6.**
