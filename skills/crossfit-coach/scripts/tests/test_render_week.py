"""Smoke tests for the weekly-plan HTML renderer.

The renderer does no arithmetic (the calculator owns that) — these guard the
JSON -> HTML contract: the summary grid, effort/type classes, tiers, and that
the bundled example renders without error.
"""

import json
import os

import render_week

EXAMPLE = os.path.join(
    os.path.dirname(__file__), "..", "..", "references", "examples", "weekly-plan.json"
)


def _render(plan):
    return render_week.render(plan)


def test_summary_grid_has_seven_day_columns_and_am_pm_rows():
    html = _render({"summary": {}, "days": []})
    for label in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
        assert f"<th>{label}</th>" in html
    assert "<th>AM</th>" in html and "<th>PM</th>" in html


def test_cell_carries_type_and_effort_classes():
    html = _render(
        {"summary": {"mon": {"pm": {"type": "Weightlifting", "effort": "High"}}}, "days": []}
    )
    assert 'class="cell t-wl"' in html  # Weightlifting -> wl slug
    assert 'class="eff e-high"' in html  # rendered effort badge
    assert "Weightlifting" in html


def test_rest_cell_has_no_effort_badge():
    html = _render({"summary": {"fri": {"am": {"type": "Rest"}}}, "days": []})
    assert "t-rest" in html
    assert 'class="eff' not in html  # no effort badge rendered for a Rest cell


def test_empty_slot_renders_placeholder():
    html = _render({"summary": {"mon": {}}, "days": []})
    assert "cell empty" in html


def test_session_tier_drives_accent_class_and_load_line():
    html = _render(
        {
            "summary": {},
            "days": [
                {
                    "day": "Mon",
                    "date": "2026-06-08",
                    "class": "heavy_squat",
                    "sessions": [
                        {
                            "tier": "PROTECT",
                            "title": "Strict Press",
                            "items": [{"name": "Strict Press", "scheme": "3×5", "load": "52.5 kg"}],
                        }
                    ],
                }
            ],
        }
    )
    assert "p-protect" in html
    assert "PROTECT" in html
    assert "52.5 kg" in html
    assert "Strict Press" in html


def test_day_without_sessions_renders_as_rest():
    html = _render(
        {"summary": {}, "days": [{"day": "Fri", "date": "2026-06-12", "rest_note": "REST"}]}
    )
    assert "day rest" in html
    assert "REST" in html


def test_html_escapes_user_text():
    html = _render({"summary": {}, "days": [], "source": "A & B <x>"})
    assert "A &amp; B &lt;x&gt;" in html


def test_bundled_example_renders():
    with open(EXAMPLE, encoding="utf-8") as fh:
        plan = json.load(fh)
    html = _render(plan)
    assert html.startswith("<!doctype html>")
    assert "Week of 2026-06-08" in html
    assert "Week summary" in html and "Training days" in html
