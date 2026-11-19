# Viva Voce & Interview Preparation Guide

**Subject**: Cloud Computing Laboratory Evaluation – 2  
**Institution**: KLE Technological University  
**Topic**: Problem 01 — Kubernetes Resource Allocation and Optimization  

---

### Q1: What is the fundamental difference between Kubernetes resource `requests` and `limits`?
**Answer**:
- **Requests (`requests`)**: Specify the minimum amount of compute resources (CPU/Memory) guaranteed to a container. The `kube-scheduler` uses requests during the scheduling phase to determine if a node has sufficient capacity to host the pod.
- **Limits (`limits`)**: Specify the maximum ceiling of resources that a container is permitted to consume at runtime. The Linux kernel (`cgroups`) enforces limits to prevent any container from monopolizing node resources.

---

### Q2: Which component of Kubernetes reads `requests`, and which enforces `limits`?
**Answer**:
- **Requests** are evaluated by the **`kube-scheduler`** on the control plane during pod placement.
- **Limits** are enforced at the node level by the container runtime (`containerd`, `CRI-O`, or Docker) in conjunction with Linux kernel **`cgroups`** (Control Groups).

---

### Q3: What is the unit of measurement for CPU in Kubernetes? What does `100m` mean?
**Answer**:
- CPU in Kubernetes is measured in millicores (or millicpus).
- `1000m` equals 1 full vCPU / physical core.
- `100m` represents $100 / 1000 = 0.10$ vCPU (or 10% of a CPU core).

---

### Q4: What is the difference between `Mi` and `M` in memory specifications?
**Answer**:
- `Mi` (Mebibyte) is based on powers of 2 ($2^{20} = 1,048,576$ bytes) — IEC binary standard.
- `M` (Megabyte) is based on powers of 10 ($10^6 = 1,000,000$ bytes) — SI metric standard.
- Kubernetes manifests typically use `Mi` and `Gi` for binary-aligned memory allocation.

---

### Q5: What happens when a container exceeds its CPU limit? Does it get terminated?
**Answer**:
**No, the container does not crash or restart.** CPU is a *compressible resource*. When a container reaches its CPU limit, the Linux kernel's Completely Fair Scheduler (CFS) enforces quota throttling. The container's threads are paused until the next CFS period (typically 100ms). The application experiences latency degradation and lower throughput, but remains alive (Restarts = 0).

---

### Q6: What happens when a container exceeds its Memory limit?
**Answer**:
Memory is an *incompressible resource*. Because memory cannot be throttled, when a container attempts to allocate more RAM than its configured limit, the Linux kernel invokes the `cgroup` **Out-Of-Memory (OOM) Killer**. The kernel sends `SIGKILL` (signal 9) to the container process. The pod terminates with exit code **137** and status **`OOMKilled`**, and Kubernetes restarts the container based on the restart policy.

---

### Q7: Why is the exit code for OOMKilled containers specifically 137?
**Answer**:
In Linux, standard process termination exit codes follow the convention:
$$\text{Exit Code} = 128 + \text{Signal Number}$$
When the OOM Killer terminates a process, it issues `SIGKILL` (Signal 9).
$$\text{Exit Code} = 128 + 9 = 137$$

---

### Q8: What are the three Kubernetes Quality of Service (QoS) classes, and how are they assigned?
**Answer**:
Kubernetes inspects the pod's container specifications and automatically assigns one of three QoS classes:
1. **Guaranteed**: Every container in the pod has both CPU and Memory requests and limits explicitly defined, and `requests == limits`.
2. **Burstable**: At least one container has requests or limits set, but they are not identical.
3. **BestEffort**: Neither requests nor limits are specified for any container in the pod.

---

### Q9: In what order does the Kubelet evict pods when a node runs out of memory?
**Answer**:
Under node memory pressure, the Kubelet evicts pods in reverse order of their QoS priority:
1. **First to be evicted**: `BestEffort` pods (they have made no resource guarantees and have an `oom_score_adj` of 1000).
2. **Second to be evicted**: `Burstable` pods that are consuming memory exceeding their requested amount.
3. **Last to be evicted**: `Guaranteed` pods (they are shielded and only evicted if critical system daemons need memory to keep the node alive).

---

### Q10: What is CFS (Completely Fair Scheduler) quota throttling, and how does it manifest in web applications?
**Answer**:
The Linux CFS uses two parameters: `cpu.cfs_period_us` (default 100,000 µs = 100 ms) and `cpu.cfs_quota_us`. If a container has a limit of `200m`, its quota is $200 / 1000 \times 100,000 = 20,000\ \mu\text{s}$ (20 ms). Once the container's threads consume 20 ms of CPU within that 100 ms window, the kernel freezes execution for the remaining 80 ms. In web applications, this manifests as high P95/P99 latency spikes and queue buildup.

---

### Q11: What is the Kubernetes Downward API, and how was it used in this project?
**Answer**:
The Downward API allows containers to consume information about themselves (pod name, namespace, node name, IP) or cluster resource allocations (`requests.cpu`, `limits.memory`) without querying the Kubernetes API server directly. In our project, it injects `requests` and `limits` as environment variables into the container so the web dashboard can display live Kubernetes configurations.

---

### Q12: What is the "Noisy Neighbor" problem, and how do resource limits mitigate it?
**Answer**:
The "Noisy Neighbor" problem occurs when one runaway container on a shared node consumes all available CPU or memory, starving adjacent pods of compute cycles. Setting hard `limits` ensures that a misbehaving or traffic-spiked container is bounded within its sandbox, isolating other tenant microservices.

---

### Q13: If a pod has CPU requests higher than any single node's allocatable capacity, what happens?
**Answer**:
The pod cannot be scheduled and remains permanently in the **`Pending`** state. Running `kubectl describe pod` will display the scheduler event: `FailedScheduling: 0/N nodes are available: Insufficient cpu`.

---

### Q14: Why is it recommended to avoid running pods without memory limits in production?
**Answer**:
Without memory limits (QoS `BestEffort`), a single container experiencing a memory leak will expand until it exhausts the entire node's physical RAM. This forces the node's OS OOM killer to terminate processes indiscriminately, which may crash the container runtime, the Kubelet, or other critical workload pods.

---

### Q15: How can an administrator inspect real-time resource consumption in Kubernetes?
**Answer**:
1. CLI tool: `kubectl top pod -n <namespace>` and `kubectl top node` (requires Metrics Server).
2. Pod events: `kubectl describe pod <pod-name>` (shows Last State, Reason, OOMKilled events).
3. Production monitoring: Prometheus and Grafana dashboards tracking `container_cpu_usage_seconds_total`, `container_cpu_cfs_throttled_periods_total`, and `container_memory_working_set_bytes`.
