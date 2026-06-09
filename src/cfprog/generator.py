"""Weekly generator — applies the policy to a class plan (spec Section 5a).

This is the glue between the policy (SKILL.md), the log (readiness), the maxes
(Sheet snapshot) and the deterministic calculator. It is **pure given its
inputs**: the same class plan + focus config + maxes always yield the same plan.
The policy/judgment is encoded as explicit, testable rules here — the model does
not make per-run decisions at runtime, and **no load arithmetic happens here**
(every weight comes from `LoadCalculator`).

Pipeline (policy, then arithmetic):
    1. TIER every piece of work (PROTECT / CRUISE / SKILL).
    2. PLACE focus-block sessions across the week, deconflicting against class
       stimulus (SKILL.md Section 3): no same-stimulus on consecutive days; don't
       double-load a pattern the class already taxes (prefer to *move* a PROTECT
       clash, else drop it with a flag); strength before conditioning on shared
       days.
    3. RESOLVE every strength target to kg + plates via the calculator.
    4. EMIT a structured `WeeklyPlan` (rendering lives in `render.py`), plus a
       per-day `daily_adjust` step for morning readiness.

Determinism note: placement is a deterministic greedy with explicit cost keys
and a stable tie-break (calendar day index), so the schedule is reproducible and
unit-testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from cfprog.calculator import LoadCalculator
from cfprog.availability import (
    AvailabilityProvider,
    DayStatus,
    ResolvedWeek,
    WEEKDAYS,
    WeekOverrides,
    resolve_week,
)
from cfprog.classplan import ClassPlanProvider, ClassSession, SetScheme, StrengthPiece
from cfprog.focus import FocusBlock, FocusTemplate
from cfprog.logstore import LogStore
from cfprog.models import PrescriptionResult

# Map availability DayStatus -> (human label, is a training day?)
_STATUS_LABEL = {
    DayStatus.TRAIN: "Train",
    DayStatus.OPEN_GYM: "Open gym",
    DayStatus.REST: "Rest",
    DayStatus.UNAVAILABLE: "Unavailable",
    DayStatus.NEEDS_CHOICE: "Needs choice",
}

# Tier ordering within a day and the triage order under time/energy pressure
# (SKILL.md §1, v1.1): PROTECT strength is priority #1 — never cut for skill. The
# athlete prefers training in class, so CRUISE sits just under it. ACCESSORY
# (low-CNS supporting work) and SKILL (frequency) are the flex — first to drop.
TIER_ORDER = {"PROTECT": 0, "CRUISE": 1, "ACCESSORY": 2, "SKILL": 3, "DELOAD": 1}
# Order in which work is shed when short on time or energy (lowest priority first).
TRIAGE_DROP_ORDER = ("SKILL", "ACCESSORY", "CRUISE", "PROTECT")
# Tiers that are optional on a squeezed/amber day (strength is protected).
FLEX_TIERS = ("ACCESSORY", "SKILL")
READINESS_TIERS = ("green", "amber", "red")

# Human-readable priority order under time/energy pressure (SKILL.md §1, v1.1).
_TRIAGE_GUIDE = (
    "1. PROTECT strength top sets — priority #1; never cut for skill.",
    "2. Class session (CRUISE) — you prefer training in class.",
    "3. Supporting accessory (ACCESSORY) — drop if time/energy short.",
    "4. Skill frequency (SKILL) — first to cut under pressure; cheap to catch another day.",
)


# ---------------------------------------------------------------------------
# Plan models (structured output — renderers consume these)
# ---------------------------------------------------------------------------

@dataclass
class ResolvedStrength:
    """A strength scheme with its calculator-resolved load."""

    label: str
    lift: str
    scheme: str                 # human-readable sets x reps @ target
    result: PrescriptionResult  # the deterministic load + plate loadout
    is_top_set: bool = False    # heaviest scheme of its piece (kept on amber)


@dataclass
class PlannedSession:
    """One session on a day: its tier, origin, loads, and any notes."""

    name: str
    origin: str                 # "class" | "focus"
    tier: str                   # PROTECT | CRUISE | ACCESSORY | SKILL
    stimulus: str
    prescriptions: List[ResolvedStrength] = field(default_factory=list)
    skill_items: List[str] = field(default_factory=list)
    movements: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    emphasis: str = ""          # week's "what to prioritise" focus (configurable)

    @property
    def order(self) -> int:
        return TIER_ORDER.get(self.tier, 1)


@dataclass
class DayPlan:
    """A single training (or rest) day."""

    day: str
    date: str
    class_stimulus: Optional[str] = None   # None on a rest / open-gym day with no WOD
    also_taxes: Tuple[str, ...] = ()
    is_rest: bool = False
    planned_readiness: str = "green"       # Sunday planning assumes GREEN
    # Availability context (populated when the generator consumes the availability
    # layer; None/empty when running class-plan-only).
    status: Optional[str] = None           # Train | Open gym | Rest | Unavailable | Needs choice
    class_slots: Tuple[str, ...] = ()      # resolved class slots (times) for the day
    avail_flags: Tuple[str, ...] = ()      # active availability context flags
    avail_notes: Tuple[str, ...] = ()      # notes from availability resolution
    sessions: List[PlannedSession] = field(default_factory=list)
    interference: List[str] = field(default_factory=list)

    def ordered_sessions(self) -> List[PlannedSession]:
        # Stable sort by tier order; preserves placement order within a tier.
        return sorted(self.sessions, key=lambda s: s.order)

    def taxed_patterns_set(self) -> set:
        """Everything the class loads this day (primary + secondary). Empty on rest."""
        if self.is_rest or self.class_stimulus is None:
            return set()
        return {self.class_stimulus, *self.also_taxes}


@dataclass
class WeeklyPlan:
    """The Sunday deliverable: schedule + tiers + loads + interference flags."""

    week_start: str
    source_label: str
    block_context: List[str]
    days: List[DayPlan]
    flags: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    triage: List[str] = field(default_factory=list)
    latest_known_readiness: Optional[str] = None

    # Ordered buckets for the "what to push / cruise / skip" summary.
    _SUMMARY_BUCKETS = ("PUSH", "CRUISE", "FLEX")
    _TIER_BUCKET = {
        "PROTECT": "PUSH",
        "CRUISE": "CRUISE",
        "ACCESSORY": "FLEX",
        "SKILL": "FLEX",
    }

    def push_cruise_skip(self) -> Dict[str, List[str]]:
        """The 'what to push / cruise / skip' summary, grouped by tier bucket.

        PUSH = PROTECT strength (priority #1). CRUISE = class work. FLEX =
        supporting accessory + skill (first to cut under time/energy pressure).
        """
        groups: Dict[str, List[str]] = {b: [] for b in self._SUMMARY_BUCKETS}
        for d in self.days:
            for s in d.ordered_sessions():
                groups[self._TIER_BUCKET.get(s.tier, "CRUISE")].append(f"{d.day}: {s.name}")
        return groups


# ---------------------------------------------------------------------------
# Deconfliction helpers (pure functions over the day list)
# ---------------------------------------------------------------------------

def _iso(d: str) -> date:
    return date.fromisoformat(d)


def _adjacent(day_a: DayPlan, day_b: DayPlan) -> bool:
    """Calendar-adjacent (1 day apart) — a rest day between breaks adjacency."""
    return abs((_iso(day_a.date) - _iso(day_b.date)).days) == 1


def _consecutive_same_stimulus(days: List[DayPlan], idx: int, stimulus: str) -> int:
    """How many calendar-adjacent training days carry `stimulus` as primary."""
    target = days[idx]
    count = 0
    for j, other in enumerate(days):
        if j == idx or other.is_rest:
            continue
        if _adjacent(target, other) and other.class_stimulus == stimulus:
            count += 1
    return count


def _focus_on_day(day: DayPlan) -> int:
    return sum(1 for s in day.sessions if s.origin == "focus")


def _class_strength_load(day: DayPlan) -> int:
    """How much heavy class barbell work the day already carries.

    Protected strength wants a *fresh* day, so placement prefers days where the
    class isn't already grinding through its own heavy lifts.
    """
    return sum(
        len(s.prescriptions) for s in day.sessions if s.origin == "class"
    )


def _focus_stimulus_adjacent(days: List[DayPlan], idx: int, stimulus: str) -> int:
    """Adjacent training days that already hold a placed focus of `stimulus`."""
    target = days[idx]
    count = 0
    for j, other in enumerate(days):
        if j == idx or other.is_rest:
            continue
        if _adjacent(target, other) and any(
            s.origin == "focus" and s.stimulus == stimulus for s in other.sessions
        ):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class WeeklyGenerator:
    """Builds a `WeeklyPlan` from a class plan, focus blocks, and the calculator."""

    def __init__(
        self,
        class_provider: ClassPlanProvider,
        focus_blocks: List[FocusBlock],
        calculator: Optional[LoadCalculator] = None,
        log_store: Optional[LogStore] = None,
        availability_provider: Optional[AvailabilityProvider] = None,
        overrides: Optional[WeekOverrides] = None,
        base_flags: Iterable[str] = (),
    ) -> None:
        self.class_provider = class_provider
        self.focus_blocks = list(focus_blocks)
        self.calc = calculator or LoadCalculator()
        self.log_store = log_store
        # Optional gym-availability layer. When supplied, it is the source of
        # truth for *which days/sessions* the athlete trains (the day spine);
        # the class plan supplies *what's in* each day. When omitted, the spine
        # is derived from the class plan alone (back-compatible).
        self.availability_provider = availability_provider
        self.overrides = overrides
        self.base_flags = tuple(base_flags)

    # -- load resolution ----------------------------------------------------

    def _resolve_piece(self, piece: StrengthPiece) -> List[ResolvedStrength]:
        """Resolve every scheme of a piece to a load. Calculator only — no math here."""
        resolved: List[ResolvedStrength] = []
        for scheme in piece.schemes:
            result = self.calc.prescribe(piece.lift, scheme.target)
            resolved.append(
                ResolvedStrength(
                    label=piece.label,
                    lift=piece.lift,
                    scheme=scheme.describe(),
                    result=result,
                )
            )
        # Mark the heaviest scheme as the top set (the one kept on amber days).
        if resolved:
            top = max(resolved, key=lambda r: r.result.working_weight_kg)
            top.is_top_set = True
        return resolved

    def _class_session(self, cs: ClassSession) -> PlannedSession:
        prescriptions: List[ResolvedStrength] = []
        for piece in cs.strength:
            prescriptions.extend(self._resolve_piece(piece))
        return PlannedSession(
            name=cs.title or "Class session",
            origin="class",
            tier="CRUISE",  # class metcons/strength are the relief valve (SKILL.md §1)
            stimulus=cs.stimulus,
            prescriptions=prescriptions,
            movements=list(cs.movements),
        )

    def _focus_session(self, block: FocusBlock, tpl: FocusTemplate) -> PlannedSession:
        prescriptions: List[ResolvedStrength] = []
        for piece in tpl.strength:
            prescriptions.extend(self._resolve_piece(piece))
        return PlannedSession(
            name=f"{tpl.name}  ·  {block.name}",
            origin="focus",
            tier=tpl.effective_tier(block.tier),
            stimulus=tpl.stimulus,
            prescriptions=prescriptions,
            skill_items=list(tpl.skill_items),
            movements=list(tpl.movements),
            emphasis=tpl.emphasis,
        )

    # -- placement / deconfliction -----------------------------------------

    def _place_protect_template(
        self, days: List[DayPlan], block: FocusBlock, tpl: FocusTemplate
    ) -> None:
        """Dispatch a PROTECT template (SKILL.md §3.3, v1.1).

        If the class already supplies this template's main lift somewhere this
        week and the template defines a low-CNS `complement`, defer the heavy
        stimulus to class and place the *supporting accessory* instead — never a
        competing barbell version of the lift. Otherwise place the protected
        barbell strength on the least-conflicting day.
        """
        training = [d for d in days if not d.is_rest]
        covered = any(tpl.stimulus in d.taxed_patterns_set() for d in training)
        if covered and tpl.use_complement_when_class_covers and tpl.complement:
            self._place_accessory(days, block, tpl, tpl.complement)
        else:
            self._place_protect(days, block, tpl)

    def _place_accessory(
        self,
        days: List[DayPlan],
        block: FocusBlock,
        primary: FocusTemplate,
        comp: FocusTemplate,
    ) -> None:
        """Append low-CNS supporting work to a non-clashing class day (never rest).

        The athlete prefers training in class, so this slots onto a class day
        whose stimulus does NOT already tax the accessory's pattern — keeping the
        rest day genuinely rest. The class covers the heavy lift; this only adds
        quad/knee development the class doesn't supply.
        """
        training = [d for d in days if not d.is_rest]
        candidates = [d for d in training if comp.stimulus not in d.taxed_patterns_set()]
        if not candidates:  # nowhere clash-free — still avoid the rest day
            candidates = training

        best = min(candidates, key=lambda d: (_focus_on_day(d), _iso(d.date).toordinal()))
        taxing_days = [d.day for d in training if primary.stimulus in d.taxed_patterns_set()]
        session = self._focus_session(block, comp)
        note = (
            f"Class already supplies {primary.stimulus} ({', '.join(taxing_days)}). "
            f"Deferring the heavy stimulus to class; personal squat work = supporting "
            f"accessory (low-CNS) appended to {best.day} — no competing barbell "
            f"front squat (SKILL.md §3.3)."
        )
        session.notes.append(note)  # inline on the session; not an interference flag
        self._decisions.append(
            f"{primary.name}: substituted supporting accessory on {best.day} "
            f"(class covers {primary.stimulus} on {', '.join(taxing_days)})."
        )
        best.sessions.append(session)

    def _place_protect(
        self, days: List[DayPlan], block: FocusBlock, tpl: FocusTemplate
    ) -> None:
        """Place one PROTECT template on the least-conflicting clean day.

        Policy 3.3: if every candidate day already taxes this pattern, the class
        covers the stimulus — move-or-drop resolves to *drop* with a flag.
        Otherwise pick the day minimising same-stimulus adjacency, tie-broken by
        emptiness then calendar order, and note any residual adjacency.
        """
        training = [d for d in days if not d.is_rest]
        # Candidate = a day the class does NOT already tax with this pattern.
        candidates = [
            d for d in training if tpl.stimulus not in d.taxed_patterns_set()
        ]
        if not candidates:
            taxing = [d.day for d in training if tpl.stimulus in d.taxed_patterns_set()]
            return self._drop_protect(days, block, tpl, taxing)

        def cost(d: DayPlan):
            idx = days.index(d)
            return (
                _consecutive_same_stimulus(days, idx, tpl.stimulus),  # avoid stacking
                _focus_stimulus_adjacent(days, idx, tpl.stimulus),    # spread focus
                _class_strength_load(d),                              # keep strength fresh
                _focus_on_day(d),                                     # keep days light
                _iso(d.date).toordinal(),                             # stable tie-break
            )

        best = min(candidates, key=cost)
        session = self._focus_session(block, tpl)
        idx = days.index(best)
        adj = _consecutive_same_stimulus(days, idx, tpl.stimulus)
        if adj:
            neighbours = [
                o.day for o in training
                if _adjacent(best, o) and o.class_stimulus == tpl.stimulus
            ]
            taxing_days = [d.day for d in training if tpl.stimulus in d.taxed_patterns_set()]
            note = (
                f"PROTECT {tpl.stimulus} placed {best.day} (no clash-free day this "
                f"week). Class taxes {tpl.stimulus} on {', '.join(taxing_days)}; "
                f"this sits next to {', '.join(neighbours)} — keep it submaximal or "
                f"drop it if the class dose was heavy (class covers the pattern)."
            )
            session.notes.append(note)
            best.interference.append(note)
        best.sessions.append(session)

    def _drop_protect(
        self, days: List[DayPlan], block: FocusBlock, tpl: FocusTemplate, taxing: List[str]
    ) -> None:
        flag = (
            f"DROPPED PROTECT '{tpl.name}' ({tpl.stimulus}): the class already "
            f"taxes {tpl.stimulus} on every training day this week "
            f"({', '.join(taxing)}). Per move-or-drop (SKILL.md §3.3), the class "
            f"supplies the stimulus — don't double-load it."
        )
        # Surface the drop on the most-loaded such day for visibility.
        for d in days:
            if not d.is_rest and tpl.stimulus in d.taxed_patterns_set():
                d.interference.append(flag)
                break
        self._dropped_flags.append(flag)

    def _place_skill(
        self, days: List[DayPlan], block: FocusBlock, tpl: FocusTemplate
    ) -> None:
        """Place one SKILL template. Frequency wins — never hard-excluded; only
        spread to avoid clustering and stacking on the class's same-stimulus day."""
        training = [
            d for d in days
            if not d.is_rest
            and not any(s.origin == "focus" and s.name == self._skill_name(block, tpl)
                        for s in d.sessions)
        ]
        if not training:
            return

        def cost(d: DayPlan):
            idx = days.index(d)
            same_day = 1 if tpl.stimulus in d.taxed_patterns_set() else 0
            return (
                _focus_stimulus_adjacent(days, idx, tpl.stimulus),    # don't cluster skill
                same_day,                                             # avoid class same-stim day
                _consecutive_same_stimulus(days, idx, tpl.stimulus),
                _focus_on_day(d),
                _iso(d.date).toordinal(),
            )

        best = min(training, key=cost)
        best.sessions.append(self._focus_session(block, tpl))

    @staticmethod
    def _skill_name(block: FocusBlock, tpl: FocusTemplate) -> str:
        return f"{tpl.name}  ·  {block.name}"

    # -- top-level generate -------------------------------------------------

    def generate(self) -> WeeklyPlan:
        self._dropped_flags: List[str] = []
        self._decisions: List[str] = []
        sessions = self.class_provider.sessions()

        # Build the day spine. When an availability layer is supplied it is the
        # source of truth for which days/sessions the athlete trains; otherwise
        # the spine is derived from the class plan (back-compatible).
        resolved = self._resolved_availability()
        if resolved is not None:
            days = self._build_days_from_availability(resolved)
        else:
            days = self._build_days_from_class(sessions)

        # 1+3. Attach + tier + load-resolve the class sessions (CRUISE), joining
        # the class plan onto the spine by date (multiple sessions/day allowed).
        self._attach_class_sessions(days, sessions)

        # 2. Place focus work — PROTECT templates first, then SKILL (policy order).
        # PROTECT may substitute its low-CNS complement when the class already
        # covers the lift (SKILL.md §3.3, v1.1).
        for block in sorted(self.focus_blocks, key=lambda b: TIER_ORDER.get(b.tier, 1)):
            for tpl in block.slots():
                if tpl.effective_tier(block.tier) == "PROTECT":
                    self._place_protect_template(days, block, tpl)
                else:
                    self._place_skill(days, block, tpl)

        return WeeklyPlan(
            week_start=self.class_provider.week_start(),
            source_label=getattr(self.class_provider, "source_label", "class plan"),
            block_context=self._block_context(),
            days=days,
            flags=list(self._dropped_flags),
            decisions=list(self._decisions),
            triage=list(_TRIAGE_GUIDE),
            latest_known_readiness=self._latest_readiness(),
        )

    # -- day spine ----------------------------------------------------------

    def _resolved_availability(self) -> Optional[ResolvedWeek]:
        if self.availability_provider is None:
            return None
        return resolve_week(
            self.availability_provider.weekly(), self.overrides, self.base_flags
        )

    def _build_days_from_availability(self, resolved: ResolvedWeek) -> List[DayPlan]:
        """Spine from the resolved availability week (Monday-first, 7 days).

        `week_start` (from the class plan) is assumed to be the Monday; each
        resolved weekday is dated off it. TRAIN / OPEN_GYM are trainable days;
        REST / UNAVAILABLE are rest; NEEDS_CHOICE is surfaced as a flag and left
        un-placed (the resolver wouldn't guess, so neither do we).
        """
        monday = _iso(self.class_provider.week_start())
        spine: List[DayPlan] = []
        for rd in resolved.days:
            offset = WEEKDAYS.index(rd.weekday)
            d = date.fromordinal(monday.toordinal() + offset)
            training = rd.status in (DayStatus.TRAIN, DayStatus.OPEN_GYM)
            notes = list(rd.notes)
            if rd.open_gym and rd.open_gym.available and rd.status == DayStatus.REST:
                when = (
                    f"before {rd.open_gym.before}" if rd.open_gym.before
                    else rd.open_gym.window or ""
                )
                notes.append(f"open gym available{f' ({when})' if when else ''}")
            day = DayPlan(
                day=d.strftime("%a"),
                date=d.isoformat(),
                is_rest=not training,
                status=_STATUS_LABEL.get(rd.status, rd.status.value),
                class_slots=tuple(str(s) for s in rd.sessions),
                avail_flags=tuple(sorted(rd.active_flags)),
                avail_notes=tuple(notes),
            )
            if rd.status == DayStatus.NEEDS_CHOICE:
                day.interference.append(
                    f"{day.day} {day.date}: availability NEEDS_CHOICE — no class "
                    "option matched the active flags; pick one (left un-placed)."
                )
            spine.append(day)
        return spine

    def _build_days_from_class(self, sessions: List[ClassSession]) -> List[DayPlan]:
        if not sessions:
            return []
        spine: List[DayPlan] = []
        ordered = sorted(sessions, key=lambda s: _iso(s.date))
        cur = _iso(ordered[0].date)
        end = _iso(ordered[-1].date)
        present = {cs.date for cs in ordered}
        while cur <= end:
            iso = cur.isoformat()
            spine.append(DayPlan(day=cur.strftime("%a"), date=iso, is_rest=iso not in present))
            cur = cur.fromordinal(cur.toordinal() + 1)
        return spine

    def _attach_class_sessions(
        self, days: List[DayPlan], sessions: List[ClassSession]
    ) -> None:
        """Join class WODs onto the spine by date; set the day's stimulus tags.

        Multiple class sessions per day are supported (e.g. an AM CrossFit + PM
        weightlifting double); the day's primary stimulus is the first session's,
        and `also_taxes` unions every attached session's patterns. A WOD landing
        on a non-training day is flagged, not silently scheduled.
        """
        by_date: Dict[str, List[ClassSession]] = {}
        for cs in sessions:
            by_date.setdefault(cs.date, []).append(cs)
        for d in days:
            css = by_date.get(d.date, [])
            if not css:
                continue
            if d.is_rest:
                self._dropped_flags.append(
                    f"{d.day} {d.date}: a class WOD exists but availability marks the "
                    f"day {d.status or 'rest'} — not scheduled."
                )
                continue
            for cs in css:
                d.sessions.append(self._class_session(cs))
            primary = css[0].stimulus
            taxed: set = set()
            for cs in css:
                taxed |= set(cs.taxed_patterns)
            d.class_stimulus = primary
            d.also_taxes = tuple(sorted(taxed - {primary}))

    def _block_context(self) -> List[str]:
        out: List[str] = []
        for b in self.focus_blocks:
            deload = "  ⚠ DELOAD week due" if b.is_deload_due else ""
            out.append(
                f"{b.name} — wk {b.current_week}/{b.length_weeks}, "
                f"{b.days_per_week}x/wk, {b.tier}{deload}"
            )
        return out

    def _latest_readiness(self) -> Optional[str]:
        if self.log_store is None:
            return None
        entry = self.log_store.latest_readiness()
        return entry.tier if entry else None

    # -- daily adjust -------------------------------------------------------

    def daily_adjust(self, day: DayPlan, readiness: str) -> DayPlan:
        """Re-emit a day's sessions adjusted for the morning's readiness.

        GREEN: unchanged (full top sets + back-off).
        AMBER: keep each piece's top set, trim back-off volume (~half the sets).
        RED:   drop loaded work to SKILL / active recovery; SKILL work survives.

        Loads are not recomputed by hand — trimming changes *set counts*, and any
        retained scheme is re-resolved through the same calculator, so the policy
        chooses the target and the calculator still owns the kilos.
        """
        readiness = readiness.lower()
        if readiness not in READINESS_TIERS:
            raise ValueError(f"readiness must be one of {READINESS_TIERS}, got {readiness!r}")

        adjusted = replace(
            day,
            planned_readiness=readiness,
            sessions=[],
            interference=list(day.interference),
        )
        if readiness == "green":
            adjusted.sessions = [self._copy_session(s) for s in day.sessions]
            return adjusted

        for s in day.ordered_sessions():
            if readiness == "amber":
                adjusted.sessions.append(self._amber_session(s))
            else:  # red
                red = self._red_session(s)
                if red is not None:
                    adjusted.sessions.append(red)
        if readiness == "red":
            adjusted.interference.append(
                "RED readiness: loaded PROTECT/CRUISE work dropped to skill / active "
                "recovery (SKILL.md §2). SKILL work is the 'productive when smashed' option."
            )
        return adjusted

    @staticmethod
    def _copy_session(s: PlannedSession) -> PlannedSession:
        return replace(
            s,
            prescriptions=list(s.prescriptions),
            skill_items=list(s.skill_items),
            movements=list(s.movements),
            notes=list(s.notes),
        )

    def _amber_session(self, s: PlannedSession) -> PlannedSession:
        out = self._copy_session(s)
        if s.tier in FLEX_TIERS:
            # Flex — strength is priority #1, so this is the first thing to drop
            # if time/energy is short. Kept here, but marked optional.
            out.notes = list(s.notes) + [
                "AMBER: flex item — drop first if short on time/energy "
                "(strength is the priority); otherwise keep it, it's low-cost."
            ]
            return out
        # Trim back-off volume; always keep the top set of each piece.
        trimmed: List[ResolvedStrength] = []
        for rs in s.prescriptions:
            new = replace(rs)
            new.scheme = self._trim_scheme(rs.scheme, keep_full=rs.is_top_set)
            trimmed.append(new)
        out.prescriptions = trimmed
        if s.tier == "PROTECT":
            out.notes = list(s.notes) + ["AMBER: top set kept, back-off volume trimmed ~half."]
        else:  # CRUISE
            out.notes = list(s.notes) + [
                "AMBER: relief valve — autoregulate intensity (drop ~1-2 RPE / trim "
                "rounds); keep movement quality. Back-off sets trimmed ~half."
            ]
        return out

    def _red_session(self, s: PlannedSession) -> Optional[PlannedSession]:
        if s.tier == "SKILL":
            return self._copy_session(s)  # survives a red day (cheap, frequency)
        if s.tier == "ACCESSORY":
            out = self._copy_session(s)
            out.notes = list(s.notes) + [
                "RED: keep rehab / mobility only (e.g. Spanish-squat holds, knee work); "
                "skip the loaded split / zombie squats."
            ]
            return out
        out = self._copy_session(s)
        out.prescriptions = []
        out.notes = list(s.notes) + [
            "RED: dropped to active recovery — skip loaded work; mobility / easy aerobic only."
        ]
        return out

    @staticmethod
    def _trim_scheme(scheme: str, keep_full: bool) -> str:
        """Halve the set count in a 'N x R @ ...' scheme string (top sets kept).

        Deterministic display-only transform; the per-set load is untouched.
        """
        if keep_full or " x " not in scheme:
            return scheme
        head, rest = scheme.split(" x ", 1)
        try:
            sets = int(head.strip())
        except ValueError:
            return scheme
        trimmed = max(1, math.ceil(sets / 2))
        return f"{trimmed} x {rest}"
