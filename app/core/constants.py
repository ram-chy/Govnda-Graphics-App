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
DATA_LOGOS_DIR = "Logos"
DATA_EXPORTS_DIR = "Exports"
DATA_EXPORTS_PDF_DIR = "PDF"
DATA_EXPORTS_EXCEL_DIR = "Excel"

# Setup validation minimum. The baseline database is roughly 12 KiB; one
# mebibyte is a deliberately conservative floor that still lets the operating
# system and SQLite finish the initial write. It is not a database-size estimate.
MINIMUM_FREE_SPACE_BYTES = 1024 * 1024

# ---------------------------------------------------------------------------
# Backup, restore and relocation (Phase 4, BACKUP_STRATEGY.md).
# ---------------------------------------------------------------------------
BACKUP_FILENAME_PREFIX = "BusinessManagement"
BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
BACKUP_METADATA_VERSION = 1
BACKUP_METADATA_SUFFIX = ".meta.json"
BACKUP_TEMP_SUFFIX = ".tmp"
BACKUP_LOCK_FILENAME = ".backup.lock"
BACKUP_STATE_FILENAME = "backup_state.json"
BACKUP_LAST_ERROR_FILENAME = "backup_last_error.json"

DEFAULT_BACKUP_ENABLED = True
DEFAULT_BACKUP_TIME = "22:00"
DEFAULT_BACKUP_RETENTION_DAYS = 30
DEFAULT_BACKUP_KEEP_MINIMUM = 5
BACKUP_RETENTION_MINIMUM_DAYS = 1
BACKUP_RETENTION_MAXIMUM_DAYS = 3650
BACKUP_KEEP_MINIMUM_FLOOR = 1
BACKUP_KEEP_MINIMUM_CEILING = 100

# Free-space reserve for preflight. A backup needs at least the source size
# plus headroom for the temporary file, metadata, and filesystem slack.
BACKUP_FREE_SPACE_FACTOR_PERCENT = 120
BACKUP_FREE_SPACE_RESERVE_BYTES = 50 * 1024 * 1024

# Restore and relocation artifacts (same volume as the live database).
RESTORE_STAGING_FILENAME = ".restore-staging.db"
RESTORE_ASSETS_STAGING_DIR = ".restore-assets-staging"
RESTORE_ASSETS_ROLLBACK_DIR = "assets-rollback"
RESTORE_MARKER_FILENAME = ".restore-in-progress.json"
RELOCATION_MARKER_FILENAME = ".relocation-in-progress.json"
RECOVERY_REQUIRED_MARKER_FILENAME = ".recovery-required.json"
ROLLBACK_DIR_NAME = "rollback"

# Backups older than this are not trustworthy evidence for retention, and an
# interrupted operation may leave a temporary file behind (BACKUP_STRATEGY §9).
STALE_TEMP_AGE_SECONDS = 24 * 60 * 60
ROLLBACK_RETENTION_DAYS = 7

# A stale lock may be reclaimed only after the owning process has been proven
# dead. The reclaim guard serialises recovery between competing processes.
LOCK_RECLAIM_SUFFIX = ".reclaim"

# Windows Task Scheduler integration.
SCHEDULED_TASK_NAME = r"GobindasBMS\DailyBackup"
SCHEDULED_TASK_DESCRIPTION = "Gobindas Graphics Business Management System daily backup"

# Headless backup runner exit codes (app.tools.backup).
BACKUP_EXIT_SUCCESS = 0
BACKUP_EXIT_FAILURE = 1
BACKUP_EXIT_CONFIGURATION = 2
BACKUP_EXIT_LOCKED = 3

# Catch-up runs once per application session after this delay so the window is
# responsive and first-launch work has settled.
CATCH_UP_DELAY_MS = 15_000

# UI feedback durations (Phase 5). Status messages remain long enough to read,
# while transient confirmations auto-dismiss after four seconds.
STATUS_MESSAGE_TIMEOUT_MS = 6_000
DATABASE_MESSAGE_TIMEOUT_MS = 8_000
TOAST_DURATION_MS = 4_000
