# start.ps1 - helper to recreate/activate venv and run the bot
# Usage: Run from repo root in PowerShell (pwsh): ./start.ps1

$ErrorActionPreference = 'Stop'

# 1) Create venv if missing
if (-not (Test-Path .venv)) {
    Write-Host "Creating virtualenv .venv..."
    python -m venv .venv
} else {
    Write-Host ".venv already exists"
}

# 2) Upgrade pip/tools in venv
Write-Host "Upgrading pip, setuptools and wheel inside venv..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

# 3) Install requirements
if (Test-Path requirements.txt) {
    Write-Host "Installing requirements from requirements.txt..."
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
} else {
    Write-Host "requirements.txt not found - skipping install"
}

# 4) Activate venv for current session (optional)
try {
    Write-Host "Activating venv in this PowerShell session..."
    & .\.venv\Scripts\Activate.ps1
} catch {
    Write-Host "Failed to activate venv automatically. You can activate manually with: .\\.venv\\Scripts\\Activate.ps1"
}

# 5) Run a safe import test and then the bot
Write-Host "Running safe import test (utils, bot_commands, database_commands)..."
& .\.venv\Scripts\python.exe -c "import utils, bot_commands, database_commands; print('IMPORTS_OK')"

Write-Host "If import test passed, starting main.py (bot)."
& .\.venv\Scripts\python.exe main.py
