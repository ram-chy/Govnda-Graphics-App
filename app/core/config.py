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


def _read_field(data: Mapping[str, Any], key: str, default: Any) -> Any:
    value = data.get(key, default)
    if isinstance(value, bool) and isinstance(default, int):
        raise ConfigurationError(f"{key} must be an integer")
    if isinstance(default, int) and not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer")
    if isinstance(default, str) and not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string")
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
    )
    config.validate()
    return config


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
        if not self._config_path.exists():
            return AppConfig()

        try:
            raw = self._config_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(
                f"configuration file could not be read: {self._config_path}"
            ) from exc

        try:
            data = json.loads(raw)
            return _config_from_mapping(data)
        except (json.JSONDecodeError, ConfigurationError) as exc:
            logger.warning(
                "Configuration file is invalid and will be reset to defaults: %s (%s)",
                self._config_path,
                exc,
            )
            self._quarantine_invalid_file()
            return AppConfig()

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

    def _quarantine_invalid_file(self) -> None:
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
        except OSError:
            logger.warning(
                "Invalid configuration could not be moved aside: %s",
                self._config_path,
                exc_info=True,
            )
