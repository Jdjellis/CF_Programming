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


def test_cell_add_renders_individual_work_chip():
    # class type + fitted individual work
    both = _render({"summary": {"mon": {"am": {"type": "WL", "add": "Ring MU"}}}, "days": []})
    assert 'class="add">Ring MU</span>' in both
    assert "t-wl" in both
    # add-only slot (individual work, no class) still renders the chip
    only = _render({"summary": {"thu": {"am": {"add": "Strict Press"}}}, "days": []})
    assert 'class="add">Strict Press</span>' in only


def test_decisions_render_as_callout():
    html = _render({"summary": {}, "days": [], "decisions": ["Deferred FS to class.", "Ring MU Mon/Wed/Sat."]})
    assert 'class="decisions"' in html
    assert "Priority decisions" in html
    assert "Deferred FS to class." in html


def test_stream_accent_overrides_label_colour():
    html = _render(
        {
            "summary": {},
            "days": [
                {"day": "Thu", "streams": [{"label": "Strict Press", "accent": "lim", "text": "x"}]}
            ],
        }
    )
    assert "stream s-lim" in html


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


# --- phone affordances: sticky day-nav, mobile summary, today, dark mode ---

def test_daynav_jumps_to_day_cards():
    html = _render(
        {
            "summary": {},
            "days": [
                {"day": "Mon", "date": "8 Jun", "streams": [{"label": "WL", "text": "x"}]},
                {"day": "Tue", "date": "9 Jun", "rest_note": "REST DAY"},
            ],
        }
    )
    assert 'class="daynav"' in html
    # each chip jumps to the matching day card anchor
    assert 'href="#day-0"' in html and 'href="#day-1"' in html
    assert 'id="day-0"' in html and 'id="day-1"' in html
    # a rest day chip is dimmed
    assert 'class="dnchip rest"' in html


def test_week_start_stamps_iso_for_today_wiring():
    html = _render(
        {
            "week_start": "2026-06-08",
            "summary": {"mon": {"am": {"type": "WL"}}},
            "days": [
                {"day": "Mon", "date": "8 Jun", "streams": [{"label": "WL", "text": "x"}]},
                {"day": "Tue", "date": "9 Jun", "streams": [{"label": "Perf", "text": "y"}]},
            ],
        }
    )
    # day cards (and nav chips / stack rows) carry the date derived by offset
    assert 'article class="day" id="day-0" data-iso="2026-06-08"' in html
    assert 'data-iso="2026-06-09"' in html  # day 1 = week_start + 1


def test_no_week_start_means_no_dated_cards():
    html = _render(
        {"summary": {}, "days": [{"day": "Mon", "streams": [{"label": "WL", "text": "x"}]}]}
    )
    assert 'id="day-0"' in html
    assert 'id="day-0" data-iso' not in html  # no ISO stamped -> "today" stays off
    assert 'class="daynav"' in html  # jump links still render


def test_mobile_summary_stack_mirrors_grid():
    html = _render(
        {
            "summary": {"mon": {"am": {"type": "WL", "add": "Ring MU"}}},
            "days": [{"day": "Mon", "date": "8 Jun", "streams": [{"label": "WL", "text": "x"}]}],
        }
    )
    assert 'class="summary-stack"' in html  # phone view present (CSS hides one or the other)
    assert "wkrow" in html
    assert "Ring MU" in html  # the fitted work shows in the stacked view too


def test_dark_mode_and_today_script_present():
    html = _render({"summary": {}, "days": []})
    assert "prefers-color-scheme:dark" in html  # honours the device theme
    assert "<script>" in html and "is-today" in html  # today-detection wired


def test_summary_button_and_today_highlight():
    html = _render(
        {
            "week_start": "2026-06-08",
            "summary": {"mon": {"am": {"type": "WL"}}},
            "days": [{"day": "Mon", "date": "8 Jun", "streams": [{"label": "WL", "text": "x"}]}],
        }
    )
    # a Summary pill jumps back to the week-summary section
    assert '<a class="navbtn" href="#week-summary">Summary</a>' in html
    assert '<section id="week-summary">' in html
    # today highlight still wired; no Today pill, and nothing scrolls on its own
    assert "classList.add('is-today')" in html
    assert "todaybtn" not in html
    assert "scrollIntoView" not in html
