"""Tkinter floating widget for usable local command delivery."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from agent_voice.config import AppConfig, WAKE_SENSITIVITY_MAX, WAKE_SENSITIVITY_MIN
from agent_voice.config_writer import update_config
from agent_voice.pipeline import CommandOutcome, CommandPipeline
from agent_voice.voice_loop import list_audio_devices


STATE_COLORS = {
    "idle": "#6b7280",
    "sending": "#2563eb",
    "sent": "#16a34a",
    "no_match": "#f97316",
    "error": "#dc2626",
    "muted": "#9ca3af",
}


class FloatingWidget:
    """Always-on-top command widget with status, input, and send controls."""

    def __init__(self, pipeline: CommandPipeline, config: AppConfig | None = None, config_path: str | None = None) -> None:
        """Create a Tkinter widget bound to a command pipeline."""

        self.pipeline = pipeline
        self.config = config
        self.config_path = config_path
        self.root = tk.Tk()
        self.root.title("Agent Voice")
        self.root.attributes("-topmost", True)
        self.root.geometry("360x160+80+80")
        self.root.minsize(320, 150)
        self._muted = False
        self._result_queue: queue.Queue[CommandOutcome] = queue.Queue()
        self._build_ui()
        self._bind_events()
        self._set_state("idle", "待机")

    def run(self) -> None:
        """Start the desktop event loop."""

        self.root.mainloop()

    def _build_ui(self) -> None:
        self.root.configure(bg="#f8fafc")
        self.status_dot = tk.Canvas(self.root, width=18, height=18, bg="#f8fafc", highlightthickness=0)
        self.status_dot.grid(row=0, column=0, padx=(12, 6), pady=(12, 4), sticky="w")
        self.status_circle = self.status_dot.create_oval(2, 2, 16, 16, fill=STATE_COLORS["idle"], outline="")

        self.status_label = tk.Label(self.root, text="待机", bg="#f8fafc", fg="#111827", font=("Arial", 13, "bold"))
        self.status_label.grid(row=0, column=1, padx=(0, 12), pady=(12, 4), sticky="w")

        self.entry = tk.Entry(self.root, font=("Arial", 14))
        self.entry.grid(row=1, column=0, columnspan=3, padx=12, pady=8, sticky="ew")

        self.send_button = tk.Button(self.root, text="发送", command=self._send_current_text, width=8)
        self.send_button.grid(row=2, column=0, padx=(12, 4), pady=(2, 8), sticky="w")

        self.mute_button = tk.Button(self.root, text="暂停", command=self._toggle_mute, width=8)
        self.mute_button.grid(row=2, column=1, padx=4, pady=(2, 8), sticky="w")

        self.feedback_label = tk.Label(self.root, text="", bg="#f8fafc", fg="#374151", anchor="w")
        self.feedback_label.grid(row=3, column=0, columnspan=3, padx=12, pady=(0, 10), sticky="ew")

        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)

    def _bind_events(self) -> None:
        self.root.bind("<Return>", lambda event: self._send_current_text())
        self.entry.focus_set()
        menu = tk.Menu(self.root, tearoff=False)
        menu.add_command(label="暂停/恢复", command=self._toggle_mute)
        menu.add_command(label="设置", command=self._open_settings)
        menu.add_separator()
        menu.add_command(label="退出", command=self.root.destroy)
        self.root.bind("<Button-2>", lambda event: menu.tk_popup(event.x_root, event.y_root))
        self.root.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))

    def _set_state(self, state: str, message: str) -> None:
        self.status_dot.itemconfig(self.status_circle, fill=STATE_COLORS[state])
        self.status_label.config(text=message)

    def _toggle_mute(self) -> None:
        self._muted = not self._muted
        if self._muted:
            self.entry.config(state="disabled")
            self.send_button.config(state="disabled")
            self.mute_button.config(text="恢复")
            self._set_state("muted", "已暂停")
        else:
            self.entry.config(state="normal")
            self.send_button.config(state="normal")
            self.mute_button.config(text="暂停")
            self._set_state("idle", "待机")
            self.entry.focus_set()

    def _send_current_text(self) -> None:
        if self._muted:
            return
        text = self.entry.get().strip()
        if not text:
            self.feedback_label.config(text="请输入指令")
            return
        self._set_state("sending", "发送中")
        self.send_button.config(state="disabled")
        thread = threading.Thread(target=self._process_in_background, args=(text,), daemon=True)
        thread.start()
        self.root.after(50, self._poll_result)

    def _process_in_background(self, text: str) -> None:
        outcome = self.pipeline.process_text(text, asr_confidence=1.0)
        self._result_queue.put(outcome)

    def _poll_result(self) -> None:
        try:
            outcome = self._result_queue.get_nowait()
        except queue.Empty:
            self.root.after(50, self._poll_result)
            return
        self._apply_outcome(outcome)
        if not self._muted:
            self.send_button.config(state="normal")

    def _apply_outcome(self, outcome: CommandOutcome) -> None:
        if outcome.status == "sent":
            self._set_state("sent", "成功")
            self.feedback_label.config(text=outcome.feedback or outcome.message)
            self.entry.delete(0, tk.END)
            self.root.after(1200, lambda: self._set_state("idle", "待机"))
            return
        if outcome.status == "no_match":
            self._set_state("no_match", "未匹配")
            self.feedback_label.config(text=outcome.message)
            self.root.after(1600, lambda: self._set_state("idle", "待机"))
            return
        self._set_state("error", "失败")
        self.feedback_label.config(text=outcome.message)
        messagebox.showwarning("Agent Voice", outcome.message)

    def _open_settings(self) -> None:
        if self.config is None or self.config_path is None:
            messagebox.showwarning("Agent Voice", "当前启动方式没有配置文件路径，无法保存设置。")
            return
        SettingsWindow(self.root, self.config, self.config_path)


class SettingsWindow:
    """Small settings dialog for microphone and business endpoint configuration."""

    def __init__(self, parent: tk.Tk, config: AppConfig, config_path: str) -> None:
        """Create and show a settings dialog."""

        self.config = config
        self.config_path = config_path
        self.window = tk.Toplevel(parent)
        self.window.title("Agent Voice 设置")
        self.window.geometry("430x250")
        self.window.resizable(False, False)
        self._devices = [device for device in list_audio_devices() if device["max_input_channels"] > 0]
        self._build_ui()

    def _build_ui(self) -> None:
        body = ttk.Frame(self.window, padding=14)
        body.grid(row=0, column=0, sticky="nsew")
        ttk.Label(body, text="麦克风").grid(row=0, column=0, sticky="w", pady=6)
        self.device_var = tk.StringVar(value=self._current_device_value())
        device_box = ttk.Combobox(body, textvariable=self.device_var, values=self._device_values(), state="readonly", width=42)
        device_box.grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(body, text="业务地址").grid(row=1, column=0, sticky="w", pady=6)
        self.base_url_var = tk.StringVar(value=self.config.transport.base_url)
        ttk.Entry(body, textvariable=self.base_url_var, width=45).grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(body, text="唤醒灵敏度").grid(row=2, column=0, sticky="w", pady=6)
        self.sensitivity_var = tk.DoubleVar(value=self.config.wake.sensitivity)
        ttk.Scale(body, variable=self.sensitivity_var, from_=WAKE_SENSITIVITY_MIN, to=WAKE_SENSITIVITY_MAX).grid(
            row=2,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(body, text="静音阈值").grid(row=3, column=0, sticky="w", pady=6)
        self.energy_var = tk.StringVar(value=str(self.config.recorder.energy_threshold))
        ttk.Entry(body, textvariable=self.energy_var, width=12).grid(row=3, column=1, sticky="w", pady=6)

        actions = ttk.Frame(body)
        actions.grid(row=4, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(actions, text="取消", command=self.window.destroy).grid(row=0, column=0, padx=6)
        ttk.Button(actions, text="保存", command=self._save).grid(row=0, column=1)
        body.columnconfigure(1, weight=1)

    def _device_values(self) -> list[str]:
        return [f'{device["index"]}: {device["name"]}' for device in self._devices]

    def _current_device_value(self) -> str:
        for device in self._devices:
            if device["index"] == self.config.audio.device_index:
                return f'{device["index"]}: {device["name"]}'
        values = self._device_values()
        return values[0] if values else ""

    def _save(self) -> None:
        try:
            device_index = int(self.device_var.get().split(":", 1)[0])
            energy_threshold = float(self.energy_var.get())
        except ValueError:
            messagebox.showwarning("Agent Voice", "设置值格式不正确。")
            return
        update_config(
            self.config_path,
            {
                "audio.device_index": device_index,
                "transport.base_url": self.base_url_var.get().strip(),
                "wake.sensitivity": round(float(self.sensitivity_var.get()), 3),
                "recorder.energy_threshold": energy_threshold,
            },
        )
        messagebox.showinfo("Agent Voice", "设置已保存，重启监听后生效。")
        self.window.destroy()
