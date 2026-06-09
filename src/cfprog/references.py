"""Program / drill reference files — the source of truth for a focus's drills.

A focus block carries a *current focus* (see `cfprog.focus.FocusEmphasis`) that
can point at a reference file describing a full program or drill library. This
module parses those files so the generator can pull *this week's* drills straight
from the program — edit the program, not the per-week config.

References are plain Markdown so they render in-repo and can be linked. Two
shapes are supported, with one dependency-free parser (no YAML / front-matter):

* **Periodised program** — `## Week N` sections, each with an optional `Cue:`
  line and a bullet list of drills. `for_week(n)` returns that week; the program
  length is the highest week number, which drives the "wk X/Y" progress marker
  and lets the focus auto-advance as the block's `current_week` increments.

* **Flat drill menu** — any non-week `## Heading` (e.g. `## Drills`) whose bullets
  form a single menu used for every week. Non-periodised focuses (rehab, mobility)
  use this; they carry no week marker.

This layer holds no load arithmetic. Where a drill names a lift + a percentage,
the load still resolves through `LoadCalculator` via the focus template's
strength pieces; the drill text here is descriptive (spec Section 8).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Repo root: src/cfprog/references.py -> parents[2]. Reference paths in config are
# stored relative to the repo root (e.g. "references/squat-12wk-block.md").
_REPO_ROOT = Path(__file__).resolve().parents[2]

_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_WEEK_RE = re.compile(r"^week\s+(\d+)\b", re.IGNORECASE)
_BULLET_RE = re.compile(r"^[-*]\s+(.+?)\s*$")
_CUE_RE = re.compile(r"^>?\s*cue\s*:\s*(.+?)\s*$", re.IGNORECASE)
# A flat-menu reference's drills come from sections with one of these headings;
# other prose sections (e.g. "Notes") don't leak into the drill list.
_MENU_RE = re.compile(r"\b(drills?|menu|exercises?|movements?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ReferenceWeek:
    """One week's prescription pulled from a reference: its cue + drill list."""

    week: int
    cues: str
    drills: Tuple[str, ...]


@dataclass(frozen=True)
class Reference:
    """A parsed program / drill reference.

    `weeks` maps week-number -> `ReferenceWeek` for a periodised program; `menu`
    is the flat drill list for a non-periodised reference (and the fallback when a
    requested week isn't defined). `num_weeks` is the program length (highest week
    number) or None for a flat menu.
    """

    title: str
    summary: str = ""
    source: str = ""
    weeks: Dict[int, ReferenceWeek] = field(default_factory=dict)
    menu: Tuple[str, ...] = ()

    @property
    def num_weeks(self) -> Optional[int]:
        return max(self.weeks) if self.weeks else None

    def for_week(self, week: int) -> ReferenceWeek:
        """This week's drills + cue. Falls back to the flat menu, then to empty.

        A periodised reference returns the matching `## Week N` section; a
        requested week beyond the program (or a flat-menu reference) returns the
        menu drills so the focus always renders *something* deterministic.
        """
        if week in self.weeks:
            return self.weeks[week]
        return ReferenceWeek(week=week, cues="", drills=self.menu)


def parse_reference(text: str, source: str = "") -> Reference:
    """Parse reference Markdown into a `Reference` (pure; no I/O)."""
    title = ""
    summary_lines: List[str] = []
    weeks: Dict[int, ReferenceWeek] = {}
    menu: List[str] = []

    # Current section accumulator.
    cur_week: Optional[int] = None      # None => generic section
    cur_is_menu = False                 # a non-week "Drills"/"Menu" section
    in_section = False
    cur_cue: str = ""
    cur_drills: List[str] = []

    def flush() -> None:
        nonlocal cur_cue, cur_drills
        if cur_week is not None:
            weeks[cur_week] = ReferenceWeek(
                week=cur_week, cues=cur_cue, drills=tuple(cur_drills)
            )
        elif cur_is_menu:
            menu.extend(cur_drills)
        cur_cue = ""
        cur_drills = []

    for raw in text.splitlines():
        line = raw.rstrip()
        sec = _SECTION_RE.match(line)
        if sec is not None:
            if in_section:
                flush()
            in_section = True
            wk = _WEEK_RE.match(sec.group(1))
            cur_week = int(wk.group(1)) if wk else None
            cur_is_menu = cur_week is None and _MENU_RE.search(sec.group(1)) is not None
            continue
        if not in_section:
            h = _HEADING_RE.match(line)
            if h is not None and not title:
                title = h.group(1)
                continue
            stripped = line.lstrip("> ").strip()
            if stripped:
                summary_lines.append(stripped)
            continue
        # Inside a section.
        cue = _CUE_RE.match(line)
        if cue is not None:
            cur_cue = f"{cur_cue} {cue.group(1)}".strip() if cur_cue else cue.group(1)
            continue
        bullet = _BULLET_RE.match(line)
        if bullet is not None:
            cur_drills.append(bullet.group(1))

    if in_section:
        flush()

    return Reference(
        title=title,
        summary=" ".join(summary_lines),
        source=source,
        weeks=weeks,
        menu=tuple(menu),
    )


def resolve_reference_path(ref: str, base_dir: Path | str | None = None) -> Path:
    """Resolve a (possibly repo-relative) reference path to an absolute Path."""
    p = Path(ref)
    if p.is_absolute():
        return p
    root = Path(base_dir) if base_dir else _REPO_ROOT
    return root / p


def load_reference(
    ref: str, base_dir: Path | str | None = None
) -> Optional[Reference]:
    """Load + parse a Markdown reference. Returns None when it can't be parsed.

    Non-Markdown references (e.g. purchased PDF programs) and missing files
    return None — those are link-only, so the focus must carry an explicit
    `this_week` in config. Markdown references are parsed for auto-advance.
    """
    path = resolve_reference_path(ref, base_dir)
    if path.suffix.lower() != ".md" or not path.is_file():
        return None
    return parse_reference(path.read_text(encoding="utf-8"), source=ref)
