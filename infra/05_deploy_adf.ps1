# =====================================================================================
# RM Copilot, Phase 2 Lab 6: deploy Data Factory building blocks from the adf/ folder.
#
# Reads every JSON file under adf/ and pushes it to the factory, in dependency order:
#   1. linkedService  (the address book: how to reach the lake)
#   2. dataset        (the exact shelves: which folder, what shape)
#   3. pipeline       (the run sheet: what to copy, in what order)
# Order matters: a dataset points at a linked service, and a pipeline points at
# datasets, so each must exist before the thing that uses it.
#
# Safe to re-run: PUT means "make it look exactly like this file". If it already
# exists it's updated to match; if it's unchanged nothing really changes.
# =====================================================================================


# Load settings ($SubscriptionId, $ResourceGroup, $DataFactory, $StorageAccount...).
. "$PSScriptRoot\00_config.ps1"

# Stop at the first failed az command (same helper as the other scripts).
function Assert-Ok($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED at: $step" -ForegroundColor Red
        exit 1
    }
}

# Make sure we're deploying into the right subscription.
az account set --subscription $SubscriptionId
Assert-Ok "select subscription"

# The factory's address on the Azure management API. Every building block lives
# underneath it, e.g. .../factories/<name>/linkedservices/ls_adls_rmcopilot
$api  = "2018-06-01"
$base = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.DataFactory/factories/$DataFactory"

# Folder name in our repo  ->  the word the REST API uses in the URL.
$kinds = [ordered]@{
    linkedService = "linkedservices"
    dataset       = "datasets"
    pipeline      = "pipelines"
}

foreach ($kind in $kinds.Keys) {
    $folder = Join-Path $PSScriptRoot "..\adf\$kind"

    # Skip kinds we haven't written yet (e.g. no pipelines in Step 3).
    if (-not (Test-Path $folder)) { continue }

    Write-Host "Deploying $kind..."
    foreach ($file in Get-ChildItem $folder -Filter *.json) {
        # The file name (without .json) becomes the building block's name in the factory.
        $name = $file.BaseName

        # Read the JSON and swap the {{StorageAccount}} placeholder for the real name,
        # so the real name lives only in your local config, never in GitHub.
        $json = (Get-Content $file.FullName -Raw).Replace("{{StorageAccount}}", $StorageAccount)

        # Write the filled-in JSON to a temp file (UTF-8, no hidden byte-order mark).
        $tmp = Join-Path $env:TEMP "adf-$name.json"
        [IO.File]::WriteAllText($tmp, $json)

        # PUT it to the factory: create it, or update it to match the file.
        az rest --method put --url "$base/$($kinds[$kind])/$($name)?api-version=$api" --body "@$tmp" --output none
        Assert-Ok "deploy $kind $name"
        Write-Host "    $name deployed"
    }
}

Write-Host "Done." -ForegroundColor Green