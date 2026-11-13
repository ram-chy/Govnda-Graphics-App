"""Application-wide constants.

Values in this module are fixed for the build. User-changeable settings live
in :mod:`app.core.config` and are persisted outside the business data folder.
"""

from __future__ import annotations

APP_NAME = "Gobindas Graphics Business Management System"
APP_SHORT_NAME = "GGBMS"
APP_SLUG = "GobindasBMS"
APP_VERSION = "0.1.0"
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
