# RM Copilot, Phase 2 Lab 5: push the generator's Bronze tables into the landing container.
# Uploads out\bronze only. out\ground_truth (the answer key) never leaves this laptop.
# Re-running replaces what's in landing: it's a post box, not storage.

. "$PSScriptRoot\00_config.ps1"

$source = Join-Path $PSScriptRoot "..\generator\out\bronze\*"
$target = "https://$StorageAccount.dfs.core.windows.net/landing/"

$env:AZCOPY_AUTO_LOGIN_TYPE = "AZCLI"
azcopy copy $source $target --recursive
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED at: upload to landing" -ForegroundColor Red
    exit 1
}
Write-Host "Done." -ForegroundColor Green