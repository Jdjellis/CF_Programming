"""CLI for the weekly generator: build the plan, render Markdown, daily-adjust.

    cfprog-week                      # generate + print the week (fixtures + availability)
    cfprog-week --out plan.md        # also write Markdown to a file
    cfprog-week --flags sessions_hard  # base availability flags for the week
    cfprog-week --no-availability     # spine from the class plan only (ignore availability)
    cfprog-week --adjust Thu amber   # re-emit one day for a morning readiness
    cfprog-week --adjust Mon red

The day spine comes from the gym-availability layer (which days/sessions); the
class plan supplies what's in each day. I/O only — all judgment is in the
generator, all arithmetic in the calculator.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from cfprog.availability import FixtureAvailabilityProvider
from cfprog.classplan import FixtureClassPlanProvider
from cfprog.focus import load_focus_blocks
from cfprog.generator import WeeklyGenerator
from cfprog.render import render_day_plan, render_weekly_plan


def _find_day(plan, key: str):
    key = key.lower()
    for d in plan.days:
        if d.day.lower() == key or d.date == key:
            return d
    raise SystemExit(f"no day {key!r} in plan; days: {[d.day for d in plan.days]}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Weekly generator (Phase 2).")
    parser.add_argument("--classplan", help="path to a class-plan fixture JSON")
    parser.add_argument("--focus", help="path to a focus-blocks fixture JSON")
    parser.add_argument("--availability", help="path to an availability template JSON")
    parser.add_argument(
        "--flags", nargs="*", default=[],
        help="base availability context flags for the week (e.g. sessions_hard pm)",
    )
    parser.add_argument(
        "--no-availability", action="store_true",
        help="ignore the availability layer; build the spine from the class plan only",
    )
    parser.add_argument("--out", help="write the rendered Markdown to this path")
    parser.add_argument(
        "--adjust", nargs=2, metavar=("DAY", "READINESS"),
        help="re-emit one day adjusted for readiness, e.g. --adjust Thu amber",
    )
    args = parser.parse_args(argv)

    availability = (
        None if args.no_availability
        else FixtureAvailabilityProvider(args.availability)
    )
    gen = WeeklyGenerator(
        class_provider=FixtureClassPlanProvider(args.classplan),
        focus_blocks=load_focus_blocks(args.focus),
        availability_provider=availability,
        base_flags=args.flags,
    )
    plan = gen.generate()

    if args.adjust:
        day_key, readiness = args.adjust
        day = _find_day(plan, day_key)
        adjusted = gen.daily_adjust(day, readiness)
        print(render_day_plan(
            adjusted, heading=f"Daily adjust — {day.day} @ {readiness.upper()}"
        ))
        return 0

    md = render_weekly_plan(plan)
    print(md)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md + "\n")
        print(f"\n[written to {args.out}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
