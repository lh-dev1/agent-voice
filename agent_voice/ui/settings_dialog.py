"""Settings dialog for Agent Voice Qt widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from agent_voice.config import AppConfig, WAKE_SENSITIVITY_MAX, WAKE_SENSITIVITY_MIN
from agent_voice.config_writer import update_config
from agent_voice.voice_loop import list_audio_devices


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
        self.sensitivity.setRange(WAKE_SENSITIVITY_MIN, WAKE_SENSITIVITY_MAX)
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


def _audio_device_options(devices: list[dict[str, Any]]) -> list[tuple[str, int | None]]:
    """Build microphone choices for settings, including the system default."""

    options: list[tuple[str, int | None]] = [("系统默认麦克风", None)]
    for device in devices:
        if int(device.get("max_input_channels") or 0) <= 0:
            continue
        options.append((f'{device.get("index")}: {device.get("name")}', int(device["index"])))
    return options
