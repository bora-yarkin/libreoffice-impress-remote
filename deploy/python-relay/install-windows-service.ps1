# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this installer from an elevated PowerShell window."
    }
}

function Get-PythonCommand {
    param([string[]]$Arguments)

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & $py.Source -3 @Arguments
        return
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source @Arguments
        return
    }
    throw "Python 3 was not found. Install Python 3 and run this script again."
}

Assert-Administrator

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path ${env:ProgramFiles} "Impress Remote Relay"
$DataDir = Join-Path $InstallDir "data"
$VenvDir = Join-Path $InstallDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (Get-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue) {
    Stop-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue
}

if ((Test-Path $VenvPython) -and (Get-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue)) {
    Push-Location $InstallDir
    try {
        & $VenvPython (Join-Path $InstallDir "windows-service.py") remove
    } finally {
        Pop-Location
    }
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Path (Join-Path $SourceDir "*") -Destination $InstallDir -Recurse -Force

if (-not (Test-Path $VenvPython)) {
    Get-PythonCommand -Arguments @("-m", "venv", $VenvDir)
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $InstallDir "requirements.txt")
& $VenvPython -m pip install -r (Join-Path $InstallDir "requirements-windows.txt")

$PostInstall = Join-Path (Split-Path $VenvPython -Parent) "pywin32_postinstall.py"
if (Test-Path $PostInstall) {
    & $VenvPython $PostInstall -install
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
& $VenvPython (Join-Path $InstallDir "run-relay.py") --config (Join-Path $DataDir "service.json") --ensure-config-only | Out-Null
$Port = & $VenvPython (Join-Path $InstallDir "run-relay.py") --config (Join-Path $DataDir "service.json") --print-port

Push-Location $InstallDir
try {
    & $VenvPython (Join-Path $InstallDir "windows-service.py") --startup auto install
} finally {
    Pop-Location
}

Start-Service -Name "ImpressRemoteRelay"

Write-Host "Installed ImpressRemoteRelay"
Write-Host "Install directory: $InstallDir"
Write-Host "Listening port: $Port"
Write-Host "Health URL: http://<server-host>:$Port/health"
