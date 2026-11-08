# RM Copilot, Phase 2 Lab 5: ADLS Gen2 storage account, four containers, data access for you.
# Safe to re-run: every step either creates the thing or leaves it as it is.

. "$PSScriptRoot\00_config.ps1"

function Assert-Ok($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED at: $step" -ForegroundColor Red
        exit 1
    }
}

Write-Host "1/5 Selecting subscription..."
az account set --subscription $SubscriptionId
Assert-Ok "select subscription"

Write-Host "2/5 Registering the Storage provider..."
az provider register --namespace Microsoft.Storage --wait --output none
Assert-Ok "register Microsoft.Storage"

Write-Host "3/5 Storage account $StorageAccount..."
$existing = az storage account list --resource-group $ResourceGroup --query "[?name=='$StorageAccount'].name" --output tsv
Assert-Ok "list storage accounts"
if ($existing) {
    Write-Host "    already exists, leaving it as it is"
} else {
    az storage account create `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku Standard_LRS `
        --kind StorageV2 `
        --enable-hierarchical-namespace true `
        --min-tls-version TLS1_2 `
        --allow-blob-public-access false `
        --tags $Tags "phase=2" `
        --output none
    Assert-Ok "create storage account"
    Write-Host "    created"
}

Write-Host "4/5 Containers..."
foreach ($c in $Containers) {
    az storage container-rm create --storage-account $StorageAccount --resource-group $ResourceGroup --name $c --output none
    Assert-Ok "create container $c"
    Write-Host "    $c ok"
}

Write-Host "5/5 Giving you Storage Blob Data Contributor..."
$me    = az ad signed-in-user show --query id --output tsv
Assert-Ok "look up your user id"
$scope = az storage account show --name $StorageAccount --resource-group $ResourceGroup --query id --output tsv
Assert-Ok "look up storage account id"
$has   = az role assignment list --assignee $me --scope $scope --role "Storage Blob Data Contributor" --query "[].id" --output tsv
if ($has) {
    Write-Host "    already assigned"
} else {
    az role assignment create --assignee-object-id $me --assignee-principal-type User `
        --role "Storage Blob Data Contributor" --scope $scope --output none
    Assert-Ok "assign data role"
    Write-Host "    assigned (can take a few minutes to take effect)"
}

Write-Host "Done." -ForegroundColor Green