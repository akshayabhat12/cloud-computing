"""
Script: trigger_oom.py
Purpose: Inject memory allocation to breach container memory limits.
Demonstrates: Linux cgroup memory limit enforcement, OOMKilled status, and Pod Restarts.
"""

import sys
import time
import json
import subprocess
import urllib.request
import urllib.error

def check_kubectl_pods():
    try:
        res = subprocess.run(
            ["kubectl", "get", "pods", "-n", "k8s-resource-lab", "-o", "wide"],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            print("\n[kubectl get pods -n k8s-resource-lab]:")
            print(res.stdout.strip())
    except Exception:
        pass

def trigger_oom(base_url="http://localhost:8080", target_mb=120):
    print("=" * 65)
    print(" MEMORY OOMKILL & STABILITY VERIFICATION TEST")
    print(f" Target Web App: {base_url}")
    print(f" Attempting memory allocation of: {target_mb} MB")
    print("=" * 65)

    print("\n[Step 1] Initial pod status check before memory stress:")
    check_kubectl_pods()

    trigger_url = f"{base_url.rstrip('/')}/api/stress/memory?megabytes={target_mb}"
    print(f"\n[Step 2] Sending POST request to {trigger_url}...")
    
    try:
        req = urllib.request.Request(trigger_url, data=b"", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as res:
            response_body = res.read().decode()
            print(f"[Result] Response received: {response_body}")
            print("[Notice] Pod survived memory allocation. Container memory limit is higher than target.")
    except (urllib.error.URLError, ConnectionResetError, RemoteDisconnected, Exception) as e:
        print("\n[Result] CONNECTION TERMINATED BY SERVER!")
        print(f" Reason: {e}")
        print(" The container process was abruptly killed by the Linux kernel OOM Killer (SIGKILL 137)!")

    print("\n[Step 3] Waiting 3 seconds for Kubernetes Kubelet to register the crash and restart container...")
    time.sleep(3)

    print("\n[Step 4] Current pod status after memory breach:")
    check_kubectl_pods()

    print("\n[Step 5] Checking pod events with 'kubectl describe pod -n k8s-resource-lab':")
    try:
        res = subprocess.run(
            ["kubectl", "get", "pods", "-n", "k8s-resource-lab", "--no-headers"],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            pod_name = res.stdout.strip().split()[0]
            desc = subprocess.run(
                ["kubectl", "describe", "pod", pod_name, "-n", "k8s-resource-lab"],
                capture_output=True, text=True, timeout=5
            )
            # Filter and show termination reason and events
            lines = desc.stdout.splitlines()
            for line in lines:
                if any(k in line.lower() for k in ["last state", "terminated", "oomkilled", "exit code", "restart count", "events:"]):
                    print("  " + line)
    except Exception:
        pass
    print("=" * 65)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    mb = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    trigger_oom(url, mb)
