param(
    [string]$EndpointId = $(if ($env:RUNPOD_ENDPOINT_ID) { $env:RUNPOD_ENDPOINT_ID } else { "h5ec6v08cb8uc2" }),
    [string]$Model = $env:RUNPOD_MODEL,
    [ValidateSet("openai", "direct", "runsync")]
    [string]$Transport = "openai",
    [int]$MaxCases = 1,
    [int]$MaxOutputTokens = 2048,
    [int]$TimeoutSec = 300,
    [switch]$ConfirmBillable
)

if (-not $env:RUNPOD_API_KEY) {
    throw "RUNPOD_API_KEY is not set. Set it in the current PowerShell session; do not paste it into the repository or chat."
}
if (-not $ConfirmBillable) {
    Write-Host "This command will submit model completions and may incur Runpod charges."
    Write-Host "Re-run with -ConfirmBillable after the endpoint health/models check passes."
    exit 2
}

$headers = @{
    Authorization = "Bearer $env:RUNPOD_API_KEY"
    Accept = "application/json"
}
$manifestPath = Join-Path $PSScriptRoot "..\experiments\runpod_endpoint_manifest.json"
$manifest = $null
if (Test-Path -LiteralPath $manifestPath) {
    try {
        $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    } catch {
        $manifest = $null
    }
}
if ($Transport -eq "runsync") {
    $baseUrl = "https://api.runpod.ai/v2/$EndpointId"
    if (-not $Model) {
        $Model = "Qwen/Qwen3-8B"
    }
} elseif ($Transport -eq "direct") {
    if (
        $manifest -and
        $manifest.endpoint_id -eq $EndpointId -and
        $manifest.endpoint_type -eq "serverless_queue"
    ) {
        throw "Endpoint $EndpointId is a serverless queue. The direct endpoint-domain URL is for Runpod load-balancing endpoints; use -Transport openai or -Transport runsync."
    }
    $baseUrl = "https://$EndpointId.api.runpod.ai/v1"
    if (-not $Model) {
        $models = Invoke-RestMethod -Uri "$baseUrl/models" -Headers $headers -Method Get -TimeoutSec 60
        $Model = @($models.data)[0].id
    }
    if (-not $Model) {
        $diagnostic = Join-Path $PSScriptRoot "..\qa\runpod_direct_models.json"
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $diagnostic) | Out-Null
        $models | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $diagnostic -Encoding UTF8
        throw "The direct endpoint returned no model id. Set RUNPOD_MODEL explicitly. Diagnostic: $diagnostic"
    }
} else {
    $baseUrl = "https://api.runpod.ai/v2/$EndpointId/openai/v1"
    if (-not $Model) {
        $models = Invoke-RestMethod -Uri "$baseUrl/models" -Headers $headers -Method Get -TimeoutSec 60
        $Model = @($models.data)[0].id
    }
    if (-not $Model) {
        throw "The endpoint returned no model id. Set RUNPOD_MODEL explicitly after the worker becomes ready."
    }
}

$runner = Join-Path $PSScriptRoot "..\experiments\openai_trace_runner.py"
$output = Join-Path $PSScriptRoot "..\experiments\live_trace_runpod_$($EndpointId)_$($Transport).json"

Write-Host "Submitting $MaxCases case(s) to Runpod endpoint $EndpointId using model $Model."
$apiStyle = if ($Transport -eq "runsync") { "runpod" } else { "chat" }
& python $runner `
    --api-style $apiStyle `
    --base-url $baseUrl `
    --model $Model `
    --max-cases $MaxCases `
    --seed 20260926 `
    --temperature 0 `
    --top-p 1 `
    --max-output-tokens $MaxOutputTokens `
    --timeout $TimeoutSec `
    --output $output

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "Trace written to $output"
