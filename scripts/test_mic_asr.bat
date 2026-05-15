@echo off
setlocal
cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m agent_voice --asr-mic-seconds 3 --config "config.example.json"
) else (
  py -3.12 -m agent_voice --asr-mic-seconds 3 --config "config.example.json"
)
