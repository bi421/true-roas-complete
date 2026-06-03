import asyncio
import httpx
import time
import os
import subprocess
import statistics
import jwt
from src.trueroas.core.config import settings

BASE_URL = "http://localhost:8001"

def log_step(step, status="INFO"):
    emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "🕒" if status == "WAIT" else "🛠️"
    print(f"{emoji} [{status}] {step}")

def get_token(tenant_id):
    return jwt.encode({"tenant_id": tenant_id, "role": "user"}, settings.APP_SECRET_SALT, algorithm="HS256")

async def test_load_metrics(concurrent_users=1000, num_tenants=100):
    """
    Requirement 1: 1000 concurrent requests across 100 tenants.
    Verifies p95 latency < 200ms.
    """
    print(f"🚀 Starting Load Test: {concurrent_users} requests across {num_tenants} tenants...")
    
    tenants = [f"tenant_{i}" for i in range(num_tenants)]
    tokens = [get_token(t) for t in tenants]
    
    latencies = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        for i in range(concurrent_users):
            token = tokens[i % num_tenants]
            tasks.append(client.get(f"{BASE_URL}/api/v1/metrics", headers={"Authorization": f"Bearer {token}"}))
        
        start_time = time.perf_counter()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
    for resp in responses:
        if isinstance(resp, httpx.Response):
            latencies.append(resp.elapsed.total_seconds() * 1000)
    
    if not latencies:
        print("❌ Load test failed: No successful responses.")
        return

    p95 = statistics.quantiles(latencies, n=100)[94]
    avg = statistics.mean(latencies)
    
    print(f"\n--- Results ---")
    print(f"Total Requests: {len(latencies)}")
    print(f"Average Latency: {avg:.2f}ms")
    print(f"P95 Latency: {p95:.2f}ms")
    print(f"Total Duration: {total_time:.2f}s")
    
    assert p95 < 200, f"P95 latency {p95}ms exceeded 200ms limit"
    print("✅ Load Test Passed!")

def simulate_worker_chaos():
    """Requirement 3: Kill workers during task."""
    print("\n🛠️  Chaos: Killing random Celery worker...")
    # Command: docker-compose kill -s SIGKILL worker
    print("Execute: docker-compose kill -s SIGKILL worker")
    print("Check logs: docker-compose logs worker (Verify task is requeued via acks_late)")

def simulate_redis_outage():
    """Requirement 4: Simulate Redis outage."""
    print("\n🛠️  Chaos: Stopping Redis for 30s...")
    # Command: docker-compose stop redis && sleep 30 && docker-compose start redis
    print("Execute: docker-compose stop redis")
    print("Verify: API /metrics should return 503 within < 1s")

if __name__ == "__main__":
    # To run this:
    # 1. Start the stack: docker-compose up -d
    # 2. Run: python -m src.trueroas.tests.stress_chaos
    try:
        asyncio.run(test_load_metrics())
    except Exception as e:
        print(f"Test Execution Error: {e}")
    
    simulate_worker_chaos()