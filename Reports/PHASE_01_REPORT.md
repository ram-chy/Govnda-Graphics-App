# Phase 1 Completion Report

| Field | Value |
| --- | --- |
| Phase | Phase 1 — Python Environment and Application Foundation |
| Project | Gobindas Graphics Business Management System |
| Report date | 2026-11-13 |
| Status | Complete; awaiting owner review and authorization for Phase 2 |
| Report path | `Reports/PHASE_01_REPORT.md` |

## 1. Phase name and number

Phase 1 — Python Environment and Application Foundation.

This phase establishes the reproducible Python environment, the approved project
foundation, configuration and logging services, INR formatting, a runnable
PySide6 desktop shell, tests, and development documentation. It deliberately
contains no database, business module, or sample business data.

## 2. Completion date

2026-11-13.

All verification commands in §9–§11 were executed on this date on the project
machine (Windows, 64-bit) from the repository root
`D:\Development\Gobindas Graphics`.

## 3. Summary of implemented work

- Created a local virtual environment on CPython 3.14.6.
- Installed and smoke-tested the seven approved runtime dependencies plus
  pytest and ruff.
- Added exact runtime pins (`requirements.txt`), a development manifest
  (`requirements-dev.txt`), project metadata and tool configuration
  (`pyproject.toml`), `.gitignore`, and `README.md`.
- Created only the application structure needed by this phase: entry point,
  composition root, core services, currency value object, UI shell, components,
  dialogs, themes, view models, and views.
- Implemented an immutable, validated `AppConfig` and an atomic
  `ConfigService` with corrupt-file quarantine.
- Implemented machine-local path resolution: configuration under `%APPDATA%`
  and logs under `%LOCALAPPDATA%`, both separate from future business data.
- Implemented rotating file logging, correlation IDs, an exception hierarchy,
  a global excepthook, and a user-safe error dialog.
- Implemented a Windows named-mutex single-instance guard.
- Implemented INR currency metadata and display formatting with Indian digit
  grouping, with `float` explicitly rejected.
- Built the main window shell: title, sidebar with 11 navigation entries, top
  bar, stacked content area, status bar, dashboard foundation, and runtime
  light/dark/system theme switching.
- Added 147 automated tests covering configuration, formatting, paths,
  logging, error handling, single instance, architecture boundaries, the shell
  view model, the main window, and real subprocess startup.
- Verified the real entry point with a headless smoke-test flag and confirmed a
  clean startup and shutdown in the log.
- Updated `README.md`, `docs/ARCHITECTURE.md`, and
  `docs/DEVELOPMENT_ROADMAP.md`.
- Initialized a Git repository without committing or pushing, as required by
  the roadmap and the instruction not to commit.

## 4. Files and directories created

### Root files

- `pyproject.toml`
- `requirements.txt`
- `requirements-dev.txt`
- `.gitignore`
- `README.md`
- `scripts/check.ps1`
- `Reports/PHASE_01_REPORT.md` (this report)
- `.git/` (initialized only; no commit was made)

### Application package

- `app/__init__.py`
- `app/main.py`
- `app/app_context.py`
- `app/core/__init__.py`
- `app/core/config.py`
- `app/core/constants.py`
- `app/core/error_handling.py`
- `app/core/exceptions.py`
- `app/core/formatting.py`
- `app/core/logging_config.py`
- `app/core/paths.py`
- `app/core/single_instance.py`
- `app/domain/__init__.py`
- `app/domain/value_objects/__init__.py`
- `app/domain/value_objects/currency.py`
- `app/ui/__init__.py`
- `app/ui/main_window.py`
- `app/ui/components/__init__.py`
- `app/ui/components/cards.py`
- `app/ui/components/placeholder_view.py`
- `app/ui/components/sidebar.py`
- `app/ui/components/top_bar.py`
- `app/ui/dialogs/__init__.py`
- `app/ui/dialogs/error_dialog.py`
- `app/ui/themes/__init__.py`
- `app/ui/themes/manager.py`
- `app/ui/themes/qss.py`
- `app/ui/themes/tokens.py`
- `app/ui/viewmodels/__init__.py`
- `app/ui/viewmodels/shell_viewmodel.py`
- `app/ui/views/__init__.py`
- `app/ui/views/home_view.py`

### Tests

- `tests/conftest.py`
- `tests/test_architecture.py`
- `tests/test_config.py`
- `tests/test_currency.py`
- `tests/test_error_handling.py`
- `tests/test_formatting.py`
- `tests/test_logging.py`
- `tests/test_main_window.py`
- `tests/test_paths.py`
- `tests/test_shell_viewmodel.py`
- `tests/test_single_instance.py`
- `tests/test_startup.py`

### Deliberately not created

`app/services`, `app/repositories`, `app/modules`, `app/infrastructure`,
`app/ui/resources`, `migrations`, and `backup_runner` are absent because no
Phase 1 code uses them. Empty placeholder packages were not added.

## 5. Files modified

Existing files changed during Phase 1:

- `docs/ARCHITECTURE.md` — recorded the locked environment and actual Phase 1
  implementation in §2.3, §14, §15, and the new §16; later noted the resolved
  currency decision.
- `docs/DEVELOPMENT_ROADMAP.md` — marked Phase 1 complete, checked its DoD,
  recorded verification results, Phase 2 dependencies, and updated the
  immediate next step; later recorded the confirmed INR decision.
- `docs/BLUEPRINT.md` — post-report owner-directed change: A-05, Q-01, Q-11, and
  the minor-unit glossary now specify INR / paise and an Indian fiscal year
  (1 April) instead of BDT / poisha and 1 July.
- `docs/DATABASE_SCHEMA.md` — post-report owner-directed change: currency minor
  unit, value-object example, and `business_profile.currency_code` default now
  specify INR; timezone and fiscal-year defaults now specify `Asia/Kolkata`
  (West Bengal, India) and 1 April (April–March).

- `Reports/Initialization_Report_2026-11-12.md` — preserved and annotated on
  2026-11-13 with the owner-confirmed INR currency and Indian fiscal year; the
  rest of the Phase 0 report remains historical.

No existing documentation was deleted or overwritten. `Reports/` previously
contained `Initialization_Report_2026-11-12.md`; it is retained with the
2026-11-13 currency/fiscal-year annotation described above.

## 6. Dependencies added and their purpose

### Runtime — `requirements.txt`

| Package | Version | Purpose |
| --- | --- | --- |
| PySide6 | 6.12.0 | Desktop framework and Qt Widgets UI |
| SQLAlchemy | 2.1.8 | ORM and unit-of-work foundation (installed and import-tested now; used in Phase 2) |
| alembic | 1.20.1 | Schema migrations (installed and import-tested now; used in Phase 2) |
| pydantic | 2.14.3 | Application-boundary validation in later phases (installed and import-tested now) |
| pyqtgraph | 0.14.0 | Charts and dashboards in later phases (installed and import-tested now) |
| numpy | 2.5.4 | PyQtGraph runtime dependency; pinned explicitly for reproducibility |
| reportlab | 5.1.0 | PDF generation in later phases; one-page PDF generation smoke-tested now |
| openpyxl | 3.1.5 | Excel export in later phases; workbook write smoke-tested now |

All seven approved runtime packages were installed in Phase 1 even though only
PySide6 is exercised by production code. This proves the locked stack installs
and imports together on Python 3.14 before Phase 2 relies on it.

### Development — `requirements-dev.txt`

| Package | Version | Purpose |
| --- | --- | --- |
| pytest | 9.2.0 | Test runner |
| ruff | 0.17.5 | Linting and formatting checks |

No other packages were added. `pytest-qt` was considered but not adopted;
offscreen Qt tests work with a plain `QApplication` (ARCHITECTURE.md AQ-08).

## 7. Architecture decisions

- **Layered modular monolith, composition root.** `app/main.py` wires explicit
  dependencies; there is no global mutable service locator. `AppContext` holds
  the Phase 1 wiring.
- **Configuration as a frozen validated dataclass.** `AppConfig` uses explicit
  validation instead of Pydantic for this small fixed shape. Pydantic remains
  installed for later boundary validation. This keeps Phase 1 dependency use
  proportionate.
- **Atomic, recoverable configuration.** Writes use a temporary file, `fsync`,
  and `os.replace`. Invalid files are renamed to
  `config.corrupt-<timestamp>.json` and defaults are used, so a damaged file
  cannot block startup or destroy evidence.
- **Configuration and logs outside business data.** Configuration is stored in
  `%APPDATA%\GobindasBMS` and logs in `%LOCALAPPDATA%\GobindasBMS\logs`, per
  ADR-009. No business database path is defined yet.
- **Design tokens plus generated QSS.** Colours, spacing, and typography live in
  `app/ui/themes/tokens.py`; QSS is generated with `string.Template`. Theme
  switching is runtime and also synchronises `QPalette` for native dialogs.
- **QtCore-only view models.** `ShellViewModel` imports no `QtWidgets`, keeping
  presentation logic testable without widgets.
- **Single-instance guard via Windows named mutex.** `Local\GobindasBMS.App`
  prevents concurrent GUI instances, consistent with ADR-013.
- **Standard-library logging with rotation.** A rotating handler (5 MB × 5) and
  correlation-ID filter provide diagnosable logs without external services.
- **Tests without extra UI frameworks.** UI tests run offscreen with a plain
  `QApplication`; startup tests launch the real entry point in a subprocess
  with isolated `APPDATA` and `LOCALAPPDATA`.
- **No speculative structure.** Future-phase folders and files were not created
  until their owning phase needs them.

## 8. INR currency implementation details

- Currency code: **INR**
- Currency symbol: **₹**
- Decimal places: **2**
- Grouping: **Indian** (last three digits, then groups of two)
- Value object: `app/domain/value_objects/currency.py` defines an immutable
  `Currency` descriptor and the `INR` default.
- Formatting utility: `app/core/formatting.py`, function `format_money`.
- Accepted input: `Decimal`, `int`, or numeric string.
- Rejected input: `float` and `bool` raise `TypeError`; empty, non-numeric, or
  non-finite values raise `ValueError`.
- Rounding: `ROUND_HALF_UP` at the configured number of decimal places.
- Grouping is display-only and configurable through the `Currency` descriptor;
  a `grouping=False` option is available for ungrouped output.
- Configuration carries `currency_code`, `currency_symbol`,
  `currency_decimal_places`, and `currency_grouping`, so the default can become
  configurable later without changing call sites. Multi-currency functionality
  was not implemented.
- No monetary calculation uses `float`. Phase 1 has no accounting or financial
  database tables; exact integer storage is deferred to Phase 2 as instructed.

Verified examples:

```text
Decimal("0")           -> ₹0.00
Decimal("1250.50")     -> ₹1,250.50
Decimal("125000.50")   -> ₹1,25,000.50
Decimal("1000000")     -> ₹10,00,000.00
Decimal("-1000000")    -> -₹10,00,000.00
Decimal("123456789.99")-> ₹12,34,56,789.99
```

The UI displays `₹1,250.50` on the dashboard as a formatting example.

## 9. Tests executed

Commands were run from the repository root with the project interpreter.

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m app.main --smoke-test
```

Test coverage by module (147 tests collected):

| Test module | Tests | Scope |
| --- | ---: | --- |
| `test_architecture.py` | 6 | Import boundaries: domain/core free of Qt and database libraries; no future-phase leakage |
| `test_config.py` | 27 | Defaults, INR defaults, validation, atomic save, round-trip, corrupt-file quarantine |
| `test_currency.py` | 20 | Currency value object and INR defaults |
| `test_error_handling.py` | 4 | Excepthook behaviour and safe messages |
| `test_formatting.py` | 51 | Positive, negative, zero, large Indian values, precision, rounding, invalid and float input |
| `test_logging.py` | 9 | Handler setup, rotation settings, correlation IDs, no duplicate handlers |
| `test_main_window.py` | 10 | Shell construction, navigation entries, theme application, status bar |
| `test_paths.py` | 9 | APPDATA/LOCALAPPDATA resolution, directory creation, filename safety |
| `test_shell_viewmodel.py` | 4 | Initial state, theme persistence, invalid theme rejection, save-failure resilience |
| `test_single_instance.py` | 4 | Acquire/release, second-instance refusal, idempotent release, context manager |
| `test_startup.py` | 3 | Real subprocess startup, corrupt-config startup, no database files created |
| **Total** | **147** | |

Additional manual/scripted verification:

- Each startup subprocess receives a unique `GOBINDAS_MUTEX_NAME`, so the
  single-instance guard cannot make tests fail when the real application or
  another test is running.
- Dependency import and version check for PySide6, SQLAlchemy, Alembic,
  Pydantic, PyQtGraph, NumPy, ReportLab, OpenPyXL, and pytest.
- ReportLab generated a valid one-page PDF during the Phase 1 smoke check.
- OpenPyXL wrote a workbook during the Phase 1 smoke check.
- `QApplication` and a minimal `QMainWindow` were created with the offscreen
  platform.
- Both themes were checked by sampling rendered pixel colours against token
  values, because the implementation agent cannot visually inspect images.
  Token application, the 11 navigation entries, top bar, sidebar, content,
  status bar, INR example, navigation, and theme persistence were confirmed.
- No database, SQLite, ORM, or Alembic file was created by startup or tests.

## 10. Actual test results

Exact results from the final verification run on 2026-11-13:

```text
$ .\.venv\Scripts\python.exe -m ruff check app tests
All checks passed!

$ .\.venv\Scripts\python.exe -m pytest -q
........................................................................ [ 48%]
........................................................................ [ 97%]
...                                                                      [100%]
147 passed in 6.12s

$ .\.venv\Scripts\python.exe -m pytest --collect-only -q
147 tests collected in 0.08s
```

No tests were skipped, xfailed, or disabled. No fake or placeholder passing
tests were added. The suite is repeatable and uses isolated temporary
configuration/log locations where filesystem state matters.

## 11. Application startup verification

Command:

```powershell
.\.venv\Scripts\python.exe -m app.main --smoke-test
```

Observed result:

- Exit code: `0`.
- The main window was created and shown offscreen.
- The dashboard navigation entry was selected.
- The application exited cleanly through the normal shutdown path.
- No traceback, error, or critical entry was written to the log.

Representative log lines from
`%LOCALAPPDATA%\GobindasBMS\logs\app.log`:

```text
2026-11-13 09:38:56 INFO app.main Starting Gobindas Graphics Business Management System 0.1.0 on Python 3.14.6
2026-11-13 09:38:56 INFO app.main Configuration: C:\Users\Ram Chowdhury\AppData\Roaming\GobindasBMS\config.json | theme=system | currency=INR | log level=INFO
2026-11-13 09:38:57 INFO app.ui.main_window Navigated to dashboard
2026-11-13 09:38:57 INFO app.main Main window shown
2026-11-13 09:38:57 INFO app.main Smoke test mode: quitting automatically
2026-11-13 09:38:59 INFO app.ui.main_window Main window closing
2026-11-13 09:38:59 INFO app.main Application shutdown requested
2026-11-13 09:38:59 INFO app.main Application exiting
```

The time between process start and the "Main window shown" entry is
approximately 1 second in this run. An earlier cold run showed about 3 seconds
between process start and the first Qt log line, which is PySide6/Qt
initialization and remains within the ≤5 second cold-start non-functional
requirement. No startup error was found in the log.

The normal interactive command is:

```powershell
.\.venv\Scripts\python.exe -m app.main
```

It was verified through the same startup path; the smoke-test flag only adds an
automatic quit after the window is shown.

## 12. Known limitations

- Phase 1 has no database, persistence, setup wizard, backups, authentication,
  or business modules by design.
- The sidebar entries are navigation placeholders. Except for the dashboard
  foundation, they show clearly labelled placeholder content.
- Theme preference is persisted, but window geometry and multi-monitor
  restoration are deferred to the UI phase.
- The application is not packaged yet; PyInstaller and Inno Setup are later
  phases. It currently runs from the virtual environment.
- The single-instance mutex and path resolution target Windows; the automated
  tests run on Windows with an offscreen Qt platform.
- UI verification was programmatic (widget state and pixel sampling), not a
  human visual review. A human walkthrough is still advisable.
- The INR/BDT documentation conflict was resolved on 2026-11-13 by the owner's
  decision to use INR; `BLUEPRINT.md` and `DATABASE_SCHEMA.md` were updated.
- No code-signing, installer, or clean-VM validation exists yet.
- Log correlation IDs are established for startup and key actions; broader
  per-use-case propagation will grow with application services.

## 13. Outstanding issues

1. **Currency documentation — resolved 2026-11-13.** The owner confirmed INR
   as the default currency. `docs/BLUEPRINT.md` (A-05, Q-01) and
   `docs/DATABASE_SCHEMA.md` were updated from BDT to INR, matching the Phase 1
   implementation. No currency conflict remains.
2. **Owner review of Phase 1.** The architecture walkthrough and explicit
   authorization to start Phase 2 have not yet been given.
3. **Human visual review.** A person should open the app in both themes at
   100% and 150% DPI and confirm the appearance against
   `docs/UI_UX_BLUEPRINT.md`.
4. **Python target confirmation.** CPython 3.14.6 is verified for development.
   The final release interpreter should be re-confirmed at packaging
   (ARCHITECTURE.md AQ-01).
5. **Git state.** A repository was initialized but nothing was committed, per
   instruction. The owner must decide the first commit and branch policy.

No functional defect, failing test, or data-safety issue is known in the Phase 1
scope.

## 14. Deviation from approved documentation

1. **Currency: INR confirmed by the owner (resolved 2026-11-13).**
   - The Phase 1 brief explicitly requires INR (code `INR`, symbol `₹`,
     2 decimals, Indian grouping).
   - Phase 1 implemented INR on that basis.
   - `docs/BLUEPRINT.md` (A-05, Q-01) and `docs/DATABASE_SCHEMA.md` were
     originally written in Phase 0 with BDT assumptions. After the owner
     confirmed INR, both documents were updated to INR on 2026-11-13.
   - No unresolved deviation remains on currency.

2. **Pydantic is installed but not used for Phase 1 configuration.**
   - The stack lists Pydantic for validation, but the Phase 1 configuration is
     a small fixed set of fields. A frozen dataclass with explicit validation
     is simpler and has no framework overhead.
   - Pydantic 2.14.3 is installed, import-tested, and reserved for application
     boundary validation in later phases. This is a proportionate
     implementation choice, not a stack change.

3. **`pytest-qt` was not adopted.**
   - ARCHITECTURE.md listed it as optional. Plain `QApplication` tests with
     `QT_QPA_PLATFORM=offscreen` cover the Phase 1 UI without another
     dependency. ARCHITECTURE.md AQ-08 and §14 were updated accordingly.

4. **Future-phase directories were not created.**
   - The brief's structure shows services, repositories, modules,
     infrastructure, migrations, and backup_runner. The same brief says to
     create only what the phase needs. They were omitted deliberately and are
     scheduled for their owning phases.

5. **Git initialization without commits.**
   - The roadmap requires Git. The instruction forbids committing or pushing
     without explicit request. The repository was initialized and left
     uncommitted.

No other stack, architecture, or scope deviation was made.

## 15. Phase 2 readiness assessment

**Assessment: ready to begin Phase 2 after owner review. The currency
documentation was reconciled to INR on 2026-11-13. Phase 2 has not been
started.**

Ready:

- CPython 3.14.6 virtual environment is reproducible from the pinned manifests.
- The full approved stack installs, imports, and smoke-tests together.
- The composition root, configuration service, path resolution, logging, error
  handling, and shell are working and tested.
- Architecture boundaries are enforced by tests, so database code can be added
  without leaking into the domain or UI.
- Configuration is versioned and written atomically, ready to hold
  schema-adjacent settings.
- Startup and shutdown paths are verified, giving Phase 2 a stable place to
  insert engine construction, migration checks, and integrity checks.

Required before or at the start of Phase 2:

1. Owner approval of this report and explicit authorization to start Phase 2.
2. ~~Resolution of the INR/BDT conflict~~ — completed 2026-11-13; the owner
   confirmed INR and both affected documents were updated.
3. Confirmation of the Phase 2 scope: SQLite engine with ADR-008 PRAGMAs,
   naming conventions, declarative base, `UnitOfWork`, repository base,
   programmatic Alembic, platform-only tables, migration runner, integrity
   checks, and temp-database test fixtures.
4. A decision on whether the first Alembic revision contains the platform
   scaffolding (`app_settings`, `business_profile`) or an empty baseline, as
   noted in the roadmap.

Phase 2 does not require the Phase 3 data-folder wizard. Tests can use temporary
database files, and the production data-folder selection remains a Phase 3
deliverable.

## Verification checklist

- [x] Virtual environment verified: CPython 3.14.6 in `.venv`.
- [x] Dependency installation verified by import/version smoke tests.
- [x] Test suite executed: 147 passed.
- [x] Lint executed: all checks passed.
- [x] Desktop application started successfully.
- [x] Main window opens (verified by smoke test and UI tests).
- [x] Light and dark themes applied and verified programmatically.
- [x] INR formatting verified by 51 formatting tests and UI example.
- [x] Logs checked: clean startup and shutdown, no startup errors.
- [x] Project structure reviewed; only Phase 1 files exist.
- [x] Documentation updated.
- [x] This report exists at `Reports/PHASE_01_REPORT.md` and contains all 15
      required sections.
- [x] No commit or push performed.
- [x] Existing `Reports/` content preserved.

**Phase 1 is complete. Phase 2 must not begin until the owner reviews this
report and explicitly authorizes it.**
