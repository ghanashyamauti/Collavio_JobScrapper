import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def run_api_benchmark():
    client = TestClient(app)
    print("Testing GET /api/filters (first call / cold cache)...")
    t0 = time.time()
    r = client.get("/api/filters")
    print(f"First GET /api/filters status: {r.status_code}, took: {time.time() - t0:.3f}s")

    print("\nTesting GET /api/filters?country=Nicaragua (cached global + country cities)...")
    t1 = time.time()
    r2 = client.get("/api/filters?country=Nicaragua")
    print(f"GET /api/filters?country=Nicaragua status: {r2.status_code}, took: {time.time() - t1:.3f}s")

    print("\nTesting GET /api/filters (subsequent cached call)...")
    t2 = time.time()
    r3 = client.get("/api/filters")
    print(f"Subsequent GET /api/filters status: {r3.status_code}, took: {time.time() - t2:.4f}s")

    print("\nTesting GET /api/jobs?q=software+engineer&country=Nicaragua&exp_years=2 (user scenario)...")
    t3 = time.time()
    r4 = client.get("/api/jobs?q=software+engineer&country=Nicaragua&exp_years=2")
    data4 = r4.json()
    print(f"GET /api/jobs user search took: {time.time() - t3:.3f}s, total jobs: {data4.get('total')}")

    print("\nTesting GET /api/jobs?q=software+engineer (global search across 77k jobs)...")
    t4 = time.time()
    r5 = client.get("/api/jobs?q=software+engineer")
    data5 = r5.json()
    print(f"Global search took: {time.time() - t4:.3f}s, total jobs: {data5.get('total')}")

if __name__ == "__main__":
    run_api_benchmark()
