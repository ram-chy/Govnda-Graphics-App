"""Explicit dependency wiring for the application root (composition root)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import AppConfig, ConfigService
from app.core.paths import AppPaths


@dataclass(frozen=True, slots=True)
class AppContext:
    """Objects constructed at startup and passed explicitly to the UI."""

    paths: AppPaths
    config: AppConfig
    config_service: ConfigService

    @classmethod
    def create(cls, paths: AppPaths) -> AppContext:
        config_service = ConfigService(paths.config_file)
        return cls(
            paths=paths,
            config=config_service.load(),
            config_service=config_service,
        )
