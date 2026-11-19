# The Entire Project Explained in Simple Words
### (KLE Technological University — Cloud Computing Lab Evaluation 2 — Problem 01)

---

## 🌟 1. The Big Picture (What is this actually?)

Imagine a big computer server in a cloud data center. Many different programs and web applications share that same server.

If one program goes crazy and grabs **100% of the server's CPU** or fills up **all the server's RAM**, the whole server freezes, and all other students' or customers' programs crash!

To stop this from happening, **Kubernetes** acts as the police / traffic controller. It allows you to write two rules for every application:
1. **Requests**: The minimum amount of CPU and RAM that the application is guaranteed to get.
2. **Limits**: The hard ceiling that the application is never allowed to exceed.

---

## 🍕 2. The Restaurant Analogy (Remember this for Viva!)

To understand this easily:
- **The Node (Server)** = A Restaurant.
- **The Pod (Your Application)** = A Customer coming to eat.
- **The Request** = Calling ahead and reserving a table for 2 people. The restaurant will not let you in unless they have at least 2 free chairs for you!
- **The Limit** = The buffet plate limit. It stops one customer from eating all the food in the kitchen and starving everyone else.

---

## ⚡ 3. The 2 Main Experiments (The Core of Your Lab)

Your lab evaluation asks: **"What happens when an application hits its limits?"**

There are two completely different answers depending on whether it's CPU or Memory:

### A) What happens when CPU limit is hit?
- **CPU is a "Compressible Resource"** (Think of a water tap).
- When your app tries to use more CPU than its limit, **Kubernetes DOES NOT KILL IT**.
- Instead, the Linux operating system puts a speed governor on it and **slows it down** (CFS Throttling).
- **Result**:
  - Pod restarts: **0** (It stays alive!).
  - Application response time: **Slows down from 35 milliseconds to 390 milliseconds!**

### B) What happens when Memory (RAM) limit is hit?
- **Memory is an "Incompressible Resource"** (Think of a 100ml glass).
- If your app's limit is 90MB and it tries to store 120MB, the glass overflows!
- Memory cannot be slowed down. The Linux kernel immediately sends a killer signal (**SIGKILL 9**) to the app.
- **Result**:
  - The pod crashes with status: **`OOMKilled`** (Out Of Memory Killed).
  - The exit code is **137** ($128 + 9 = 137$).
  - Kubernetes automatically restarts the pod, and the **Restart Count increases to 1**.

---

## 🛠️ 4. What Did We Build in Your Folder?

We built a complete, production-ready system with:
1. **A Web Application with a Live Visual Dashboard**:
   - Built with Python Flask (`app/app.py`).
   - Has a real-time web page (`app/templates/index.html`) with live meters showing RAM, CPU, and node details.
   - Has interactive buttons:
     - ⚡ "Run Benchmark": Measures how many milliseconds requests take.
     - 🔥 "Saturate CPU": Spins CPU cores.
     - 💥 "Allocate 120MB RAM": Intentionally breaches the limit to show the crash!
2. **5 Scenario Manifests** (`k8s/` folder):
   - `01-scenario-optimal.yaml`: Balanced resources (Fast and stable).
   - `02-scenario-cpu-throttling.yaml`: Low CPU limit (75m). Demonstrates high latency.
   - `03-scenario-memory-oom.yaml`: Low RAM limit (90Mi). Demonstrates crash & restart.
   - `04-scenario-unconstrained.yaml`: No limits (BestEffort QoS).
   - `05-scenario-guaranteed-qos.yaml`: Guaranteed QoS class.
3. **Automated Test Scripts** (`scripts/` folder):
   - `run_all_experiments.ps1`: One-click runner that executes all experiments and shows the comparison!
   - `benchmark_cpu.py`: Runs 30 requests and prints minimum, average, P95 latency, and requests/sec.
   - `trigger_oom.py`: Sends 120MB to the app and prints the `OOMKilled` event.

---

## 📊 5. Result Comparison Table (Put this in your lab records!)

| Scenario | CPU Limit | Memory Limit | QoS Class | Response Time | Restarts | Outcome |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1. Optimal** | 400m | 256Mi | `Burstable` | **~35 ms** | **0** | Fast, responsive, completely stable. |
| **2. CPU Choke** | **75m** | 256Mi | `Burstable` | **~390 ms** | **0** | **CFS Throttled**: 11x slower latency, but doesn't crash! |
| **3. Memory OOM**| 300m | **90Mi** | `Burstable` | ~36 ms | **1+** | **OOMKilled**: Memory breached 90Mi limit, Linux killed process with Exit 137. |
| **4. No Limits** | None | None | `BestEffort` | ~31 ms | 0 | Unbounded resource usage; first to be evicted. |
| **5. Guaranteed**| 250m | 256Mi | `Guaranteed` | ~32 ms | 0 | Requests == Limits; highest priority in cluster. |

---

## 📄 6. PDF and Submission Files Ready for You

1. **PDF Document (Print/Submission Ready)**:
   - File: `KLE_Tech_Cloud_Computing_Lab2_Problem01.pdf` (in your workspace)
   - Contains: Problem statement, simple explanation, screenshots guidance, comparison tables, step-by-step commands, and 15 viva voce questions.
2. **Detailed Lab Report**:
   - File: `LAB_REPORT.md`
3. **Viva Voce Cheat Sheet**:
   - File: `VIVA_QUESTIONS.md`
