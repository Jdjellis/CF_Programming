"""cfprog — deterministic arithmetic core for the crossfit-coach skill.

This package is the *only* place load/percentage/plate math happens. The skill
(the model, in chat) supplies judgment; this code supplies arithmetic — it never
does the math in its head (PROJECT_SPEC §8). Pure standard library, no install:
the skill's scripts put this package on the path and import it directly.

Surface:
    - Deterministic load/plate calculator (cfprog.plates, cfprog.targets, cfprog.calculator)
    - Maxes read behind an interface (cfprog.maxes), sourced from the Google Sheet
      top section (stubbed to a local fixture until Sheets auth is wired).
    - Estimated 1RM from a performed set (cfprog.estimate) — the inverse of the
      same rep-max table the calculator uses.
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
from cfprog.calculator import LoadCalculator, load_inventory
from cfprog.maxes import (
    MaxesProvider,
    FixtureMaxesProvider,
    GoogleSheetsMaxesProvider,
    SHEET_ID,
    normalize_lift,
)
from cfprog.estimate import estimate_one_rm

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
    "load_inventory",
    "MaxesProvider",
    "FixtureMaxesProvider",
    "GoogleSheetsMaxesProvider",
    "SHEET_ID",
    "normalize_lift",
    "estimate_one_rm",
]

__version__ = "1.0.0"
