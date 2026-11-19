# Deploy CloudCommerce to Kubernetes Cluster
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  DEPLOYING CLOUDCOMMERCE TO KUBERNETES CLUSTER & MONITORING" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan

# Check cluster connectivity
kubectl get nodes 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[Action Required] Your Kubernetes cluster is not yet running." -ForegroundColor Yellow
    Write-Host "Please start your cluster using ONE of these options:" -ForegroundColor Cyan
    Write-Host "  1. Docker Desktop: Open Docker Desktop -> Settings -> Kubernetes -> Enable Kubernetes -> Apply" -ForegroundColor White
    Write-Host "  2. Kind: Run: kind create cluster --name k8s-ecommerce" -ForegroundColor White
    Write-Host "  3. Minikube: Run: minikube start" -ForegroundColor White
    Write-Host "`nOnce started, re-run this script: .\scripts\deploy_ecommerce.ps1" -ForegroundColor Green
    exit 1
}

Write-Host "`n[Step 1] Building Docker Image: k8s-resource-demo:latest..." -ForegroundColor Cyan
docker build -t k8s-resource-demo:latest ./app

# Kind or Minikube image sync if applicable
$contexts = kubectl config current-context
if ($contexts -match "kind") {
    Write-Host "Loading image into Kind cluster..." -ForegroundColor Yellow
    kind load docker-image k8s-resource-demo:latest --name ($contexts -replace "kind-","")
} elseif ($contexts -match "minikube") {
    Write-Host "Loading image into Minikube..." -ForegroundColor Yellow
    minikube image load k8s-resource-demo:latest
}

Write-Host "`n[Step 2] Applying Kubernetes Manifests..." -ForegroundColor Cyan
kubectl apply -f ./k8s/ecommerce-app.yaml

Write-Host "`n[Step 3] Waiting for Pods to be Ready..." -ForegroundColor Cyan
kubectl rollout status deployment/ecommerce-web -n k8s-resource-lab --timeout=90s

Write-Host "`n[Step 4] Pods & Services Status:" -ForegroundColor Yellow
kubectl get pods -n k8s-resource-lab -o wide
kubectl get svc -n k8s-resource-lab

Write-Host "`n==================================================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "To open the application and monitoring dashboard, run:" -ForegroundColor Magenta
Write-Host "kubectl port-forward svc/ecommerce-svc 8080:8080 -n k8s-resource-lab" -ForegroundColor White
Write-Host "Then open your browser at: http://localhost:8080" -ForegroundColor White
Write-Host "Or if using NodePort on Docker Desktop: http://localhost:30080" -ForegroundColor White
