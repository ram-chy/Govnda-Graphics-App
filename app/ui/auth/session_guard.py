"""Application-wide idle timer, deliberate-activity filter, and lock screen."""

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from app.domain.auth import SESSION_ENTITY_TYPE, AuthEventType, actor_for_user
from app.services.auth_services import AuthServices
from app.services.auth_support import actor_payload
from app.ui.dialogs.auth_dialogs import LockDialog

logger = logging.getLogger(__name__)

_ACTIVITY_EVENTS = frozenset(
    {
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseButtonRelease,
        QEvent.Type.MouseButtonDblClick,
        QEvent.Type.Wheel,
        QEvent.Type.KeyPress,
        QEvent.Type.KeyRelease,
    }
)
_CHECK_INTERVAL_MS = 1_000


class SessionGuard(QObject):
    """Enforce the idle lock while the Qt event loop is running.

    The timer itself never counts as activity. Only deliberate keyboard and
    mouse events delivered to this application reset the in-memory timer, so an
    untouched modal dialog still locks and OS activity elsewhere does not keep
    the session alive.
    """

    def __init__(self, services: AuthServices, window: QWidget) -> None:
        super().__init__(window)
        self._services = services
        self._window = window
        self._application = QApplication.instance()
        self._timer = QTimer(self)
        self._timer.setInterval(_CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._check_idle)
        self._locked = False

    def install(self) -> None:
        if self._application is not None:
            self._application.installEventFilter(self)
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        if self._application is not None:
            self._application.removeEventFilter(self)

    @property
    def is_locked(self) -> bool:
        return self._locked

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        del watched
        if not self._locked and event.type() in _ACTIVITY_EVENTS:
            self._services.session.touch()
        return False

    def _check_idle(self) -> None:
        if self._locked:
            return
        if self._services.session.should_lock():
            self._lock()

    def _lock(self) -> None:
        if not self._services.session.lock():
            return
        self._locked = True
        identity = self._services.session.identity
        if identity is not None:
            self._services.audit.record(
                event_type=AuthEventType.LOCK,
                entity_type=SESSION_ENTITY_TYPE,
                entity_id=str(identity.user_id),
                actor=actor_for_user(identity.user_id, identity.username),
                payload=actor_payload(self._services.session),
            )
        logger.info("Session locked for user %s", identity.user_id if identity else "unknown")

        dialog = LockDialog(self._services)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        previously_enabled = [
            (widget, widget.isEnabled())
            for widget in QApplication.topLevelWidgets()
            if widget is not dialog
        ]
        for widget, _was_enabled in previously_enabled:
            widget.setEnabled(False)
        try:
            dialog.exec()
        finally:
            for widget, was_enabled in previously_enabled:
                if widget is not dialog:
                    widget.setEnabled(was_enabled)
            self._locked = False
            if dialog.result() == QDialog.DialogCode.Accepted:
                self._services.session.touch()
                self._window.activateWindow()
                self._window.setFocus()
            else:
                self._services.session.end()
                if self._application is not None:
                    self._application.quit()

    def check_now(self) -> bool:
        """Force one idle check; useful for tests and manual verification."""

        self._check_idle()
        return self._locked


__all__ = ["SessionGuard"]
