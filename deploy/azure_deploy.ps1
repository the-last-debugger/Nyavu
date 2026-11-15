# Deploy Nyavu to Azure App Service (Linux, Python 3.12, B1).
#
# No Docker: App Service builds the app from requirements.txt with Oryx.
# Run after `az login`. Safe to re-run - each step checks before creating.
param(
    [string]$ResourceGroup = "nyavu-rg",
    [string]$PlanName = "nyavu-plan",
    [string]$AppName = "",
    [string]$Region = "southafricanorth",
    [string]$Sku = "B1"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $AppName) {
    $AppName = "nyavu-" + -join ((48..57) + (97..122) | Get-Random -Count 6 | ForEach-Object { [char]$_ })
}

Write-Host "== staging files ==" -ForegroundColor Cyan
$stage = Join-Path $env:TEMP ("nyavu-stage-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item "$root\app" $stage -Recurse
Copy-Item "$root\requirements.txt" $stage
New-Item -ItemType Directory -Force -Path "$stage\ml\artifacts" | Out-Null
Copy-Item "$root\ml\features.py" "$stage\ml"
foreach ($f in @("model.joblib", "metrics.json", "allowlist.txt")) {
    Copy-Item "$root\ml\artifacts\$f" "$stage\ml\artifacts"
}
Get-ChildItem $stage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
$zip = Join-Path $env:TEMP "nyavu.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path "$stage\*" -DestinationPath $zip
Write-Host ("   package: {0:N1} MB" -f ((Get-Item $zip).Length / 1MB))

Write-Host "== resource group ==" -ForegroundColor Cyan
az group create --name $ResourceGroup --location $Region --output none

Write-Host "== app service plan ($Sku, Linux) ==" -ForegroundColor Cyan
az appservice plan create --name $PlanName --resource-group $ResourceGroup `
    --is-linux --sku $Sku --output none

Write-Host "== web app ==" -ForegroundColor Cyan
az webapp create --name $AppName --resource-group $ResourceGroup `
    --plan $PlanName --runtime "PYTHON:3.12" --output none

Write-Host "== configuration ==" -ForegroundColor Cyan
az webapp config appsettings set --name $AppName --resource-group $ResourceGroup `
    --settings SCM_DO_BUILD_DURING_DEPLOYMENT=1 WEBSITES_PORT=8000 `
    NYAVU_COOKIE_SECURE=1 NYAVU_DB_PATH=/home/data/nyavu.db PYTHONUNBUFFERED=1 `
    --output none

az webapp config set --name $AppName --resource-group $ResourceGroup `
    --startup-file "uvicorn app.main:app --host 0.0.0.0 --port 8000" --output none

Write-Host "== deploy ==" -ForegroundColor Cyan
az webapp deploy --name $AppName --resource-group $ResourceGroup `
    --src-path $zip --type zip --output none

$url = "https://$AppName.azurewebsites.net"
Write-Host "`nDeployed: $url" -ForegroundColor Green
Write-Host "Health:   $url/api/health"
Remove-Item $stage -Recurse -Force
