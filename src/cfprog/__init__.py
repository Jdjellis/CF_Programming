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
]

__version__ = "0.1.0"
