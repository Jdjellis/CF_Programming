"""Tests for the weekly generator: tiering, deconfliction placement, load
resolution, determinism, and the daily readiness-adjust step.

The generator is pure given its inputs, so every rule is asserted against a
realistic fixture week (the Claremont Competitors plan) plus a couple of
synthetic weeks that isolate edge cases (the move-or-drop branch, adjacency).
"""

import pytest

from cfprog.calculator import LoadCalculator
from cfprog.classplan import (
    ClassSession,
    FixtureClassPlanProvider,
    InMemoryClassPlanProvider,
    SetScheme,
    StrengthPiece,
)
from cfprog.focus import FocusBlock, FocusTemplate, load_focus_blocks
from cfprog.generator import WeeklyGenerator
from cfprog.models import Target


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def calc():
    return LoadCalculator()


@pytest.fixture
def gen(calc):
    return WeeklyGenerator(
        class_provider=FixtureClassPlanProvider(),
        focus_blocks=load_focus_blocks(),
        calculator=calc,
    )


@pytest.fixture
def plan(gen):
    return gen.generate()


def _day(plan, label):
    return next(d for d in plan.days if d.day == label)


def _sessions_of(plan, label, tier=None, origin=None):
    out = []
    for s in _day(plan, label).sessions:
        if tier is not None and s.tier != tier:
            continue
        if origin is not None and s.origin != origin:
            continue
        out.append(s)
    return out


# ---------------------------------------------------------------------------
# Tiering
# ---------------------------------------------------------------------------

def test_class_sessions_are_cruise(plan):
    for label in ("Mon", "Tue", "Wed", "Thu", "Sat"):
        class_sessions = _sessions_of(plan, label, origin="class")
        assert class_sessions, f"{label} should have a class session"
        assert all(s.tier == "CRUISE" for s in class_sessions)


def test_focus_strength_is_protect_and_skill_is_skill(plan):
    protect = [s for d in plan.days for s in d.sessions if s.tier == "PROTECT"]
    skill = [s for d in plan.days for s in d.sessions if s.tier == "SKILL"]
    assert {s.stimulus for s in protect} == {"heavy_squat", "press"}
    assert all(s.stimulus == "gymnastics" for s in skill)
    assert all(s.origin == "focus" for s in protect + skill)


def test_push_cruise_skip_summary_groups_by_tier(plan):
    groups = plan.push_cruise_skip()
    assert any("Strict Press" in x for x in groups["PUSH"])
    assert any("Front Squat strength" in x for x in groups["PUSH"])
    assert len(groups["SKILL/SKIP"]) == 3  # ring-MU placed 3x
    assert len(groups["CRUISE"]) == 5      # five class days


# ---------------------------------------------------------------------------
# Placement / deconfliction
# ---------------------------------------------------------------------------

def test_strict_press_avoids_days_the_class_already_presses(plan):
    """Class taxes 'press' on Mon and Sat -> strict-press PROTECT must not land
    there; it goes to the earliest clean day (Tue)."""
    press_days = [
        d.day for d in plan.days
        for s in d.sessions
        if s.tier == "PROTECT" and s.stimulus == "press"
    ]
    assert press_days == ["Tue"]
    assert not _sessions_of(plan, "Mon", tier="PROTECT")
    assert not _sessions_of(plan, "Sat", tier="PROTECT")


def test_front_squat_protect_lands_on_least_conflicting_day(plan):
    """Class squats Mon/Wed/Sat; only Tue/Thu are clash-free. Tue sits between
    two squat days (Mon+Wed), Thu next to one (Wed) -> Thu wins, with a flag."""
    fs_days = [
        d.day for d in plan.days
        for s in d.sessions
        if s.tier == "PROTECT" and s.stimulus == "heavy_squat"
    ]
    assert fs_days == ["Thu"]
    thu = _day(plan, "Thu")
    assert thu.interference, "residual adjacency should be flagged"
    assert "Mon, Wed, Sat" in thu.interference[0]


def test_ring_mu_skill_placed_three_times_and_spread(plan):
    skill_days = [
        d.day for d in plan.days
        for s in d.sessions
        if s.tier == "SKILL"
    ]
    assert len(skill_days) == 3
    assert len(set(skill_days)) == 3            # no day double-booked
    # spread away from the class-gymnastics days (Tue/Thu)
    assert skill_days == ["Mon", "Wed", "Sat"]


def test_strength_sequenced_before_conditioning_on_shared_day(plan):
    """Tue carries PROTECT strict press + a CRUISE engine WOD -> strength first."""
    ordered = _day(plan, "Tue").ordered_sessions()
    tiers = [s.tier for s in ordered]
    assert tiers.index("PROTECT") < tiers.index("CRUISE")


def test_rest_day_present_and_empty(plan):
    fri = _day(plan, "Fri")
    assert fri.is_rest
    assert fri.sessions == []


# ---------------------------------------------------------------------------
# Move-or-drop branch (synthetic week)
# ---------------------------------------------------------------------------

def _squat_every_day_week():
    days = [
        ("Mon", "2026-06-08"), ("Tue", "2026-06-09"), ("Wed", "2026-06-10"),
        ("Thu", "2026-06-11"), ("Fri", "2026-06-12"),
    ]
    sessions = [
        ClassSession(day=d, date=dt, title=f"{d} squat", stimulus="heavy_squat")
        for d, dt in days
    ]
    return InMemoryClassPlanProvider("2026-06-08", sessions)


def _fs_protect_block():
    piece = StrengthPiece(
        lift="front_squat", label="Paused FS",
        schemes=(SetScheme(sets=3, target=Target.percent_of_1rm(80), reps=3),),
    )
    tpl = FocusTemplate(name="FS strength", stimulus="heavy_squat", strength=(piece,))
    return FocusBlock(
        name="FS block", length_weeks=6, current_week=2,
        days_per_week=1, tier="PROTECT", templates=(tpl,),
    )


def test_protect_dropped_when_class_taxes_pattern_every_day(calc):
    gen = WeeklyGenerator(_squat_every_day_week(), [_fs_protect_block()], calc)
    plan = gen.generate()
    # No PROTECT placed anywhere...
    assert not [s for d in plan.days for s in d.sessions if s.tier == "PROTECT"]
    # ...and a move-or-drop flag is raised.
    assert plan.flags
    assert "DROPPED PROTECT" in plan.flags[0]
    assert "every training day" in plan.flags[0]


# ---------------------------------------------------------------------------
# Load resolution (calculator owns the kilos)
# ---------------------------------------------------------------------------

def test_loads_match_the_calculator_exactly(plan, calc):
    """Every resolved load equals a direct calculator call — no generator math."""
    mon_class = _sessions_of(plan, "Mon", origin="class")[0]
    bs = next(p for p in mon_class.prescriptions if p.lift == "back_squat")
    direct = calc.prescribe("back_squat", Target.percent_of_1rm(87.5))
    assert bs.result.working_weight_kg == direct.working_weight_kg
    assert bs.result.loadout.achieved_kg == direct.loadout.achieved_kg == 144.5


def test_top_set_is_the_heaviest_scheme(plan):
    """Monday's push-press ladder tops out at 85% -> that scheme is the top set."""
    mon_class = _sessions_of(plan, "Mon", origin="class")[0]
    pp = [p for p in mon_class.prescriptions if p.lift == "push_press"]
    tops = [p for p in pp if p.is_top_set]
    assert len(tops) == 1
    assert "85%" in tops[0].scheme


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_generation_is_deterministic(gen):
    a, b = gen.generate(), gen.generate()
    def shape(p):
        return [
            (d.day, [(s.tier, s.stimulus, s.name) for s in d.ordered_sessions()])
            for d in p.days
        ]
    assert shape(a) == shape(b)


# ---------------------------------------------------------------------------
# Daily adjust
# ---------------------------------------------------------------------------

def test_green_adjust_is_unchanged(gen, plan):
    thu = _day(plan, "Thu")
    adj = gen.daily_adjust(thu, "green")
    before = [(s.name, [r.scheme for r in s.prescriptions]) for s in thu.ordered_sessions()]
    after = [(s.name, [r.scheme for r in s.prescriptions]) for s in adj.ordered_sessions()]
    assert before == after


def test_amber_keeps_top_set_trims_backoff(gen, plan):
    thu = _day(plan, "Thu")
    adj = gen.daily_adjust(thu, "amber")
    protect = next(s for s in adj.sessions if s.tier == "PROTECT")
    top = next(r for r in protect.prescriptions if r.is_top_set)
    backoff = next(r for r in protect.prescriptions if not r.is_top_set)
    assert top.scheme.startswith("1 x")        # top set untouched
    assert backoff.scheme.startswith("2 x")    # 3 sets -> trimmed to 2
    assert any("AMBER" in n for n in protect.notes)


def test_red_drops_loaded_work_keeps_skill(gen, plan):
    mon = _day(plan, "Mon")
    adj = gen.daily_adjust(mon, "red")
    by_tier = {s.tier for s in adj.sessions}
    assert "SKILL" in by_tier                  # ring-MU survives
    cruise = next(s for s in adj.sessions if s.tier == "CRUISE")
    assert cruise.prescriptions == []          # loaded work dropped
    assert any("RED" in n for n in cruise.notes)
    skill = next(s for s in adj.sessions if s.tier == "SKILL")
    assert skill.skill_items                   # skill content intact


def test_invalid_readiness_rejected(gen, plan):
    with pytest.raises(ValueError):
        gen.daily_adjust(_day(plan, "Mon"), "purple")
