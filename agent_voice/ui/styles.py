"""Stylesheets for Agent Voice Qt widgets."""

from __future__ import annotations


def floating_widget_style_sheet() -> str:
    """Return the floating widget stylesheet."""

    return """
    QFrame#agentVoicePet {
      background: transparent;
      border: 0;
    }
    QLabel#statusLabel {
      background: rgba(17, 24, 39, 224);
      border: 1px solid rgba(103, 232, 249, 112);
      border-radius: 9px;
      color: #e0f2fe;
      font-size: 12px;
      font-weight: 600;
      padding: 3px 8px;
    }
    QLineEdit {
      background: rgba(255, 255, 255, 24);
      border: 1px solid rgba(148, 163, 184, 84);
      border-radius: 10px;
      color: #f8fafc;
      padding: 8px 10px;
      selection-background-color: #0e7490;
    }
    QLineEdit:focus {
      border-color: #67e8f9;
    }
    QPushButton {
      background: #0f766e;
      border: 0;
      border-radius: 10px;
      color: #f8fafc;
      font-weight: 700;
      padding: 8px 14px;
    }
    QPushButton:hover {
      background: #0d9488;
    }
    QPushButton:disabled {
      background: #475569;
      color: #cbd5e1;
    }
    QMenu {
      background: #111827;
      color: #f8fafc;
      border: 1px solid #334155;
      padding: 6px;
    }
    QMenu::item {
      padding: 7px 22px;
    }
    QMenu::item:selected {
      background: #0f766e;
    }
    """
