"""PySide6 floating widget for Agent Voice."""

from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QPoint, QThread, QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from agent_voice.config import AppConfig
from agent_voice.config_writer import update_config
from agent_voice.pipeline import CommandOutcome, CommandPipeline
from agent_voice.ui.styles import floating_widget_style_sheet
from agent_voice.ui.status_avatar import StatusAvatar
from agent_voice.voice_status import DEFAULT_STATUS_PATH, read_voice_status
from agent_voice.voice_loop import list_audio_devices


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
        text, accepted = QInputDialog.getText(self, "输入指令", "文字指令：")
        if accepted:
            self._send_text(text)

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
            self._set_state("sent", "已发送")
            self.setToolTip(outcome.feedback or outcome.message)
            return
        if outcome.status == "no_match":
            self._set_state("no_match", "未匹配")
            self.setToolTip(outcome.message)
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


class SettingsDialog(QDialog):
    """Settings dialog for microphone and endpoint values."""

    def __init__(self, config: AppConfig, config_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.config_path = config_path
        self.device_options = _audio_device_options(list_audio_devices())
        self.setWindowTitle("Agent Voice 设置")
        self.setFixedWidth(460)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.device_box = QComboBox()
        for label, device_index in self.device_options:
            self.device_box.addItem(label, device_index)
        current = self.config.audio.device_index
        for index, (_label, device_index) in enumerate(self.device_options):
            if device_index == current:
                self.device_box.setCurrentIndex(index)
        self.base_url = QLineEdit(self.config.transport.base_url)
        self.sensitivity = QDoubleSpinBox()
        self.sensitivity.setRange(0.1, 0.9)
        self.sensitivity.setSingleStep(0.05)
        self.sensitivity.setValue(self.config.wake.sensitivity)
        self.energy = QDoubleSpinBox()
        self.energy.setRange(0.001, 0.1)
        self.energy.setDecimals(3)
        self.energy.setSingleStep(0.001)
        self.energy.setValue(self.config.recorder.energy_threshold)
        form.addRow("麦克风", self.device_box)
        form.addRow("业务地址", self.base_url)
        form.addRow("唤醒灵敏度", self.sensitivity)
        form.addRow("静音阈值", self.energy)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        save = QPushButton("保存")
        save.clicked.connect(self._save)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(actions)

    def _save(self) -> None:
        update_config(
            self.config_path,
            {
                "audio.device_index": self.device_box.currentData(),
                "transport.base_url": self.base_url.text().strip(),
                "wake.sensitivity": round(self.sensitivity.value(), 3),
                "recorder.energy_threshold": round(self.energy.value(), 3),
            },
        )
        QMessageBox.information(self, "Agent Voice", "设置已保存，重启监听后生效。")
        self.accept()


def run_qt_widget(pipeline: CommandPipeline, config: AppConfig, config_path: str) -> int:
    """Run the Qt floating widget."""

    app = QApplication.instance() or QApplication(sys.argv)
    widget = FloatingWidget(pipeline, config, config_path)
    widget.show()
    return app.exec()


def _audio_device_options(devices: list[dict[str, Any]]) -> list[tuple[str, int | None]]:
    """Build microphone choices for settings, including the system default."""

    options: list[tuple[str, int | None]] = [("系统默认麦克风", None)]
    for device in devices:
        if int(device.get("max_input_channels") or 0) <= 0:
            continue
        options.append((f'{device.get("index")}: {device.get("name")}', int(device["index"])))
    return options


def _compact_status_text(text: str) -> str:
    """Return the first useful status line for the compact header."""

    first_line = text.strip().splitlines()[0] if text.strip() else ""
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
        return f"最近识别：{text}\n结果：{outcome} / {intent}"
    if event == "empty_recording":
        return "最近识别：录音为空"
    if event == "recording_complete":
        return "最近识别：录音完成，正在识别"
    message = status.get("message")
    return f"最近识别：{message or event or '暂无'}"
