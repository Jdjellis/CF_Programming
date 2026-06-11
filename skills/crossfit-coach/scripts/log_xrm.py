"""Minimal X-rep-max (xRM) training log: append and read performed sets.

    python3 log_xrm.py add --lift front_squat --weight 120 --reps 3 --date 2026-06-11
    python3 log_xrm.py add --lift strict_press --weight 60 --reps 5 --rpe 8 --note "felt strong"
    python3 log_xrm.py list                       # all entries, newest first
    python3 log_xrm.py list --lift front_squat    # one lift's history + best estimated 1RM

The log is a flat JSON array at data/xrm_log.json — human-readable and diffable.
This is the v1 training log: it tracks xRMs so progress (and estimated 1RMs) can
be seen within a block. Estimation reuses cfprog.estimate (the inverse of the
calculator's rep-max table); no arithmetic happens by hand.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date as date_cls

sys.path.insert(0, os.path.dirname(__file__))

from cfprog.estimate import estimate_one_rm
from cfprog.maxes import normalize_lift

_LOG_PATH = os.path.join(os.path.dirname(__file__), "data", "xrm_log.json")


def _load() -> list[dict]:
    if not os.path.exists(_LOG_PATH):
        return []
    with open(_LOG_PATH, "r", encoding="utf-8") as fh:
        text = fh.read().strip()
    return json.loads(text) if text else []


def _save(entries: list[dict]) -> None:
    with open(_LOG_PATH, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _cmd_add(args: argparse.Namespace) -> int:
    entry = {
        "lift": normalize_lift(args.lift),
        "weight_kg": args.weight,
        "reps": args.reps,
        "rpe": args.rpe,
        "date": args.date or date_cls.today().isoformat(),
        "note": args.note,
    }
    entries = _load()
    entries.append(entry)
    _save(entries)
    est, _ = estimate_one_rm(args.weight, args.reps, args.rpe)
    rpe_str = f" @ RPE {args.rpe:g}" if args.rpe is not None else ""
    print(
        f"logged {entry['lift']}: {args.weight:g} kg x {args.reps}{rpe_str} "
        f"on {entry['date']} -> estimated 1RM ~{est:g} kg"
    )
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    entries = _load()
    if args.lift:
        key = normalize_lift(args.lift)
        entries = [e for e in entries if e["lift"] == key]
    if not entries:
        print("no entries" + (f" for {normalize_lift(args.lift)}" if args.lift else ""))
        return 0

    rows = sorted(entries, key=lambda e: e.get("date", ""), reverse=True)
    best = None
    for e in rows:
        est, _ = estimate_one_rm(e["weight_kg"], e["reps"], e.get("rpe"))
        best = est if best is None else max(best, est)
        rpe_str = f" @RPE{e['rpe']:g}" if e.get("rpe") is not None else ""
        note = f"  ({e['note']})" if e.get("note") else ""
        print(
            f"{e.get('date','?')}  {e['lift']:<14} {e['weight_kg']:g} x {e['reps']}"
            f"{rpe_str}  -> e1RM ~{est:g} kg{note}"
        )
    if args.lift:
        print(f"\nbest estimated 1RM for {normalize_lift(args.lift)}: ~{best:g} kg")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Minimal xRM training log.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="append a performed set")
    p_add.add_argument("--lift", required=True)
    p_add.add_argument("--weight", type=float, required=True, help="kg")
    p_add.add_argument("--reps", type=int, required=True)
    p_add.add_argument("--rpe", type=float, default=None)
    p_add.add_argument("--date", default=None, help="ISO date (default: today)")
    p_add.add_argument("--note", default=None)
    p_add.set_defaults(func=_cmd_add)

    p_list = sub.add_parser("list", help="show entries (optionally one lift)")
    p_list.add_argument("--lift", default=None)
    p_list.set_defaults(func=_cmd_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
