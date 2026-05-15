"""PySide6 floating widget for Agent Voice."""

from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QPoint, QThread, QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QVBoxLayout,
)

from agent_voice.config import AppConfig
from agent_voice.pipeline import CommandOutcome, CommandPipeline
from agent_voice.ui.settings_dialog import SettingsDialog
from agent_voice.ui.styles import floating_widget_style_sheet
from agent_voice.ui.status_avatar import StatusAvatar
from agent_voice.voice_status import DEFAULT_STATUS_PATH, read_voice_status


class CommandWorker(QThread):
    """Run one command send operation off the UI thread."""

    finished = Signal(object)

    def __init__(self, pipeline: CommandPipeline, text: str) -> None:
        super().__init__()
        self.pipeline = pipeline
        self.text = text

    def run(self) -> None:
        self.finished.emit(self.pipeline.process_text(self.text, asr_confidence=1.0))


class FloatingWidget(QMainWindow):
    """Always-on-top Qt command widget."""

    def __init__(self, pipeline: CommandPipeline, config: AppConfig, config_path: str) -> None:
        super().__init__()
        self.pipeline = pipeline
        self.config = config
        self.config_path = config_path
        self.worker: CommandWorker | None = None
        self.muted = False
        self.last_status_updated_at = ""
        self.drag_start: QPoint | None = None
        self.setWindowTitle("Agent Voice")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(116, 106)
        self._build_ui()
        self._set_state("idle", "待机")
        self._start_status_timer()

    def _build_ui(self) -> None:
        root = QFrame(self)
        root.setObjectName("agentVoicePet")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.avatar = StatusAvatar()
        layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignCenter)
        self.status_label = QLabel("待机")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)
        self.setStyleSheet(floating_widget_style_sheet())

    def contextMenuEvent(self, event: Any) -> None:
        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.addAction("输入指令", self._open_text_command)
        menu.addAction("暂停/恢复", self._toggle_mute)
        menu.addAction("设置", self._open_settings)
        menu.addSeparator()
        menu.addAction("退出", self.close)
        menu.exec(event.globalPos())

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: Any) -> None:
        if self.drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_start)
            event.accept()

    def mouseReleaseEvent(self, _event: Any) -> None:
        self.drag_start = None

    def _set_state(self, state: str, message: str) -> None:
        self.status_label.setText(message)
        self.avatar.set_state(state)

    def _toggle_mute(self) -> None:
        self.muted = not self.muted
        self._set_state("muted" if self.muted else "idle", "已暂停" if self.muted else "待机")

    def _open_text_command(self) -> None:
        dialog = _build_text_command_dialog(self)
        if dialog.exec():
            self._send_text(dialog.textValue())

    def _send_text(self, text: str) -> None:
        if self.muted:
            return
        text = text.strip()
        if not text:
            self._set_state("no_match", "请输入指令")
            return
        self._set_state("sending", "发送中")
        self.worker = CommandWorker(self.pipeline, text)
        self.worker.finished.connect(self._apply_outcome)
        self.worker.start()

    def _apply_outcome(self, outcome: CommandOutcome) -> None:
        if outcome.status == "sent":
            message = outcome.feedback or outcome.message
            self._set_state("sent", "发送成功")
            self.setToolTip(message)
            QMessageBox.information(self, "发送结果", message)
            return
        if outcome.status == "no_match":
            message = outcome.message
            self._set_state("no_match", "未匹配")
            self.setToolTip(message)
            QMessageBox.information(self, "发送结果", message)
            return
        self._set_state("error", "失败")
        self.setToolTip(outcome.message)
        QMessageBox.warning(self, "Agent Voice", outcome.message)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self.config_path, self)
        dialog.exec()

    def _start_status_timer(self) -> None:
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._refresh_voice_status)
        self.status_timer.start(1000)
        self._refresh_voice_status()

    def _refresh_voice_status(self) -> None:
        status = read_voice_status(DEFAULT_STATUS_PATH)
        updated_at = str(status.get("updated_at") or "")
        if not status or updated_at == self.last_status_updated_at:
            return
        self.last_status_updated_at = updated_at
        formatted = _format_voice_status(status)
        self.status_label.setText(_compact_status_text(formatted))
        self.setToolTip(formatted)


def run_qt_widget(pipeline: CommandPipeline, config: AppConfig, config_path: str) -> int:
    """Run the Qt floating widget."""

    app = QApplication.instance() or QApplication(sys.argv)
    widget = FloatingWidget(pipeline, config, config_path)
    widget.show()
    return app.exec()


def _build_text_command_dialog(parent: QMainWindow) -> QInputDialog:
    """Build the manual text command dialog with Chinese action labels."""

    dialog = QInputDialog(parent)
    dialog.setWindowTitle("输入指令")
    dialog.setLabelText("文字指令：")
    dialog.setOkButtonText("发送")
    dialog.setCancelButtonText("取消")
    return dialog


def _compact_status_text(text: str) -> str:
    """Return the first useful status line for the compact header."""

    lines = [line for line in text.strip().splitlines() if line]
    first_line = lines[0] if lines else ""
    for line in lines:
        if line.startswith("发送结果："):
            return line.replace("发送结果：", "").split("/", 1)[0].strip()
    if first_line.startswith("麦克风："):
        return first_line.replace("麦克风：", "").replace("，音量", "")
    if first_line.startswith("最近识别：唤醒词"):
        return "已唤醒"
    if first_line.startswith("最近识别：录音完成"):
        return "识别中"
    if first_line.startswith("麦克风ASR："):
        return "ASR结果"
    return first_line or "等待语音"


def _format_voice_status(status: dict[str, Any]) -> str:
    event = status.get("event")
    if event == "mic_level":
        active = bool(status.get("active"))
        level = int(status.get("level_percent") or 0)
        state = "有声音" if active else "安静"
        return f"麦克风：{state}，音量 {level}%\n最近识别：等待唤醒词"
    if event == "mic_asr_result":
        text = status.get("asr_text", "")
        elapsed_ms = int(status.get("asr_elapsed_ms") or 0)
        return f"麦克风ASR：{text}\n耗时：{elapsed_ms} ms"
    if event == "mic_recording":
        seconds = status.get("seconds")
        return f"麦克风ASR：正在录音 {seconds} 秒"
    if event == "mic_asr_empty":
        return f'麦克风ASR：{status.get("message") or "未识别到文字"}'
    if event == "wake_detected":
        return f'最近识别：唤醒词 {status.get("keyword", "")}'
    if event == "asr_result":
        return f'最近识别：{status.get("asr_text", "")}'
    if event == "command_result":
        text = status.get("asr_text", "")
        outcome = status.get("outcome_status", "")
        intent = status.get("intent") or "未匹配"
        message = status.get("outcome_message") or ""
        readable = _readable_outcome_status(str(outcome))
        detail = f"\n说明：{message}" if message else ""
        return f"最近识别：{text}\n发送结果：{readable} / {intent}{detail}"
    if event == "empty_recording":
        return "最近识别：录音为空"
    if event == "recording_complete":
        return "最近识别：录音完成，正在识别"
    message = status.get("message")
    return f"最近识别：{message or event or '暂无'}"


def _readable_outcome_status(status: str) -> str:
    """Return a short Chinese label for command delivery status."""

    labels = {
        "sent": "已发送",
        "no_match": "未匹配",
        "error": "发送失败",
    }
    return labels.get(status, status or "未知")
