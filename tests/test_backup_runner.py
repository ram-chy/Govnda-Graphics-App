"""Phase 4 headless backup runner tests: stable exit codes and retention."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.core import constants
from app.core.config import AppConfig, ConfigService
from app.core.exceptions import BackupError, ConfigurationError
from app.domain.backup import BackupType
from app.infrastructure.backup.lock import OperationLock
from app.tools.backup import _apply_retention, _load_config, _resolve_config_path, run_backup
from tests.backup_helpers import (
    build_directories,
    build_factory,
    build_runtime,
    create_data_root,
    save_location,
)
from tests.backup_helpers import (
    build_directories as _directories,
)


def _config(tmp_path: Path) -> tuple[ConfigService, Path, Path]:
    root, database_path = create_data_root(tmp_path)
    config_path = tmp_path / "config" / "config.json"
    config_service = ConfigService(config_path)
    save_location(config_service, root, database_path)
    return config_service, root, database_path


def test_runner_creates_a_scheduled_automatic_backup(tmp_path: Path) -> None:
    config_service, root, _database = _config(tmp_path)
    factory = build_factory(config_service, build_runtime(_database))

    code = run_backup(config_path=config_service.config_path, scheduled=True, factory=factory)

    assert code == constants.BACKUP_EXIT_SUCCESS
    directories = build_directories(root)
    backups = list(directories.automatic.glob("*.db"))
    assert len(backups) == 1
    assert backups[0].name.endswith("_AUTOMATIC.db")
    assert not list(directories.manual.glob("*.db"))


def test_runner_creates_a_manual_backup_when_not_scheduled(tmp_path: Path) -> None:
    config_service, root, database = _config(tmp_path)
    factory = build_factory(config_service, build_runtime(database))

    code = run_backup(config_path=config_service.config_path, scheduled=False, factory=factory)

    assert code == constants.BACKUP_EXIT_SUCCESS
    directories = build_directories(root)
    assert len(list(directories.manual.glob("*.db"))) == 1
    assert not list(directories.automatic.glob("*.db"))


def test_runner_reports_a_missing_configuration(tmp_path: Path) -> None:
    code = run_backup(config_path=tmp_path / "missing.json", scheduled=True)

    assert code == constants.BACKUP_EXIT_CONFIGURATION


def test_runner_reports_an_invalid_configuration_without_quarantining_it(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")

    code = run_backup(config_path=path, scheduled=True)

    assert code == constants.BACKUP_EXIT_CONFIGURATION
    assert path.exists()
    assert not list(tmp_path.glob("config.corrupt-*"))


def test_runner_reports_a_legacy_configuration_without_a_data_root(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    path = tmp_path / "config.json"
    ConfigService(path).save(
        AppConfig(theme="light", database_path=str(database_path))
    )
    assert root.is_dir()

    code = run_backup(config_path=path, scheduled=True)

    assert code == constants.BACKUP_EXIT_CONFIGURATION


def test_runner_reports_a_locked_operation(tmp_path: Path) -> None:
    config_service, root, database = _config(tmp_path)
    directories = _directories(root)
    directories.ensure()
    holder = OperationLock(directories.lock_path, operation="restore")
    holder.acquire()
    try:
        code = run_backup(
            config_path=config_service.config_path,
            scheduled=True,
            factory=build_factory(config_service, build_runtime(database)),
        )
    finally:
        holder.release()

    assert code == constants.BACKUP_EXIT_LOCKED
    assert not list(directories.automatic.glob("*.db"))


def test_runner_reports_a_backup_failure(tmp_path: Path) -> None:
    config_service, root, database = _config(tmp_path)
    database.unlink()

    code = run_backup(
        config_path=config_service.config_path,
        scheduled=True,
        factory=build_factory(config_service, build_runtime(database)),
    )

    assert code == constants.BACKUP_EXIT_FAILURE
    directories = build_directories(root)
    assert not list(directories.automatic.glob("*.db"))


def test_runner_retention_failure_never_changes_the_exit_code(tmp_path: Path) -> None:
    config_service, root, database = _config(tmp_path)
    workspace = build_factory(config_service, build_runtime(database)).build()

    def fail(*_args, **_kwargs):
        raise BackupError("retention failed", user_message="Retention failed.")

    workspace.retention_service.apply = fail  # type: ignore[method-assign]
    result = workspace.backup_service.create_backup(
        BackupType.AUTOMATIC, trigger="scheduled"
    )

    assert result.path.is_file()
    _apply_retention(workspace)
    assert result.path.is_file()


def test_apply_retention_swallows_an_unexpected_error() -> None:
    class Exploding:
        def apply(self, **_kwargs):
            raise RuntimeError("boom")

    workspace = SimpleNamespace(
        config=AppConfig(backup_retention_days=30, backup_keep_minimum=5),
        retention_service=Exploding(),
    )

    _apply_retention(workspace)  # must not raise


def test_load_config_rejects_incomplete_settings(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    ConfigService(path).save(AppConfig())

    try:
        _load_config(ConfigService(path))
    except ConfigurationError as error:
        assert "no business data location" in error.user_message
    else:
        raise AssertionError("incomplete configuration was accepted")


def test_resolve_config_path_defaults_to_an_absolute_path(tmp_path: Path) -> None:
    raw = Path("relative-config.json")
    resolved = _resolve_config_path(raw)
    assert resolved.is_absolute()

    explicit = tmp_path / "explicit.json"
    assert _resolve_config_path(explicit) == explicit


def test_runner_does_not_create_a_database_when_missing(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    config_path = tmp_path / "config" / "config.json"
    config_service = ConfigService(config_path)
    save_location(config_service, root, database_path)
    database_path.unlink()

    code = run_backup(
        config_path=config_path,
        scheduled=True,
        factory=build_factory(config_service, build_runtime(database_path)),
    )

    assert code == constants.BACKUP_EXIT_FAILURE
    assert not database_path.exists()
