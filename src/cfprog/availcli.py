"""CLI for the gym-availability layer: render the resolved week.

    cfprog-avail                             # usual week, no changes
    cfprog-avail --flags pm                  # this week starts late -> all-PM days
    cfprog-avail --flags sessions_hard       # hard week -> Monday AM+PM double
    cfprog-avail --rest wednesday            # day-to-day: rest Wednesday
    cfprog-avail --unavailable thursday      # travelling Thursday
    cfprog-avail --choose saturday=sat-wl-only
    cfprog-avail --day-flags saturday=wl_priority
    cfprog-avail --overrides week.json       # full override file (see WeekOverrides)

This is I/O only — all resolution lives in cfprog.availability and is unit-tested.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List

from cfprog.availability import (
    DayOverride,
    FixtureAvailabilityProvider,
    WeekOverrides,
    normalize_weekday,
    render_week_markdown,
    resolve_week,
)


def _split_csv(value: str) -> frozenset[str]:
    return frozenset(p.strip() for p in value.split(",") if p.strip())


def _parse_day_kv(items: List[str], field: str) -> Dict[str, dict]:
    """Parse repeated 'weekday=value' args into a {weekday: {field: ...}} map."""
    out: Dict[str, dict] = {}
    for item in items or ():
        if "=" not in item:
            raise SystemExit(f"--{field.replace('_', '-')} expects WEEKDAY=VALUE, got {item!r}")
        day, value = item.split("=", 1)
        out.setdefault(normalize_weekday(day), {})[field] = value
    return out


def _build_overrides(args: argparse.Namespace) -> WeekOverrides:
    if args.overrides:
        with open(args.overrides, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        loader = WeekOverrides.from_dated_dict if "dates" in data else WeekOverrides.from_dict
        return loader(data)

    day_data: Dict[str, dict] = {}
    for day in args.rest or ():
        day_data.setdefault(normalize_weekday(day), {})["rest"] = True
    for day in args.unavailable or ():
        day_data.setdefault(normalize_weekday(day), {})["unavailable"] = True
    for day, kv in _parse_day_kv(args.choose, "choose").items():
        day_data.setdefault(day, {}).update(kv)
    for day, kv in _parse_day_kv(args.day_flags, "flags").items():
        day_data.setdefault(day, {})["flags"] = sorted(_split_csv(kv["flags"]))

    days = {wd: DayOverride.from_dict(d) for wd, d in day_data.items()}
    return WeekOverrides(base_flags=_split_csv(args.flags or ""), days=days)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the resolved weekly gym availability."
    )
    parser.add_argument("--flags", help="week-wide context flags, comma-separated "
                                        "(e.g. pm,sessions_hard)")
    parser.add_argument("--rest", action="append", metavar="WEEKDAY",
                        help="force a rest day (repeatable)")
    parser.add_argument("--unavailable", action="append", metavar="WEEKDAY",
                        help="mark a day unavailable (repeatable)")
    parser.add_argument("--choose", action="append", metavar="WEEKDAY=OPTION_ID",
                        help="force a specific option (repeatable)")
    parser.add_argument("--day-flags", action="append", metavar="WEEKDAY=flag1,flag2",
                        dest="day_flags", help="per-day context flags (repeatable)")
    parser.add_argument("--overrides", metavar="FILE",
                        help="JSON override file (ignores the inline flags above)")
    parser.add_argument("--title", default="Weekly availability")
    args = parser.parse_args(argv)

    weekly = FixtureAvailabilityProvider().weekly()
    overrides = _build_overrides(args)
    week = resolve_week(weekly, overrides)
    print(render_week_markdown(week, title=args.title))
    return 0


if __name__ == "__main__":
    sys.exit(main())
