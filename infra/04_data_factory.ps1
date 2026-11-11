# =====================================================================================
# RM Copilot, Phase 2 Lab 6: Data Factory with a managed identity that can use the lake.
#
# What this script builds:
#   1. An Azure Data Factory (the "courier" that will move files from landing to bronze)
#   2. A managed identity for that factory (its own ID badge, no passwords anywhere)
#   3. Permission for that badge to read and write files in the storage account
#
# Safe to re-run: every step checks first, then either creates the thing or leaves it
# as it is. Running it twice gives the same result as running it once (idempotent).
# =====================================================================================


# -------------------------------------------------------------------------------------
# Load settings
# The dot at the start ("dot-sourcing") copies every variable from 00_config.ps1 into
# this script: $SubscriptionId, $ResourceGroup, $Location, $Tags, $StorageAccount,
# $DataFactory. $PSScriptRoot is the folder this script lives in, so it works no matter
# which folder you run it from.
# -------------------------------------------------------------------------------------
. "$PSScriptRoot\00_config.ps1"


# -------------------------------------------------------------------------------------
# Safety check helper
# "az" is a separate program, not a PowerShell command, so PowerShell doesn't notice
# when it fails. $LASTEXITCODE holds the exit code of the last program that ran:
# 0 means success, anything else means failure. Call Assert-Ok after every az command
# so the script stops at the first problem instead of carrying on half-broken.
# -------------------------------------------------------------------------------------
function Assert-Ok($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED at: $step" -ForegroundColor Red
        exit 1
    }
}


# -------------------------------------------------------------------------------------
# The factory's address in Azure
# Every Azure resource has a URL on the management API. We build it once here and
# reuse it for both creating the factory and reading its identity later.
# - $api is the version of the Data Factory REST API we're speaking to.
# - $($DataFactory) needs the $( ) wrapper, otherwise PowerShell would read the "?"
#   that follows as part of the variable name and the URL would break.
# -------------------------------------------------------------------------------------
$api        = "2018-06-01"
$factoryUrl = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.DataFactory/factories/$($DataFactory)?api-version=$api"


# -------------------------------------------------------------------------------------
# Step 1: Point the CLI at the right subscription
# Guarantees everything below is created in YOUR subscription, even if the CLI was
# last used with a different account.
# -------------------------------------------------------------------------------------
Write-Host "1/4 Selecting subscription..."
az account set --subscription $SubscriptionId
Assert-Ok "select subscription"


# -------------------------------------------------------------------------------------
# Step 2: Switch on the Data Factory service for this subscription
# Azure services are enabled per subscription ("resource providers"). On a new
# subscription Data Factory may not be switched on yet, which causes confusing errors
# (like the "Subscription not found" you saw with Storage in Lab 5).
# --wait makes the script pause until registration finishes. If it's already
# registered, this does nothing, so it's safe to re-run.
# -------------------------------------------------------------------------------------
Write-Host "2/4 Registering the Data Factory provider..."
az provider register --namespace Microsoft.DataFactory --wait --output none
Assert-Ok "register Microsoft.DataFactory"


# -------------------------------------------------------------------------------------
# Step 3: Create the Data Factory (only if it doesn't exist yet)
# -------------------------------------------------------------------------------------
Write-Host "3/4 Data Factory $DataFactory..."

# Ask Azure: is there already a factory with this name in our resource group?
# --query filters the list down to just that name; --output tsv returns plain text.
# $existing will hold the name if found, or be empty if not.
$existing = az resource list --resource-group $ResourceGroup --resource-type Microsoft.DataFactory/factories --query "[?name=='$DataFactory'].name" --output tsv
Assert-Ok "list factories"

if ($existing) {
    # Already there: do nothing. This is what makes the script safe to re-run.
    Write-Host "    already exists, leaving it as it is"
} else {
    # Convert the tags into the shape the REST API expects.
    # In the config they're text like "project=rm-copilot" (the format the CLI wants).
    # The REST API wants an object like { "project": "rm-copilot" }.
    # -split "=", 2 cuts each tag at the first "=" into a key ($k) and a value ($v).
    # We also add phase=2 so Cost Management can show what this phase costs.
    $tagObject = @{ phase = "2" }
    foreach ($t in $Tags) { $k, $v = $t -split "=", 2; $tagObject[$k] = $v }

    # Build the request body: where the factory lives, its tags, and its identity.
    # identity.type = SystemAssigned asks Azure to create a managed identity (an ID
    # badge in Microsoft Entra ID) tied to this factory. Microsoft's docs say this
    # only happens automatically in the portal or PowerShell; through the REST API
    # you must ask for it explicitly, which is why it's spelled out here.
    $body = @{
        location = $Location
        identity = @{ type = "SystemAssigned" }
        tags     = $tagObject
    }

    # Write the body to a temporary JSON file for az rest to send.
    # [IO.File]::WriteAllText writes plain UTF-8 without a hidden byte-order mark,
    # which az can choke on (Set-Content in Windows PowerShell adds one).
    $bodyFile = Join-Path $env:TEMP "rm-copilot-factory.json"
    [IO.File]::WriteAllText($bodyFile, ($body | ConvertTo-Json -Depth 5))

    # PUT = "create this resource at this address with this body".
    # The "@" in front of the file path tells az to read the body from that file.
    az rest --method put --url $factoryUrl --body "@$bodyFile" --output none
    Assert-Ok "create data factory"
    Write-Host "    created"
}


# -------------------------------------------------------------------------------------
# Step 4: Let the factory's badge read and write files in the lake
# Same role you gave yourself in Lab 5 (Storage Blob Data Contributor), now given to
# the factory's managed identity. Without it, the factory could see the storage
# account exists but would be refused when touching files in landing or bronze.
# -------------------------------------------------------------------------------------
Write-Host "4/4 Giving the factory Storage Blob Data Contributor on the lake..."

# Read the factory back from Azure and pull out its identity's ID ("principalId").
# This is the unique ID of the badge in Microsoft Entra ID.
$factoryId = az rest --method get --url $factoryUrl --query identity.principalId --output tsv
Assert-Ok "read factory identity"

# If the factory somehow has no identity, stop now with a clear message.
# Giving a role to an empty ID would fail later with a much more confusing error.
if (-not $factoryId) {
    Write-Host "FAILED: the factory has no managed identity" -ForegroundColor Red
    exit 1
}

# Get the full Azure ID of the storage account. This is the "scope": the exact
# thing the permission applies to. Scoping to one storage account (not the whole
# subscription) is least privilege: the factory can touch the lake and nothing else.
$scope = az storage account show --name $StorageAccount --resource-group $ResourceGroup --query id --output tsv
Assert-Ok "look up storage account id"

# Check whether the factory already has this role on this storage account.
$has = az role assignment list --assignee $factoryId --scope $scope --role "Storage Blob Data Contributor" --query "[].id" --output tsv

if ($has) {
    # Already granted: do nothing.
    Write-Host "    already assigned"
} else {
    # Grant the role.
    # --assignee-object-id passes the badge's ID directly, so az doesn't have to
    #   search the directory for it (that lookup can fail for brand-new identities).
    # --assignee-principal-type ServicePrincipal says this is an app/service identity,
    #   not a person (User), which is what Azure calls a managed identity.
    # The backtick ` at the end of the first line means "continues on the next line".
    az role assignment create --assignee-object-id $factoryId --assignee-principal-type ServicePrincipal `
        --role "Storage Blob Data Contributor" --scope $scope --output none
    Assert-Ok "assign data role to the factory"
    Write-Host "    assigned"
}


# -------------------------------------------------------------------------------------
# Finished. Green "Done." means every step above succeeded.
# -------------------------------------------------------------------------------------
Write-Host "Done." -ForegroundColor Green