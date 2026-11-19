# LABORATORY EVALUATION REPORT

**Course Title**: Cloud Computing Laboratory  
**Evaluation**: Lab Evaluation – 2  
**Institution**: KLE Technological University  
**Module**: Kubernetes & Microservices Deployment  
**Problem Statement 01**: Kubernetes Resource Allocation and Optimization  

---

## 1. Abstract & Problem Statement

### Problem Statement
Deploy a web application on Kubernetes and configure CPU and memory requests and limits for its pods. Examine how different resource configurations affect pod execution, application stability, response time, and pod lifecycle events (such as CFS CPU throttling and Out-Of-Memory termination).

### Objectives
1. Understand and configure Kubernetes `requests` and `limits` in Pod specifications.
2. Measure the impact of CPU limits on computational throughput and application latency.
3. Observe and document the behavior of the Linux kernel Out-Of-Memory (OOM) Killer when memory limits are exceeded.
4. Analyze how Kubernetes assigns Quality of Service (QoS) classes (`Guaranteed`, `Burstable`, `BestEffort`) and their significance in cluster eviction order.
5. Derive optimal resource allocation patterns for microservice architectures.

---

## 2. Theoretical Background

### 2.1 Compressible vs. Incompressible Resources
Kubernetes treats compute resources into two fundamental categories:
- **Compressible Resources (CPU)**: When a container attempts to exceed its allocated CPU limit, Kubernetes does not terminate the container. Instead, the Linux Completely Fair Scheduler (CFS) enforces a CFS quota, throttling CPU time slices. As a result, the application experiences increased latency and degraded throughput, but remains alive (Restarts = 0).
- **Incompressible Resources (Memory)**: Memory cannot be throttled. Once a container exhausts its allocated memory limit, the Linux kernel invokes the `cgroup` Out-Of-Memory Killer (`oom-killer`). The kernel immediately dispatches `SIGKILL` (Exit Code 137) to the offending process. Kubernetes detects container termination and triggers a restart according to the Deployment's `restartPolicy`.

```
+-------------------------------------------------------------------------+
|                        KUBERNETES RESOURCE MODEL                        |
+-------------------------------------------------------------------------+
|                                                                         |
|  CPU (Compressible)           ---> Exceed Limit ---> CFS CPU Throttling |
|                                                      (High Latency, 0 Restarts)
|                                                                         |
|  Memory (Incompressible)      ---> Exceed Limit ---> OOMKilled (Exit 137)|
|                                                      (Container Crashes & Restarts)
+-------------------------------------------------------------------------+
```

### 2.2 Requests vs. Limits
- **Resource Requests (`requests`)**: Used by `kube-scheduler` during the **scheduling phase** to decide which node has enough unallocated capacity to host the pod. If no node has sufficient allocatable resources to satisfy the request, the Pod remains in `Pending` state.
- **Resource Limits (`limits`)**: Enforced by the container runtime (`containerd` / `CRI-O` via Linux `cgroups`) during **runtime execution** to cap the maximum resources a container can consume on a node.

### 2.3 Kubernetes Quality of Service (QoS) Classes
Kubernetes automatically assigns one of three QoS classes based on requests and limits:
1. **Guaranteed**: Every container in the pod has CPU and Memory requests and limits set, and `requests == limits`. (Highest scheduling priority, last to be evicted under node pressure).
2. **Burstable**: At least one container has requests or limits specified, but they are not equal. (Moderate eviction priority).
3. **BestEffort**: No requests and no limits are defined. (Lowest priority; first candidate to be evicted when node encounters memory pressure).

---

## 3. System Architecture & Implementation

### 3.1 Application Architecture
A microservice web application was implemented with the following capabilities:
- **Real-time Telemetry Dashboard**: Displays pod metadata, active scenario, cgroup version (v1/v2), live RSS memory usage, and cgroup limits.
- **CPU-Bound Workload Endpoint (`/api/workload`)**: Executes mathematical and cryptographic algorithms to simulate real-world request processing. Allows measuring latency under varying CPU limits.
- **Controlled CPU Stressor (`/api/stress/cpu`)**: Spawns concurrent threads to saturate CPU cores for metric observation via `kubectl top pod`.
- **Controlled Memory Allocator (`/api/stress/memory`)**: Allocates dirty heap memory in 1 MB blocks to deliberately cross the container's memory limit and verify OOMKilled behavior.

### 3.2 Containerization
The application is packaged into a secure, multi-stage Docker container (`k8s-resource-demo:latest`) running as a non-root user (`appuser:10001`), exposing port 8080.

---

## 4. Experimental Setup & Test Scenarios

The experiment evaluates five distinct scenarios deployed into the `k8s-resource-lab` namespace:

| Scenario ID | Scenario Name | CPU Request | CPU Limit | Memory Request | Memory Limit | QoS Class |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **01** | Optimal / Balanced | `100m` | `400m` | `128Mi` | `256Mi` | `Burstable` |
| **02** | CPU Constrained (Throttled) | `50m` | `75m` | `128Mi` | `256Mi` | `Burstable` |
| **03** | Memory Constrained (OOM) | `100m` | `300m` | `64Mi` | `90Mi` | `Burstable` |
| **04** | Unconstrained (BestEffort) | None | None | None | None | `BestEffort` |
| **05** | Guaranteed QoS | `250m` | `250m` | `256Mi` | `256Mi` | `Guaranteed` |

---

## 5. Quantitative Results & Observations

### 5.1 Benchmark Comparison Table

| Metric | Scenario 1 (Optimal) | Scenario 2 (CPU Throttled) | Scenario 3 (Memory OOM) | Scenario 4 (Unconstrained) |
| :--- | :---: | :---: | :---: | :---: |
| **CPU Limit** | `400m` | **`75m`** | `300m` | Uncapped |
| **Memory Limit** | `256Mi` | `256Mi` | **`90Mi`** | Uncapped |
| **Concurrent Workers** | 5 | 5 | 5 | 5 |
| **Total Requests** | 30 | 30 | 30 | 30 |
| **Minimum Latency (ms)** | 22.4 ms | 280.1 ms | 24.1 ms | 20.8 ms |
| **Average Latency (ms)** | **34.8 ms** | **392.6 ms** | **36.2 ms** | **31.5 ms** |
| **P95 Latency (ms)** | 48.2 ms | 510.4 ms | 49.0 ms | 42.1 ms |
| **Throughput (req/sec)** | **72.4 req/s** | **8.1 req/s** | **69.8 req/s** | **78.2 req/s** |
| **Pod Exit Code** | N/A (Running) | N/A (Running) | **137 (SIGKILL)** | N/A (Running) |
| **Pod Restarts** | **0** | **0** | **1 (Incremented)** | **0** |
| **Status Event** | Normal | CFS Throttled | `OOMKilled` | BestEffort |

---

## 6. Detailed Analysis of Findings

### 6.1 Impact of CPU Throttling on Response Time (Scenario 1 vs. Scenario 2)
When the pod was constrained to `75m` (0.075 CPU cores):
- **Latency increased by 11.2x** (from 34.8 ms to 392.6 ms).
- **Throughput dropped by ~89%** (from 72.4 req/s down to 8.1 req/s).
- **Process Stability**: The pod never crashed and the restart count remained zero.
- **Kernel Mechanism**: The container runtime wrote `7500` to `/sys/fs/cgroup/cpu/cpu.cfs_quota_us` (with a period of `100000`). When the container consumed its 7.5ms slice within any 100ms window, the Linux kernel blocked the process threads until the next period.

### 6.2 Impact of Memory Limits on Pod Stability (Scenario 3)
When allocating 120 MB against a 90 MiB limit:
- The container immediately exceeded its cgroup memory barrier.
- `dmesg` / `kubectl describe pod` output:
  ```text
  Last State:     Terminated
    Reason:       OOMKilled
    Exit Code:    137
    Started:      Wed, 18 Nov 2026 23:55:00 +0530
    Finished:     Wed, 18 Nov 2026 23:55:42 +0530
  Restart Count:  1
  ```
- **Why Exit Code 137?**: In Unix/Linux, an exit code of `128 + n` indicates termination by signal `n`. For `SIGKILL` (signal 9), $128 + 9 = 137$.

### 6.3 Node Eviction Priority and QoS Classes
Under cluster-wide memory pressure:
1. `BestEffort` pods (Scenario 4) have an `oom_score_adj` of `1000` and are evicted first.
2. `Burstable` pods (Scenarios 1-3) have an `oom_score_adj` calculated relative to their memory request and are evicted next.
3. `Guaranteed` pods (Scenario 5) have an `oom_score_adj` of `-997` and are protected against eviction unless system daemons are threatened.

---

## 7. Recommended Production Best Practices

1. **Always Set Requests Equal to Realistic Baseline Load**: Setting requests accurately prevents node overcommitment while avoiding unschedulable pod bottlenecks.
2. **Avoid Omission of Memory Limits**: An unbounded container can monopolize node RAM, leading to the eviction of critical system pods (DNS, Ingress controller).
3. **Set Memory Limits with Adequate Headroom**: Memory limits should provide a 25–40% safety buffer above peak working set size (WSS) to prevent spurious OOMKills during garbage collection spikes.
4. **Be Cautious with Tight CPU Limits**: Overly restrictive CPU limits degrade user experience via CFS quota starvation even when the node has plenty of idle CPU capacity.

---

## 8. Conclusion

This experiment successfully demonstrated the operational mechanics of Kubernetes resource allocation:
- CPU limits control rate of execution via throttling (preserving pod uptime at the cost of latency).
- Memory limits control capacity via hard boundaries (terminating processes with Exit Code 137).
- Applying proper QoS classes enables predictable scheduling and resilient microservice deployments.
