import argparse
import logging
from typing import Dict

from .config import Settings
from .generator import generate_events
from .storage import land_raw_batch, load_events


def ingest(count: int = 500, seed: int = 42) -> Dict:
    settings = Settings()
    events = generate_events(count=count, seed=seed)
    object_key = land_raw_batch(events, settings)
    inserted = load_events(events, settings)
    return {"generated": len(events), "inserted": inserted, "object_key": object_key}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and ingest industrial telemetry")
    parser.add_argument("--events", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = ingest(args.events, args.seed)
    logging.info("Ingestion complete: %s", result)


if __name__ == "__main__":
    main()
