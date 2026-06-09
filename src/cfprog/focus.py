"""Focus-block configuration (spec Section 3.4 / SKILL.md Section 4).

A focus block is the personal work the generator slots *around* the class plan:
a skill block and/or a strength emphasis running concurrently (they don't
interfere — different systems). Blocks are CONFIGURED, not hardcoded: each has a
name, length, days/week, tier, and one or more session templates. The generator
places `days_per_week` template-instances across the week, deconflicting against
class stimuli.

Like everything else, this layer holds no load arithmetic — a template's
strength pieces carry targets; the calculator resolves the kilos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from cfprog.classplan import StrengthPiece, _check_stimulus, parse_strength_piece

_DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[2] / "data" / "focus_blocks.fixture.json"
)

# Tiers a focus block may carry (DELOAD is a week-level state, not a block tier).
FOCUS_TIERS = ("PROTECT", "SKILL")
# Tiers a template may override to (ACCESSORY = low-CNS supporting work, the
# substitute used when the class already covers a PROTECT block's main lift).
TEMPLATE_TIERS = ("PROTECT", "SKILL", "ACCESSORY")


@dataclass(frozen=True)
class FocusTemplate:
    """One session shape the generator can place on a day.

    `stimulus` is the pattern this template loads — used by deconfliction the
    same way a class session's primary stimulus is. `strength` pieces (if any)
    are load-resolved by the calculator; `skill_items` are unloaded skill work.

    `emphasis` is a free-text "what to prioritise this week" line (e.g. the
    specific ring-MU drills to chase) — configured per week so the focus can be
    refined without touching code. `tier` overrides the block tier (used by a
    `complement`). When the class already supplies this template's pattern,
    `use_complement_when_class_covers` swaps in `complement` — a low-CNS
    supporting variant — instead of duplicating the class's main lift.
    """

    name: str
    stimulus: str
    movements: Tuple[str, ...] = ()
    skill_items: Tuple[str, ...] = ()
    strength: Tuple[StrengthPiece, ...] = ()
    emphasis: str = ""
    tier: Optional[str] = None
    low_cns: bool = False
    complement: Optional["FocusTemplate"] = None
    use_complement_when_class_covers: bool = False

    def __post_init__(self) -> None:
        _check_stimulus(self.stimulus)
        if self.tier is not None and self.tier not in TEMPLATE_TIERS:
            raise ValueError(f"template tier must be one of {TEMPLATE_TIERS}, got {self.tier!r}")

    def effective_tier(self, block_tier: str) -> str:
        return self.tier or block_tier


@dataclass(frozen=True)
class FocusBlock:
    """A configured focus block (Section 3.4)."""

    name: str
    length_weeks: int
    current_week: int
    days_per_week: int
    tier: str
    templates: Tuple[FocusTemplate, ...]

    def __post_init__(self) -> None:
        if self.tier not in FOCUS_TIERS:
            raise ValueError(f"focus tier must be one of {FOCUS_TIERS}, got {self.tier!r}")
        if self.days_per_week < 1:
            raise ValueError("days_per_week must be >= 1")
        if not self.templates:
            raise ValueError("a focus block needs at least one template")

    @property
    def is_deload_due(self) -> bool:
        """True on the planned down-week (~every 4th week of the block)."""
        return self.current_week % 4 == 0

    def slots(self) -> List[FocusTemplate]:
        """The `days_per_week` template-instances to place, rotating templates.

        Two-template strength block over 2 days -> [FS, press]; a one-template
        skill block over 3 days -> [skill, skill, skill].
        """
        return [self.templates[i % len(self.templates)] for i in range(self.days_per_week)]


def _parse_template(d: dict) -> FocusTemplate:
    complement = d.get("complement")
    return FocusTemplate(
        name=str(d["name"]),
        stimulus=_check_stimulus(str(d["stimulus"])),
        movements=tuple(d.get("movements", ())),
        skill_items=tuple(d.get("skill_items", ())),
        strength=tuple(parse_strength_piece(s) for s in d.get("strength", ())),
        emphasis=str(d.get("emphasis", "")),
        tier=d.get("tier"),
        low_cns=bool(d.get("low_cns", False)),
        complement=_parse_template(complement) if complement else None,
        use_complement_when_class_covers=bool(d.get("use_complement_when_class_covers", False)),
    )


def _parse_block(d: dict) -> FocusBlock:
    return FocusBlock(
        name=str(d["name"]),
        length_weeks=int(d["length_weeks"]),
        current_week=int(d.get("current_week", 1)),
        days_per_week=int(d["days_per_week"]),
        tier=str(d["tier"]),
        templates=tuple(_parse_template(t) for t in d["templates"]),
    )


def load_focus_blocks(path: Path | str | None = None) -> List[FocusBlock]:
    path = Path(path) if path else _DEFAULT_FIXTURE
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return [_parse_block(b) for b in data["blocks"]]
