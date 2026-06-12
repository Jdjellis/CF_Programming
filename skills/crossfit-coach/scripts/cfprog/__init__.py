"""cfprog — deterministic arithmetic core for the crossfit-coach skill.

This package is the *only* place load/percentage math happens. The skill (the
model, in chat) supplies judgment; this code supplies arithmetic — it never does
the math in its head (PROJECT_SPEC §8). Pure standard library, no install: the
skill's scripts put this package on the path and import it directly.

Surface:
    - Deterministic load calculator (cfprog.targets, cfprog.calculator): resolves
      a %/RPE/rep-max target against the current 1RM to a loadable working weight.
    - Maxes read behind an interface (cfprog.maxes), sourced from the Google Sheet
      top section (stubbed to a local fixture until Sheets auth is wired).
    - Estimated 1RM from a performed set (cfprog.estimate) — the inverse of the
      same rep-max table the calculator uses.
"""

from cfprog.models import (
    Target,
    PrescriptionResult,
    round_to_half_kg,
)
from cfprog.targets import REP_MAX_PCT, resolve_target_fraction, resolve_target_weight
from cfprog.calculator import LoadCalculator
from cfprog.maxes import (
    MaxesProvider,
    FixtureMaxesProvider,
    GoogleSheetsMaxesProvider,
    SHEET_ID,
    normalize_lift,
)
from cfprog.estimate import estimate_one_rm

__all__ = [
    "Target",
    "PrescriptionResult",
    "round_to_half_kg",
    "REP_MAX_PCT",
    "resolve_target_fraction",
    "resolve_target_weight",
    "LoadCalculator",
    "MaxesProvider",
    "FixtureMaxesProvider",
    "GoogleSheetsMaxesProvider",
    "SHEET_ID",
    "normalize_lift",
    "estimate_one_rm",
]

__version__ = "1.0.0"
