# RM Copilot, Phase 2 Lab 4: resource group and monthly budget.
# Safe to re-run: every step either creates the thing or leaves it as it is.

. "$PSScriptRoot\00_config.ps1"

# Stop with a clear message if the last az command failed.
function Assert-Ok($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED at: $step" -ForegroundColor Red
        exit 1
    }
}

Write-Host "1/4 Selecting subscription..."
az account set --subscription $SubscriptionId
Assert-Ok "select subscription (run az login first?)"

Write-Host "2/4 Creating resource group $ResourceGroup in $Location..."
az group create --name $ResourceGroup --location $Location --tags $Tags --output none
Assert-Ok "create resource group"

Write-Host "3/4 Registering the Consumption provider..."
az provider register --namespace Microsoft.Consumption --output none
Assert-Ok "register Microsoft.Consumption"

Write-Host "4/4 Budget $BudgetName..."
$api = "2023-05-01"
$budgetsUrl = "https://management.azure.com/subscriptions/$SubscriptionId/providers/Microsoft.Consumption/budgets"

$existing = az rest --method get --url "$($budgetsUrl)?api-version=$api" --query "value[?name=='$BudgetName'].name" --output tsv
Assert-Ok "list budgets"

if ($existing) {
    Write-Host "    already exists, leaving it as it is"
} else {
    $notifications = @{}
    foreach ($pct in $AlertPercents) {
        $notifications["Actual_$pct"] = @{
            enabled       = $true
            operator      = "GreaterThanOrEqualTo"
            threshold     = $pct
            thresholdType = "Actual"
            contactEmails = @($AlertEmail)
        }
    }
    $body = @{
        properties = @{
            category      = "Cost"
            amount        = $BudgetAmount
            timeGrain     = "Monthly"
            timePeriod    = @{ startDate = (Get-Date -Day 1).ToString("yyyy-MM-01T00:00:00Z") }
            notifications = $notifications
        }
    }
    $bodyFile = Join-Path $env:TEMP "rm-copilot-budget.json"
    [IO.File]::WriteAllText($bodyFile, ($body | ConvertTo-Json -Depth 6))

    az rest --method put --url "$budgetsUrl/$($BudgetName)?api-version=$api" --body "@$bodyFile" --output none
    Assert-Ok "create budget (new subscription? see the 48-hour note)"
    Write-Host "    created: alerts at $($AlertPercents -join '%, ')% of $BudgetAmount"
}

Write-Host "Done." -ForegroundColor Green