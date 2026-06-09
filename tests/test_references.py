"""Tests for the program/drill reference parser (issue #3).

The parser is dependency-free and pure over text, so every shape is asserted
against small inline documents plus the shipped reference files.
"""

import pytest

from cfprog.references import (
    Reference,
    load_reference,
    parse_reference,
    resolve_reference_path,
)

_PERIODISED = """\
# Demo program

> A two-week demo. Loads resolve via the calculator.

## Week 1
Cue: Build in; leave reps in the tank.
- Back squat — 5x5 @ 70%
- Spanish squat — 3x20s

## Week 2
Cue: A little heavier.
- Back squat — 5x4 @ 75%
- Bulgarian split squat — 3x8/leg
"""

_FLAT_MENU = """\
# Rehab menu

> Non-periodised.

## Drills
- Spanish squat — 3x20s holds
- ATG split squat — 3x8/leg

## Notes
- Keep it pain-free.
"""


def test_parses_title_and_summary():
    ref = parse_reference(_PERIODISED, source="demo.md")
    assert ref.title == "Demo program"
    assert "two-week demo" in ref.summary
    assert ref.source == "demo.md"


def test_periodised_weeks_and_length():
    ref = parse_reference(_PERIODISED)
    assert ref.num_weeks == 2
    wk1 = ref.for_week(1)
    assert wk1.cues == "Build in; leave reps in the tank."
    assert wk1.drills == ("Back squat — 5x5 @ 70%", "Spanish squat — 3x20s")
    wk2 = ref.for_week(2)
    assert "5x4 @ 75%" in wk2.drills[0]


def test_week_beyond_program_falls_back_to_empty_menu():
    ref = parse_reference(_PERIODISED)
    wk9 = ref.for_week(9)            # no week 9, no menu -> empty drills
    assert wk9.drills == ()
    assert wk9.week == 9


def test_flat_menu_has_no_weeks_and_serves_every_week():
    ref = parse_reference(_FLAT_MENU)
    assert ref.num_weeks is None
    assert "Spanish squat — 3x20s holds" in ref.menu
    # A flat menu answers any week with the same menu.
    assert ref.for_week(3).drills == ref.menu
    # Prose sections (## Notes) don't leak into the drill menu.
    assert "Keep it pain-free." not in ref.menu


def test_quoted_cue_form_is_accepted():
    ref = parse_reference("# T\n\n## Week 1\n> Cue: quoted cue.\n- a drill\n")
    assert ref.for_week(1).cues == "quoted cue."


def test_load_reference_resolves_shipped_files():
    ref = load_reference("references/squat-12wk-block.md")
    assert ref is not None
    assert ref.num_weeks == 12
    assert ref.for_week(4).drills          # week 4 has drills


def test_load_reference_missing_or_nonmarkdown_returns_none():
    assert load_reference("references/does-not-exist.md") is None
    # Non-Markdown (e.g. a purchased PDF) is link-only -> not parsed.
    assert load_reference("references/some-program.pdf") is None


def test_resolve_reference_path_is_repo_relative():
    p = resolve_reference_path("references/knee-rehab.md")
    assert p.is_absolute()
    assert p.name == "knee-rehab.md"
