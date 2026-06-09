"""High-level load calculator: lift + target + max -> working weight + loadout.

Ties together the three deterministic pieces:
    maxes (source of truth) -> targets (% resolution) -> plates (loadout).
No arithmetic happens here that isn't delegated to a tested module.
"""

from __future__ import annotations

import json
from pathlib import Path

from cfprog.maxes import FixtureMaxesProvider, MaxesProvider
from cfprog.models import PlateInventory, PrescriptionResult, Target
from cfprog.plates import best_loadout
from cfprog.targets import resolve_target_weight

_DEFAULT_INVENTORY = (
    Path(__file__).resolve().parents[2] / "data" / "plate_inventory.json"
)


def load_inventory(path: Path | str | None = None) -> PlateInventory:
    path = Path(path) if path else _DEFAULT_INVENTORY
    with open(path, "r", encoding="utf-8") as fh:
        return PlateInventory.from_dict(json.load(fh))


class LoadCalculator:
    """Resolve prescriptions to concrete loadable weights and plate maps."""

    def __init__(
        self,
        maxes: MaxesProvider | None = None,
        inventory: PlateInventory | None = None,
    ) -> None:
        self.maxes: MaxesProvider = maxes or FixtureMaxesProvider()
        self.inventory: PlateInventory = inventory or load_inventory()

    def prescribe(self, lift: str, target: Target) -> PrescriptionResult:
        one_rm = self.maxes.get_max(lift)
        working_weight, fraction, notes = resolve_target_weight(target, one_rm)
        loadout = best_loadout(working_weight, self.inventory)
        return PrescriptionResult(
            lift=lift,
            target=target,
            one_rm_kg=one_rm,
            target_fraction=fraction,
            working_weight_kg=working_weight,
            loadout=loadout,
            notes=notes,
        )
