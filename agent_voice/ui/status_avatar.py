"""Painted status avatar for the floating widget."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


AVATAR_ACCENTS = {
    "idle": "#67e8f9",
    "sending": "#93c5fd",
    "sent": "#86efac",
    "no_match": "#fdba74",
    "error": "#fca5a5",
    "muted": "#9ca3af",
}


class StatusAvatar(QWidget):
    """Small painted face that reflects current assistant state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = "idle"
        self.setFixedSize(62, 62)

    def set_state(self, state: str) -> None:
        """Update avatar state and repaint."""

        self.state = state
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = QColor(AVATAR_ACCENTS.get(self.state, AVATAR_ACCENTS["idle"]))

        outer = QRectF(4, 4, 54, 54)
        painter.setPen(QPen(accent, 2.5))
        painter.setBrush(QColor("#111827"))
        painter.drawEllipse(outer)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawEllipse(QPointF(22, 27), 4, 5)
        painter.drawEllipse(QPointF(40, 27), 4, 5)

        painter.setPen(QPen(accent, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if self.state == "muted":
            painter.drawLine(24, 41, 40, 41)
        elif self.state == "error":
            painter.drawArc(QRectF(23, 38, 18, 12), 20 * 16, 140 * 16)
        else:
            painter.drawArc(QRectF(22, 34, 20, 14), 200 * 16, 140 * 16)
