# Automated Full Experiment Runner for Lab Evaluation
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " KLE TECH CLOUD COMPUTING LAB EVALUATION 2: AUTOMATED RUNNER" -ForegroundColor Yellow
Write-Host " Problem 01: Kubernetes Resource Allocation and Optimization" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check prerequisites
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Error "kubectl is not installed or not in PATH."
    exit 1
}

# 2. Deploy Namespace & Service
Write-Host "`n[Setup] Deploying Namespace and Service..." -ForegroundColor Cyan
kubectl apply -f ./k8s/00-namespace.yaml
kubectl apply -f ./k8s/service.yaml

# 3. Experiment A: Optimal Scenario Benchmark
Write-Host "`n-----------------------------------------------------------------" -ForegroundColor Magenta
Write-Host " EXPERIMENT 1: BASELINE / OPTIMAL CONFIGURATION (Burstable QoS)" -ForegroundColor Magenta
Write-Host "-----------------------------------------------------------------" -ForegroundColor Magenta
kubectl apply -f ./k8s/01-scenario-optimal.yaml
kubectl rollout status deployment/resource-demo -n k8s-resource-lab --timeout=60s

Write-Host "`nStarting Port-Forward in background on port 8080..." -ForegroundColor Cyan
$pf = Start-Process -FilePath "kubectl" -ArgumentList "port-forward svc/resource-demo-svc 8080:8080 -n k8s-resource-lab" -PassThru
Start-Sleep -Seconds 4

Write-Host "Running Benchmark against Optimal Pod..." -ForegroundColor Green
python ./scripts/benchmark_cpu.py "http://localhost:8080" 20 4

# 4. Experiment B: CPU Throttling
Write-Host "`n-----------------------------------------------------------------" -ForegroundColor Magenta
Write-Host " EXPERIMENT 2: CPU CONSTRAINED CONFIGURATION (CFS Throttling)" -ForegroundColor Magenta
Write-Host "-----------------------------------------------------------------" -ForegroundColor Magenta
kubectl apply -f ./k8s/02-scenario-cpu-throttling.yaml
kubectl rollout status deployment/resource-demo -n k8s-resource-lab --timeout=60s
Start-Sleep -Seconds 3

Write-Host "Running Benchmark against CPU-Throttled Pod..." -ForegroundColor Yellow
python ./scripts/benchmark_cpu.py "http://localhost:8080" 20 4

# 5. Experiment C: Memory OOMKill & Pod Restarts
Write-Host "`n-----------------------------------------------------------------" -ForegroundColor Magenta
Write-Host " EXPERIMENT 3: MEMORY CONSTRAINED CONFIGURATION (OOMKilled Test)" -ForegroundColor Magenta
Write-Host "-----------------------------------------------------------------" -ForegroundColor Magenta
kubectl apply -f ./k8s/03-scenario-memory-oom.yaml
kubectl rollout status deployment/resource-demo -n k8s-resource-lab --timeout=60s
Start-Sleep -Seconds 3

Write-Host "Triggering Memory Stress to exceed container limit (90MiB limit vs 120MiB allocation)..." -ForegroundColor Red
python ./scripts/trigger_oom.py "http://localhost:8080" 120

# Cleanup port forward
if ($pf -and -not $pf.HasExited) {
    Stop-Process -Id $pf.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host " ALL EXPERIMENTS COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host " Refer to LAB_REPORT.md for documentation and graphs." -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan
