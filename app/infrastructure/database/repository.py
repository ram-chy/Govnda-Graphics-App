"""Generic repository foundation.

Repositories receive the session owned by a :class:`UnitOfWork`; services own
commit and rollback. Business-specific repositories are added with their first
aggregate in later phases.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


class Repository[ModelT]:
    """Minimal typed repository for one mapped model."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    @property
    def session(self) -> Session:
        return self._session

    @property
    def model(self) -> type[ModelT]:
        return self._model

    def get(self, entity_id: Any) -> ModelT | None:
        return self._session.get(self._model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        self._session.delete(entity)


__all__ = ["Repository"]
