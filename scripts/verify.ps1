# Run before every push:  powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Run($cmd) { Invoke-Expression $cmd; if ($LASTEXITCODE -ne 0) { throw "FAILED: $cmd" } }

Run ".\.venv\Scripts\python.exe scripts\check_env.py"
Push-Location backend
Run "..\.venv\Scripts\python.exe -m pytest -q"
Pop-Location
Push-Location frontend
Run "npm run build"
Pop-Location
Write-Host "ALL CHECKS PASSED. Safe to push."
