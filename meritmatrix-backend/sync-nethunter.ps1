$Project = "C:\Users\CIPHER\Documents\Projects-Dev\meritmatrix-pro-foundation\meritmatrix-pro"
$Temp = "$env:TEMP\meritmatrix-sync"
$Zip = "$env:TEMP\meritmatrix-sync.zip"

Remove-Item $Temp -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $Zip -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Path $Temp | Out-Null

Copy-Item "$Project\backend" "$Temp\backend" -Recurse
Copy-Item "$Project\frontend" "$Temp\frontend" -Recurse
Copy-Item "$Project\docs" "$Temp\docs" -Recurse
Copy-Item "$Project\scripts" "$Temp\scripts" -Recurse

Copy-Item "$Project\README.md" "$Temp\README.md"
Copy-Item "$Project\.gitignore" "$Temp\.gitignore"
Copy-Item "$Project\docker-compose.yml" "$Temp\docker-compose.yml"
Copy-Item "$Project\.env.example" "$Temp\.env.example"

# Never transfer NetHunter environment/runtime files
Remove-Item "$Temp\backend\.env" -Force -ErrorAction SilentlyContinue
Remove-Item "$Temp\backend\.venv" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$Temp\backend\test_meritmatrix.db" -Force -ErrorAction SilentlyContinue
Remove-Item "$Temp\backend\.pytest_cache" -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $Temp -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Compress-Archive -Path "$Temp\*" -DestinationPath $Zip -Force

Write-Host "Uploading to NetHunter..." -ForegroundColor Cyan
scp $Zip kali@10.84.212.193:/home/kali/meritmatrix-sync.zip

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Upload failed." -ForegroundColor Red
    exit 1
}

Write-Host "Extracting on NetHunter..." -ForegroundColor Cyan

ssh kali@10.84.212.193 "rm -rf /tmp/meritmatrix-sync; mkdir -p /tmp/meritmatrix-sync; python3 -m zipfile -e /home/kali/meritmatrix-sync.zip /tmp/meritmatrix-sync"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Extraction failed." -ForegroundColor Red
    exit 1
}

Write-Host "Installing synchronized files..." -ForegroundColor Cyan

ssh kali@10.84.212.193 "cp -a /tmp/meritmatrix-sync/. /home/kali/meritmatrix-pro-nethunter/; rm -rf /tmp/meritmatrix-sync /home/kali/meritmatrix-sync.zip"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Installation failed." -ForegroundColor Red
    exit 1
}

Remove-Item $Temp -Recurse -Force
Remove-Item $Zip -Force

Write-Host ""
Write-Host "SUCCESS: Windows -> NetHunter synchronization complete." -ForegroundColor Green
