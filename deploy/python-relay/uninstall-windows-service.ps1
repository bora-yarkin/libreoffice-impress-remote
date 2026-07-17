# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this uninstaller from an elevated PowerShell window."
    }
}

Assert-Administrator

$InstallDir = Join-Path ${env:ProgramFiles} "Impress Remote Relay"
$VenvPython = Join-Path $InstallDir ".venv\Scripts\python.exe"

if (Get-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue) {
    Stop-Service -Name "ImpressRemoteRelay" -ErrorAction SilentlyContinue
}

if (Test-Path $VenvPython) {
    Push-Location $InstallDir
    try {
        & $VenvPython (Join-Path $InstallDir "windows-service.py") remove
    } finally {
        Pop-Location
    }
}

if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force
}

Write-Host "Removed ImpressRemoteRelay"
