# =====================================================================================
# RM Copilot, Phase 2 Lab 7: run the ingest pipeline incrementally, showing every step.
#
# The watermark is a timestamp saved in bronze/_control/watermark.txt.
# It means: "every file that landed BEFORE this moment has already been copied."
#
#   windowStart = the saved watermark      (where the last successful run ended)
#   windowEnd   = now                      (where this run ends)
#   The pipeline copies only files whose Last modified time is inside that window.
#   Every run writes one line per table to bronze/_audit/ingest_log.csv (Lab 7.2).
#   If the run succeeds, windowEnd is saved as the new watermark.
#   If it fails, the watermark stays put, so the next run retries the same window.
# =====================================================================================


# -------------------------------------------------------------------------------------
# Setup: load settings and the "stop on failure" helper
# -------------------------------------------------------------------------------------
. "$PSScriptRoot\00_config.ps1"

function Assert-Ok($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED at: $step" -ForegroundColor Red
        exit 1
    }
}

az account set --subscription $SubscriptionId
Assert-Ok "select subscription"

# The factory's address on the management API, and where the watermark file lives.
$api        = "2018-06-01"
$factoryUrl = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.DataFactory/factories/$DataFactory"
$markBlob   = "_control/watermark.txt"
$markFile   = Join-Path $env:TEMP "rm-copilot-watermark.txt"

# Used only the very first time, before any watermark file exists:
# the moment of the first full load in Lab 6 (11 Nov 2026, 19:32 SAST = 17:32 UTC).
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
# STEP 2: Work out this run's window (watermark -> now)
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 2  Work out the window" -ForegroundColor Cyan

$windowEnd = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
Write-Host "        windowStart = $windowStart   (the watermark)"
Write-Host "        windowEnd   = $windowEnd   (now, in UTC)"
Write-Host "        Rule: copy only files that landed between these two moments."


# -------------------------------------------------------------------------------------
# STEP 3: Start the pipeline, passing it the window
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
# STEP 5: Ask Data Factory what each Copy activity did
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 5  What did it copy?" -ForegroundColor Cyan

# queryActivityruns needs a time range to search in; a day either side is plenty.
$queryFile = Join-Path $env:TEMP "rm-copilot-query.json"
$from = (Get-Date).ToUniversalTime().AddDays(-1).ToString("yyyy-MM-ddTHH:mm:ssZ")
$to   = (Get-Date).ToUniversalTime().AddDays(1).ToString("yyyy-MM-ddTHH:mm:ssZ")
[IO.File]::WriteAllText($queryFile, (@{ lastUpdatedAfter = $from; lastUpdatedBefore = $to } | ConvertTo-Json))

$acts = az rest --method post --url "$factoryUrl/pipelineruns/$runId/queryActivityruns?api-version=$api" `
        --body "@$queryFile" | Out-String | ConvertFrom-Json

# Keep only the six Copy activities (the list also contains the ForEach itself).
$copies = $acts.value | Where-Object { $_.activityType -eq "Copy" }

$total = 0
foreach ($c in $copies) { $total += [int]$c.output.filesWritten }
Write-Host "        Copy activities run: $($copies.Count)"
Write-Host "        Files copied to bronze: $total"


# -------------------------------------------------------------------------------------
# STEP 5b: Write the audit log, one line per table (runs even if the pipeline failed)
#
# The log lives at bronze/_audit/ingest_log.csv, next to the watermark.
#   watermark.txt   answers "where did the last run end?"
#   ingest_log.csv  answers "what did every run actually do, table by table?"
# -------------------------------------------------------------------------------------
Write-Host ""
Write-Host "STEP 5b Write the audit log" -ForegroundColor Cyan

$auditBlob = "_audit/ingest_log.csv"
$auditFile = Join-Path $env:TEMP "rm-copilot-audit.csv"
$loggedAt  = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

# Turn each Copy activity's result into one tidy row.
# - userProperties.table is the label pinned on each copy in the pipeline JSON.
# - output.filesWritten / dataWritten are Data Factory's own counts.
#   On a run that copied nothing these can be missing, so [long] turns "nothing" into 0.
$rows = foreach ($c in $copies) {
    [pscustomobject]@{
        run_id        = $runId
        table         = $c.userProperties.table
        window_start  = $windowStart
        window_end    = $windowEnd
        run_status    = $status
        copy_status   = $c.status
        files_read    = [long]$c.output.filesRead
        files_written = [long]$c.output.filesWritten
        bytes_written = [long]$c.output.dataWritten
        duration_sec  = ($c.durationInMs / 1000).ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
        logged_at     = $loggedAt
    }
}

# Show it on screen so you can see exactly what's being logged.
$rows | Sort-Object table |
    Format-Table table, copy_status, files_read, files_written, bytes_written, duration_sec -AutoSize |
    Out-String | Write-Host

# Get the existing log from the lake. On the very first run there isn't one yet,
# so start a new file that contains only the header row (the column names).
$auditExists = az storage blob exists --account-name $StorageAccount --container-name bronze `
               --name $auditBlob --auth-mode login --query exists --output tsv
Assert-Ok "check audit log"

if ($auditExists -eq "true") {
    az storage blob download --account-name $StorageAccount --container-name bronze `
        --name $auditBlob --file $auditFile --auth-mode login --overwrite --output none
    Assert-Ok "download audit log"
} else {
    $header = ($rows | Select-Object -First 1 | ConvertTo-Csv)[0]
    [IO.File]::WriteAllText($auditFile, $header + "`n")
    Write-Host "        No audit log yet. Starting a new one."
}

# Add this run's rows to the end of the file (data lines only, no header),
# then upload the whole file back, replacing the old version.
$lines = $rows | Sort-Object table | ConvertTo-Csv | Select-Object -Skip 1
Add-Content -Path $auditFile -Value $lines
az storage blob upload --account-name $StorageAccount --container-name bronze `
    --name $auditBlob --file $auditFile --auth-mode login --overwrite --output none
Assert-Ok "save audit log"

Write-Host "        Logged $($rows.Count) rows to bronze/$auditBlob"


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