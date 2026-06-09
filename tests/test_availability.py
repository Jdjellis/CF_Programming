"""Tests for the gym-availability layer: general schedule + week/day overrides.

These pin the deterministic resolution rules against the athlete's real general
schedule (data/availability.template.json): most-specific eligible option wins,
explicit choice overrides flag logic, and overrides compose with the template
without mutating it.
"""

from datetime import date

import pytest

from cfprog.availability import (
    WEEKDAYS,
    ClassSlot,
    DayAvailability,
    DayOption,
    DayOverride,
    DayStatus,
    FixtureAvailabilityProvider,
    WeekOverrides,
    WeeklyAvailability,
    normalize_weekday,
    render_week_markdown,
    resolve_day,
    resolve_week,
    weekday_name,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def weekly() -> WeeklyAvailability:
    return FixtureAvailabilityProvider().weekly()


def _ids(day) -> list[str]:
    return [o.id for o in day.options]


# ---------------------------------------------------------------------------
# Loading the general schedule
# ---------------------------------------------------------------------------

def test_template_loads_all_seven_days(weekly):
    assert set(weekly.days) == set(WEEKDAYS)
    assert weekly.version == "1.0.0"


def test_friday_and_sunday_are_rest_with_open_gym(weekly):
    fri = weekly.day("friday")
    sun = weekly.day("sunday")
    assert fri.rest_day and sun.rest_day
    assert fri.open_gym and fri.open_gym.available
    assert sun.open_gym and sun.open_gym.before == "12:00"


def test_class_slot_time_of_day():
    assert ClassSlot("05:30", "crossfit", "CrossFit").time_of_day == "am"
    assert ClassSlot("18:30", "weightlifting", "WL").time_of_day == "pm"


# ---------------------------------------------------------------------------
# Weekday normalisation
# ---------------------------------------------------------------------------

def test_normalize_weekday_accepts_abbreviations():
    assert normalize_weekday("Mon") == "monday"
    assert normalize_weekday("THURS") == "thursday"
    assert normalize_weekday("saturday") == "saturday"


def test_normalize_weekday_rejects_unknown():
    with pytest.raises(ValueError):
        normalize_weekday("someday")


def test_weekday_name_from_date():
    # 2026-06-09 is a Tuesday.
    assert weekday_name(date(2026, 6, 9)) == "tuesday"


# ---------------------------------------------------------------------------
# Monday: AM+PM double only when sessions are hard
# ---------------------------------------------------------------------------

def test_monday_defaults_to_pm_double(weekly):
    r = resolve_day(weekly.day("monday"))
    assert r.status is DayStatus.TRAIN
    assert r.chosen_option_id == "mon-pm-cf-pm-wl"
    assert [s.time for s in r.sessions] == ["17:30", "18:30"]


def test_monday_hard_picks_am_pm_double(weekly):
    r = resolve_day(weekly.day("monday"), base_flags={"sessions_hard"})
    assert r.chosen_option_id == "mon-am-cf-pm-wl"
    assert r.sessions[0].time == "05:30"


def test_monday_hard_but_pm_excludes_morning_option(weekly):
    # Hard day but can't do the morning -> the AM option is excluded by `pm`,
    # so it falls back to the all-PM double.
    r = resolve_day(weekly.day("monday"), base_flags={"sessions_hard", "pm"})
    assert r.chosen_option_id == "mon-pm-cf-pm-wl"


# ---------------------------------------------------------------------------
# Tuesday: AM by default, PM when the `pm` flag is set
# ---------------------------------------------------------------------------

def test_tuesday_defaults_am(weekly):
    r = resolve_day(weekly.day("tuesday"))
    assert r.chosen_option_id == "tue-am-cf"


def test_tuesday_pm_flag_swaps_to_evening(weekly):
    r = resolve_day(weekly.day("tuesday"), base_flags={"pm"})
    assert r.chosen_option_id == "tue-pm-cf"
    assert r.sessions[0].time == "17:30"


# ---------------------------------------------------------------------------
# Wednesday: preferred AM-WL/PM-CF, all-PM alternative under `pm`
# ---------------------------------------------------------------------------

def test_wednesday_preferred_default(weekly):
    r = resolve_day(weekly.day("wednesday"))
    assert r.chosen_option_id == "wed-am-wl-pm-cf"


def test_wednesday_pm_uses_all_pm_option(weekly):
    r = resolve_day(weekly.day("wednesday"), base_flags={"pm"})
    assert r.chosen_option_id == "wed-pm-cf-pm-wl"


# ---------------------------------------------------------------------------
# Thursday: default is gymnastics + comp
# ---------------------------------------------------------------------------

def test_thursday_defaults_to_gym_plus_comp(weekly):
    r = resolve_day(weekly.day("thursday"))
    assert r.chosen_option_id == "thu-gym-comp"
    assert [s.time for s in r.sessions] == ["17:30", "18:30"]


def test_thursday_choose_comp_only(weekly):
    ov = DayOverride(choose="thu-comp")
    r = resolve_day(weekly.day("thursday"), ov)
    assert r.chosen_option_id == "thu-comp"
    assert len(r.sessions) == 1


# ---------------------------------------------------------------------------
# Saturday: the three-way priority logic
# ---------------------------------------------------------------------------

def test_saturday_default_cf_then_wl(weekly):
    r = resolve_day(weekly.day("saturday"))
    assert r.chosen_option_id == "sat-cf-wl"


def test_saturday_wl_priority_drops_crossfit(weekly):
    r = resolve_day(weekly.day("saturday"), base_flags={"wl_priority"})
    assert r.chosen_option_id == "sat-wl-only"
    assert [s.discipline for s in r.sessions] == ["weightlifting"]


def test_saturday_double_needs_both_flags(weekly):
    # Only one of the two flags -> not the double.
    r = resolve_day(weekly.day("saturday"), base_flags={"needs_double"})
    assert r.chosen_option_id == "sat-cf-wl"
    r2 = resolve_day(weekly.day("saturday"), base_flags={"needs_double", "wl_heavy"})
    assert r2.chosen_option_id == "sat-double-wl-heavy"


def test_saturday_double_beats_wl_priority_on_specificity(weekly):
    # All three flags: the 2-flag double option is more specific than wl-only.
    r = resolve_day(
        weekly.day("saturday"),
        base_flags={"wl_priority", "needs_double", "wl_heavy"},
    )
    assert r.chosen_option_id == "sat-double-wl-heavy"


# ---------------------------------------------------------------------------
# Override precedence: unavailable > rest > choose > flags
# ---------------------------------------------------------------------------

def test_unavailable_trumps_everything(weekly):
    ov = DayOverride(unavailable=True, choose="mon-am-cf-pm-wl")
    r = resolve_day(weekly.day("monday"), ov, base_flags={"sessions_hard"})
    assert r.status is DayStatus.UNAVAILABLE
    assert r.sessions == ()


def test_rest_override_forces_rest(weekly):
    r = resolve_day(weekly.day("monday"), DayOverride(rest=True))
    assert r.status is DayStatus.REST
    assert r.sessions == ()


def test_choose_wins_over_flags(weekly):
    # Flags would pick the PM double, but an explicit choice forces the AM one
    # even though its `pm` exclusion would normally bar it.
    ov = DayOverride(choose="mon-am-cf-pm-wl")
    r = resolve_day(weekly.day("monday"), ov, base_flags={"pm"})
    assert r.chosen_option_id == "mon-am-cf-pm-wl"


def test_choose_unknown_option_raises(weekly):
    with pytest.raises(KeyError):
        resolve_day(weekly.day("monday"), DayOverride(choose="nope"))


# ---------------------------------------------------------------------------
# Open gym / rest-day overrides
# ---------------------------------------------------------------------------

def test_rest_day_is_rest_by_default(weekly):
    r = resolve_day(weekly.day("friday"))
    assert r.status is DayStatus.REST
    assert r.open_gym and r.open_gym.available


def test_rest_day_open_gym_session_added(weekly):
    ov = DayOverride(extra_sessions=(ClassSlot("10:00", "open_gym", "Skill work"),))
    r = resolve_day(weekly.day("sunday"), ov)
    assert r.status is DayStatus.OPEN_GYM
    assert r.sessions[0].class_name == "Skill work"


def test_extra_session_appends_to_training_day(weekly):
    ov = DayOverride(extra_sessions=(ClassSlot("12:00", "open_gym", "Rehab"),))
    r = resolve_day(weekly.day("tuesday"), ov)
    assert r.chosen_option_id == "tue-am-cf"
    assert r.sessions[-1].class_name == "Rehab"


# ---------------------------------------------------------------------------
# NEEDS_CHOICE when nothing is eligible
# ---------------------------------------------------------------------------

def test_needs_choice_when_no_option_eligible():
    # A day whose only option requires a flag that isn't active -> needs choice.
    day = DayAvailability(
        weekday="monday",
        options=(
            DayOption(
                id="only", label="Only if flagged",
                sessions=(ClassSlot("17:00", "crossfit", "CrossFit"),),
                requires=frozenset({"some_flag"}),
            ),
        ),
    )
    r = resolve_day(day)
    assert r.status is DayStatus.NEEDS_CHOICE
    assert r.chosen_option_id is None
    assert r.notes  # explains why


# ---------------------------------------------------------------------------
# Whole-week resolution + flag composition
# ---------------------------------------------------------------------------

def test_resolve_week_is_monday_first(weekly):
    week = resolve_week(weekly)
    assert tuple(d.weekday for d in week.days) == WEEKDAYS


def test_resolve_week_default_training_days(weekly):
    week = resolve_week(weekly)
    training = {d.weekday for d in week.training_days}
    assert training == {"monday", "tuesday", "wednesday", "thursday", "saturday"}


def test_week_base_flags_merge_with_override_flags(weekly):
    # base_flags arg + overrides.base_flags + per-day flags all compose.
    overrides = WeekOverrides(
        base_flags=frozenset({"pm"}),
        days={"saturday": DayOverride(flags=frozenset({"wl_priority"}))},
    )
    week = resolve_week(weekly, overrides)
    assert week.day("tuesday").chosen_option_id == "tue-pm-cf"        # from base
    assert week.day("saturday").chosen_option_id == "sat-wl-only"     # per-day flag
    assert "pm" in week.day("saturday").active_flags                  # base reaches Sat


def test_week_overrides_from_dict(weekly):
    overrides = WeekOverrides.from_dict(
        {
            "base_flags": ["sessions_hard"],
            "days": {
                "wednesday": {"rest": True},
                "friday": {
                    "extra_sessions": [
                        {"time": "11:00", "discipline": "open_gym", "class_name": "Engine"}
                    ]
                },
            },
        }
    )
    week = resolve_week(weekly, overrides)
    assert week.day("monday").chosen_option_id == "mon-am-cf-pm-wl"   # sessions_hard
    assert week.day("wednesday").status is DayStatus.REST
    assert week.day("friday").status is DayStatus.OPEN_GYM


def test_week_overrides_from_dated_dict(weekly):
    overrides = WeekOverrides.from_dated_dict(
        {"dates": {"2026-06-09": {"unavailable": True}}}  # a Tuesday
    )
    week = resolve_week(weekly, overrides)
    assert week.day("tuesday").status is DayStatus.UNAVAILABLE


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def test_render_week_markdown_smoke(weekly):
    md = render_week_markdown(resolve_week(weekly), title="Test week")
    assert md.startswith("# Test week")
    assert "## Monday — Train" in md
    assert "## Friday — Rest" in md
    assert "17:30 — CrossFit" in md


# ---------------------------------------------------------------------------
# Immutability: resolving doesn't mutate the template
# ---------------------------------------------------------------------------

def test_resolution_does_not_mutate_template(weekly):
    before = _ids(weekly.day("saturday"))
    resolve_week(weekly, WeekOverrides(base_flags=frozenset({"wl_priority"})))
    assert _ids(weekly.day("saturday")) == before
