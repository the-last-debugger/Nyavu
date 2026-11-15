#!/usr/bin/env bash
# Deploy Nyavu to Azure App Service from Azure Cloud Shell.
#
# Cloud Shell is already authenticated inside your subscription, so the
# AADSTS530035 security-defaults block that stops `az login` does not apply.
#
# Paste this whole file into Cloud Shell (Bash). It prints the public URL.
set -euo pipefail

RG="nyavu-rg"
PLAN="nyavu-plan"
LOCATION="${LOCATION:-southafricanorth}"
APP="nyavu-$RANDOM$RANDOM"
SRC="/tmp/nyavu-src"
ZIP="/tmp/nyavu.zip"

echo "== fetching source =="
rm -rf "$SRC"
git clone --depth 1 https://github.com/the-last-debugger/Nyavu.git "$SRC"
cd "$SRC"

echo "== packaging =="
rm -f "$ZIP"
zip -rq "$ZIP" app requirements.txt ml/features.py \
    ml/artifacts/model.joblib ml/artifacts/metrics.json ml/artifacts/allowlist.txt \
    -x "*/__pycache__/*"
echo "   $(du -h "$ZIP" | cut -f1) package"

echo "== resource group =="
az group create --name "$RG" --location "$LOCATION" --output none

echo "== plan (B1, Linux) =="
az appservice plan create --name "$PLAN" --resource-group "$RG" \
    --is-linux --sku B1 --output none

echo "== web app =="
az webapp create --name "$APP" --resource-group "$RG" \
    --plan "$PLAN" --runtime "PYTHON:3.12" --output none

echo "== configuration =="
az webapp config appsettings set --name "$APP" --resource-group "$RG" --settings \
    SCM_DO_BUILD_DURING_DEPLOYMENT=1 \
    WEBSITES_PORT=8000 \
    NYAVU_COOKIE_SECURE=1 \
    NYAVU_DB_PATH=/home/data/nyavu.db \
    PYTHONUNBUFFERED=1 --output none

az webapp config set --name "$APP" --resource-group "$RG" \
    --startup-file "uvicorn app.main:app --host 0.0.0.0 --port 8000" --output none

echo "== deploying =="
az webapp deploy --name "$APP" --resource-group "$RG" \
    --src-path "$ZIP" --type zip --output none

echo
echo "=============================================="
echo " NYAVU IS DEPLOYED"
echo "   https://$APP.azurewebsites.net"
echo "=============================================="
echo
echo "The first request may take ~60s while App Service builds."
echo "Check health at: https://$APP.azurewebsites.net/api/health"
