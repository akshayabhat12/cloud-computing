import os
import sys
import time
import math
import uuid
import threading
from collections import deque
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__)

# ---------------------------------------------------------
# IN-MEMORY E-COMMERCE DATABASE
# ---------------------------------------------------------
PRODUCTS = [
    {
        "id": 1,
        "name": "Cloud Native Kubernetes Cluster Node",
        "category": "Servers",
        "price": 149.99,
        "stock": 25,
        "rating": 4.9,
        "badge": "Popular",
        "image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&q=80",
        "description": "Enterprise-grade high-availability bare-metal compute node with dual 10Gbps NICs and hardware virtualization."
    },
    {
        "id": 2,
        "name": "DevOps Mechanical Keyboard (Cherry MX)",
        "category": "Gear",
        "price": 89.50,
        "stock": 40,
        "rating": 4.8,
        "badge": "Hot",
        "image": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400&q=80",
        "description": "Ergonomic programmable mechanical keyboard designed specifically for terminal speed, vim shortcuts, and long deployments."
    },
    {
        "id": 3,
        "name": "Edge AI TPU Neural Accelerator",
        "category": "Electronics",
        "price": 199.00,
        "stock": 18,
        "rating": 4.95,
        "badge": "Featured",
        "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&q=80",
        "description": "Low-power USB-C inference accelerator delivering 8 TOPS for computer vision and microservice edge inference."
    },
    {
        "id": 4,
        "name": "Kubernetes Captain Organic Hoodie",
        "category": "Merch",
        "price": 45.00,
        "stock": 60,
        "rating": 4.7,
        "badge": "Best Seller",
        "image": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400&q=80",
        "description": "100% premium combed cotton hoodie embroidered with cloud engineering motifs. Tested for extreme debugging comfort."
    },
    {
        "id": 5,
        "name": "NVMe PCIe Gen4 High-IOPS Cloud SSD 2TB",
        "category": "Servers",
        "price": 129.99,
        "stock": 30,
        "rating": 4.85,
        "badge": "Sale",
        "image": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=400&q=80",
        "description": "7000 MB/s sequential read, 1 Million IOPS random write. Ideal for intensive persistent volume claims and database pods."
    },
    {
        "id": 6,
        "name": "Ultra-Wide 34\" Curved 4K Monitor",
        "category": "Electronics",
        "price": 349.00,
        "stock": 12,
        "rating": 4.9,
        "badge": "Top Rated",
        "image": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&q=80",
        "description": "IPS HDR 144Hz panel with dual USB-C display input and 90W power delivery. Perfect for side-by-side terminal & dashboard views."
    }
]

CART = {}       # In-memory session cart: { product_id: quantity }
ORDERS = []     # List of processed orders
METRICS_HISTORY = deque(maxlen=60) # Rolling request latency (ms)
TOTAL_REQUESTS = 0
TOTAL_ORDERS = 0
MEM_STRESS_BUFFER = []
STRESS_STOP_FLAG = False
GLOBAL_CPU_PCT = 0.0

# ---------------------------------------------------------
# ACCURATE BACKGROUND CPU MONITOR
# ---------------------------------------------------------
def _cpu_monitor_loop():
    """Continuously samples process and system CPU utilization every 0.5 seconds."""
    global GLOBAL_CPU_PCT
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        proc.cpu_percent(interval=None) # Prime initial sample
        while True:
            time.sleep(0.5)
            # Measure CPU percent over the 0.5s interval
            pct = proc.cpu_percent(interval=None)
            GLOBAL_CPU_PCT = round(pct, 1)
    except Exception:
        pass

# Start background CPU monitor daemon thread
cpu_thread = threading.Thread(target=_cpu_monitor_loop, daemon=True)
cpu_thread.start()

# ---------------------------------------------------------
# KUBERNETES & SYSTEM TELEMETRY HELPERS
# ---------------------------------------------------------
def get_cgroup_memory():
    """Reads Linux cgroups v1/v2 memory limit and usage."""
    info = {"limit_bytes": None, "usage_bytes": None, "version": "unknown"}
    # cgroup v2
    if os.path.exists("/sys/fs/cgroup/memory.max") and os.path.exists("/sys/fs/cgroup/memory.current"):
        try:
            with open("/sys/fs/cgroup/memory.max", "r") as f:
                val = f.read().strip()
                info["limit_bytes"] = int(val) if val != "max" else "unlimited"
            with open("/sys/fs/cgroup/memory.current", "r") as f:
                info["usage_bytes"] = int(f.read().strip())
            info["version"] = "v2"
            return info
        except Exception:
            pass
    # cgroup v1
    v1_max = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    v1_cur = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
    if os.path.exists(v1_max) and os.path.exists(v1_cur):
        try:
            with open(v1_max, "r") as f:
                val = int(f.read().strip())
                info["limit_bytes"] = val if val < 9000000000000000000 else "unlimited"
            with open(v1_cur, "r") as f:
                info["usage_bytes"] = int(f.read().strip())
            info["version"] = "v1"
            return info
        except Exception:
            pass
    return info

def get_process_stats():
    """Returns process RSS memory in MB and current sampled CPU percentage."""
    try:
        import psutil
        p = psutil.Process(os.getpid())
        rss_mb = round(p.memory_info().rss / (1024 * 1024), 2)
        return rss_mb, GLOBAL_CPU_PCT
    except Exception:
        return 42.5, GLOBAL_CPU_PCT

# ---------------------------------------------------------
# REQUEST HOOKS FOR METRICS TRACKING
# ---------------------------------------------------------
@app.before_request
def start_timer():
    request._start_time = time.perf_counter()
    global TOTAL_REQUESTS
    TOTAL_REQUESTS += 1

@app.after_request
def record_metrics(response):
    if hasattr(request, "_start_time"):
        elapsed_ms = round((time.perf_counter() - request._start_time) * 1000, 2)
        METRICS_HISTORY.append(elapsed_ms)
    return response

# ---------------------------------------------------------
# STOREFRONT ENDPOINTS
# ---------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    search = request.args.get("search", "").lower()
    
    filtered = PRODUCTS
    if category and category != "All":
        filtered = [p for p in filtered if p["category"].lower() == category.lower()]
    if search:
        filtered = [p for p in filtered if search in p["name"].lower() or search in p["description"].lower()]
        
    return jsonify({"products": filtered, "total": len(filtered)})

@app.route("/api/cart", methods=["GET"])
def get_cart():
    items = []
    subtotal = 0.0
    for pid, qty in CART.items():
        prod = next((p for p in PRODUCTS if p["id"] == pid), None)
        if prod:
            item_total = round(prod["price"] * qty, 2)
            subtotal += item_total
            items.append({
                "product": prod,
                "quantity": qty,
                "item_total": item_total
            })
    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + tax, 2)
    return jsonify({
        "items": items,
        "item_count": sum(CART.values()),
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "total": total
    })

@app.route("/api/cart/add", methods=["POST"])
def add_to_cart():
    data = request.get_json() or {}
    pid = int(data.get("product_id", 0))
    qty = int(data.get("quantity", 1))
    
    prod = next((p for p in PRODUCTS if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Product not found"}), 404
        
    CART[pid] = CART.get(pid, 0) + qty
    return jsonify({"message": f"Added {prod['name']} to cart", "cart_count": sum(CART.values())})

@app.route("/api/cart/update", methods=["POST"])
def update_cart():
    data = request.get_json() or {}
    pid = int(data.get("product_id", 0))
    qty = int(data.get("quantity", 0))
    if qty <= 0:
        CART.pop(pid, None)
    else:
        CART[pid] = qty
    return get_cart()

@app.route("/api/cart/clear", methods=["POST"])
def clear_cart():
    CART.clear()
    return jsonify({"message": "Cart cleared successfully"})

@app.route("/api/checkout", methods=["POST"])
def checkout():
    global TOTAL_ORDERS
    data = request.get_json() or {}
    customer_name = data.get("name", "Cloud Shopper")
    email = data.get("email", "shopper@kletech.ac.in")
    address = data.get("address", "Campus Hub, Hubballi")
    
    if not CART:
        return jsonify({"error": "Cart is empty"}), 400

    time.sleep(0.03) # Realistic DB latency
    order_items = []
    subtotal = 0.0
    for pid, qty in list(CART.items()):
        prod = next((p for p in PRODUCTS if p["id"] == pid), None)
        if prod:
            prod["stock"] = max(0, prod["stock"] - qty)
            item_total = round(prod["price"] * qty, 2)
            subtotal += item_total
            order_items.append({
                "product_id": pid,
                "name": prod["name"],
                "price": prod["price"],
                "quantity": qty,
                "item_total": item_total
            })

    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + tax, 2)
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    order = {
        "order_id": order_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": customer_name,
        "email": email,
        "address": address,
        "items": order_items,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "processed_by_pod": os.environ.get("POD_NAME", "ecommerce-web-pod")
    }
    
    ORDERS.insert(0, order)
    CART.clear()
    TOTAL_ORDERS += 1
    
    return jsonify({
        "success": True,
        "order": order,
        "message": f"Order {order_id} placed successfully!"
    })

@app.route("/api/orders", methods=["GET"])
def get_orders():
    return jsonify({"orders": ORDERS[:20], "total": len(ORDERS)})

# ---------------------------------------------------------
# CLUSTER MONITORING & RESOURCE TELEMETRY API
# ---------------------------------------------------------
@app.route("/api/cluster/telemetry", methods=["GET"])
def get_telemetry():
    rss_mb, cpu_pct = get_process_stats()
    cgroup = get_cgroup_memory()
    
    cg_lim_mb = "Unlimited"
    if isinstance(cgroup["limit_bytes"], int):
        cg_lim_mb = round(cgroup["limit_bytes"] / (1024 * 1024), 2)
        
    cg_cur_mb = "N/A"
    if isinstance(cgroup["usage_bytes"], int):
        cg_cur_mb = round(cgroup["usage_bytes"] / (1024 * 1024), 2)

    latencies = list(METRICS_HISTORY)
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if len(latencies) >= 5 else avg_latency

    return jsonify({
        "pod": {
            "name": os.environ.get("POD_NAME", "ecommerce-web-pod"),
            "namespace": os.environ.get("POD_NAMESPACE", "k8s-resource-lab"),
            "node": os.environ.get("NODE_NAME", "docker-desktop-worker"),
            "ip": os.environ.get("POD_IP", "10.244.0.15"),
            "scenario": os.environ.get("SCENARIO_NAME", "CloudCommerce Production (Burstable)")
        },
        "resources": {
            "cpu_request": os.environ.get("CPU_REQUEST", "100m"),
            "cpu_limit": os.environ.get("CPU_LIMIT", "400m"),
            "memory_request": os.environ.get("MEM_REQUEST", "128Mi"),
            "memory_limit": os.environ.get("MEM_LIMIT", "256Mi"),
            "qos_class": os.environ.get("QOS_CLASS", "Burstable")
        },
        "metrics": {
            "rss_memory_mb": rss_mb,
            "cpu_percent": cpu_pct,
            "cgroup_memory_limit_mb": cg_lim_mb,
            "cgroup_memory_usage_mb": cg_cur_mb,
            "allocated_chunks_mb": len(MEM_STRESS_BUFFER),
            "total_requests": TOTAL_REQUESTS,
            "total_orders": TOTAL_ORDERS,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "active_cart_items": sum(CART.values())
        }
    })

# ---------------------------------------------------------
# ACTIVE CPU BURNER & LOAD GENERATOR ENDPOINTS
# ---------------------------------------------------------
def _burn_cpu_worker(duration_sec):
    """Spins CPU in a tight mathematical loop to saturate core utilization."""
    end_time = time.time() + duration_sec
    while time.time() < end_time and not STRESS_STOP_FLAG:
        for _ in range(50000):
            _ = math.sqrt(987654.321) * math.sin(12345.678)

@app.route("/api/stress/cpu", methods=["POST", "GET"])
@app.route("/api/load/stress-cpu", methods=["POST", "GET"])
def stress_cpu():
    """
    Spawns aggressive multi-threaded CPU workers to spike CPU to 80-100%.
    Demonstrates CFS quota throttling live on the cluster.
    """
    global STRESS_STOP_FLAG
    STRESS_STOP_FLAG = False
    
    duration = int(request.args.get("duration", request.json.get("duration", 15) if request.is_json else 15))
    threads = int(request.args.get("threads", request.json.get("threads", 4) if request.is_json else 4))
    
    for _ in range(threads):
        t = threading.Thread(target=_burn_cpu_worker, args=(duration,), daemon=True)
        t.start()
        
    return jsonify({
        "status": "success",
        "message": f"🔥 Burning CPU on {threads} worker threads for {duration} seconds!",
        "threads": threads,
        "duration_sec": duration
    })

@app.route("/api/load/flash-sale", methods=["POST"])
def flash_sale_simulation():
    """
    Simulates a sudden burst of high e-commerce traffic.
    Combines CPU computation loops with order generation.
    """
    global STRESS_STOP_FLAG
    STRESS_STOP_FLAG = False
    data = request.get_json() or {}
    concurrency = int(data.get("concurrency", 20))
    
    def simulate_shopper():
        end_time = time.time() + 8
        while time.time() < end_time and not STRESS_STOP_FLAG:
            # Active CPU computation
            for _ in range(80000):
                _ = math.sqrt(12345.67) * math.sin(9876.54)
            global TOTAL_ORDERS
            TOTAL_ORDERS += 1
            time.sleep(0.01)

    for _ in range(concurrency):
        t = threading.Thread(target=simulate_shopper, daemon=True)
        t.start()
        
    return jsonify({
        "status": "success",
        "message": f"Simulating Flash Sale with {concurrency} concurrent shopper threads!",
        "tip": "Observe CPU% and memory climbing in real-time on the Monitoring tab."
    })

@app.route("/api/stress/memory", methods=["POST", "GET"])
@app.route("/api/load/stress-memory", methods=["POST", "GET"])
def stress_memory():
    """Allocates dirty memory chunks to test container limits and OOMKilled."""
    global MEM_STRESS_BUFFER
    target_mb = int(request.args.get("megabytes", 120))
    chunk_size = 1024 * 1024  # 1 MB
    for _ in range(target_mb):
        MEM_STRESS_BUFFER.append(bytearray(chunk_size))
        time.sleep(0.01)
    rss_mb, _ = get_process_stats()
    return jsonify({
        "message": f"Allocated {target_mb} MB in RAM.",
        "current_rss_mb": rss_mb,
        "total_buffer_mb": len(MEM_STRESS_BUFFER)
    })

@app.route("/api/stress/reset", methods=["POST", "GET"])
@app.route("/api/load/reset-stress", methods=["POST", "GET"])
def reset_stress():
    global MEM_STRESS_BUFFER, STRESS_STOP_FLAG
    STRESS_STOP_FLAG = True
    freed = len(MEM_STRESS_BUFFER)
    MEM_STRESS_BUFFER = []
    import gc
    gc.collect()
    rss_mb, _ = get_process_stats()
    return jsonify({"message": f"Freed {freed} MB and stopped CPU threads.", "current_rss_mb": rss_mb})

@app.route("/api/workload", methods=["GET"])
def compute_workload():
    """Computes mathematical / cryptographic operations to measure response time."""
    iterations = int(request.args.get("iterations", 300000))
    start_time = time.perf_counter()
    val = 0
    for i in range(1, iterations + 1):
        val += math.sqrt(i) * math.sin(i)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return jsonify({"status": "success", "iterations": iterations, "elapsed_ms": elapsed_ms})

@app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """Prometheus exposition format for external scraping."""
    rss_mb, cpu_pct = get_process_stats()
    output = [
        "# HELP ecommerce_http_requests_total Total HTTP requests received",
        "# TYPE ecommerce_http_requests_total counter",
        f'ecommerce_http_requests_total {TOTAL_REQUESTS}',
        "# HELP ecommerce_orders_placed_total Total orders successfully checked out",
        "# TYPE ecommerce_orders_placed_total counter",
        f'ecommerce_orders_placed_total {TOTAL_ORDERS}',
        "# HELP ecommerce_process_resident_memory_bytes Resident memory size in bytes",
        "# TYPE ecommerce_process_resident_memory_bytes gauge",
        f'ecommerce_process_resident_memory_bytes {int(rss_mb * 1024 * 1024)}',
        "# HELP ecommerce_process_cpu_percent Process CPU utilization percentage",
        "# TYPE ecommerce_process_cpu_percent gauge",
        f'ecommerce_process_cpu_percent {cpu_pct}',
    ]
    return Response("\n".join(output) + "\n", mimetype="text/plain; version=0.0.4")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "app": "CloudCommerce E-Commerce Service",
        "pod": os.environ.get("POD_NAME", "ecommerce-web-pod"),
        "timestamp": time.time()
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"============================================================")
    print(f"  CloudCommerce E-Commerce & K8s Telemetry Server Active")
    print(f"  URL: http://localhost:{port}")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
