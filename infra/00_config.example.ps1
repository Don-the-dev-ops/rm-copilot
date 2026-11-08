# RM Copilot: settings shared by every infra script.
# Copy this file to 00_config.ps1 and fill in your own values.
# 00_config.ps1 is ignored by Git; this example file is committed.

$SubscriptionId = "<your-subscription-id>"
$Location       = "southafricanorth"
$ResourceGroup  = "rg-rm-copilot"
$Tags           = @("project=rm-copilot", "env=dev", "owner=<your-name>")

$BudgetName     = "budget-rm-copilot"
$BudgetAmount   = 500            # in your billing currency
$AlertPercents  = @(50, 80, 100)
$AlertEmail     = "<your-email>"

$StorageAccount = "<globally-unique-lowercase-name>"
$Containers     = @("landing", "bronze", "silver", "gold")