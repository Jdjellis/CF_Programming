"""Smoke tests for the weekly-plan HTML renderer.

The renderer does no arithmetic (the calculator owns that) — these guard the
JSON -> HTML contract: the summary grid, stream colour slugs, verbatim workout
text, the %-loads block, and that the bundled example renders without error.
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


def test_grid_slugs_map_stream_abbreviations():
    assert render_week.grid_slugs("WL") == ["wl"]
    assert render_week.grid_slugs("Weightlifting") == ["wl"]
    assert render_week.grid_slugs("Perf") == ["perf"]
    assert render_week.grid_slugs("Comp") == ["comp"]
    assert render_week.grid_slugs("Rest") == ["rest"]
    # combined cell -> multiple slugs -> combo styling
    assert render_week.grid_slugs("Performance + WL") == ["wl", "perf"]


def test_combined_cell_uses_combo_class():
    html = _render({"summary": {"sun": {"am": {"type": "Performance + WL"}}}, "days": []})
    assert "t-combo" in html
    assert "Performance + WL" in html


def test_cell_effort_is_optional():
    # no effort -> no badge
    plain = _render({"summary": {"mon": {"am": {"type": "WL"}}}, "days": []})
    assert 'class="eff' not in plain
    # effort supplied -> badge rendered
    badged = _render({"summary": {"mon": {"am": {"type": "WL", "effort": "High"}}}, "days": []})
    assert 'class="eff e-high"' in badged


def test_empty_slot_renders_placeholder():
    html = _render({"summary": {"sat": {}}, "days": []})
    assert "cell empty" in html


def test_stream_reproduces_verbatim_text_and_loads():
    html = _render(
        {
            "summary": {},
            "days": [
                {
                    "day": "Mon",
                    "date": "8 Jun",
                    "streams": [
                        {
                            "label": "Weightlifting",
                            "text": "A. Back Squat: 6s x 2r x 87.5%\n*note line",
                            "loads": [
                                {"lift": "Back Squat", "scheme": "6 x 2 @ 87.5%", "load": "144.5 kg"}
                            ],
                        }
                    ],
                }
            ],
        }
    )
    assert "stream s-wl" in html
    # verbatim text preserved, including the newline and the literal scheme
    assert "A. Back Squat: 6s x 2r x 87.5%\n*note line" in html
    assert '<div class="wod">' in html
    assert "% loads" in html
    assert "144.5 kg" in html


def test_day_without_streams_renders_as_rest():
    html = _render(
        {"summary": {}, "days": [{"day": "Fri", "date": "12 Jun", "rest_note": "REST DAY"}]}
    )
    assert "day rest" in html
    assert "REST DAY" in html


def test_html_escapes_user_text():
    html = _render(
        {"summary": {}, "days": [{"day": "Mon", "streams": [{"label": "Performance", "text": 'Box (24/20") & <go>'}]}]}
    )
    assert "(24/20&quot;) &amp; &lt;go&gt;" in html


def test_bundled_example_renders():
    with open(EXAMPLE, encoding="utf-8") as fh:
        plan = json.load(fh)
    html = _render(plan)
    assert html.startswith("<!doctype html>")
    assert "Week of 8–14 Jun 2026" in html
    assert "Week summary" in html and "Training days" in html
    # a verbatim line and a calculated load both present
    assert "50/40 Calorie Echo Bike" in html
    assert "144.5 kg (87.5% of 165)" in html
