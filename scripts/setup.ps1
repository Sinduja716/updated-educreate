# One-time setup. Run from anywhere:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# Works with the py launcher, with a plain `python` (for example one installed by mise), and Python 3.11-3.13.
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Run($cmd) { Invoke-Expression $cmd; if ($LASTEXITCODE -ne 0) { throw "FAILED: $cmd" } }

function Find-Python {
    foreach ($v in "3.12", "3.13", "3.11") {
        try {
            $out = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) { return "$out".Trim() }
        } catch { }
    }
    try {
        $out = & python -c "import sys; print(sys.executable if (3,11) <= sys.version_info[:2] <= (3,13) else '')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return "$out".Trim() }
    } catch { }
    return $null
}

if (-not (Test-Path .venv)) {
    $py = Find-Python
    if (-not $py) { throw "No Python 3.11, 3.12 or 3.13 found. Install one from python.org (tick Add to PATH), then run this again." }
    Write-Host "Using Python at $py"
    Run "& '$py' -m venv .venv"
}
Run ".\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt"
Push-Location frontend
Run "npm ci"
Pop-Location
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Run ".\.venv\Scripts\python.exe scripts\check_env.py"
Write-Host "Setup finished."
