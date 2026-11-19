param (
    [Parameter(Mandatory=$false)]
    [ValidateSet("1", "2", "3", "4", "5", "optimal", "cpu", "memory", "unconstrained", "guaranteed")]
    [string]$Scenario = "1"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " KUBERNETES RESOURCE ALLOCATION LAB - SCENARIO DEPLOYER" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# Ensure namespace exists
kubectl apply -f ../k8s/00-namespace.yaml 2>$null
if ($LASTEXITCODE -ne 0) {
    kubectl apply -f ./k8s/00-namespace.yaml
}

# Ensure service is deployed
kubectl apply -f ../k8s/service.yaml 2>$null
if ($LASTEXITCODE -ne 0) {
    kubectl apply -f ./k8s/service.yaml
}

$fileToApply = ""
$scenarioDesc = ""

switch ($Scenario) {
    { $_ -in "1", "optimal" } {
        $fileToApply = "k8s/01-scenario-optimal.yaml"
        $scenarioDesc = "Scenario 1: Optimal & Balanced (CPU: 100m/400m, Mem: 128Mi/256Mi, QoS: Burstable)"
    }
    { $_ -in "2", "cpu" } {
        $fileToApply = "k8s/02-scenario-cpu-throttling.yaml"
        $scenarioDesc = "Scenario 2: CPU Constrained (CPU: 50m/75m, Mem: 128Mi/256Mi, Demonstrates CFS Throttling)"
    }
    { $_ -in "3", "memory" } {
        $fileToApply = "k8s/03-scenario-memory-oom.yaml"
        $scenarioDesc = "Scenario 3: Memory Constrained (CPU: 100m/300m, Mem: 64Mi/90Mi, Demonstrates OOMKill)"
    }
    { $_ -in "4", "unconstrained" } {
        $fileToApply = "k8s/04-scenario-unconstrained.yaml"
        $scenarioDesc = "Scenario 4: Unconstrained (No requests/limits, QoS: BestEffort)"
    }
    { $_ -in "5", "guaranteed" } {
        $fileToApply = "k8s/05-scenario-guaranteed-qos.yaml"
        $scenarioDesc = "Scenario 5: Guaranteed QoS (Requests == Limits: CPU 250m, Mem 256Mi)"
    }
}

Write-Host "[Deploying] $scenarioDesc" -ForegroundColor Green
if (Test-Path "../$fileToApply") {
    kubectl apply -f "../$fileToApply"
} else {
    kubectl apply -f "./$fileToApply"
}

Write-Host "`nWaiting for pod rollout to complete..." -ForegroundColor Cyan
kubectl rollout status deployment/resource-demo -n k8s-resource-lab --timeout=60s

Write-Host "`n[Current Pods]:" -ForegroundColor Yellow
kubectl get pods -n k8s-resource-lab -o wide

Write-Host "`nTo open the interactive Web Dashboard in browser, run in a separate terminal:" -ForegroundColor Magenta
Write-Host "kubectl port-forward svc/resource-demo-svc 8080:8080 -n k8s-resource-lab" -ForegroundColor White
Write-Host "Then visit: http://localhost:8080`n" -ForegroundColor White
