"""
Script: benchmark_cpu.py
Purpose: Measure web application latency and throughput under different CPU limits.
Demonstrates: How CFS quota throttling affects response time.
"""

import sys
import time
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_single_request(url):
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "K8s-Benchmark/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            t1 = time.perf_counter()
            data = json.loads(response.read().decode())
            return {
                "success": True,
                "latency_ms": round((t1 - t0) * 1000, 2),
                "server_ms": data.get("elapsed_ms", 0),
                "error": None
            }
    except Exception as e:
        t1 = time.perf_counter()
        return {
            "success": False,
            "latency_ms": round((t1 - t0) * 1000, 2),
            "server_ms": 0,
            "error": str(e)
        }

def run_benchmark(base_url="http://localhost:8080", total_requests=30, concurrency=5):
    target_url = f"{base_url.rstrip('/')}/api/workload?iterations=300000"
    print("=" * 60)
    print(" KUBERNETES APPLICATION RESPONSE TIME BENCHMARK")
    print(f" Target: {target_url}")
    print(f" Requests: {total_requests} | Concurrency: {concurrency}")
    print("=" * 60)

    # First fetch pod info
    try:
        info_req = urllib.request.Request(f"{base_url.rstrip('/')}/api/info")
        with urllib.request.urlopen(info_req, timeout=3) as res:
            pod_info = json.loads(res.read().decode())
            print(f" Active Scenario : {pod_info['pod']['scenario']}")
            print(f" Pod Name        : {pod_info['pod']['name']}")
            print(f" CPU Request/Lim : {pod_info['k8s_resources']['cpu_request']} / {pod_info['k8s_resources']['cpu_limit']}")
            print(f" QoS Class       : {pod_info['k8s_resources']['qos_class']}")
            print("-" * 60)
    except Exception as e:
        print(f"[Notice] Could not fetch pod metadata: {e}")

    start_bench = time.perf_counter()
    latencies = []
    failures = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(run_single_request, target_url) for _ in range(total_requests)]
        for idx, f in enumerate(as_completed(futures), 1):
            res = f.result()
            if res["success"]:
                latencies.append(res["latency_ms"])
                print(f"[{idx:02d}/{total_requests}] Latency: {res['latency_ms']:6.2f} ms (Server: {res['server_ms']} ms)")
            else:
                failures += 1
                print(f"[{idx:02d}/{total_requests}] FAILED: {res['error']}")

    total_time = round(time.perf_counter() - start_bench, 2)
    
    print("=" * 60)
    print(" BENCHMARK RESULTS SUMMARY")
    print("=" * 60)
    if latencies:
        latencies.sort()
        avg_lat = round(sum(latencies) / len(latencies), 2)
        min_lat = round(latencies[0], 2)
        max_lat = round(latencies[-1], 2)
        p95_lat = round(latencies[int(len(latencies) * 0.95)], 2)
        rps = round(len(latencies) / total_time, 2)

        print(f" Total Requests Completed : {len(latencies)} / {total_requests}")
        print(f" Total Time Taken         : {total_time} seconds")
        print(f" Throughput (RPS)         : {rps} req/sec")
        print(f" Minimum Latency          : {min_lat} ms")
        print(f" Average Latency          : {avg_lat} ms")
        print(f" 95th Percentile (P95)    : {p95_lat} ms")
        print(f" Maximum Latency          : {max_lat} ms")
        print(f" Failure Rate             : {round((failures/total_requests)*100, 2)}%")
    else:
        print("All requests failed. Verify pod connection and port-forward.")
    print("=" * 60)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    reqs = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    conc = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    run_benchmark(url, reqs, conc)
