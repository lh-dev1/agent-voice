#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

APP_NAME="AgentVoice"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/build"
RELEASE_DIR="${ROOT_DIR}/release/AgentVoice-macos"
DMG_PATH="${ROOT_DIR}/release/AgentVoice-macos.dmg"

cd "${ROOT_DIR}"

if [[ ! -d "${ROOT_DIR}/models" ]]; then
  echo "缺少 models 目录，请先下载唤醒和 ASR 模型。" >&2
  exit 1
fi

"${PYTHON_BIN}" -m pip install --upgrade pyinstaller

rm -rf "${BUILD_DIR}" "${DIST_DIR}" "${RELEASE_DIR}" "${DMG_PATH}"
mkdir -p "${RELEASE_DIR}"

"${PYTHON_BIN}" -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --name "${APP_NAME}" \
  --collect-all "funasr" \
  --collect-all "sherpa_onnx" \
  --collect-all "sounddevice" \
  --collect-all "PySide6" \
  --hidden-import "sentencepiece" \
  --hidden-import "pypinyin" \
  --hidden-import "soundfile" \
  --hidden-import "torch" \
  --hidden-import "torchaudio" \
  "agent_voice/__main__.py"

cp -R "${DIST_DIR}/${APP_NAME}" "${RELEASE_DIR}/${APP_NAME}"
cp "${ROOT_DIR}/config.example.json" "${RELEASE_DIR}/config.example.json"
cp -R "${ROOT_DIR}/models" "${RELEASE_DIR}/models"
mkdir -p "${RELEASE_DIR}/launchers/macos"

cat > "${RELEASE_DIR}/launchers/macos/启动挂件.command" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"
exec "AgentVoice/AgentVoice" --gui --config "config.example.json"
EOF

cat > "${RELEASE_DIR}/launchers/macos/启动语音监听.command" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"
exec "AgentVoice/AgentVoice" --voice-loop --config "config.example.json"
EOF

cat > "${RELEASE_DIR}/launchers/macos/启动业务Mock.command" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"
exec "AgentVoice/AgentVoice" --mock-server --config "config.example.json"
EOF

cat > "${RELEASE_DIR}/launchers/macos/测试麦克风ASR.command" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"
exec "AgentVoice/AgentVoice" --asr-mic-seconds 3 --config "config.example.json"
EOF

chmod +x "${RELEASE_DIR}/launchers/macos/"*.command

hdiutil create -volname "AgentVoice" -srcfolder "${RELEASE_DIR}" -ov -format UDZO "${DMG_PATH}"

echo "macOS 打包完成：${RELEASE_DIR}"
echo "DMG 输出：${DMG_PATH}"
