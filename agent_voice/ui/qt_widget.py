"""PySide6 floating widget for Agent Voice."""

from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QThread, QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
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
from agent_voice.voice_status import DEFAULT_STATUS_PATH, read_voice_status
from agent_voice.voice_loop import list_audio_devices


STATE_COLORS = {
    "idle": "#6b7280",
    "sending": "#2563eb",
    "sent": "#16a34a",
    "no_match": "#f97316",
    "error": "#dc2626",
    "muted": "#9ca3af",
}


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
        self.setWindowTitle("Agent Voice")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(380, 170)
        self._build_ui()
        self._set_state("idle", "待机")
        self._start_status_timer()

    def _build_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)
        header = QHBoxLayout()
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(14, 14)
        self.status_label = QLabel("待机")
        self.status_label.setStyleSheet("font-weight: 700; font-size: 14px;")
        header.addWidget(self.status_dot)
        header.addWidget(self.status_label)
        header.addStretch(1)
        layout.addLayout(header)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("输入指令，例如：调取患者 123456")
        self.entry.returnPressed.connect(self._send_current_text)
        layout.addWidget(self.entry)

        actions = QHBoxLayout()
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self._send_current_text)
        self.mute_button = QPushButton("暂停")
        self.mute_button.clicked.connect(self._toggle_mute)
        self.settings_button = QPushButton("设置")
        self.settings_button.clicked.connect(self._open_settings)
        actions.addWidget(self.send_button)
        actions.addWidget(self.mute_button)
        actions.addWidget(self.settings_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.feedback_label = QLabel("")
        self.feedback_label.setWordWrap(True)
        layout.addWidget(self.feedback_label)
        self.voice_text_label = QLabel("最近识别：暂无")
        self.voice_text_label.setWordWrap(True)
        self.voice_text_label.setStyleSheet("color: #374151;")
        layout.addWidget(self.voice_text_label)
        self.setCentralWidget(root)

    def contextMenuEvent(self, event: Any) -> None:
        menu = QMenu(self)
        menu.addAction("暂停/恢复", self._toggle_mute)
        menu.addAction("设置", self._open_settings)
        menu.addSeparator()
        menu.addAction("退出", self.close)
        menu.exec(event.globalPos())

    def _set_state(self, state: str, message: str) -> None:
        color = STATE_COLORS[state]
        self.status_dot.setStyleSheet(f"background: {color}; border-radius: 7px;")
        self.status_label.setText(message)

    def _toggle_mute(self) -> None:
        self.muted = not self.muted
        self.entry.setEnabled(not self.muted)
        self.send_button.setEnabled(not self.muted)
        self.mute_button.setText("恢复" if self.muted else "暂停")
        self._set_state("muted" if self.muted else "idle", "已暂停" if self.muted else "待机")

    def _send_current_text(self) -> None:
        if self.muted:
            return
        text = self.entry.text().strip()
        if not text:
            self.feedback_label.setText("请输入指令")
            return
        self._set_state("sending", "发送中")
        self.send_button.setEnabled(False)
        self.worker = CommandWorker(self.pipeline, text)
        self.worker.finished.connect(self._apply_outcome)
        self.worker.start()

    def _apply_outcome(self, outcome: CommandOutcome) -> None:
        self.send_button.setEnabled(not self.muted)
        if outcome.status == "sent":
            self._set_state("sent", "成功")
            self.feedback_label.setText(outcome.feedback or outcome.message)
            self.entry.clear()
            return
        if outcome.status == "no_match":
            self._set_state("no_match", "未匹配")
            self.feedback_label.setText(outcome.message)
            return
        self._set_state("error", "失败")
        self.feedback_label.setText(outcome.message)
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
        self.voice_text_label.setText(_format_voice_status(status))


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
