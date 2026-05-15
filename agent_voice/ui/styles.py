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
    QMenu {
      background: #111827;
      color: #f8fafc;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 6px;
    }
    QMenu::item {
      border-radius: 8px;
      padding: 7px 22px;
    }
    QMenu::item:selected {
      background: #0f766e;
    }
    QMenu::separator {
      background: #334155;
      height: 1px;
      margin: 6px 8px;
    }
    """
