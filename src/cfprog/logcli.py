"""CLI for logging actuals and reading back basic analytics.

    cfprog-log set front_squat --weight 115 --reps 3 --rpe 8
    cfprog-log readiness amber --score 62 --source wearable
    cfprog-log show --lift front_squat
    cfprog-log ratios

Records go to the SQLite store (data/cfprog.db by default). Arithmetic is
delegated to cfprog.analytics; this is just I/O.
"""

from __future__ import annotations

import argparse
import sys

from cfprog.analytics import (
    best_estimated_one_rm,
    estimate_one_rm_for_set,
    ratio_gaps,
    tonnage,
)
from cfprog.logstore import LoggedSet, ReadinessEntry, SQLiteLogStore
from cfprog.maxes import FixtureMaxesProvider


def _cmd_set(args, store: SQLiteLogStore) -> int:
    entry = store.log_set(
        LoggedSet(
            lift=args.lift,
            weight_kg=args.weight,
            reps=args.reps,
            rpe=args.rpe,
            date=args.date,
            readiness=args.readiness,
            notes=args.notes,
        )
    )
    est = estimate_one_rm_for_set(entry)
    print(
        f"logged #{entry.id}: {entry.lift} {entry.weight_kg:g}kg x{entry.reps}"
        + (f" @RPE{entry.rpe:g}" if entry.rpe is not None else "")
        + f"  (est 1RM ~ {est:g} kg, tonnage {entry.tonnage_kg:g} kg)"
    )
    return 0


def _cmd_readiness(args, store: SQLiteLogStore) -> int:
    entry = store.log_readiness(
        ReadinessEntry(
            tier=args.tier, score=args.score, source=args.source,
            date=args.date, notes=args.notes,
        )
    )
    print(f"readiness for {entry.date}: {entry.tier}"
          + (f" (score {entry.score:g})" if entry.score is not None else ""))
    return 0


def _cmd_show(args, store: SQLiteLogStore) -> int:
    sets = store.sets(lift=args.lift, since=args.since)
    if not sets:
        print("no sets logged for that filter")
        return 0
    for s in sets:
        rpe = f" @RPE{s.rpe:g}" if s.rpe is not None else ""
        print(f"{s.date}  {s.lift:<14} {s.weight_kg:g}kg x{s.reps}{rpe}"
              f"  est1RM~{estimate_one_rm_for_set(s):g}")
    print(f"\n{len(sets)} sets | tonnage {tonnage(sets):g} kg"
          f" | best est 1RM {best_estimated_one_rm(sets):g} kg")
    return 0


def _cmd_ratios(args, store: SQLiteLogStore) -> int:
    for r in ratio_gaps(FixtureMaxesProvider()):
        print(r.summary())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Log actuals + basic analytics.")
    parser.add_argument("--db", default=None, help="SQLite path (default data/cfprog.db)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set", help="log a performed set")
    p_set.add_argument("lift")
    p_set.add_argument("--weight", type=float, required=True)
    p_set.add_argument("--reps", type=int, required=True)
    p_set.add_argument("--rpe", type=float, default=None)
    p_set.add_argument("--date", default=None)
    p_set.add_argument("--readiness", default=None, choices=["green", "amber", "red"])
    p_set.add_argument("--notes", default=None)
    p_set.set_defaults(func=_cmd_set)

    p_rd = sub.add_parser("readiness", help="log daily readiness")
    p_rd.add_argument("tier", choices=["green", "amber", "red"])
    p_rd.add_argument("--score", type=float, default=None)
    p_rd.add_argument("--source", default=None)
    p_rd.add_argument("--date", default=None)
    p_rd.add_argument("--notes", default=None)
    p_rd.set_defaults(func=_cmd_readiness)

    p_show = sub.add_parser("show", help="list logged sets")
    p_show.add_argument("--lift", default=None)
    p_show.add_argument("--since", default=None)
    p_show.set_defaults(func=_cmd_show)

    p_ratio = sub.add_parser("ratios", help="lift-ratio gap analysis vs standards")
    p_ratio.set_defaults(func=_cmd_ratios)

    args = parser.parse_args(argv)
    store = SQLiteLogStore(args.db)
    try:
        return args.func(args, store)
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
