"""cfprog — personal CrossFit programming + autoregulation system.

Phase 1 surface:
    - Deterministic load/plate calculator (cfprog.plates, cfprog.targets, cfprog.calculator)
    - Maxes read behind an interface (cfprog.maxes), sourced from the Google Sheet
      top section (stubbed to a local fixture until Sheets auth is wired).

Hard rule (spec Section 8): all arithmetic lives in tested, deterministic code.
The model never does load math at runtime.
"""

from cfprog.models import (
    Plate,
    PlateInventory,
    Target,
    Loadout,
    PlateCount,
    PrescriptionResult,
)
from cfprog.targets import REP_MAX_PCT, resolve_target_fraction, resolve_target_weight
from cfprog.plates import best_loadout
from cfprog.calculator import LoadCalculator
from cfprog.maxes import (
    MaxesProvider,
    FixtureMaxesProvider,
    GoogleSheetsMaxesProvider,
    SHEET_ID,
)
from cfprog.logstore import (
    LoggedSet,
    ReadinessEntry,
    LogStore,
    SQLiteLogStore,
    READINESS_TIERS,
)
from cfprog.analytics import (
    estimate_one_rm,
    best_estimated_one_rm,
    tonnage,
    tonnage_by_lift,
    ratio_gaps,
    RATIO_STANDARDS,
)
from cfprog.classplan import (
    STIMULUS_TAGS,
    SetScheme,
    StrengthPiece,
    ClassSession,
    ClassPlanProvider,
    FixtureClassPlanProvider,
    InMemoryClassPlanProvider,
)
from cfprog.focus import (
    FocusEmphasis,
    FocusTemplate,
    FocusBlock,
    load_focus_blocks,
)
from cfprog.availability import (
    AvailabilityProvider,
    FixtureAvailabilityProvider,
    WeeklyAvailability,
    DayAvailability,
    DayOption,
    ClassSlot,
    OpenGym,
    DayOverride,
    WeekOverrides,
    DayStatus,
    ResolvedDay,
    ResolvedWeek,
    resolve_day,
    resolve_week,
    render_week_markdown,
    normalize_weekday,
    weekday_name,
    WEEKDAYS,
)
from cfprog.references import (
    Reference,
    ReferenceWeek,
    parse_reference,
    load_reference,
    resolve_reference_path,
)
from cfprog.generator import (
    WeeklyGenerator,
    WeeklyPlan,
    DayPlan,
    PlannedSession,
    ResolvedStrength,
    ResolvedFocus,
)
from cfprog.render import render_weekly_plan, render_day_plan

__all__ = [
    "Plate",
    "PlateInventory",
    "Target",
    "Loadout",
    "PlateCount",
    "PrescriptionResult",
    "REP_MAX_PCT",
    "resolve_target_fraction",
    "resolve_target_weight",
    "best_loadout",
    "LoadCalculator",
    "MaxesProvider",
    "FixtureMaxesProvider",
    "GoogleSheetsMaxesProvider",
    "SHEET_ID",
    "LoggedSet",
    "ReadinessEntry",
    "LogStore",
    "SQLiteLogStore",
    "READINESS_TIERS",
    "estimate_one_rm",
    "best_estimated_one_rm",
    "tonnage",
    "tonnage_by_lift",
    "ratio_gaps",
    "RATIO_STANDARDS",
    "STIMULUS_TAGS",
    "SetScheme",
    "StrengthPiece",
    "ClassSession",
    "ClassPlanProvider",
    "FixtureClassPlanProvider",
    "InMemoryClassPlanProvider",
    "FocusEmphasis",
    "FocusTemplate",
    "FocusBlock",
    "load_focus_blocks",
    "AvailabilityProvider",
    "FixtureAvailabilityProvider",
    "WeeklyAvailability",
    "DayAvailability",
    "DayOption",
    "ClassSlot",
    "OpenGym",
    "DayOverride",
    "WeekOverrides",
    "DayStatus",
    "ResolvedDay",
    "ResolvedWeek",
    "resolve_day",
    "resolve_week",
    "render_week_markdown",
    "normalize_weekday",
    "weekday_name",
    "WEEKDAYS",
    "Reference",
    "ReferenceWeek",
    "parse_reference",
    "load_reference",
    "resolve_reference_path",
    "WeeklyGenerator",
    "WeeklyPlan",
    "DayPlan",
    "PlannedSession",
    "ResolvedStrength",
    "ResolvedFocus",
    "render_weekly_plan",
    "render_day_plan",
]

__version__ = "0.1.0"
