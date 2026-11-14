# =====================================================================================
# RM Copilot, Phase 2 Lab 7: run the ingest pipeline incrementally, showing every step.
#
# The watermark is a timestamp saved in bronze/_control/watermark.txt.
# It means: "every file that landed BEFORE this moment has already been copied."
#
#   windowStart = the saved watermark      (where the last successful run ended)
#   windowEnd   = now                      (where this run ends)
#   The pipeline copies only files whose Last modified time is inside that window.
#   If the run succeeds, windowEnd is saved as the new watermark.
#   If it fails, the watermark stays put, so the next run retries the same window.
# =====================================================================================

. "$PSScriptRoot\00_config.ps1"

function Assert-Ok($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED at: $step" -ForegroundColor Red
        exit 1
    }
}

az account set --subscription $SubscriptionId
Assert-Ok "select subscription"

$api          = "2018-06-01"
$factoryUrl   = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.DataFactory/factories/$DataFactory"
$markBlob     = "_control/watermark.txt"
$markFile     = Join-Path $env:TEMP "rm-copilot-watermark.txt"

# Used only the very first time, before any watermark file exists:
# the moment of your first full load in Lab 6 (11 Nov 2026, 19:32 SAST = 17:32 UTC).
$firstWatermark = "2026-11-11T17:32:00Z"


# -------------------------------------------------------------------------------------
# STEP 1: Read the watermark (where did the last successful run end?)
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 1  Read the watermark" -ForegroundColor Cyan
$exists = az storage blob exists --account-name $StorageAccount --container-name bronze `
          --name $markBlob --auth-mode login --query exists --output tsv
Assert-Ok "check watermark file"

if ($exists -eq "true") {
    az storage blob download --account-name $StorageAccount --container-name bronze `
        --name $markBlob --file $markFile --auth-mode login --overwrite --output none
    Assert-Ok "download watermark"
    $windowStart = (Get-Content $markFile -Raw).Trim()
    Write-Host "        Found watermark file. Last successful run ended at: $windowStart"
} else {
    $windowStart = $firstWatermark
    Write-Host "        No watermark file yet (first incremental run)."
    Write-Host "        Starting from the Lab 6 full load: $windowStart"
}


# -------------------------------------------------------------------------------------
# STEP 2: Work out this run's window
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 2  Work out the window" -ForegroundColor Cyan
$windowEnd = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
Write-Host "        windowStart = $windowStart   (the watermark)"
Write-Host "        windowEnd   = $windowEnd   (now, in UTC)"
Write-Host "        Rule: copy only files that landed between these two moments."


# -------------------------------------------------------------------------------------
# STEP 3: Start the pipeline with that window
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 3  Start the pipeline" -ForegroundColor Cyan
$bodyFile = Join-Path $env:TEMP "rm-copilot-run.json"
[IO.File]::WriteAllText($bodyFile, (@{ windowStart = $windowStart; windowEnd = $windowEnd } | ConvertTo-Json))
$runId = az rest --method post --url "$factoryUrl/pipelines/pl_ingest_bank/createRun?api-version=$api" `
         --body "@$bodyFile" --query runId --output tsv
Assert-Ok "start pipeline"
Write-Host "        Run started. runId = $runId"


# -------------------------------------------------------------------------------------
# STEP 4: Wait for it to finish (check every 10 seconds)
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 4  Wait for the run to finish" -ForegroundColor Cyan
do {
    Start-Sleep -Seconds 10
    $status = az rest --method get --url "$factoryUrl/pipelineruns/$($runId)?api-version=$api" --query status --output tsv
    Write-Host "        status: $status"
} while ($status -in @("Queued", "InProgress", "Canceling"))


# -------------------------------------------------------------------------------------
# STEP 5: Count what was copied (add up "files written" across the six Copy activities)
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 5  What did it copy?" -ForegroundColor Cyan
$queryFile = Join-Path $env:TEMP "rm-copilot-query.json"
$from = (Get-Date).ToUniversalTime().AddDays(-1).ToString("yyyy-MM-ddTHH:mm:ssZ")
$to   = (Get-Date).ToUniversalTime().AddDays(1).ToString("yyyy-MM-ddTHH:mm:ssZ")
[IO.File]::WriteAllText($queryFile, (@{ lastUpdatedAfter = $from; lastUpdatedBefore = $to } | ConvertTo-Json))
$acts = az rest --method post --url "$factoryUrl/pipelineruns/$runId/queryActivityruns?api-version=$api" `
        --body "@$queryFile" | Out-String | ConvertFrom-Json
$copies = $acts.value | Where-Object { $_.activityType -eq "Copy" }
$total = 0
foreach ($c in $copies) { $total += [int]$c.output.filesWritten }
Write-Host "        Copy activities run: $($copies.Count)"
Write-Host "        Files copied to bronze: $total"


# -------------------------------------------------------------------------------------
# STEP 6: Move the watermark, but ONLY if the run succeeded
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 6  Update the watermark" -ForegroundColor Cyan
if ($status -eq "Succeeded") {
    [IO.File]::WriteAllText($markFile, $windowEnd)
    az storage blob upload --account-name $StorageAccount --container-name bronze `
        --name $markBlob --file $markFile --auth-mode login --overwrite --output none
    Assert-Ok "save watermark"
    Write-Host "        Run succeeded. Watermark moved: $windowStart  ->  $windowEnd" -ForegroundColor Green
    Write-Host "        Next run will start from $windowEnd."
} else {
    Write-Host "        Run ended as '$status'. Watermark NOT moved; it stays at $windowStart." -ForegroundColor Red
    Write-Host "        Next run will retry the same window, so no files are skipped."
    exit 1
}