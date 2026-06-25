"""Seed Supabase max_events from the local maxes fixture (one-time, idempotent).

The xRM log fixture is empty, so only maxes are seeded. Re-running skips lifts
that already have a source='seed' event.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO / "skills/crossfit-coach/scripts/data/maxes.fixture.json"


def main() -> int:
    dsn = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    rows = [
        (lift, float(entry["one_rm"]), f"{entry.get('year', 2025)}-01-01")
        for lift, entry in data["maxes"].items()
    ]
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        for lift, one_rm, on_date in rows:
            cur.execute(
                "insert into max_events (lift, weight_kg, date, source) "
                "select %s, %s, %s, 'seed' "
                "where not exists "
                "(select 1 from max_events where lift = %s and source = 'seed')",
                (lift, one_rm, on_date, lift),
            )
        conn.commit()
    print(f"seeded {len(rows)} maxes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
