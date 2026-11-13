# Gobindas Graphics Business Management System

A standalone, offline Windows desktop application for small-business management.
Built with Python 3.14, PySide6 (Qt Widgets), and a layered MVVM / application
service architecture.

**Current status: Phase 1 complete.** The project contains the technical
foundation only. There is no database, no business module, and no sample data.

## Phase 1 scope

Implemented:

- Reproducible Python virtual environment and pinned dependencies.
- Application package structure for UI, domain, and core services.
- Runnable desktop shell: sidebar navigation, top bar, content area, status bar.
- Light and dark themes with runtime switching and persistence.
- Application configuration stored separately from business data.
- INR currency formatting with Indian digit grouping.
- Rotating file logging, correlation IDs, and a global exception hook.
- Single-instance guard.
- Unit, UI, and startup tests.

Explicitly not implemented (later phases): SQLite/SQLAlchemy/Alembic, setup
wizard, backups, authentication, customers, suppliers, products, sales,
purchases, inventory, accounting, expenses, and reports.

## Requirements

| Item | Value |
| --- | --- |
| OS | Windows 10 22H2 or Windows 11, 64-bit |
| Python | CPython 3.14.6 (tested; 3.13 is allowed by `pyproject.toml`) |
| Desktop framework | PySide6 6.12.0 |
| Database | None yet (SQLite in Phase 2) |

No system-wide Python packages are used. All commands below run from the
repository root `D:\Development\Gobindas Graphics`.

## Environment setup

PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If script execution is blocked for the current session, either run
`Set-ExecutionPolicy -Scope Process Bypass` or call the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`requirements.txt` contains the exact runtime versions. `requirements-dev.txt`
adds pytest and ruff. `pyproject.toml` contains compatible version ranges for
the same stack.

## Running the application

```powershell
.\.venv\Scripts\python.exe -m app.main
```

A headless startup self-check (starts the shell, verifies it initialises, then
exits after about one second) is available for verification:

```powershell
.\.venv\Scripts\python.exe -m app.main --smoke-test
```

Normal startup creates only the log folder. No database or business file is
created in Phase 1.

## Testing and linting

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests
```

Or run both with the helper script:

```powershell
.\scripts\check.ps1
```

UI tests use Qt's `offscreen` platform platform plugin, so they run without
opening windows. The startup tests launch the real entry point in a subprocess
with isolated `APPDATA` and `LOCALAPPDATA` folders.

## Configuration and logs

| Item | Location |
| --- | --- |
| Configuration | `%APPDATA%\GobindasBMS\config.json` |
| Logs | `%LOCALAPPDATA%\GobindasBMS\logs\app.log` |
| Business data | Not configured in Phase 1; chosen in a later phase |

The configuration file is created on the first settings change (for example,
switching the theme). It is written atomically. An invalid file is preserved as
`config.corrupt-<timestamp>.json` and defaults are used instead, so a damaged
file cannot prevent startup or destroy the previous content.

Logging rotates at 5 MB with five retained files. Logs contain timestamps,
levels, module names, correlation IDs, and error details. They must not contain
personal or financial payloads.

## Default currency

- Code: **INR**
- Symbol: **₹**
- Decimal places: **2**
- Grouping: **Indian** (`₹1,25,000.50`)

Formatting lives in `app/core/formatting.py` and is separate from calculation
logic. It accepts `Decimal`, `int`, or numeric strings and rejects `float`
values explicitly, so display code cannot introduce binary rounding errors.

```python
from decimal import Decimal
from app.core.formatting import format_money

format_money(Decimal("1250.50"))       # ₹1,250.50
format_money(Decimal("125000.50"))     # ₹1,25,000.50
format_money(Decimal("-1000000"))      # -₹10,00,000.00
```

The active currency is read from `AppConfig.currency`, so changing it later
does not require changing formatting call sites.

> **Confirmed currency decision:** INR is the default currency. The Phase 1
> implementation, `docs/BLUEPRINT.md` (A-05, Q-01), and
> `docs/DATABASE_SCHEMA.md` now agree on INR with 2 decimal places.

## Project structure

```text
app/
├── __init__.py
├── main.py                     # Composition root and entry point
├── app_context.py              # Explicit startup wiring
├── core/
│   ├── config.py               # AppConfig, validation, atomic config service
│   ├── constants.py            # Fixed application constants
│   ├── exceptions.py           # Application exception hierarchy
│   ├── formatting.py           # INR / Indian-grouping display formatting
│   ├── logging_config.py       # Rotating logging and correlation IDs
│   ├── error_handling.py       # Global excepthook
│   ├── paths.py                # %APPDATA% / %LOCALAPPDATA% paths
│   └── single_instance.py      # Named Windows mutex guard
├── domain/
│   └── value_objects/
│       └── currency.py         # Currency descriptor and INR default
└── ui/
    ├── main_window.py          # Shell layout and navigation
    ├── components/             # Sidebar, top bar, cards, placeholder view
    ├── dialogs/                # Safe user-facing error dialogs
    ├── themes/                 # Tokens, QSS generator, runtime theme manager
    ├── viewmodels/             # QtCore-only view models
    └── views/                  # Dashboard foundation
tests/                          # pytest unit, UI, and startup tests
scripts/check.ps1               # Lint + test helper
docs/                           # Approved project documentation
Reports/                        # Phase completion reports
```

`app/services`, `app/repositories`, `app/modules`, `app/infrastructure`,
`migrations`, and `backup_runner` are intentionally absent until the phases
that need them.

## Architecture rules in force

- Views hold no business logic; view models never import `QtWidgets`.
- Domain code imports no Qt, SQLAlchemy, Alembic, or `sqlite3`.
- Core infrastructure imports no Qt or database libraries.
- Money is never handled through `float`.
- Configuration and logs live outside the future business data folder.
- Dependencies are passed explicitly through `AppContext`; there is no global
  service locator.

These boundaries are checked by `tests/test_architecture.py`.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `ModuleNotFoundError: PySide6` | Activate `.venv` or use `.\.venv\Scripts\python.exe`. |
| App exits immediately | Check `%LOCALAPPDATA%\GobindasBMS\logs\app.log`. |
| "already running" message | Only one GUI instance is allowed; close the existing window. |
| Theme resets after restart | Check that `%APPDATA%\GobindasBMS` is writable; see the log for a save error. |
| Invalid configuration | The old file is kept as `config.corrupt-*.json`; the app starts with defaults. |
| Tests cannot open a display | Set `QT_QPA_PLATFORM=offscreen` (the test suite sets it automatically). |

## Documentation

- `docs/BLUEPRINT.md` - product scope and open questions
- `docs/ARCHITECTURE.md` - technical architecture and Phase 1 implementation notes
- `docs/DEVELOPMENT_ROADMAP.md` - phase plan and completion status
- `docs/UI_UX_BLUEPRINT.md` - UI direction and design tokens
- `docs/BACKUP_STRATEGY.md`, `docs/SECURITY_AND_DATA_PROTECTION.md`,
  `docs/DATABASE_SCHEMA.md` - later-phase references
- `Reports/PHASE_01_REPORT.md` - Phase 1 completion report

## Next phase

Phase 2 adds SQLite, SQLAlchemy 2, Alembic, a unit-of-work foundation, and
integrity checks, with no business tables beyond platform scaffolding. Do not
start Phase 2 until the Phase 1 report is reviewed and authorized.
