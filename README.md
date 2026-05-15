# Agent Voice

医疗桌面语音助手 MVP，支持桌面宠物挂件、真实麦克风监听、`小图小图` 唤醒、离线 ASR、指令解析和业务接口透传。

## 功能

- 桌面宠物挂件：常驻桌面，右键打开设置、输入指令、暂停或退出。
- 真实麦克风监听：显示麦克风音量，唤醒后自动录制后续指令。
- 离线唤醒词：使用 sherpa-onnx，本地识别 `小图小图`。
- 离线 ASR：使用 SenseVoiceSmall，本地转写中文语音。
- 业务透传：把解析后的指令发送到 HTTP 业务接口。
- 跨平台启动：macOS 提供 `.command`，Windows 提供 `.bat`。

## 目录

```text
agent_voice/                 Python 源码
models/                      本地模型目录，不提交 Git
scripts/                     启动和打包脚本
config.example.json          本地运行配置
launchers/macos/启动挂件.command / launchers/windows/启动挂件.bat       启动桌面宠物挂件
launchers/macos/启动语音监听.command / launchers/windows/启动语音监听.bat   启动麦克风监听流程
launchers/macos/启动业务Mock.command / launchers/windows/启动业务Mock.bat   启动本地业务 Mock
launchers/macos/测试麦克风ASR.command / launchers/windows/测试麦克风ASR.bat  录 3 秒并显示 ASR 结果
```

## 安装

### macOS

```bash
cd "/Users/lh/developer/IdeaProjects/github/agent-voice"
python3.12 -m venv ".venv"
".venv/bin/python" -m pip install --upgrade pip
".venv/bin/python" -m pip install -r "requirements.txt"
```

### Windows

在 PowerShell 里执行：

```powershell
cd "项目目录"
py -3.12 -m venv ".venv"
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
```

模型目录需要放在：

```text
models/wake/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01
models/asr/SenseVoiceSmall
models/wake/keywords.txt
```

## 使用

建议按这个顺序启动：

1. 启动业务 Mock
   - macOS：双击 `launchers/macos/启动业务Mock.command`
   - Windows：双击 `launchers/windows/启动业务Mock.bat`
2. 启动挂件
   - macOS：双击 `launchers/macos/启动挂件.command`
   - Windows：双击 `launchers/windows/启动挂件.bat`
3. 启动语音监听
   - macOS：双击 `launchers/macos/启动语音监听.command`
   - Windows：双击 `launchers/windows/启动语音监听.bat`

挂件是桌面宠物形态：

- 左键拖动位置。
- 右键打开菜单。
- 右键 `设置` 修改麦克风、业务地址、唤醒灵敏度和静音阈值。
- 右键 `输入指令` 可以不用语音，直接发送文字指令。

麦克风默认使用系统默认设备。需要指定设备时，在挂件右键 `设置` 里选择麦克风，保存后重启 `启动语音监听`。

语音流程：

```text
说“小图小图”
等待监听终端出现 wake_detected
继续说“调取患者一二三四五六”
挂件显示识别结果，业务 Mock 收到请求
```

测试 ASR：

- macOS：双击 `launchers/macos/测试麦克风ASR.command`
- Windows：双击 `launchers/windows/测试麦克风ASR.bat`

它会录 3 秒真实麦克风，并显示 ASR 把声音识别成了什么字。

## 命令行

列出音频设备：

```bash
".venv/bin/python" -m agent_voice --config "config.example.json" --list-audio-devices
```

文字指令 dry-run：

```bash
".venv/bin/python" -m agent_voice --config "config.example.json" --text "调取患者123456" --dry-run
```

启动监听：

```bash
".venv/bin/python" -m agent_voice --config "config.example.json" --voice-loop
```

## 打包

打包使用 PyInstaller 的 `onedir` 模式。模型不会塞进单文件 exe，而是复制到发布目录旁边，便于替换和排查。

### Windows 打包 exe

在 Windows PowerShell 里执行：

```powershell
cd "项目目录"
.\scripts\package_windows.ps1
```

输出目录：

```text
release/AgentVoice-windows/
```

里面包含：

```text
AgentVoice/AgentVoice.exe
config.example.json
models/
launchers/windows/StartWidget.bat
launchers/windows/StartVoiceLoop.bat
launchers/windows/StartMockServer.bat
launchers/windows/TestMicAsr.bat
```

把整个 `release/AgentVoice-windows/` 发给使用者。不要只拷贝 `AgentVoice.exe`，否则模型和配置会丢失。

### macOS 打包 dmg

在 macOS 里执行：

```bash
cd "/Users/lh/developer/IdeaProjects/github/agent-voice"
"scripts/package_macos.sh"
```

输出：

```text
release/AgentVoice-macos/
release/AgentVoice-macos.dmg
```

DMG 内包含：

```text
AgentVoice/AgentVoice
config.example.json
models/
launchers/macos/启动挂件.command
launchers/macos/启动语音监听.command
launchers/macos/启动业务Mock.command
launchers/macos/测试麦克风ASR.command
```

首次打开 macOS 可能提示安全限制。测试阶段可在系统设置里允许运行；正式分发需要做 Apple Developer 签名和公证。

## 打包注意事项

- Windows exe 需要在 Windows 上打包。
- macOS dmg 需要在 macOS 上打包。
- `models/`、`.venv/`、`release/`、`dist/`、`build/` 都不提交 Git。
- 完整发布包通常会很大，主要体积来自 `torch`、`funasr`、`PySide6` 和本地模型。
- 如果杀毒软件误报，优先使用 `onedir` 目录包，不建议做单文件 exe。

## 常见问题

### 挂件有音量，但说“小图小图”没反应

先用 `测试麦克风ASR` 确认麦克风是否能识别中文。如果 ASR 能识别但唤醒不触发，在挂件右键 `设置` 里提高唤醒灵敏度，然后重启语音监听。

### 保存麦克风后没生效

麦克风选择保存在 `config.example.json`，保存后需要重启 `启动语音监听`。

### 磁盘突然变满

不要把 `models/` 加入 Git。仓库已经在 `.gitignore` 里忽略模型和发布产物。
