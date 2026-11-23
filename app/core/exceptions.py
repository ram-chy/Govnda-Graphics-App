"""Application exception hierarchy.

Domain and infrastructure code raises specific exceptions; the presentation
layer decides how to show them. ``user_message`` is safe to display and never
contains technical detail, SQL, or file content.
"""

from __future__ import annotations

from collections.abc import Mapping

DEFAULT_USER_MESSAGE = "The operation could not be completed. See the application log for details."


class AppError(Exception):
    """Base class for all expected application errors."""

    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message = user_message or DEFAULT_USER_MESSAGE


class ConfigurationError(AppError):
    """The configuration file is missing, unreadable, or invalid."""


class ValidationError(AppError):
    """Input failed application-level validation."""

    def __init__(
        self,
        message: str,
        *,
        field_errors: Mapping[str, str] | None = None,
        user_message: str | None = None,
    ) -> None:
        super().__init__(message, user_message=user_message)
        self.field_errors: dict[str, str] = dict(field_errors or {})


class DomainRuleError(AppError):
    """A business rule was violated."""


class NotFoundError(AppError):
    """A requested record does not exist."""


class ConflictError(AppError):
    """A uniqueness or concurrency conflict occurred."""


class SetupError(AppError):
    """First-launch setup could not complete safely."""


class DatabaseUnavailableError(AppError):
    """The configured database cannot be opened or reached."""


class MigrationError(AppError):
    """A schema migration failed or the schema is newer than the application."""


class BackupError(AppError):
    """A backup operation failed."""


class BackupVerificationError(BackupError):
    """A created or selected backup did not pass verification."""


class OperationLockedError(AppError):
    """Another backup, restore, relocation, or upgrade owns the operation lock."""

    def __init__(
        self,
        message: str,
        *,
        owner: object | None = None,
        user_message: str | None = None,
    ) -> None:
        super().__init__(message, user_message=user_message)
        self.owner = owner


class RestoreError(AppError):
    """A restore operation failed."""


class RelocationError(AppError):
    """The database could not be moved to the selected location."""


class RetentionError(AppError):
    """Backup retention could not be applied safely."""


class SchedulerError(AppError):
    """Windows Task Scheduler registration or removal failed."""


class UpgradeError(AppError):
    """A schema upgrade could not be performed safely."""


class ExportError(AppError):
    """A PDF or Excel export failed."""


class AuthenticationError(AppError):
    """Authentication failed or the cooldown policy rejected an attempt."""


class AuthorizationError(AppError):
    """The authenticated actor lacks a required permission or the session is locked."""

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        permission: str | None = None,
    ) -> None:
        super().__init__(message, user_message=user_message)
        self.permission = permission


class SessionError(AppError):
    """The in-memory session is absent, locked, or cannot perform the operation."""


class PasswordHashingError(AppError):
    """No approved password hashing algorithm can be initialized safely."""
