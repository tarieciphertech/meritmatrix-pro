$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"

$HostName = "kali@10.84.212.193"
$RemoteRoot = "/home/kali/meritmatrix-pro-nethunter"
$Archive = "meritmatrix-sync.tar.gz"
$LocalArchive = Join-Path $env:TEMP $Archive
$RemoteArchive = "$RemoteRoot/$Archive"

function Log($Message) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message"
}

Log "=== MeritMatrix Pro Sync: Windows -> NetHunter ==="
Log "Project: $ProjectRoot"
Log "Target: $HostName`:$RemoteRoot"

if (-not (Test-Path $Backend)) {
    throw "Backend directory not found: $Backend"
}

Log "Testing SSH connection..."
ssh -o ConnectTimeout=10 $HostName "echo SSH_OK"

if ($LASTEXITCODE -ne 0) {
    throw "SSH connection failed."
}

Log "Creating archive..."

if (Test-Path $LocalArchive) {
    Remove-Item $LocalArchive -Force
}

tar -czf $LocalArchive `
    --exclude=".venv" `
    --exclude=".env" `
    --exclude="__pycache__" `
    --exclude=".pytest_cache" `
    --exclude="*.pyc" `
    -C $Backend .

if ($LASTEXITCODE -ne 0) {
    throw "Failed to create archive."
}

Log "Uploading archive..."
scp $LocalArchive "${HostName}:$RemoteArchive"

if ($LASTEXITCODE -ne 0) {
    throw "SCP upload failed."
}

Log "Installing synchronized backend..."

$InstallCmd = @"
set -e
mkdir -p '$RemoteRoot'
rm -rf '$RemoteRoot/backend.sync'
mkdir -p '$RemoteRoot/backend.sync'
tar -xzf '$RemoteArchive' -C '$RemoteRoot/backend.sync'

if [ -d '$RemoteRoot/backend' ]; then
    if [ -f '$RemoteRoot/backend/.env' ]; then
        cp '$RemoteRoot/backend/.env' '$RemoteRoot/backend.sync/.env'
    fi
fi

if [ -d '$RemoteRoot/backend/.venv' ]; then
    mv '$RemoteRoot/backend/.venv' '$RemoteRoot/backend.sync/.venv'
fi

rm -rf '$RemoteRoot/backend.old'
if [ -d '$RemoteRoot/backend' ]; then
    mv '$RemoteRoot/backend' '$RemoteRoot/backend.old'
fi

mv '$RemoteRoot/backend.sync' '$RemoteRoot/backend'
rm -f '$RemoteArchive'

echo INSTALL_OK
"@

ssh $HostName $InstallCmd

if ($LASTEXITCODE -ne 0) {
    throw "Remote installation failed."
}

Log "[OK] Files synchronized."

Log "Verifying SQLAlchemy models..."

# Write a temporary Python script to a file to avoid shell quoting issues
$RemoteVerifyScript = "$RemoteRoot/backend/_verify_models.py"
$VerifyScript = @"
from app.models import *
from sqlalchemy.orm import configure_mappers
configure_mappers()
print("MODEL_MAPPERS_OK")
"@
$VerifyScript | Out-File -FilePath "$env:TEMP\_verify_models.py" -Encoding ascii
scp "$env:TEMP\_verify_models.py" "${HostName}:${RemoteVerifyScript}"

ssh $HostName "cd '$RemoteRoot/backend' && source .venv/bin/activate && python3 _verify_models.py"
$verifyExitCode = $LASTEXITCODE
ssh $HostName "rm -f '$RemoteVerifyScript'"

if ($verifyExitCode -ne 0) {
    throw "SQLAlchemy mapper verification failed."
}

Log "[OK] SQLAlchemy models verified."

Log "Checking Alembic..."

ssh $HostName "cd '$RemoteRoot/backend' && source .venv/bin/activate && alembic current && alembic heads"

if ($LASTEXITCODE -ne 0) {
    throw "Alembic verification failed."
}

Log "[OK] Alembic verified."

Log "Running guardian school-isolation security test..."

ssh $HostName "cd '$RemoteRoot/backend' && source .venv/bin/activate && python3 -m pytest tests/test_guardians.py::test_school_id_cannot_be_changed -x -vv"

if ($LASTEXITCODE -ne 0) {
    throw "Guardian test failed."
}

Log "[OK] Guardian security test passed."

Log "Running malformed refresh-token test..."

ssh $HostName "cd '$RemoteRoot/backend' && source .venv/bin/activate && python3 -m pytest tests/test_tokens.py::test_invalid_refresh_token_string_is_rejected -x -vv"

if ($LASTEXITCODE -ne 0) {
    throw "Refresh-token test failed."
}

Log "[OK] Refresh-token test passed."

Log "Running full test suite..."

ssh $HostName "cd '$RemoteRoot/backend' && source .venv/bin/activate && python3 -m pytest -q"

if ($LASTEXITCODE -ne 0) {
    throw "Full test suite failed."
}

if (Test-Path $LocalArchive) {
    Remove-Item $LocalArchive -Force
}

Log ""
Log "==============================================="
Log "SUCCESS: Sync + verification + tests complete"
Log "==============================================="



