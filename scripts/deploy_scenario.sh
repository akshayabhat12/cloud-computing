#!/usr/bin/env bash
# Deploy scenario helper script

SCENARIO=${1:-1}

echo "=========================================================="
echo " KUBERNETES RESOURCE ALLOCATION LAB - SCENARIO DEPLOYER"
echo "=========================================================="

# Ensure namespace and service exist
kubectl apply -f ./k8s/00-namespace.yaml 2>/dev/null || kubectl apply -f ../k8s/00-namespace.yaml
kubectl apply -f ./k8s/service.yaml 2>/dev/null || kubectl apply -f ../k8s/service.yaml

case "$SCENARIO" in
  1|optimal)
    TARGET="k8s/01-scenario-optimal.yaml"
    DESC="Scenario 1: Optimal (CPU: 100m/400m, Mem: 128Mi/256Mi)"
    ;;
  2|cpu)
    TARGET="k8s/02-scenario-cpu-throttling.yaml"
    DESC="Scenario 2: CPU Constrained (CPU: 50m/75m, CFS Throttling)"
    ;;
  3|memory)
    TARGET="k8s/03-scenario-memory-oom.yaml"
    DESC="Scenario 3: Memory Constrained (Mem: 64Mi/90Mi, OOMKilled)"
    ;;
  4|unconstrained)
    TARGET="k8s/04-scenario-unconstrained.yaml"
    DESC="Scenario 4: Unconstrained (No requests/limits, BestEffort)"
    ;;
  5|guaranteed)
    TARGET="k8s/05-scenario-guaranteed-qos.yaml"
    DESC="Scenario 5: Guaranteed QoS (Requests == Limits)"
    ;;
  *)
    echo "Unknown scenario. Use 1, 2, 3, 4, or 5."
    exit 1
    ;;
esac

echo "[Deploying] $DESC"
if [ -f "./$TARGET" ]; then
  kubectl apply -f "./$TARGET"
else
  kubectl apply -f "../$TARGET"
fi

echo "Waiting for rollout..."
kubectl rollout status deployment/resource-demo -n k8s-resource-lab --timeout=60s
echo ""
kubectl get pods -n k8s-resource-lab -o wide
echo ""
echo "Access Dashboard: kubectl port-forward svc/resource-demo-svc 8080:8080 -n k8s-resource-lab"
echo "URL: http://localhost:8080"
