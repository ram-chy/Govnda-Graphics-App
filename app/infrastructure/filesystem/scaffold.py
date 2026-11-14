"""Safe creation and cleanup of the business data directory layout.

Creation is additive: existing folders and files are never deleted or moved.
If a step fails, the caller can remove only the empty directories that this
attempt created, deepest first, so a partially prepared folder is left tidy
without touching user data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import SetupError
from app.infrastructure.filesystem.layout import DataRootLayout

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DirectoryCreation:
    """One directory that was present or created during setup."""

    path: Path
    purpose: str
    existed: bool


@dataclass(frozen=True, slots=True)
class ScaffoldResult:
    """The complete folder plan after a successful scaffold."""

    layout: DataRootLayout
    directories: tuple[DirectoryCreation, ...]

    @property
    def created_paths(self) -> tuple[Path, ...]:
        return tuple(item.path for item in self.directories if not item.existed)

    @property
    def existing_paths(self) -> tuple[Path, ...]:
        return tuple(item.path for item in self.directories if item.existed)


class DataRootScaffolder:
    """Create the approved data-root folders without overwriting anything."""

    def create(self, layout: DataRootLayout) -> ScaffoldResult:
        """Create every required directory and verify the result.

        Existing paths are accepted only when they are directories. A file in
        the way is a hard error: setup never deletes it to make room.
        """
        directories: list[DirectoryCreation] = []
        try:
            for path, purpose in layout.directory_purposes():
                existed = self._prepare_directory(path, purpose)
                directories.append(
                    DirectoryCreation(path=path, purpose=purpose, existed=existed)
                )
        except BaseException:
            self._remove_empty_created(directories)
            raise
        return ScaffoldResult(layout=layout, directories=tuple(directories))

    def cleanup(self, result: ScaffoldResult) -> tuple[Path, ...]:
        """Remove empty directories created by a failed setup attempt.

        Returns the paths that were removed. A directory that now contains any
        file or folder is retained, and pre-existing directories are skipped.
        """
        return self._remove_empty_created(result.directories)

    def _prepare_directory(self, path: Path, purpose: str) -> bool:
        try:
            existed = path.exists()
        except OSError as exc:
            raise SetupError(
                f"could not inspect setup directory {path}: {exc}",
                user_message=(
                    f"The folder {path} could not be inspected. Check the drive and its "
                    "Windows permissions. No files were changed."
                ),
            ) from exc

        if existed:
            if not path.is_dir():
                raise SetupError(
                    f"setup path is not a directory: {path}",
                    user_message=(
                        f"A file already exists where the {purpose.lower()} folder is needed "
                        f"({path}). Setup will not delete it. Choose another location."
                    ),
                )
            return True

        try:
            path.mkdir()
        except OSError as exc:
            raise SetupError(
                f"could not create setup directory {path}: {exc}",
                user_message=(
                    f"The folder {path} could not be created. Check the drive, free space, "
                    "and Windows permissions. Existing files were not changed."
                ),
            ) from exc

        if not path.is_dir():
            try:
                path.rmdir()
            except OSError:
                logger.debug("Incomplete setup directory could not be removed: %s", path)
            raise SetupError(
                f"setup directory was not created: {path}",
                user_message=(
                    f"The folder {path} was not created successfully. Choose another location."
                ),
            )
        return False

    def _remove_empty_created(
        self, directories: list[DirectoryCreation] | tuple[DirectoryCreation, ...]
    ) -> tuple[Path, ...]:
        removed: list[Path] = []
        for item in reversed(tuple(directories)):
            if item.existed:
                continue
            try:
                if not item.path.is_dir():
                    continue
                if next(item.path.iterdir(), None) is not None:
                    logger.info(
                        "Keeping non-empty setup directory created earlier: %s", item.path
                    )
                    continue
                item.path.rmdir()
                removed.append(item.path)
            except OSError:
                logger.warning(
                    "Could not remove empty setup directory %s", item.path, exc_info=True
                )
        return tuple(removed)


__all__ = ["DataRootScaffolder", "DirectoryCreation", "ScaffoldResult"]
