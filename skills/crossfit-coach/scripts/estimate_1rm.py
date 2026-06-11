"""Estimate a 1RM from a performed set (xRM). Deterministic; wraps cfprog.estimate.

    python3 estimate_1rm.py --lift front_squat --weight 120 --reps 3
    python3 estimate_1rm.py --lift strict_press --weight 60 --reps 5 --rpe 8

Prints the estimated 1RM (kg) and any RPE/clamping assumption the table surfaced.
Arithmetic is the inverse of the calculator's rep-max table — the model never
estimates a 1RM in its head.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from cfprog.estimate import estimate_one_rm
from cfprog.maxes import normalize_lift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate 1RM from a performed set.")
    parser.add_argument("--lift", required=True, help="e.g. front_squat, clean")
    parser.add_argument("--weight", type=float, required=True, help="weight lifted (kg)")
    parser.add_argument("--reps", type=int, required=True, help="reps performed")
    parser.add_argument("--rpe", type=float, default=None, help="optional RPE of the set")
    args = parser.parse_args(argv)

    est, notes = estimate_one_rm(args.weight, args.reps, args.rpe)
    lift = normalize_lift(args.lift)
    rpe_str = f" @ RPE {args.rpe:g}" if args.rpe is not None else ""
    print(f"{lift}: {args.weight:g} kg x {args.reps}{rpe_str} -> estimated 1RM ~{est:g} kg")
    for n in notes:
        print(f"    note: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
