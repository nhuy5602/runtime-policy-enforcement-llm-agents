param(
    [string]$EndpointId = $(if ($env:RUNPOD_ENDPOINT_ID) { $env:RUNPOD_ENDPOINT_ID } else { "h5ec6v08cb8uc2" }),
    [int]$TimeoutSec = 30,
    [string]$Output = "qa\runpod_endpoint_check.json"
)

if (-not $env:RUNPOD_API_KEY) {
    throw "RUNPOD_API_KEY is not set. Set it in the current PowerShell session; do not paste it into the repository or chat."
}

$headers = @{
    Authorization = "Bearer $env:RUNPOD_API_KEY"
    Accept = "application/json"
}
$baseUrl = "https://api.runpod.ai/v2/$EndpointId/openai/v1"
$healthUrl = "https://api.runpod.ai/v2/$EndpointId/health"

$result = [ordered]@{
    endpoint_id = $EndpointId
    base_url = $baseUrl
    health = $null
    models = $null
    status = "blocked"
    interpretation = $null
}

try {
    $result.health = Invoke-RestMethod -Uri $healthUrl -Headers $headers -Method Get -TimeoutSec $TimeoutSec
} catch {
    $statusCode = $null
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    $result.health = [ordered]@{
        error = "http_or_transport_error"
        http_status = $statusCode
    }
}

try {
    $result.models = Invoke-RestMethod -Uri "$baseUrl/models" -Headers $headers -Method Get -TimeoutSec $TimeoutSec
    $result.status = "ready"
    $result.interpretation = "health_and_openai_models_ok"
} catch {
    $statusCode = $null
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    $result.models = [ordered]@{
        error = "http_or_transport_error"
        http_status = $statusCode
    }
    $readyWorkers = 0
    if ($result.health -and $result.health.workers -and $result.health.workers.ready) {
        $readyWorkers = [int]$result.health.workers.ready
    }
    if ($readyWorkers -gt 0) {
        $result.status = "health_ready_models_unavailable"
        $result.interpretation = "Workers are ready; use the generic /runsync adapter. The endpoint-domain direct route is only for load-balancing endpoints."
    }
}

$json = $result | ConvertTo-Json -Depth 8
$outputPath = Join-Path (Get-Location) $Output
$outputDirectory = Split-Path -Parent $outputPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
Set-Content -LiteralPath $outputPath -Value $json -Encoding UTF8
$json
if ($result.status -eq "blocked") {
    exit 1
}
