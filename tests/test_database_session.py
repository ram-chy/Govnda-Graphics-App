"""Unit-of-work transaction semantics and repository delegation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.infrastructure.database.engine import Database
from app.infrastructure.database.repository import Repository


def _create_scratch_table(database: Database) -> None:
    with database.engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE scratch (value INTEGER)")


def _scratch_count(database: Database) -> int:
    with database.engine.connect() as connection:
        return int(connection.exec_driver_sql("SELECT COUNT(*) FROM scratch").scalar_one())


def test_explicit_commit_persists(initialized_database: Database) -> None:
    _create_scratch_table(initialized_database)

    with initialized_database.unit_of_work() as uow:
        uow.session.connection().exec_driver_sql("INSERT INTO scratch (value) VALUES (1)")
        uow.commit()

    assert _scratch_count(initialized_database) == 1


def test_exit_without_commit_rolls_back(initialized_database: Database) -> None:
    _create_scratch_table(initialized_database)

    with initialized_database.unit_of_work() as uow:
        uow.session.connection().exec_driver_sql("INSERT INTO scratch (value) VALUES (1)")
        assert uow.committed is False

    assert _scratch_count(initialized_database) == 0


def test_exception_rolls_back_and_propagates(initialized_database: Database) -> None:
    _create_scratch_table(initialized_database)

    with pytest.raises(RuntimeError, match="boom"), initialized_database.unit_of_work() as uow:
        uow.session.connection().exec_driver_sql("INSERT INTO scratch (value) VALUES (1)")
        raise RuntimeError("boom")

    assert _scratch_count(initialized_database) == 0


def test_session_closes_after_the_scope(initialized_database: Database) -> None:
    with initialized_database.unit_of_work() as uow:
        session = uow.session

    with pytest.raises(RuntimeError, match="closed"):
        _ = uow.session
    assert not session.in_transaction()


def test_commit_after_close_is_rejected(initialized_database: Database) -> None:
    with initialized_database.unit_of_work() as uow:
        uow.commit()

    with pytest.raises(RuntimeError, match="closed"):
        uow.commit()


def test_rollback_is_idempotent_and_never_raises(initialized_database: Database) -> None:
    uow = initialized_database.unit_of_work()
    uow.rollback()
    with uow:
        pass
    uow.rollback()


def test_repository_delegates_to_the_session() -> None:
    session = MagicMock()
    model = MagicMock()
    repository = Repository(session, model)
    entity = object()

    repository.add(entity)
    session.add.assert_called_once_with(entity)

    session.get.return_value = entity
    assert repository.get(1) is entity
    session.get.assert_called_once_with(model, 1)

    repository.delete(entity)
    session.delete.assert_called_once_with(entity)
    assert repository.session is session
    assert repository.model is model
