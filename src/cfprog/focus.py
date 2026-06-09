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
class FocusEmphasis:
    """The "current focus" carried by a template — what to prioritise this week.

    Replaces the old bare `emphasis` string with a structured, optionally
    program-driven focus (issue #3). A focus can be:

    * **Program-driven** — a `reference` to a program/drill file (see
      `cfprog.references`). When `this_week` is omitted, the generator reads the
      drills for `program_week` straight from that file (single source of truth),
      and `program_week`/`program_length` give a visible "wk X/Y" progress marker
      that auto-advances as the block's `current_week` increments.
    * **Inline** — an explicit `this_week` drill list (and/or `cues`), used when
      there's no parseable reference (e.g. a purchased PDF program is link-only).
    * **Plain cue** — a bare string in config is treated as `cues` with no
      reference (backward-compatible with the old free-text `emphasis`).

    Holds no load arithmetic: where a drill names a lift + %, the load still
    resolves through the calculator via the template's `strength` pieces.
    """

    name: str = ""
    reference: Optional[str] = None
    program_week: Optional[int] = None
    program_length: Optional[int] = None
    this_week: Tuple[str, ...] = ()
    cues: str = ""

    @property
    def is_empty(self) -> bool:
        return not (self.name or self.reference or self.this_week or self.cues)


@dataclass(frozen=True)
class FocusTemplate:
    """One session shape the generator can place on a day.

    `stimulus` is the pattern this template loads — used by deconfliction the
    same way a class session's primary stimulus is. `strength` pieces (if any)
    are load-resolved by the calculator; `skill_items` are unloaded skill work.

    `emphasis` is the structured "current focus" (`FocusEmphasis`) — what to
    prioritise this week, optionally backed by a referenced program/drill file so
    the focus auto-advances by program week without hand-typing drills each week.
    `tier` overrides the block tier (used by a `complement`). When the class
    already supplies this template's pattern, `use_complement_when_class_covers`
    swaps in `complement` — a low-CNS supporting variant — instead of duplicating
    the class's main lift.
    """

    name: str
    stimulus: str
    movements: Tuple[str, ...] = ()
    skill_items: Tuple[str, ...] = ()
    strength: Tuple[StrengthPiece, ...] = ()
    emphasis: FocusEmphasis = FocusEmphasis()
    tier: Optional[str] = None
    low_cns: bool = False
    complement: Optional["FocusTemplate"] = None
    use_complement_when_class_covers: bool = False

    def __post_init__(self) -> None:
        _check_stimulus(self.stimulus)
        if self.tier is not None and self.tier not in TEMPLATE_TIERS:
            raise ValueError(f"template tier must be one of {TEMPLATE_TIERS}, got {self.tier!r}")
        # Coerce a plain string / None emphasis to FocusEmphasis so backward-
        # compatible callers (and code-built templates) work the same as config.
        if not isinstance(self.emphasis, FocusEmphasis):
            object.__setattr__(self, "emphasis", _coerce_emphasis(self.emphasis))

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


def _coerce_emphasis(value) -> FocusEmphasis:
    """Coerce a template's `emphasis` config into a `FocusEmphasis`.

    Accepts a `FocusEmphasis`, a structured object/dict, a plain string (treated
    as `cues` — backward compatible with the old free-text emphasis), or nothing
    (an empty focus).
    """
    if isinstance(value, FocusEmphasis):
        return value
    if value is None:
        return FocusEmphasis()
    if isinstance(value, str):
        return FocusEmphasis(cues=value)
    if not isinstance(value, dict):
        raise ValueError(f"emphasis must be a string or object, got {type(value).__name__}")
    program_week = value.get("program_week")
    program_length = value.get("program_length")
    return FocusEmphasis(
        name=str(value.get("name", "")),
        reference=value.get("reference"),
        program_week=int(program_week) if program_week is not None else None,
        program_length=int(program_length) if program_length is not None else None,
        this_week=tuple(value.get("this_week", ())),
        cues=str(value.get("cues", "")),
    )


def _parse_template(d: dict) -> FocusTemplate:
    complement = d.get("complement")
    return FocusTemplate(
        name=str(d["name"]),
        stimulus=_check_stimulus(str(d["stimulus"])),
        movements=tuple(d.get("movements", ())),
        skill_items=tuple(d.get("skill_items", ())),
        strength=tuple(parse_strength_piece(s) for s in d.get("strength", ())),
        emphasis=_coerce_emphasis(d.get("emphasis")),
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
