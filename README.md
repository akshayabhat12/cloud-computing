# Kubernetes Resource Allocation and Optimization

**Course / Lab**: Cloud Computing Lab Evaluation – 2  
**Institution**: KLE Technological University  
**Topic**: Problem 01 — Kubernetes & Microservices Deployment  

---

## 📌 Problem Overview

Deploy a web application on Kubernetes and configure CPU and memory requests and limits for its pods. Examine how different resource configurations affect pod execution, CPU CFS quota throttling, application latency, and stability (OOMKilled events and pod restarts).

### Core Questions Addressed
1. What happens when a container exceeds its CPU limit? (CFS Quota Throttling vs Crash)
2. What happens when a container exceeds its Memory limit? (Linux cgroup OOM Killer vs Restarts)
3. How do CPU limits affect end-user application response time and throughput?
4. How does Kubernetes assign Quality of Service (QoS) classes (`Guaranteed`, `Burstable`, `BestEffort`)?

---

## 🏗️ Repository Architecture

```text
cloud computing/
├── app/
│   ├── app.py                 # Telemetry & stress-testing REST API + Web Dashboard
│   ├── requirements.txt       # Flask & psutil dependencies
│   ├── Dockerfile             # Container definition (non-root, production-ready)
│   └── templates/
│       └── index.html         # Live telemetry dashboard with real-time gauges
├── k8s/
│   ├── 00-namespace.yaml      # Dedicated namespace (k8s-resource-lab)
│   ├── service.yaml           # ClusterIP + NodePort (30080) service
│   ├── 01-scenario-optimal.yaml        # Scenario 1: Balanced (Burstable)
│   ├── 02-scenario-cpu-throttling.yaml # Scenario 2: Low CPU (CFS Throttling)
│   ├── 03-scenario-memory-oom.yaml     # Scenario 3: Low Memory (OOMKilled)
│   ├── 04-scenario-unconstrained.yaml  # Scenario 4: No Limits (BestEffort)
│   └── 05-scenario-guaranteed-qos.yaml # Scenario 5: Requests == Limits (Guaranteed)
├── scripts/
│   ├── benchmark_cpu.py       # Latency benchmark measuring response time (ms)
│   ├── trigger_oom.py         # Memory breach injector testing pod crash & restarts
│   ├── deploy_scenario.ps1    # Interactive PowerShell scenario deployer
│   ├── deploy_scenario.sh     # Interactive Bash scenario deployer
│   └── run_all_experiments.ps1# End-to-end automated experiment runner
├── README.md                  # Quickstart guide
├── LAB_REPORT.md              # Complete University Lab Report submission
└── VIVA_QUESTIONS.md          # 15+ In-depth Viva Voce Questions & Answers
```

---

## 🚀 Step-by-Step Setup and Execution

### Step 1: Start Docker and Kubernetes Cluster
Ensure your local Kubernetes cluster is running:
- **Docker Desktop**: Open Docker Desktop, navigate to `Settings -> Kubernetes`, check `Enable Kubernetes`, and click `Apply & restart`.
- **OR Minikube**: `minikube start --cpus=2 --memory=3072`
- **OR Kind**: `kind create cluster --name k8s-lab`

Verify cluster readiness:
```powershell
kubectl get nodes
```

---

### Step 2: Build the Container Image
From the workspace root directory:
```powershell
docker build -t k8s-resource-demo:latest ./app
```

> **Note for Minikube / Kind users**:  
> If using Minikube: run `minikube image load k8s-resource-demo:latest`  
> If using Kind: run `kind load docker-image k8s-resource-demo:latest --name k8s-lab`

---

### Step 3: Run the Experiments

#### Option A: One-Click Automated Suite
Run the full test suite in PowerShell:
```powershell
.\scripts\run_all_experiments.ps1
```

#### Option B: Step-by-Step Interactive Scenarios

#### Scenario 1: Optimal Resource Allocation (Baseline)
```powershell
# Deploy scenario 1
.\scripts\deploy_scenario.ps1 -Scenario 1

# Start port-forward in a separate terminal
kubectl port-forward svc/resource-demo-svc 8080:8080 -n k8s-resource-lab

# Open web dashboard: http://localhost:8080
# Run CPU latency benchmark:
python ./scripts/benchmark_cpu.py "http://localhost:8080" 25 5
```
*Expected Result*: Latency is very low (~30-50ms), Pod is healthy, 0 restarts.

---

#### Scenario 2: CPU Constrained (CFS Quota Throttling)
```powershell
# Deploy scenario 2
.\scripts\deploy_scenario.ps1 -Scenario 2

# Run CPU latency benchmark:
python ./scripts/benchmark_cpu.py "http://localhost:8080" 25 5
```
*Expected Result*: Latency spikes dramatically (~300ms-600ms+) due to kernel CFS throttling. The pod **does not crash** (Restarts = 0).

---

#### Scenario 3: Memory Constrained (OOMKilled & Restarts)
```powershell
# Deploy scenario 3
.\scripts\deploy_scenario.ps1 -Scenario 3

# Inject memory stress to exceed the 90Mi limit:
python ./scripts/trigger_oom.py "http://localhost:8080" 120
```
*Expected Result*: The container breaches the 90Mi memory limit. The Linux kernel terminates the process with `OOMKilled (Exit Code 137)`. Kubernetes restarts the container, incrementing the `RESTARTS` counter!

---

### Step 4: Inspect Live Resource Usage with Metrics
To view real-time resource utilization:
```powershell
kubectl top pod -n k8s-resource-lab
kubectl top node
kubectl describe pod -l app=resource-demo -n k8s-resource-lab
```

---

## 📊 Summary of Experimental Results

| Metric / Scenario | Scenario 1 (Optimal) | Scenario 2 (CPU Throttled) | Scenario 3 (Memory OOM) | Scenario 4 (Unconstrained) | Scenario 5 (Guaranteed) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CPU Request / Limit** | 100m / 400m | 50m / 75m | 100m / 300m | None / None | 250m / 250m |
| **Memory Request / Limit**| 128Mi / 256Mi | 128Mi / 256Mi | 64Mi / 90Mi | None / None | 256Mi / 256Mi |
| **QoS Class** | `Burstable` | `Burstable` | `Burstable` | `BestEffort` | `Guaranteed` |
| **Average Latency (ms)** | ~35 ms | **~380 ms** (Throttled) | ~40 ms | ~30 ms | ~32 ms |
| **Pod Restarts** | 0 | 0 | **1+ (OOMKilled 137)**| 0 (unless node OOM) | 0 |
| **Application Stability** | Excellent | Degraded Latency | Crashes under load | High risk of eviction| Maximum priority |
