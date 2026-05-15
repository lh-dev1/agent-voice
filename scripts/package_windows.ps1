Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$AppName = "AgentVoice"
$DistDir = Join-Path $Root "dist"
$BuildDir = Join-Path $Root "build"
$ReleaseDir = Join-Path $Root "release\AgentVoice-windows"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

function Invoke-AgentPython {
    param([string[]]$Arguments)

    if (Test-Path $VenvPython) {
        & $VenvPython @Arguments
    } else {
        & py -3.12 @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Set-Location $Root

if (!(Test-Path (Join-Path $Root "models"))) {
    Write-Error "Missing models directory. Download wake and ASR models before packaging."
    exit 1
}

if (Test-Path $VenvPython) {
    & $VenvPython -m PyInstaller --version *> $null
} else {
    & py -3.12 -m PyInstaller --version *> $null
}
if ($LASTEXITCODE -ne 0) {
    Write-Error "Missing PyInstaller. Install it first: python -m pip install pyinstaller"
    exit 1
}

if (Test-Path $BuildDir) {
    Remove-Item $BuildDir -Recurse -Force
}
if (Test-Path $DistDir) {
    Remove-Item $DistDir -Recurse -Force
}
if (Test-Path $ReleaseDir) {
    Remove-Item $ReleaseDir -Recurse -Force
}
New-Item -ItemType Directory -Path $ReleaseDir | Out-Null

Invoke-AgentPython @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--name", $AppName,
    "--collect-all", "funasr",
    "--collect-all", "sherpa_onnx",
    "--collect-all", "sounddevice",
    "--collect-all", "PySide6",
    "--hidden-import", "sentencepiece",
    "--hidden-import", "pypinyin",
    "--hidden-import", "soundfile",
    "--hidden-import", "torch",
    "--hidden-import", "torchaudio",
    "agent_voice\__main__.py"
)

Copy-Item (Join-Path $DistDir $AppName) (Join-Path $ReleaseDir $AppName) -Recurse
Copy-Item (Join-Path $Root "config.example.json") (Join-Path $ReleaseDir "config.example.json")
Copy-Item (Join-Path $Root "models") (Join-Path $ReleaseDir "models") -Recurse
$ReleaseModelsDir = Join-Path $ReleaseDir "models"
Get-ChildItem -Path $ReleaseModelsDir -Filter ".DS_Store" -Recurse -Force | Remove-Item -Force
$LauncherDir = Join-Path $ReleaseDir "launchers\windows"
New-Item -ItemType Directory -Path $LauncherDir | Out-Null

Set-Content -Path (Join-Path $LauncherDir "StartWidget.bat") -Encoding ASCII -Value @"
@echo off
cd /d "%~dp0..\.."
"AgentVoice\AgentVoice.exe" --gui --config "config.example.json"
"@

Set-Content -Path (Join-Path $LauncherDir "StartVoiceLoop.bat") -Encoding ASCII -Value @"
@echo off
cd /d "%~dp0..\.."
"AgentVoice\AgentVoice.exe" --voice-loop --config "config.example.json"
"@

Set-Content -Path (Join-Path $LauncherDir "StartMockServer.bat") -Encoding ASCII -Value @"
@echo off
cd /d "%~dp0..\.."
"AgentVoice\AgentVoice.exe" --mock-server --config "config.example.json"
"@

Set-Content -Path (Join-Path $LauncherDir "TestMicAsr.bat") -Encoding ASCII -Value @"
@echo off
cd /d "%~dp0..\.."
"AgentVoice\AgentVoice.exe" --asr-mic-seconds 3 --config "config.example.json"
"@

Write-Host "Windows package created: $ReleaseDir"
