import httpx
import sys

candidates = [
    # Pune focus
    "pubmatic", "ensono", "modulr", "rubrik", "ivalua", "zocdoc", "druva", "mindtickle",
    # Mumbai focus
    "browserstack", "clevertap", "dream11", "games24x7", "upstox", "bookmyshow", "fractal",
    # India tech general
    "stripe", "razorpay", "postman", "phonepe", "meesho", "swiggy", "cred", "groww", "urbancompany",
    "inmobi", "cars24", "delhivery", "paytm", "zomato"
]

print("=== Testing Greenhouse ===", flush=True)
for slug in candidates:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        r = httpx.get(url, timeout=3.0)
        if r.status_code == 200:
            jobs = r.json().get("jobs", [])
            pune = sum(1 for j in jobs if "pune" in (j.get("location", {}).get("name", "")).lower())
            mumbai = sum(1 for j in jobs if "mumbai" in (j.get("location", {}).get("name", "")).lower() or "bombay" in (j.get("location", {}).get("name", "")).lower())
            india = sum(1 for j in jobs if "india" in (j.get("location", {}).get("name", "")).lower() or "bangalore" in (j.get("location", {}).get("name", "")).lower() or "bengaluru" in (j.get("location", {}).get("name", "")).lower())
            print(f"GH: {slug:<15} -> {len(jobs):4d} total | Pune: {pune:2d} | Mumbai: {mumbai:2d} | India: {india:2d}", flush=True)
    except Exception as e:
        pass

print("\n=== Testing Lever ===", flush=True)
for slug in candidates:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        r = httpx.get(url, timeout=3.0)
        if r.status_code == 200:
            jobs = r.json()
            if isinstance(jobs, list):
                pune = sum(1 for j in jobs if "pune" in (j.get("categories", {}).get("location", "") or "").lower())
                mumbai = sum(1 for j in jobs if "mumbai" in (j.get("categories", {}).get("location", "") or "").lower())
                india = sum(1 for j in jobs if "india" in (j.get("categories", {}).get("location", "") or "").lower())
                print(f"Lever: {slug:<15} -> {len(jobs):4d} total | Pune: {pune:2d} | Mumbai: {mumbai:2d} | India: {india:2d}", flush=True)
    except Exception as e:
        pass

