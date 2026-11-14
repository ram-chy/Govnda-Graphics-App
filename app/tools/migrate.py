"""Headless database maintenance tool.

Every command takes an explicit absolute database path. There is no default
location and no command creates a database implicitly: ``init`` is the only
command that may create a file, and it refuses to overwrite an existing one.

Examples (from the repository root)::

    python -m app.tools.migrate --database "D:\\GGBMS\\gobindas.db" init
    python -m app.tools.migrate --database "D:\\GGBMS\\gobindas.db" status
    python -m app.tools.migrate --database "D:\\GGBMS\\gobindas.db" upgrade
    python -m app.tools.migrate --database "D:\\GGBMS\\gobindas.db" history
    python -m app.tools.migrate --database "D:\\GGBMS\\gobindas.db" check --full
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core.exceptions import AppError
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.health import DatabaseDiagnostics
from app.infrastructure.database.migrations import MigrationHistoryEntry, MigrationManager


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.tools.migrate",
        description=(
            "Inspect and migrate a Gobindas Graphics database. The database path must be "
            "an absolute path and must already exist except for the init command."
        ),
    )
    parser.add_argument(
        "--database",
        required=True,
        type=Path,
        help="Absolute path to the SQLite database file.",
    )
    parser.add_argument(
        "--busy-timeout-ms",
        type=int,
        default=None,
        help="SQLite busy timeout in milliseconds (default: application default).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Log verbosity for the maintenance run.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="Create a new database and apply all migrations.")
    upgrade = commands.add_parser("upgrade", help="Upgrade an existing database.")
    upgrade.add_argument("--revision", default="head", help="Target revision (default: head).")
    downgrade = commands.add_parser("downgrade", help="Downgrade an existing database.")
    downgrade.add_argument(
        "--revision",
        required=True,
        help="Target revision, or 'base' to remove every revision.",
    )
    commands.add_parser("status", help="Show the current revision and whether an upgrade is due.")
    commands.add_parser("history", help="List migration scripts in application order.")
    check = commands.add_parser("check", help="Run database health checks.")
    check.add_argument(
        "--full",
        action="store_true",
        help="Also run the expensive PRAGMA integrity_check.",
    )
    return parser


def _database_from_args(args: argparse.Namespace) -> Database:
    kwargs = {}
    if args.busy_timeout_ms is not None:
        kwargs["busy_timeout_ms"] = args.busy_timeout_ms
    return Database(DatabaseConfig(path=args.database, **kwargs))


def _print_status(status: object) -> None:
    from app.infrastructure.database.migrations import MigrationStatus

    assert isinstance(status, MigrationStatus)
    print(f"state:   {status.state.value}")
    print(f"current: {status.current_revision or '(none)'}")
    print(f"head:    {status.head_revision or '(none)'}")
    if status.pending_revisions:
        print(f"pending: {', '.join(status.pending_revisions)}")


def _print_history(entries: list[MigrationHistoryEntry]) -> None:
    for entry in entries:
        description = f" - {entry.description}" if entry.description else ""
        print(f"{entry.revision} (down: {entry.down_revision or 'base'}){description}")


def _run(args: argparse.Namespace, database: Database) -> int:
    manager = MigrationManager(database)

    if args.command == "init":
        _print_status(manager.create_database())
        return 0

    if args.command == "upgrade":
        _print_status(manager.upgrade(args.revision))
        return 0

    if args.command == "downgrade":
        _print_status(manager.downgrade(args.revision))
        return 0

    if args.command == "status":
        _print_status(manager.status())
        return 0

    if args.command == "history":
        _print_history(manager.history())
        return 0

    if args.command == "check":
        report = DatabaseDiagnostics(database).check(full=args.full)
        print(f"status:  {report.status.value}")
        print(f"message: {report.message}")
        for name, result in report.checks.items():
            print(f"  {name}: {result}")
        if report.file_info is not None:
            info = report.file_info
            print(f"  size: {info.size_bytes} bytes")
            print(f"  wal:  exists={info.wal_exists} size={info.wal_size_bytes}")
            print(f"  shm:  exists={info.shm_exists} size={info.shm_size_bytes}")
        if report.migration is not None:
            print(f"  schema revision: {report.migration.current_revision}")
        return 0 if report.healthy else 1

    raise AssertionError(f"unhandled command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.database.is_absolute():
        print(
            f"error: --database must be an absolute path (got {args.database})",
            file=sys.stderr,
        )
        return 2

    database: Database | None = None
    try:
        database = _database_from_args(args)
        database.config.validate_parent()
        return _run(args, database)
    except AppError as exc:
        print(f"error: {exc.user_message}", file=sys.stderr)
        print(f"detail: {exc}", file=sys.stderr)
        return 1
    finally:
        if database is not None:
            database.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
