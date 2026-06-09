"""Athlete gym availability: the general weekly schedule + week/day overrides.

This is the *availability* layer the weekly generator consumes (spec Section 5a,
"available training days"; Section 9, interim class-plan input). It answers one
question deterministically: **given my usual weekly schedule, plus whatever has
changed this week or today, which sessions am I actually doing each day?**

Two inputs, cleanly separated:

1. **General availability** — the usual weekly schedule, read from
   ``data/availability.template.json`` behind an ``AvailabilityProvider``
   interface (same pattern as ``MaxesProvider``). Each day offers one or more
   *options*; an option is an ordered list of class slots. Options carry
   ``requires`` / ``excludes`` context flags so the resolver can pick the right
   one (e.g. the Monday AM+PM double only when the day is hard).

2. **Overrides** — week-to-week or day-to-day changes layered on top: rest a
   day, mark it unavailable, force a specific option, set context flags, or add
   an ad-hoc open-gym session. Overrides never edit the template; they compose
   with it at resolve time.

No load arithmetic happens here, and no stimulus is invented — availability is
about *when/what class*, not the day's specific WOD. That stays the calculator's
and the class plan's job (spec Section 8: the model never does load math; this
module does none either).

Resolution rule (deterministic, total): for a trainable day, the chosen option
is the **most specific eligible** one — eligible means every ``requires`` flag is
active and no ``excludes`` flag is active; most specific means the most
``requires`` satisfied, ties broken by listed order. An explicit ``choose``
override wins outright. If nothing is eligible the day resolves to
``NEEDS_CHOICE`` rather than guessing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Protocol, Tuple, runtime_checkable

_DEFAULT_TEMPLATE = (
    Path(__file__).resolve().parents[2] / "data" / "availability.template.json"
)

# Monday-first canonical week order. date.weekday() indexes into this.
WEEKDAYS: Tuple[str, ...] = (
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
)


def normalize_weekday(name: str) -> str:
    """Canonicalise a weekday name to lowercase full form (e.g. 'Mon' -> 'monday')."""
    key = name.strip().lower()
    for full in WEEKDAYS:
        if full == key or full.startswith(key) and len(key) >= 3:
            return full
    raise ValueError(f"unknown weekday {name!r}; expected one of {WEEKDAYS}")


def weekday_name(d: date) -> str:
    """The canonical weekday name for a date."""
    return WEEKDAYS[d.weekday()]


# ---------------------------------------------------------------------------
# General-availability models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClassSlot:
    """A single class on offer: a time, a discipline, and a class name."""

    time: str                       # local 24h "HH:MM"
    discipline: str                 # crossfit | weightlifting | gymnastics | comp | open_gym
    class_name: str

    @property
    def time_of_day(self) -> str:
        """'am' if the slot starts before noon, else 'pm'."""
        hour = int(self.time.split(":", 1)[0])
        return "am" if hour < 12 else "pm"

    def __str__(self) -> str:
        return f"{self.time} {self.class_name}"

    @classmethod
    def from_dict(cls, data: Mapping) -> "ClassSlot":
        return cls(
            time=str(data["time"]),
            discipline=str(data.get("discipline", "")),
            class_name=str(data.get("class_name", data.get("discipline", "session"))),
        )


@dataclass(frozen=True)
class DayOption:
    """One way to train a given day: an ordered list of class slots.

    ``requires`` flags must all be active for this option to be eligible;
    ``excludes`` flags must all be inactive. An option with empty ``requires``
    is the unconditional default/fallback for the day.
    """

    id: str
    label: str
    sessions: Tuple[ClassSlot, ...]
    requires: frozenset[str] = frozenset()
    excludes: frozenset[str] = frozenset()
    default: bool = False
    note: Optional[str] = None      # e.g. "preferred", or when it applies

    def is_eligible(self, active_flags: frozenset[str]) -> bool:
        return self.requires <= active_flags and not (self.excludes & active_flags)

    def specificity(self) -> int:
        """How conditional this option is — more requires => more specific."""
        return len(self.requires)

    @classmethod
    def from_dict(cls, data: Mapping) -> "DayOption":
        return cls(
            id=str(data["id"]),
            label=str(data["label"]),
            sessions=tuple(ClassSlot.from_dict(s) for s in data.get("sessions", ())),
            requires=frozenset(data.get("requires", ())),
            excludes=frozenset(data.get("excludes", ())),
            default=bool(data.get("default", False)),
            note=data.get("preferred_when") or data.get("note"),
        )


@dataclass(frozen=True)
class OpenGym:
    """Open-gym availability for a (usually rest) day."""

    available: bool = False
    window: Optional[str] = None     # e.g. "daytime"
    before: Optional[str] = None     # e.g. "12:00"
    note: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Mapping]) -> Optional["OpenGym"]:
        if not data:
            return None
        return cls(
            available=bool(data.get("available", False)),
            window=data.get("window"),
            before=data.get("before"),
            note=data.get("note"),
        )


@dataclass(frozen=True)
class DayAvailability:
    """A weekday's general availability: its options (or a rest day)."""

    weekday: str
    options: Tuple[DayOption, ...] = ()
    rest_day: bool = False
    open_gym: Optional[OpenGym] = None

    def option(self, option_id: str) -> DayOption:
        for o in self.options:
            if o.id == option_id:
                return o
        raise KeyError(
            f"no option {option_id!r} for {self.weekday}; "
            f"known: {[o.id for o in self.options]}"
        )

    def default_option(self) -> Optional[DayOption]:
        """The option flagged default, else the first unconditional one, else None."""
        for o in self.options:
            if o.default:
                return o
        for o in self.options:
            if not o.requires:
                return o
        return None

    @classmethod
    def from_dict(cls, weekday: str, data: Mapping) -> "DayAvailability":
        return cls(
            weekday=weekday,
            options=tuple(DayOption.from_dict(o) for o in data.get("options", ())),
            rest_day=bool(data.get("rest_day", False)),
            open_gym=OpenGym.from_dict(data.get("open_gym")),
        )


@dataclass(frozen=True)
class WeeklyAvailability:
    """The whole general week, keyed by canonical weekday name."""

    days: Mapping[str, DayAvailability]
    version: Optional[str] = None

    def day(self, weekday: str) -> DayAvailability:
        return self.days[normalize_weekday(weekday)]

    @classmethod
    def from_dict(cls, data: Mapping) -> "WeeklyAvailability":
        week = data.get("week", {})
        days = {
            normalize_weekday(name): DayAvailability.from_dict(
                normalize_weekday(name), day_data
            )
            for name, day_data in week.items()
        }
        # Any weekday absent from the file is a plain rest day.
        for wd in WEEKDAYS:
            days.setdefault(wd, DayAvailability(weekday=wd, rest_day=True))
        return cls(days=days, version=data.get("version"))


# ---------------------------------------------------------------------------
# Provider interface (mirrors MaxesProvider)
# ---------------------------------------------------------------------------

@runtime_checkable
class AvailabilityProvider(Protocol):
    """Anything that can supply the general weekly availability."""

    def weekly(self) -> WeeklyAvailability: ...


class FixtureAvailabilityProvider:
    """Reads the general weekly schedule from the local template JSON.

    Phase-2 stand-in for any future source (a calendar feed, a Sheet tab). Swap
    by implementing ``weekly()`` elsewhere; callers don't change.
    """

    def __init__(self, template_path: Path | str | None = None) -> None:
        self.template_path = Path(template_path) if template_path else _DEFAULT_TEMPLATE
        with open(self.template_path, "r", encoding="utf-8") as fh:
            self._data = json.load(fh)

    def weekly(self) -> WeeklyAvailability:
        return WeeklyAvailability.from_dict(self._data)


# ---------------------------------------------------------------------------
# Overrides — the week-to-week / day-to-day flexibility
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DayOverride:
    """A change to one day, layered over the general schedule.

    Precedence when resolving a day:
        unavailable  -> the day is off the table entirely
        rest         -> force a rest day (training options ignored)
        choose       -> force a specific option by id (wins over flag logic)
        flags        -> add context flags, then resolve normally
    ``extra_sessions`` are always appended (e.g. an ad-hoc open-gym slot), and
    apply even on a rest day (turning it into an open-gym day).
    """

    unavailable: bool = False
    rest: bool = False
    choose: Optional[str] = None
    flags: frozenset[str] = frozenset()
    extra_sessions: Tuple[ClassSlot, ...] = ()
    note: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping) -> "DayOverride":
        return cls(
            unavailable=bool(data.get("unavailable", False)),
            rest=bool(data.get("rest", False)),
            choose=data.get("choose"),
            flags=frozenset(data.get("flags", ())),
            extra_sessions=tuple(
                ClassSlot.from_dict(s) for s in data.get("extra_sessions", ())
            ),
            note=data.get("note"),
        )


@dataclass(frozen=True)
class WeekOverrides:
    """Per-weekday overrides plus week-wide context flags.

    ``base_flags`` apply to every day (e.g. set ``pm`` for a week of late
    starts); per-day ``flags`` add to them.
    """

    base_flags: frozenset[str] = frozenset()
    days: Mapping[str, DayOverride] = field(default_factory=dict)

    def for_day(self, weekday: str) -> DayOverride:
        return self.days.get(normalize_weekday(weekday), DayOverride())

    @classmethod
    def from_dict(cls, data: Mapping) -> "WeekOverrides":
        days = {
            normalize_weekday(name): DayOverride.from_dict(od)
            for name, od in data.get("days", {}).items()
        }
        return cls(base_flags=frozenset(data.get("base_flags", ())), days=days)

    @classmethod
    def from_dated_dict(cls, data: Mapping) -> "WeekOverrides":
        """Build from a date-keyed override map (ISO 'YYYY-MM-DD' -> override).

        Convenience for genuinely day-specific changes; dates collapse to their
        weekday. ``base_flags`` is still read from the top level.
        """
        days = {
            weekday_name(date.fromisoformat(iso)): DayOverride.from_dict(od)
            for iso, od in data.get("dates", {}).items()
        }
        return cls(base_flags=frozenset(data.get("base_flags", ())), days=days)


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

class DayStatus(str, Enum):
    TRAIN = "train"
    REST = "rest"
    OPEN_GYM = "open_gym"
    UNAVAILABLE = "unavailable"
    NEEDS_CHOICE = "needs_choice"  # trainable day, but no option is eligible


@dataclass(frozen=True)
class ResolvedDay:
    """The concrete plan for one day after applying overrides."""

    weekday: str
    status: DayStatus
    sessions: Tuple[ClassSlot, ...] = ()
    chosen_option_id: Optional[str] = None
    active_flags: frozenset[str] = frozenset()
    open_gym: Optional[OpenGym] = None
    notes: Tuple[str, ...] = ()

    @property
    def is_training(self) -> bool:
        return self.status in (DayStatus.TRAIN, DayStatus.OPEN_GYM)


@dataclass(frozen=True)
class ResolvedWeek:
    """Monday-first list of resolved days."""

    days: Tuple[ResolvedDay, ...]

    def day(self, weekday: str) -> ResolvedDay:
        wd = normalize_weekday(weekday)
        for d in self.days:
            if d.weekday == wd:
                return d
        raise KeyError(wd)

    @property
    def training_days(self) -> Tuple[ResolvedDay, ...]:
        return tuple(d for d in self.days if d.is_training)


def _pick_option(
    options: Iterable[DayOption], active_flags: frozenset[str]
) -> Optional[DayOption]:
    """Most-specific eligible option; ties broken by listed order. None if no fit."""
    best: Optional[Tuple[int, int, DayOption]] = None
    for index, opt in enumerate(options):
        if not opt.is_eligible(active_flags):
            continue
        # Higher specificity wins; for equal specificity the earlier index wins
        # (so we compare on -index and keep the max).
        key = (opt.specificity(), -index)
        if best is None or key > (best[0], best[1]):
            best = (key[0], key[1], opt)
    return best[2] if best else None


def resolve_day(
    day: DayAvailability,
    override: DayOverride | None = None,
    base_flags: Iterable[str] = (),
) -> ResolvedDay:
    """Resolve one day's general availability against an override. Deterministic."""
    override = override or DayOverride()
    active_flags = frozenset(base_flags) | override.flags
    notes: List[str] = []
    if override.note:
        notes.append(override.note)

    extra = override.extra_sessions

    # 1) Unavailable trumps everything.
    if override.unavailable:
        return ResolvedDay(
            weekday=day.weekday, status=DayStatus.UNAVAILABLE,
            active_flags=active_flags, open_gym=day.open_gym, notes=tuple(notes),
        )

    # 2) Forced rest (still allow an ad-hoc open-gym slot to ride along).
    if override.rest:
        status = DayStatus.OPEN_GYM if extra else DayStatus.REST
        return ResolvedDay(
            weekday=day.weekday, status=status, sessions=extra,
            active_flags=active_flags, open_gym=day.open_gym, notes=tuple(notes),
        )

    # 3) General rest day — open gym only if the override adds a session.
    if day.rest_day and not override.choose:
        status = DayStatus.OPEN_GYM if extra else DayStatus.REST
        return ResolvedDay(
            weekday=day.weekday, status=status, sessions=extra,
            active_flags=active_flags, open_gym=day.open_gym, notes=tuple(notes),
        )

    # 4) Explicit choice wins over flag logic.
    if override.choose:
        opt = day.option(override.choose)  # raises if unknown -> caller error
        notes.append(f"forced option: {opt.label}")
        return ResolvedDay(
            weekday=day.weekday, status=DayStatus.TRAIN,
            sessions=opt.sessions + extra, chosen_option_id=opt.id,
            active_flags=active_flags, open_gym=day.open_gym, notes=tuple(notes),
        )

    # 5) Pick the most-specific eligible option.
    opt = _pick_option(day.options, active_flags)
    if opt is None:
        if not day.options:
            # No options and not a rest day: only an ad-hoc session, if any.
            status = DayStatus.OPEN_GYM if extra else DayStatus.REST
            return ResolvedDay(
                weekday=day.weekday, status=status, sessions=extra,
                active_flags=active_flags, open_gym=day.open_gym, notes=tuple(notes),
            )
        notes.append(
            "no option matches the active flags "
            f"({sorted(active_flags) or 'none'}); pick one explicitly"
        )
        return ResolvedDay(
            weekday=day.weekday, status=DayStatus.NEEDS_CHOICE, sessions=extra,
            active_flags=active_flags, open_gym=day.open_gym, notes=tuple(notes),
        )

    if opt.note:
        notes.append(opt.note)
    return ResolvedDay(
        weekday=day.weekday, status=DayStatus.TRAIN,
        sessions=opt.sessions + extra, chosen_option_id=opt.id,
        active_flags=active_flags, open_gym=day.open_gym, notes=tuple(notes),
    )


def resolve_week(
    weekly: WeeklyAvailability,
    overrides: WeekOverrides | None = None,
    base_flags: Iterable[str] = (),
) -> ResolvedWeek:
    """Resolve the whole week. ``base_flags`` merges with ``overrides.base_flags``."""
    overrides = overrides or WeekOverrides()
    week_flags = frozenset(base_flags) | overrides.base_flags
    days = tuple(
        resolve_day(weekly.days[wd], overrides.for_day(wd), week_flags)
        for wd in WEEKDAYS
    )
    return ResolvedWeek(days=days)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_STATUS_LABEL = {
    DayStatus.TRAIN: "Train",
    DayStatus.OPEN_GYM: "Open gym",
    DayStatus.REST: "Rest",
    DayStatus.UNAVAILABLE: "Unavailable",
    DayStatus.NEEDS_CHOICE: "Needs choice",
}


def render_week_markdown(week: ResolvedWeek, title: str = "Weekly availability") -> str:
    """Render a resolved week as a readable Markdown summary."""
    lines = [f"# {title}", ""]
    for d in week.days:
        head = f"## {d.weekday.capitalize()} — {_STATUS_LABEL[d.status]}"
        if d.active_flags:
            head += f"  _(flags: {', '.join(sorted(d.active_flags))})_"
        lines.append(head)
        if d.sessions:
            for s in d.sessions:
                disc = f" · {s.discipline}" if s.discipline else ""
                lines.append(f"- {s.time} — {s.class_name}{disc}")
        elif d.status in (DayStatus.REST, DayStatus.OPEN_GYM) and d.open_gym \
                and d.open_gym.available:
            when = d.open_gym.before and f"before {d.open_gym.before}" \
                or d.open_gym.window or ""
            tail = f" ({when})" if when else ""
            lines.append(f"- _open gym available{tail}_")
        elif d.status == DayStatus.UNAVAILABLE:
            lines.append("- _not training_")
        elif d.status == DayStatus.NEEDS_CHOICE:
            lines.append("- _no option selected_")
        for n in d.notes:
            lines.append(f"  - note: {n}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
