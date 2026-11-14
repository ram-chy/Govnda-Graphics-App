"""Application-wide constants.

Values in this module are fixed for the build. User-changeable settings live
in :mod:`app.core.config` and are persisted outside the business data folder.
"""

from __future__ import annotations

APP_NAME = "Gobindas Graphics Business Management System"
APP_SHORT_NAME = "GGBMS"
APP_SLUG = "GobindasBMS"
APP_VERSION = "0.2.0"
ORGANIZATION_NAME = "Gobindas Graphics"

# Currency defaults. The active values are stored in AppConfig so they can be
# made configurable later without changing formatting call sites.
DEFAULT_CURRENCY_CODE = "INR"
DEFAULT_CURRENCY_SYMBOL = "\u20b9"
DEFAULT_CURRENCY_DECIMAL_PLACES = 2
DEFAULT_CURRENCY_GROUPING = "indian"

# Theme preferences accepted by the configuration file.
THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"
AVAILABLE_THEMES = (THEME_SYSTEM, THEME_LIGHT, THEME_DARK)
DEFAULT_THEME = THEME_SYSTEM

DEFAULT_LOG_LEVEL = "INFO"
AVAILABLE_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

CONFIG_SCHEMA_VERSION = 1
CONFIG_FILENAME = "config.json"
LOG_FILENAME = "app.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

# Named mutex used by ADR-013 to keep the GUI single-instance.
MUTEX_NAME = r"Local\GobindasBMS.App"

# Business data root layout (BACKUP_STRATEGY.md §2). The user selects the root;
# the application creates these folders only after explicit confirmation.
DATABASE_FILENAME = "BusinessManagement.db"
DATA_DATABASE_DIR = "Database"
DATA_BACKUPS_DIR = "Backups"
DATA_BACKUPS_AUTOMATIC_DIR = "Automatic"
DATA_BACKUPS_MANUAL_DIR = "Manual"
DATA_BACKUPS_SAFETY_DIR = "Safety"
DATA_ATTACHMENTS_DIR = "Attachments"
DATA_EXPORTS_DIR = "Exports"
DATA_EXPORTS_PDF_DIR = "PDF"
DATA_EXPORTS_EXCEL_DIR = "Excel"

# Setup validation minimum. The baseline database is roughly 12 KiB; one
# mebibyte is a deliberately conservative floor that still lets the operating
# system and SQLite finish the initial write. It is not a database-size estimate.
MINIMUM_FREE_SPACE_BYTES = 1024 * 1024
