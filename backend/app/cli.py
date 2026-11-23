import sys
import argparse
import logging
from app.pipeline import run_ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def main():
    parser = argparse.ArgumentParser(
        description="JobPulse CLI - Multi-Source Automated Job Ingestion"
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "full"],
        default="full",
        help="Sync mode: 'fast' (ATS + Public Feeds + Optional APIs) or 'full' (includes JobSpy)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default=None,
        help="Comma-separated collector names (e.g. 'public_feeds,ats_direct,jobspy,optional_apis,jsonld')",
    )

    args = parser.parse_args()

    sources_list = None
    if args.sources:
        sources_list = [s.strip() for s in args.sources.split(",") if s.strip()]

    print(f"Starting JobPulse ingestion (mode={args.mode}, sources={sources_list})...")
    results = run_ingestion(sources=sources_list, mode=args.mode)

    print("\n--- Ingestion Run Summary ---")
    total_found = 0
    total_new = 0
    total_merged = 0
    for r in results:
        status = r.get("status")
        name = r.get("collector")
        found = r.get("jobs_found", 0)
        new = r.get("new_jobs", 0)
        merged = r.get("duplicates_merged", 0)
        total_found += found
        total_new += new
        total_merged += merged
        print(f"• [{name}] status={status} | found={found} | new={new} | merged={merged}")

    print(f"\nTotals: Found={total_found}, New={total_new}, Merged={total_merged}")
    print("Ingestion complete.")


if __name__ == "__main__":
    main()
