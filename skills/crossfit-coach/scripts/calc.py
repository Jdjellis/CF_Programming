"""Deterministic load/plate calculator — the skill's arithmetic entry point.

    python3 calc.py front_squat --percent 85
    python3 calc.py clean --rep-max 3
    python3 calc.py strict_press --rpe 8 --reps 5
    python3 calc.py --demo

Arithmetic is delegated to the tested deterministic modules; this is only I/O.
The model never computes a working weight or plate loadout in its head — it runs
this and pastes the output (PROJECT_SPEC §8).
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from cfprog.calculator import LoadCalculator
from cfprog.models import Target


def _build_target(args: argparse.Namespace) -> Target:
    if args.percent is not None:
        return Target.percent_of_1rm(args.percent)
    if args.rep_max is not None:
        return Target.rep_max(args.rep_max)
    if args.rpe is not None:
        return Target.rpe(reps=args.reps, rpe=args.rpe)
    raise SystemExit("specify one of --percent, --rep-max, or --rpe (with --reps)")


DEMO_CASES = [
    ("front_squat", Target.percent_of_1rm(85)),
    ("clean", Target.rep_max(3)),
    ("strict_press", Target.rpe(reps=5, rpe=8)),
    ("back_squat", Target.percent_of_1rm(70)),
    ("snatch", Target.rep_max(2)),
    ("deadlift", Target.percent_of_1rm(80)),
]


def _run_demo() -> int:
    calc = LoadCalculator()
    print("Load calculator — demo cases (maxes from fixture mirroring the Sheet)\n")
    for lift, target in DEMO_CASES:
        print(calc.prescribe(lift, target).summary())
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic load/plate calculator.")
    parser.add_argument("lift", nargs="?", help="e.g. front_squat, clean, strict_press")
    parser.add_argument("--percent", type=float, help="percent of 1RM, e.g. 85")
    parser.add_argument("--rep-max", type=int, dest="rep_max", help="rep-max target, e.g. 3")
    parser.add_argument("--rpe", type=float, help="RPE value (use with --reps)")
    parser.add_argument("--reps", type=int, default=1, help="reps for --rpe (default 1)")
    parser.add_argument("--demo", action="store_true", help="run the demo cases")
    args = parser.parse_args(argv)

    if args.demo or not args.lift:
        return _run_demo()

    calc = LoadCalculator()
    target = _build_target(args)
    print(calc.prescribe(args.lift, target).summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
