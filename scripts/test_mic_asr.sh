#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

exec ".venv/bin/python" -m agent_voice --asr-mic-seconds 3 --asr-mic-output "runtime/mic-asr-last.wav" --config "config.example.json"
