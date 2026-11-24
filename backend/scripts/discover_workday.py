import asyncio
import json
import os
import httpx

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data")

print("Downloading full Workday catalog (11,944 tenants)...")
r = httpx.get("https://raw.githubusercontent.com/Riley-Dorrington/job-board-aggregator/main/data/workday_companies.json", timeout=30.0)
all_slugs = r.json()
print(f"Downloaded {len(all_slugs)} tenants.")

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

verified = []

async def probe_one(client, sem, slug):
    parts = slug.split("|")
    if len(parts) != 3:
        return
    company, wd, site_id = parts
    wd_num = wd.replace("wd", "")
    base_url = f"https://{company}.wd{wd_num}.myworkdayjobs.com"
    api_url = f"{base_url}/wday/cxs/{company}/{site_id}/jobs"
    
    h = dict(headers)
    h["Origin"] = base_url
    h["Referer"] = f"{base_url}/{site_id}"

    async with sem:
        try:
            resp = await client.post(
                api_url,
                json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
                headers=h,
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total", 0)
                postings = data.get("jobPostings", [])
                if total > 0 and len(postings) > 0:
                    verified.append((slug, total))
                    print(f"[{len(verified)}] VERIFIED: {slug} ({total} jobs)")
        except Exception:
            pass

async def main():
    sem = asyncio.Semaphore(40)
    limits = httpx.Limits(max_keepalive_connections=40, max_connections=80)
    async with httpx.AsyncClient(limits=limits, headers=headers, follow_redirects=True) as client:
        # Check first 800 tenants
        batch = all_slugs[:800]
        tasks = [probe_one(client, sem, s) for s in batch]
        await asyncio.gather(*tasks)

    print(f"\nDiscovered {len(verified)} live Workday enterprises!")
    verified_slugs = [v[0] for v in verified]
    
    verified_file = os.path.join(DATA_DIR, "workday_companies.json")
    with open(verified_file, "w", encoding="utf-8") as f:
        json.dump(verified_slugs, f, indent=2)
    print(f"Saved {len(verified_slugs)} verified Workday tenants to {verified_file}.")

if __name__ == "__main__":
    asyncio.run(main())
