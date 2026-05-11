# 医疗桌面语音助手技术方案

> 范围：唤醒词、离线 ASR、桌面悬浮挂件、结构化指令透传。本文面向产品和研发，用于直接拆任务实现首版 MVP。

## 1. 结论

首版目标不是做通用医疗语音大模型，而是在 Windows 医疗工作站上实现一个本地运行的语音入口：

1. 用户说出唤醒词“小图小图”。
2. 客户端进入短时聆听状态，采集 1 到 6 秒语音。
3. 本地 ASR 转写文本。
4. 规则解析为固定业务指令。
5. 通过 HTTP POST 把结构化 JSON 推送给业务系统。
6. 客户端回到待机状态，并通过悬浮挂件展示状态。

首版只负责“采集、识别、解析、透传”，不直接操作 HIS/EMR/PACS 等业务系统，不做诊疗判断，不做医嘱推荐，不保存原始音频。

## 2. 产品边界

### 2.1 首版必须实现

|能力|说明|验收口径|
|---|---|---|
|唤醒词监听|后台常驻监听“小图小图”|正常音量 1 米内可唤醒，误唤醒率进入试点前实测|
|短句识别|唤醒后识别固定医疗工作站指令|支持 1 到 6 秒短句，超时自动结束|
|桌面挂件|悬浮小球展示状态，支持拖拽和右键菜单|待机、聆听、识别、发送、成功、失败状态清晰可见|
|规则解析|把 ASR 文本解析为 intent 和 params|规则单测覆盖全部内置指令|
|业务透传|HTTP POST JSON 到业务端|超时、失败、重复请求均有明确处理|
|本地运行|不上传音频、不依赖云端 ASR|断网状态下唤醒、识别、解析可用|
|可打包部署|Windows 10/11 x64 免 Python 环境运行|提供 one-dir 安装包和配置文件|

### 2.2 首版不做

|不做项|原因|
|---|---|
|自由问答、病情解释、诊疗建议|超出固定指令入口范围，合规风险高|
|自动修改业务数据|语音层只透传请求，最终业务动作由业务端确认和执行|
|云端 ASR 或云端大模型|医疗场景默认离线，避免音频和患者信息外传|
|多轮复杂对话|首版只处理单轮短指令，降低误操作风险|
|默认保存原始音频|音频属于敏感数据，默认不落盘|

## 3. 技术选型

### 3.1 首版选型

|模块|首版选型|原因|注意事项|
|---|---|---|---|
|桌面 GUI|PySide6|LGPL/商业双许可，比 PyQt6 更适合闭源桌面分发；Qt 能稳定实现悬浮窗|发版前固定版本和许可清单|
|音频采集|sounddevice + PortAudio|Python 调用简单，跨平台，适合 16k 单声道采集|需要处理设备切换、无麦克风、占用失败|
|唤醒词|Porcupine|成熟度高，CPU 占用低，自定义唤醒词落地快|SDK/模型/AccessKey 的商业使用条款必须在发版前确认|
|ASR|FunASR + SenseVoiceSmall CPU 推理|中文短句效果较好，能本地运行|模型体积和运行内存按实测确认，不承诺几十 MB 级别|
|端点检测|WebRTC VAD 优先，能量阈值兜底|控制录音起止，减少空音频送 ASR|嘈杂环境需要现场调参|
|指令解析|正则 + 词典 + 置信度规则|固定指令集可控、可测、低延迟|无法解析时不透传业务动作|
|业务通信|HTTP POST JSON|业务端接入成本低，便于调试|必须有 request_id、超时、鉴权和幂等|
|打包|PyInstaller one-dir|模型和动态库较多，one-dir 更稳定|首版不承诺单 exe；稳定后再评估 one-file|

### 3.2 备选方案

如果 Porcupine 的授权、AccessKey 或模型生成流程不满足项目要求，唤醒模块切换为 openWakeWord 或自训练 ONNX 唤醒模型。代价是需要额外采集唤醒词样本、训练和误唤醒调优，首版周期至少增加 1 到 2 周。

如果 SenseVoiceSmall 在目标工控机上资源占用过高，ASR 可切换为 sherpa-onnx 生态下的 Paraformer/Whisper 量化模型。代价是医疗短句效果需要重新评测。

## 4. 总体架构

### 4.1 进程与线程模型

首版采用“主进程 + ASR Worker 子进程”的结构：

```text
agent-voice.exe
  ├─ UI 主线程：PySide6 悬浮挂件、右键菜单、状态展示
  ├─ Audio 线程：麦克风采集、重采样、音频帧分发
  ├─ Wake 线程：唤醒词检测
  ├─ Recorder 线程：唤醒后录音、VAD 端点检测
  ├─ Business 线程：HTTP 发送、超时和失败处理
  └─ ASR Worker 子进程：模型加载、语音转文字
```

ASR 使用子进程隔离，原因是模型加载、推理和依赖库更容易引发内存波动或崩溃。子进程异常退出时，主进程可以恢复 UI、提示错误并按策略重启 Worker。

### 4.2 数据流

```text
麦克风
  -> AudioCapture
  -> WakeDetector
  -> CommandRecorder
  -> AsrWorker
  -> IntentParser
  -> BusinessClient
  -> 业务系统
```

所有模块只通过明确的数据对象通信，不跨层直接调用业务逻辑。

### 4.3 推荐目录结构

```text
agent_voice/
  app.py
  config.py
  state.py
  audio/
    capture.py
    vad.py
    wav.py
  wake/
    base.py
    porcupine_engine.py
  asr/
    worker.py
    sensevoice.py
  nlu/
    parser.py
    rules.py
  transport/
    http_client.py
    schema.py
  ui/
    floating_widget.py
    tray.py
  logging/
    privacy_filter.py
tests/
  fixtures/
  test_parser.py
  test_schema.py
  test_state.py
models/
  wake/
  asr/
config.example.json
```

## 5. 状态机

|状态|触发条件|UI 表现|下一状态|
|---|---|---|---|
|STARTING|程序启动、加载配置|灰色闪烁|IDLE 或 ERROR|
|IDLE|唤醒引擎正常运行|灰色常亮|LISTENING、MUTED、ERROR|
|LISTENING|检测到“小图小图”|绿色常亮|RECOGNIZING、IDLE、ERROR|
|RECOGNIZING|录音结束，ASR 推理中|黄色常亮|SENDING、NO_MATCH、ERROR|
|SENDING|已解析，发送业务端|蓝色闪烁|DONE、ERROR|
|DONE|业务端返回 accepted|蓝色常亮 1 秒|IDLE|
|NO_MATCH|无可执行指令|橙色常亮 1 秒|IDLE|
|MUTED|用户暂停语音|灰色斜杠|IDLE|
|ERROR|麦克风、模型、网络等异常|红色常亮|IDLE 或退出|

悬浮挂件右键菜单至少包含：暂停/恢复语音、选择麦克风、打开配置目录、查看日志、退出。

## 6. 核心模块设计

### 6.1 AudioCapture

职责：

- 打开指定麦克风。
- 采集 16kHz、16-bit、mono PCM。
- 按固定 frame 分发给唤醒引擎。
- 在设备丢失、被占用、权限不足时抛出明确错误并更新状态。

关键配置：

```json
{
  "audio": {
    "sample_rate": 16000,
    "channels": 1,
    "device_index": null,
    "frame_ms": 30
  }
}
```

### 6.2 WakeDetector

职责：

- 常驻监听唤醒词。
- 检测成功后发布 `wake_detected` 事件。
- 防止连续重复触发，默认 1500ms 冷却时间。

首版使用 Porcupine 时，必须把 `access_key`、`keyword_path`、`model_path` 做成配置项。AccessKey 不允许硬编码在源码中，优先从环境变量或 Windows Credential Manager 读取。

```json
{
  "wake": {
    "engine": "porcupine",
    "keyword_path": "models/wake/xiaotuxiaotu.ppn",
    "sensitivity": 0.55,
    "cooldown_ms": 1500
  }
}
```

### 6.3 CommandRecorder

职责：

- 唤醒后立即开始录音。
- 使用 VAD 判断说话结束。
- 设置最短录音、最长录音和静音截止时间。
- 输出内存中的 PCM/WAV，不默认落盘。

默认策略：

|参数|默认值|说明|
|---|---:|---|
|min_duration_ms|800|少于该时长视为误触发或空指令|
|max_duration_ms|6000|超过后强制结束，避免长时间占用|
|end_silence_ms|900|连续静音达到阈值后结束|
|pre_roll_ms|300|保留唤醒后前置缓冲，避免吞字|

### 6.4 AsrWorker

职责：

- 启动时加载 SenseVoiceSmall。
- 接收音频任务，返回文本、置信度和耗时。
- 失败时返回明确错误，不伪造空成功。

运行策略：

- 默认采用 warm 模式：程序启动后预热 ASR Worker，换取低延迟。
- 可配置 lazy 模式：首次唤醒后加载 ASR，降低待机内存，但第一次识别会变慢。
- 模型运行在 CPU，默认不依赖 CUDA。
- ASR 子进程设置最大并发 1，避免连续唤醒导致模型并发推理。

```json
{
  "asr": {
    "engine": "sensevoice",
    "model_dir": "models/asr/SenseVoiceSmall",
    "mode": "warm",
    "device": "cpu",
    "num_threads": 4,
    "timeout_ms": 8000
  }
}
```

### 6.5 IntentParser

职责：

- 归一化 ASR 文本。
- 按规则解析 intent 和 params。
- 给出 parser_confidence。
- 无匹配或低置信度时返回 `NO_MATCH`，不发送业务动作。

首版指令集：

|口语示例|intent|params|处理说明|
|---|---|---|---|
|调取患者 123456|fetch_patient|`{"patient_id":"123456"}`|数字按患者 ID 透传|
|打开患者 123456|fetch_patient|`{"patient_id":"123456"}`|同义词归一|
|查看患者张三|fetch_patient|`{"patient_name":"张三"}`|重名由业务端处理|
|呼叫下一个患者|call_next_patient|`{}`|业务端决定队列|
|开始录音|record_control|`{"action":"start"}`|业务端执行|
|暂停录音|record_control|`{"action":"pause"}`|业务端执行|
|继续录音|record_control|`{"action":"resume"}`|业务端执行|
|关闭录音|record_control|`{"action":"stop"}`|业务端执行|

唤醒词本身不默认发送给业务端。若产品需要统计唤醒次数，可通过配置开启 `notify_wake_event`，并走单独 event 类型。

### 6.6 BusinessClient

职责：

- 将解析结果发送给业务系统。
- 设置请求超时。
- 使用 request_id 保证幂等。
- 处理 2xx、4xx、5xx、超时和连接失败。

默认不对业务指令做后台无限重试，避免重复操作。网络短暂失败时最多重试 1 次，并使用相同 request_id。业务端必须按 request_id 去重。

## 7. 业务接口协议

### 7.1 请求

默认接口：

```text
POST {base_url}/api/voice/commands
```

Headers：

```text
Content-Type: application/json
X-Request-Id: <request_id>
X-Agent-Voice-Version: 0.1.0
X-Voice-Signature: <optional-hmac-sha256>
```

Body：

```json
{
  "version": "1.0",
  "request_id": "20260511-143012-8f3a6c",
  "timestamp": "2026-05-11T14:30:12+08:00",
  "device_id": "clinic-room-01-pc-03",
  "source": "desktop_voice_widget",
  "event_type": "command",
  "text": "调取患者123456",
  "normalized_text": "调取患者123456",
  "asr_confidence": 0.86,
  "parser_confidence": 0.98,
  "intent": "fetch_patient",
  "params": {
    "patient_id": "123456"
  },
  "duration_ms": {
    "recording": 1820,
    "asr": 640,
    "parse": 2
  }
}
```

### 7.2 响应

```json
{
  "accepted": true,
  "code": "OK",
  "message": "accepted",
  "feedback": "正在调取患者信息"
}
```

响应处理：

|情况|客户端行为|
|---|---|
|`accepted=true`|展示成功状态，1 秒后回到待机|
|`accepted=false`|展示失败状态和业务端 message|
|HTTP 4xx|不重试，记录脱敏日志|
|HTTP 5xx|最多重试 1 次|
|超时或连接失败|最多重试 1 次，仍失败则展示失败|

## 8. 配置文件

`config.json` 示例：

```json
{
  "app": {
    "device_id": "clinic-room-01-pc-03",
    "app_version": "0.1.0",
    "log_level": "INFO",
    "log_retention_days": 7
  },
  "audio": {
    "sample_rate": 16000,
    "channels": 1,
    "device_index": null,
    "frame_ms": 30
  },
  "wake": {
    "engine": "porcupine",
    "keyword_path": "models/wake/xiaotuxiaotu.ppn",
    "sensitivity": 0.55,
    "cooldown_ms": 1500
  },
  "asr": {
    "engine": "sensevoice",
    "model_dir": "models/asr/SenseVoiceSmall",
    "mode": "warm",
    "device": "cpu",
    "num_threads": 4,
    "timeout_ms": 8000
  },
  "recorder": {
    "min_duration_ms": 800,
    "max_duration_ms": 6000,
    "end_silence_ms": 900,
    "pre_roll_ms": 300
  },
  "transport": {
    "base_url": "http://127.0.0.1:18080",
    "command_path": "/api/voice/commands",
    "timeout_ms": 3000,
    "retry": 1,
    "hmac_secret_env": "AGENT_VOICE_HMAC_SECRET"
  },
  "privacy": {
    "save_audio": false,
    "mask_patient_id_in_log": true,
    "mask_patient_name_in_log": true
  }
}
```

## 9. 安全与合规边界

1. 默认不保存原始音频。
2. 默认不上传云端服务。
3. 日志中患者 ID、患者姓名必须脱敏。
4. AccessKey、HMAC Secret 不允许写入源码和 Git。
5. 业务请求必须包含 request_id，业务端必须做幂等。
6. 建议生产环境只连接 localhost 或内网白名单地址。
7. 如果跨机器通信，必须启用 HTTPS 或内网安全通道。
8. 语音层不直接写业务数据库，不绕过业务系统权限。
9. 产品文案避免宣称“符合医疗合规”，只能描述“本地处理、默认不保存音频、默认不上传云端”，最终合规结论由项目合规评审确认。

## 10. 资源占用目标

以下为首版验收目标，最终数值以目标机器实测为准。

|模式|目标|说明|
|---|---:|---|
|冷启动时间|<= 10 秒|含 UI、配置、唤醒引擎和 ASR warm 加载|
|待机 CPU|<= 3%|无说话、唤醒监听中|
|待机内存 warm 模式|<= 900 MB|ASR 常驻，换取低延迟|
|待机内存 lazy 模式|<= 250 MB|ASR 不常驻，首次识别较慢|
|唤醒到开始聆听|<= 300 ms|唤醒命中后 UI 进入绿色状态|
|说话结束到 ASR 返回|<= 2.5 秒|6 秒内短句，CPU 推理|
|业务请求超时|3 秒|可配置|
|连续运行|>= 8 小时|无内存持续增长、无 UI 卡死|

不再承诺“ASR 模型 45MB、峰值 120MB”这类未经实测的数值。SenseVoiceSmall 和推理框架的实际占用会明显高于普通 Python GUI 程序，需要在目标工控机上实测。

## 11. 打包与部署

### 11.1 离线包内容

```text
AgentVoice/
  agent-voice.exe
  config.json
  models/
    wake/
      xiaotuxiaotu.ppn
    asr/
      SenseVoiceSmall/
  runtime/
  logs/
  licenses/
  install.ps1
  uninstall.ps1
  README.md
```

### 11.2 打包策略

首版使用 PyInstaller one-dir，不使用 one-file：

- 模型文件大，one-file 每次启动解压会变慢。
- ASR 依赖和动态库多，one-dir 更容易定位问题。
- 医疗工作站部署更看重稳定性，不需要强行压成单 exe。

### 11.3 安装策略

1. 解压到固定目录，例如 `C:\Program Files\AgentVoice`。
2. 首次启动生成本机 `device_id`。
3. 通过配置文件指定业务端地址和麦克风。
4. 可选安装开机自启快捷方式。
5. 卸载时保留或删除日志由运维参数控制。

## 12. 测试计划

### 12.1 单元测试

|模块|测试重点|
|---|---|
|IntentParser|同义词、患者 ID、患者姓名、无匹配、低置信度|
|Schema|请求 JSON 必填字段、字段类型、request_id|
|StateMachine|正常流程、失败流程、重复唤醒、暂停恢复|
|PrivacyFilter|日志脱敏，不泄露患者 ID 和姓名|

### 12.2 集成测试

|场景|验收|
|---|---|
|麦克风正常|可唤醒、可录音、可识别|
|无麦克风|UI 显示错误，日志记录原因|
|业务端不可达|显示发送失败，不伪造成功|
|业务端 500|最多重试 1 次，request_id 不变|
|ASR Worker 崩溃|主进程不退出，进入错误状态并尝试恢复|
|连续运行 8 小时|无明显内存泄漏和线程堆积|

### 12.3 现场试点测试

现场至少覆盖：

- 不同医生、护士、收费窗口等真实口音。
- 安静诊室、嘈杂候诊区、多人同时说话。
- 台式机内置麦克风、USB 麦克风、耳麦。
- 网络正常、业务端重启、业务端超时。
- 业务系统有重名患者、无患者、排队为空等业务边界。

## 13. 里程碑

|阶段|目标|产出|
|---|---|---|
|M0 依赖验证|确认 GUI、唤醒、ASR、授权和打包可行|依赖锁定、许可清单、最小 Demo|
|M1 音频与唤醒|实现麦克风采集和“小图小图”唤醒|可运行唤醒 Demo|
|M2 录音与 ASR|唤醒后录音并返回文本|ASR Worker、端点检测、耗时统计|
|M3 指令解析与协议|固定指令转 JSON 并发送 mock server|parser 单测、协议文档、mock server|
|M4 桌面挂件|悬浮 UI、状态机、右键菜单|可交互桌面客户端|
|M5 打包部署|Windows one-dir 包、配置、日志|可交付测试包|
|M6 现场试点|目标工作站试运行和调参|资源、准确率、误唤醒报告|

## 14. 研发任务拆分

首版建议按以下任务拆分：

1. 建立 Python 项目、依赖锁定、配置加载、日志框架。
2. 实现状态机和事件总线。
3. 实现 AudioCapture，完成设备枚举和采样。
4. 接入 WakeDetector，完成唤醒回调和冷却机制。
5. 实现 CommandRecorder，接入 VAD 和超时策略。
6. 实现 ASR Worker 子进程，完成 warm/lazy 模式。
7. 实现 IntentParser 和规则单测。
8. 实现 BusinessClient、请求签名、超时和重试。
9. 实现 PySide6 悬浮挂件、托盘和右键菜单。
10. 实现隐私日志过滤和错误展示。
11. 接入 mock server 做端到端联调。
12. PyInstaller 打包，整理 licenses 和离线模型目录。
13. 在目标 Windows 机器做资源、准确率和稳定性测试。

## 15. 风险与处理

|风险|影响|处理|
|---|---|---|
|Porcupine 授权或 AccessKey 不满足发版要求|无法按当前唤醒方案商用发布|M0 阶段确认；不满足则切换 openWakeWord/ONNX 方案|
|ASR 资源占用高于预期|低配工控机卡顿|提供 warm/lazy 双模式；必要时评估量化模型|
|医院环境噪声导致误识别|误触发业务动作|VAD 调参、低置信度不发送、业务端二次确认高风险动作|
|患者姓名重名|调错患者|语音层只透传姓名，业务端必须展示候选并由用户确认|
|业务请求重复|重复执行业务动作|request_id 幂等，客户端不做无限重试|
|打包后依赖缺失|现场无法启动|M5 阶段在干净 Windows 虚拟机验证|
|日志泄露患者信息|合规风险|默认脱敏，默认不保存音频，debug 模式需要显式开启|

## 16. 发版准入清单

- [ ] 目标 Windows 10/11 机器可启动。
- [ ] 断网状态下唤醒、录音、ASR、解析可用。
- [ ] 业务端 mock 接口端到端通过。
- [ ] 日志无明文患者 ID、患者姓名和密钥。
- [ ] 无麦克风、模型缺失、业务端不可达均有错误提示。
- [ ] 连续运行 8 小时无明显内存增长。
- [ ] licenses 目录包含三方依赖许可证。
- [ ] 产品确认“不做诊疗判断、不保存音频、不上传云端”的对外口径。

## 17. 参考链接

- PySide6 官方文档：https://doc.qt.io/qtforpython-6/
- Qt for Python 许可说明：https://doc.qt.io/qtforpython-6/licenses.html
- Picovoice Porcupine：https://picovoice.ai/platform/porcupine/
- FunASR：https://github.com/modelscope/FunASR
- SenseVoice：https://github.com/FunAudioLLM/SenseVoice
