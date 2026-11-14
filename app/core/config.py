"""Application configuration stored in ``%APPDATA%\\GobindasBMS\\config.json``.

The configuration file is separate from the business database and is written
atomically so a crash cannot leave a half-written file. Invalid configuration
is preserved for diagnosis and the application continues with defaults rather
than risking a startup failure loop.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.core import constants
from app.core.exceptions import ConfigurationError
from app.domain.value_objects.currency import Currency

logger = logging.getLogger(__name__)

_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated, immutable application settings."""

    schema_version: int = constants.CONFIG_SCHEMA_VERSION
    currency_code: str = constants.DEFAULT_CURRENCY_CODE
    currency_symbol: str = constants.DEFAULT_CURRENCY_SYMBOL
    currency_decimal_places: int = constants.DEFAULT_CURRENCY_DECIMAL_PLACES
    currency_grouping: str = constants.DEFAULT_CURRENCY_GROUPING
    theme: str = constants.DEFAULT_THEME
    log_level: str = constants.DEFAULT_LOG_LEVEL
    # Absolute path to the business data root chosen in the setup wizard. It is
    # ``None`` until setup records a location, or for a legacy Phase 2 config
    # that stored only ``database_path``.
    data_root: str | None = None
    # Absolute path to the SQLite database. ``None`` means no database has been
    # configured yet; the setup wizard owns that decision in Phase 3. There is
    # deliberately no default location so the application can never silently
    # create a database on C:.
    database_path: str | None = None

    @property
    def app_name(self) -> str:
        return constants.APP_NAME

    @property
    def app_version(self) -> str:
        return constants.APP_VERSION

    @property
    def currency(self) -> Currency:
        return Currency(
            code=self.currency_code,
            symbol=self.currency_symbol,
            decimal_places=self.currency_decimal_places,
            grouping=self.currency_grouping,
        )

    def with_theme(self, theme: str) -> AppConfig:
        updated = replace(self, theme=theme)
        updated.validate()
        return updated

    def with_database_location(self, *, data_root: Path, database_path: Path) -> AppConfig:
        """Return a validated copy pointing at the selected business location."""
        updated = replace(
            self,
            data_root=str(data_root),
            database_path=str(database_path),
        )
        updated.validate()
        return updated

    def validate(self) -> None:
        """Raise :class:`ConfigurationError` when a field is invalid."""
        if self.schema_version != constants.CONFIG_SCHEMA_VERSION:
            raise ConfigurationError(
                f"unsupported configuration schema version {self.schema_version!r}; "
                f"expected {constants.CONFIG_SCHEMA_VERSION}"
            )
        if not isinstance(self.currency_code, str) or not _CURRENCY_CODE_PATTERN.match(
            self.currency_code
        ):
            raise ConfigurationError("currency_code must be a three-letter ISO 4217 code")
        if not isinstance(self.currency_symbol, str) or not self.currency_symbol.strip():
            raise ConfigurationError("currency_symbol must not be empty")
        if (
            isinstance(self.currency_decimal_places, bool)
            or not isinstance(self.currency_decimal_places, int)
            or not 0 <= self.currency_decimal_places <= 4
        ):
            raise ConfigurationError("currency_decimal_places must be an integer from 0 to 4")
        if self.currency_grouping not in ("indian", "western"):
            raise ConfigurationError("currency_grouping must be 'indian' or 'western'")
        if self.theme not in constants.AVAILABLE_THEMES:
            raise ConfigurationError(
                f"theme must be one of {', '.join(constants.AVAILABLE_THEMES)}"
            )
        if self.log_level not in constants.AVAILABLE_LOG_LEVELS:
            raise ConfigurationError(
                f"log_level must be one of {', '.join(constants.AVAILABLE_LOG_LEVELS)}"
            )
        if self.data_root is not None:
            if not isinstance(self.data_root, str) or not self.data_root.strip():
                raise ConfigurationError("data_root must be a non-empty absolute path or null")
            root = Path(self.data_root)
            if not root.is_absolute():
                raise ConfigurationError("data_root must be an absolute path")
            if root.name in ("", ".", ".."):
                raise ConfigurationError("data_root must name a directory")

        if self.database_path is not None:
            if not isinstance(self.database_path, str) or not self.database_path.strip():
                raise ConfigurationError("database_path must be a non-empty absolute path or null")
            candidate = Path(self.database_path)
            if not candidate.is_absolute():
                raise ConfigurationError("database_path must be an absolute path")
            if candidate.name in ("", ".", ".."):
                raise ConfigurationError("database_path must name a database file")

        if self.data_root is not None and self.database_path is not None:
            root = Path(self.data_root)
            candidate = Path(self.database_path)
            try:
                inside_root = candidate.is_relative_to(root)
            except ValueError:
                inside_root = False
            if not inside_root:
                raise ConfigurationError("database_path must reside inside data_root")


def _read_field(data: Mapping[str, Any], key: str, default: Any) -> Any:
    value = data.get(key, default)
    if isinstance(value, bool) and isinstance(default, int):
        raise ConfigurationError(f"{key} must be an integer")
    if isinstance(default, int) and not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer")
    if isinstance(default, str) and not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string")
    return value


def _read_optional_str(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string or null")
    return value


def _config_from_mapping(data: Mapping[str, Any]) -> AppConfig:
    if not isinstance(data, Mapping):
        raise ConfigurationError("configuration root must be a JSON object")

    config = AppConfig(
        schema_version=_read_field(data, "schema_version", constants.CONFIG_SCHEMA_VERSION),
        currency_code=_read_field(data, "currency_code", constants.DEFAULT_CURRENCY_CODE),
        currency_symbol=_read_field(
            data, "currency_symbol", constants.DEFAULT_CURRENCY_SYMBOL
        ),
        currency_decimal_places=_read_field(
            data, "currency_decimal_places", constants.DEFAULT_CURRENCY_DECIMAL_PLACES
        ),
        currency_grouping=_read_field(
            data, "currency_grouping", constants.DEFAULT_CURRENCY_GROUPING
        ),
        theme=_read_field(data, "theme", constants.DEFAULT_THEME),
        log_level=_read_field(data, "log_level", constants.DEFAULT_LOG_LEVEL),
        data_root=_read_optional_str(data, "data_root"),
        database_path=_read_optional_str(data, "database_path"),
    )
    config.validate()
    return config


class ConfigLoadStatus(StrEnum):
    """Outcome of loading the configuration file."""

    MISSING = "missing"
    LOADED = "loaded"
    RECOVERED = "recovered"


@dataclass(frozen=True, slots=True)
class ConfigLoadResult:
    """Loaded configuration plus how it was obtained.

    ``RECOVERED`` means the file existed but was invalid. It was preserved with a
    ``.corrupt-<timestamp>`` suffix and defaults were returned. Startup uses this
    distinction to offer a recovery workflow rather than silently re-running
    first-launch setup.
    """

    config: AppConfig
    status: ConfigLoadStatus
    quarantined_path: Path | None = None


class ConfigService:
    """Loads and atomically saves :class:`AppConfig`."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        return self._config_path

    def load(self) -> AppConfig:
        """Load configuration, falling back to defaults if the file is unusable.

        A malformed or invalid file is renamed with a ``.corrupt-<timestamp>``
        suffix so it can be inspected later and is never silently destroyed.
        """
        return self.load_with_status().config

    def load_with_status(self) -> ConfigLoadResult:
        """Load configuration and report whether it was missing or repaired."""
        if not self._config_path.exists():
            return ConfigLoadResult(AppConfig(), ConfigLoadStatus.MISSING)

        try:
            raw = self._config_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(
                f"configuration file could not be read: {self._config_path}"
            ) from exc

        try:
            data = json.loads(raw)
            config = _config_from_mapping(data)
            return ConfigLoadResult(config, ConfigLoadStatus.LOADED)
        except (json.JSONDecodeError, ConfigurationError) as exc:
            logger.warning(
                "Configuration file is invalid and will be reset to defaults: %s (%s)",
                self._config_path,
                exc,
            )
            quarantined = self._quarantine_invalid_file()
            return ConfigLoadResult(
                AppConfig(),
                ConfigLoadStatus.RECOVERED,
                quarantined_path=quarantined,
            )

    def save(self, config: AppConfig) -> None:
        """Validate and atomically replace the configuration file."""
        config.validate()
        payload = {
            "schema_version": config.schema_version,
            "currency_code": config.currency_code,
            "currency_symbol": config.currency_symbol,
            "currency_decimal_places": config.currency_decimal_places,
            "currency_grouping": config.currency_grouping,
            "theme": config.theme,
            "log_level": config.log_level,
            "data_root": config.data_root,
            "database_path": config.database_path,
        }

        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigurationError(
                f"configuration directory could not be created: {self._config_path.parent}"
            ) from exc

        temp_path: Path | None = None
        try:
            file_descriptor, temp_name = tempfile.mkstemp(
                prefix=".config-", suffix=".tmp", dir=self._config_path.parent
            )
            temp_path = Path(temp_name)
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self._config_path)
            temp_path = None
        except OSError as exc:
            raise ConfigurationError(
                f"configuration file could not be saved: {self._config_path}"
            ) from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _quarantine_invalid_file(self) -> Path | None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self._config_path.with_name(
            f"{self._config_path.stem}.corrupt-{timestamp}{self._config_path.suffix}"
        )
        counter = 1
        while target.exists():
            target = self._config_path.with_name(
                f"{self._config_path.stem}.corrupt-{timestamp}-{counter}"
                f"{self._config_path.suffix}"
            )
            counter += 1
        try:
            os.replace(self._config_path, target)
            logger.warning("Invalid configuration preserved at %s", target)
            return target
        except OSError:
            logger.warning(
                "Invalid configuration could not be moved aside: %s",
                self._config_path,
                exc_info=True,
            )
            return None
