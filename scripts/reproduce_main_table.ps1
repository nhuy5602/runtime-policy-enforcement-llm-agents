$ErrorActionPreference = "Stop"

python experiments/policy_guard_sim.py --self-test `
  --output experiments/policy_guard_sim_results.json
if ($LASTEXITCODE -ne 0) {
  throw "policy_guard_sim.py failed with exit code $LASTEXITCODE"
}

python experiments/offline_benchmark_harness.py --self-test `
  --output-dir experiments/benchmark_outputs `
  --seed 20260926 `
  --bootstrap 1000
if ($LASTEXITCODE -ne 0) {
  throw "offline_benchmark_harness.py failed with exit code $LASTEXITCODE"
}

python -m compileall -q experiments scripts
if ($LASTEXITCODE -ne 0) {
  throw "compileall failed with exit code $LASTEXITCODE"
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$gitCheck = & git diff --check 2>&1
$ErrorActionPreference = $previousErrorActionPreference
$gitExit = $LASTEXITCODE
$gitCheck | ForEach-Object { Write-Host $_ }
if ($gitExit -ne 0) {
    throw "git diff --check failed with exit code $gitExit"
}

Write-Host "Reproduction self-test passed. Live LLM efficacy cells remain pending."
