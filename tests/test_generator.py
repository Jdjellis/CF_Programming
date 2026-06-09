"""Tests for the weekly generator: tiering, deconfliction placement, load
resolution, determinism, and the daily readiness-adjust step.

The generator is pure given its inputs, so every rule is asserted against a
realistic fixture week (the Claremont Competitors plan) plus a couple of
synthetic weeks that isolate edge cases (the move-or-drop branch, adjacency).
"""

import pytest

from cfprog.availability import (
    DayOverride,
    FixtureAvailabilityProvider,
    WeekOverrides,
)
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


def test_only_uncovered_lift_stays_protect(plan):
    """Class covers the squat this week -> the squat block demotes to ACCESSORY;
    strict press (class under-supplies it) is the only PROTECT."""
    protect = [s for d in plan.days for s in d.sessions if s.tier == "PROTECT"]
    accessory = [s for d in plan.days for s in d.sessions if s.tier == "ACCESSORY"]
    skill = [s for d in plan.days for s in d.sessions if s.tier == "SKILL"]
    assert {s.stimulus for s in protect} == {"press"}
    assert {s.stimulus for s in accessory} == {"heavy_squat"}
    assert all(s.stimulus == "gymnastics" for s in skill)
    assert all(s.origin == "focus" for s in protect + accessory + skill)


def test_push_cruise_skip_summary_groups_by_bucket(plan):
    groups = plan.push_cruise_skip()
    # Strict press is the only PUSH item this week (squat deferred to class).
    assert len(groups["PUSH"]) == 1
    assert "Strict Press strength" in groups["PUSH"][0]
    assert len(groups["CRUISE"]) == 5                       # five class days
    # FLEX = 3 ring-MU + 1 squat accessory
    assert len(groups["FLEX"]) == 4
    assert any("Quad / knee" in x for x in groups["FLEX"])


# ---------------------------------------------------------------------------
# Placement / deconfliction
# ---------------------------------------------------------------------------

def test_strict_press_protect_lands_on_a_clean_fresh_day(plan):
    """Class taxes 'press' Mon+Sat; the protected press avoids those, and the
    class-load tie-break keeps it off the heavy-barbell days (Wed) -> Thu."""
    press_days = [
        d.day for d in plan.days
        for s in d.sessions
        if s.tier == "PROTECT" and s.stimulus == "press"
    ]
    assert press_days == ["Thu"]
    assert not _sessions_of(plan, "Mon", tier="PROTECT")
    assert not _sessions_of(plan, "Sat", tier="PROTECT")


def test_squat_strength_substituted_with_accessory_when_class_covers(plan):
    """Class squats Mon/Wed/Sat -> defer the heavy stimulus to class. No
    competing barbell front squat; a low-CNS accessory is appended instead."""
    # No independent heavy front-squat strength anywhere.
    assert not [
        s for d in plan.days for s in d.sessions
        if s.tier == "PROTECT" and s.stimulus == "heavy_squat"
    ]
    accessory = [
        (d.day, s) for d in plan.days for s in d.sessions if s.tier == "ACCESSORY"
    ]
    assert len(accessory) == 1
    day, sess = accessory[0]
    assert "Quad / knee" in sess.name
    assert not sess.prescriptions          # supporting work, not a loaded barbell lift
    assert plan.decisions and "substituted supporting accessory" in plan.decisions[0]


def test_accessory_appended_to_light_nonclashing_class_day_never_rest(plan):
    accessory_days = [
        d for d in plan.days for s in d.sessions if s.tier == "ACCESSORY"
    ]
    for d in accessory_days:
        assert not d.is_rest                       # never the rest day
        assert "heavy_squat" not in d.taxed_patterns_set()  # non-clashing day
    assert {d.day for d in accessory_days} == {"Tue"}


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
    """Thu carries PROTECT strict press + a CRUISE gymnastics WOD -> strength first."""
    ordered = _day(plan, "Thu").ordered_sessions()
    tiers = [s.tier for s in ordered]
    assert tiers.index("PROTECT") < tiers.index("CRUISE")


def test_strength_outranks_skill_and_accessory_in_order(plan):
    """PROTECT sorts ahead of CRUISE, ACCESSORY and SKILL within a day."""
    from cfprog.generator import TIER_ORDER
    assert TIER_ORDER["PROTECT"] < TIER_ORDER["CRUISE"] < TIER_ORDER["ACCESSORY"]
    assert TIER_ORDER["ACCESSORY"] < TIER_ORDER["SKILL"]


def test_triage_guide_present_strength_first(plan):
    assert plan.triage
    assert "PROTECT strength" in plan.triage[0]
    assert "Skill" in plan.triage[-1]


def test_focus_sessions_carry_configurable_emphasis(plan):
    """The per-week drill focus is surfaced (point: refine what to prioritise)."""
    focus = [s for d in plan.days for s in d.sessions if s.origin == "focus"]
    ring = next(s for s in focus if "Ring MU" in s.name)
    press = next(s for s in focus if "Strict Press" in s.name)
    assert "false-grip" in ring.emphasis.lower()
    assert press.emphasis


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


def test_amber_keeps_protect_top_set_trims_backoff(gen, plan):
    """Thu's PROTECT strict press: top set kept (1x5 @RPE8), back-off 3x5 -> 2x5."""
    thu = _day(plan, "Thu")
    adj = gen.daily_adjust(thu, "amber")
    protect = next(s for s in adj.sessions if s.tier == "PROTECT")
    top = next(r for r in protect.prescriptions if r.is_top_set)
    backoff = next(r for r in protect.prescriptions if not r.is_top_set)
    assert top.scheme.startswith("1 x")        # top set untouched
    assert backoff.scheme.startswith("2 x")    # 3 sets -> trimmed to 2
    assert any("AMBER" in n for n in protect.notes)


def test_amber_marks_flex_optional_not_trimmed(gen, plan):
    """Skill/accessory are the flex items on amber -> kept but flagged optional."""
    tue = _day(plan, "Tue")
    adj = gen.daily_adjust(tue, "amber")
    acc = next(s for s in adj.sessions if s.tier == "ACCESSORY")
    assert any("flex" in n.lower() for n in acc.notes)


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


def test_red_keeps_accessory_as_rehab_only(gen, plan):
    tue = _day(plan, "Tue")
    adj = gen.daily_adjust(tue, "red")
    acc = next(s for s in adj.sessions if s.tier == "ACCESSORY")
    assert any("rehab" in n.lower() for n in acc.notes)


def test_invalid_readiness_rejected(gen, plan):
    with pytest.raises(ValueError):
        gen.daily_adjust(_day(plan, "Mon"), "purple")


# ---------------------------------------------------------------------------
# Availability integration (generator consumes the gym-availability layer)
# ---------------------------------------------------------------------------

@pytest.fixture
def avail_gen(calc):
    return WeeklyGenerator(
        class_provider=FixtureClassPlanProvider(),
        focus_blocks=load_focus_blocks(),
        calculator=calc,
        availability_provider=FixtureAvailabilityProvider(),
    )


def test_availability_drives_a_full_monday_to_sunday_spine(avail_gen):
    plan = avail_gen.generate()
    assert [d.day for d in plan.days] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    # Fri + Sun are rest in the template; the rest are training days.
    assert {d.day for d in plan.days if d.is_rest} == {"Fri", "Sun"}
    assert _day(plan, "Fri").status == "Rest"


def test_availability_surfaces_class_slots(avail_gen):
    plan = avail_gen.generate()
    # Monday's default option is the 17:30 CrossFit + 18:30 Weightlifting double.
    assert len(_day(plan, "Mon").class_slots) == 2
    assert any("Weightlifting" in s for s in _day(plan, "Mon").class_slots)
    # Tuesday's default is a single CrossFit class.
    assert len(_day(plan, "Tue").class_slots) == 1


def test_placement_is_stable_under_availability(avail_gen):
    """Deconfliction outcome is unchanged when the spine comes from availability."""
    plan = avail_gen.generate()
    press = [d.day for d in plan.days for s in d.sessions
             if s.tier == "PROTECT" and s.stimulus == "press"]
    accessory = [d.day for d in plan.days for s in d.sessions if s.tier == "ACCESSORY"]
    skill = [d.day for d in plan.days for s in d.sessions if s.tier == "SKILL"]
    assert press == ["Thu"]
    assert accessory == ["Tue"]
    assert skill == ["Mon", "Wed", "Sat"]


def test_override_rest_day_moves_protected_strength(calc):
    """Resting Thursday (override) forces the strict-press PROTECT off Thu."""
    overrides = WeekOverrides(days={"thursday": DayOverride(rest=True)})
    gen = WeeklyGenerator(
        FixtureClassPlanProvider(), load_focus_blocks(), calc,
        availability_provider=FixtureAvailabilityProvider(), overrides=overrides,
    )
    plan = gen.generate()
    assert _day(plan, "Thu").is_rest
    press = [d.day for d in plan.days for s in d.sessions
             if s.tier == "PROTECT" and s.stimulus == "press"]
    assert press and "Thu" not in press


def test_class_wod_on_availability_rest_day_is_flagged_not_scheduled(calc):
    """A WOD that lands on an availability-rested day is flagged, not scheduled."""
    overrides = WeekOverrides(days={"saturday": DayOverride(unavailable=True)})
    gen = WeeklyGenerator(
        FixtureClassPlanProvider(), load_focus_blocks(), calc,
        availability_provider=FixtureAvailabilityProvider(), overrides=overrides,
    )
    plan = gen.generate()
    sat = _day(plan, "Sat")
    assert sat.is_rest
    assert not sat.sessions                      # the Sat WOD is not scheduled
    assert any("not scheduled" in f for f in plan.flags)


def test_multi_session_day_attaches_all_and_unions_stimuli(calc):
    """Two class sessions on one date (e.g. AM CF + PM WL) both attach; the day's
    taxed patterns union (uses the class-plan fallback spine)."""
    sessions = [
        ClassSession(day="Mon", date="2026-06-08", title="AM CrossFit",
                     stimulus="engine", also_taxes=("gymnastics",)),
        ClassSession(day="Mon", date="2026-06-08", title="PM Weightlifting",
                     stimulus="heavy_squat", also_taxes=("heavy_pull",)),
    ]
    gen = WeeklyGenerator(
        InMemoryClassPlanProvider("2026-06-08", sessions), load_focus_blocks(), calc,
    )
    plan = gen.generate()
    mon = plan.days[0]
    class_sessions = [s for s in mon.sessions if s.origin == "class"]
    assert len(class_sessions) == 2
    assert mon.class_stimulus == "engine"        # first session's primary
    assert mon.taxed_patterns_set() == {"engine", "gymnastics", "heavy_squat", "heavy_pull"}
