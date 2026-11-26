# RM Copilot, Phase 5 Lab 12: Azure SQL logical server (Entra only), free-tier database, laptop firewall rule.
# Safe to re-run: every step either creates the thing or leaves it as it is.

. "$PSScriptRoot\00_config.ps1"

function Assert-Ok($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED at: $step" -ForegroundColor Red
        exit 1
    }
}

Write-Host "1/7 Selecting subscription..."
az account set --subscription $SubscriptionId
Assert-Ok "select subscription (run az login first?)"

Write-Host "2/7 Registering the Sql provider..."
az provider register --namespace Microsoft.Sql --wait --output none
Assert-Ok "register Microsoft.Sql"

Write-Host "3/7 Finding you (you become the server's Entra admin)..."
$me = az ad signed-in-user show | ConvertFrom-Json
Assert-Ok "read signed-in user"
Write-Host "    admin will be $($me.userPrincipalName)"

Write-Host "4/7 SQL server $SqlServer in $SqlLocation (Entra authentication only)..."
$existing = az sql server list --resource-group $ResourceGroup --query "[?name=='$SqlServer'].name" --output tsv
Assert-Ok "list SQL servers"
if ($existing) {
    Write-Host "    already exists, leaving it as it is"
} else {
    az sql server create --name $SqlServer --resource-group $ResourceGroup --location $SqlLocation `
        --enable-ad-only-auth --external-admin-principal-type User `
        --external-admin-name $me.userPrincipalName --external-admin-sid $me.id `
        --minimal-tls-version 1.2 --output none
    Assert-Ok "create SQL server"
}

Write-Host "5/7 Free-tier database $SqlDatabase..."
$existing = az sql db list --resource-group $ResourceGroup --server $SqlServer --query "[?name=='$SqlDatabase'].name" --output tsv
Assert-Ok "list databases"
if ($existing) {
    Write-Host "    already exists, leaving it as it is"
} else {
    # --use-free-limit true is the flag that makes it free. Never remove it.
    az sql db create --name $SqlDatabase --server $SqlServer --resource-group $ResourceGroup `
        --edition GeneralPurpose --family Gen5 --capacity 2 --compute-model Serverless `
        --use-free-limit true --free-limit-exhaustion-behavior AutoPause --output none
    Assert-Ok "create free-tier database"
}

Write-Host "6/7 Firewall: allow this laptop only..."
$myIp = Invoke-RestMethod -Uri "https://api.ipify.org"
$existing = az sql server firewall-rule list --resource-group $ResourceGroup --server $SqlServer --query "[?name=='AllowLaptop'].name" --output tsv
Assert-Ok "list firewall rules"
if ($existing) {
    az sql server firewall-rule update --resource-group $ResourceGroup --server $SqlServer --name AllowLaptop `
        --start-ip-address $myIp --end-ip-address $myIp --output none
} else {
    az sql server firewall-rule create --resource-group $ResourceGroup --server $SqlServer --name AllowLaptop `
        --start-ip-address $myIp --end-ip-address $myIp --output none
}
Assert-Ok "firewall rule"
Write-Host "    open for $myIp"

Write-Host "7/7 Checking the settings that matter..."
az sql db show --resource-group $ResourceGroup --server $SqlServer --name $SqlDatabase `
    --query "{name:name, sku:sku.name, free:useFreeLimit, atLimit:freeLimitExhaustionBehavior, status:status}" --output table
Write-Host "Done." -ForegroundColor Green