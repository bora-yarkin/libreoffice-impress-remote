# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $RootDir "relay-runtime"
$InstallDir = Join-Path ${env:ProgramFiles} "Impress Remote Relay"
$DataDir = Join-Path $InstallDir "data"
$InstallVenvDir = Join-Path $InstallDir ".venv"
$InstallVenvPython = Join-Path $InstallVenvDir "Scripts\python.exe"

if (-not (Test-Path $RuntimeDir)) {
    throw "Could not find relay runtime folder: $RuntimeDir"
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this action from an elevated PowerShell window."
    }
}

function Invoke-SystemPython {
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

function Read-RelayPort {
    $port = Read-Host "Port [leave empty for random/default behavior]"
    if ($port -and ($port -notmatch '^[0-9]+$')) {
        throw "Port must be a number."
    }
    return $port
}

function Start-RelayOnce {
    param([string]$Port)

    $venvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $RuntimeDir ".venv" }
    $venvPython = Join-Path $venvDir "Scripts\python.exe"

    if (-not (Test-Path $venvPython)) {
        Invoke-SystemPython -Arguments @("-m", "venv", $venvDir)
    }

    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $RuntimeDir "requirements.txt")
    if ($Port) {
        & $venvPython (Join-Path $RuntimeDir "run-relay.py") --port $Port
    } else {
        & $venvPython (Join-Path $RuntimeDir "run-relay.py")
    }
}

function Install-RelayService {
    param([string]$Port)

    Assert-Administrator

    if (Get-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue) {
        Stop-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue
    }

    if ((Test-Path $InstallVenvPython) -and (Get-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue)) {
        Push-Location $InstallDir
        try {
            & $InstallVenvPython (Join-Path $InstallDir "windows-service.py") remove
        } finally {
            Pop-Location
        }
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Copy-Item -Path (Join-Path $RuntimeDir "*") -Destination $InstallDir -Recurse -Force
    Remove-Item -Path $InstallVenvDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $DataDir -Recurse -Force -ErrorAction SilentlyContinue

    Invoke-SystemPython -Arguments @("-m", "venv", $InstallVenvDir)

    & $InstallVenvPython -m pip install --upgrade pip
    & $InstallVenvPython -m pip install -r (Join-Path $InstallDir "requirements.txt")
    & $InstallVenvPython -m pip install -r (Join-Path $InstallDir "requirements-windows.txt")

    $postInstall = Join-Path (Split-Path $InstallVenvPython -Parent) "pywin32_postinstall.py"
    if (Test-Path $postInstall) {
        & $InstallVenvPython $postInstall -install
    }

    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    if ($Port) {
        & $InstallVenvPython (Join-Path $InstallDir "run-relay.py") --config (Join-Path $DataDir "service.json") --port $Port --ensure-config-only | Out-Null
    } else {
        & $InstallVenvPython (Join-Path $InstallDir "run-relay.py") --config (Join-Path $DataDir "service.json") --ensure-config-only | Out-Null
    }
    $selectedPort = & $InstallVenvPython (Join-Path $InstallDir "run-relay.py") --config (Join-Path $DataDir "service.json") --print-port

    Push-Location $InstallDir
    try {
        & $InstallVenvPython (Join-Path $InstallDir "windows-service.py") --startup auto install
    } finally {
        Pop-Location
    }

    Start-Service -Name "ImpressRemoteRelay"

    Write-Host "Installed ImpressRemoteRelay"
    Write-Host "Install directory: $InstallDir"
    Write-Host "Listening port: $selectedPort"
    Write-Host "Health URL: http://<server-host>:$selectedPort/health"
}

function Uninstall-RelayService {
    Assert-Administrator

    if (Get-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue) {
        Stop-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue
    }

    if (Test-Path $InstallVenvPython) {
        Push-Location $InstallDir
        try {
            & $InstallVenvPython (Join-Path $InstallDir "windows-service.py") remove
        } finally {
            Pop-Location
        }
    }

    if (Test-Path $InstallDir) {
        Remove-Item -Path $InstallDir -Recurse -Force
    }

    Write-Host "Removed ImpressRemoteRelay"
}

Write-Host "LibreOffice Impress Remote Relay"
Write-Host ""
Write-Host "1) Run once in this terminal"
Write-Host "2) Install as a Windows service"
Write-Host "3) Uninstall the Windows service"
Write-Host ""

$action = Read-Host "Choose an action [1-3]"

switch ($action) {
    "1" {
        $port = Read-RelayPort
        Start-RelayOnce -Port $port
    }
    "2" {
        $port = Read-RelayPort
        Install-RelayService -Port $port
    }
    "3" {
        Uninstall-RelayService
    }
    default {
        throw "Unknown action: $action"
    }
}
