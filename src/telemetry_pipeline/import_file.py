"""Import real newline-delimited JSON sensor readings, archive and build marts."""
import argparse
import json
import math
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from telemetry_pipeline.config import Settings
from telemetry_pipeline.storage import EXPECTED_KEYS, land_raw_batch, load_events


def validate(row, line):
    if not isinstance(row, dict) or set(row) != EXPECTED_KEYS:
        raise ValueError(f"Line {line}: expected fields {sorted(EXPECTED_KEYS)}")
    uuid.UUID(row["event_id"])
    stamp = datetime.fromisoformat(row["event_ts"].replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError(f"Line {line}: event_ts must be timezone-aware and not in the future")
    for key in ("machine_id", "line_id"):
        if not isinstance(row[key], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", row[key]):
            raise ValueError(f"Line {line}: invalid {key}")
    for key in ("temperature_c", "vibration_mm_s", "pressure_bar", "power_kw"):
        if type(row[key]) not in (int, float) or not math.isfinite(row[key]):
            raise ValueError(f"Line {line}: {key} must be finite numeric data")
    if row["status"] not in ("healthy", "warning", "critical") or row["schema_version"] != 1:
        raise ValueError(f"Line {line}: status must be healthy/warning/critical and schema_version 1")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    if args.path.stat().st_size > 100 * 1024 * 1024:
        parser.error("Split files larger than 100 MB")
    settings, batch, total = Settings(), [], 0
    def save(rows):
        land_raw_batch(rows, settings)
        return load_events(rows, settings)
    with args.path.open() as source:
        for line, text in enumerate(source, 1):
            if not text.strip():
                continue
            batch.append(validate(json.loads(text), line))
            if len(batch) == 1000:
                total += save(batch)
                batch = []
        if batch:
            total += save(batch)
    print(json.dumps({"inserted": total, "note": "Earlier batches remain committed if a later batch fails"}))
    if not args.no_build:
        subprocess.run(["dbt", "run", "--project-dir", "dbt_project"], check=True)


if __name__ == "__main__":
    main()
