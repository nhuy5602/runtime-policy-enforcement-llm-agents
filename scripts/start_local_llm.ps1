param(
    [string]$Model = "Qwen/Qwen3-4B-GGUF:Q4_K_M",
    [string]$ModelPath = "",
    [int]$Port = 8080,
    [int]$Context = 8192,
    [int]$Threads = 8,
    [int]$ReasoningBudget = 0
)

$server = Get-Command llama-server -ErrorAction SilentlyContinue
if ($server) {
    $serverPath = $server.Source
} else {
    $serverPath = Get-ChildItem `
        -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" `
        -Filter "llama-server.exe" -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}

if (-not $serverPath) {
    throw "llama-server.exe was not found. Install ggml.llamacpp with winget first."
}

$modelArgs = if ($ModelPath) {
    @("-m", $ModelPath)
} else {
    @("-hf", $Model)
}

& $serverPath `
    @modelArgs `
    --host 127.0.0.1 `
    --port $Port `
    --jinja `
    -c $Context `
    -t $Threads `
    --reasoning-budget $ReasoningBudget `
    --metrics
