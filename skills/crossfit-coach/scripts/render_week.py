#!/usr/bin/env python3
"""Render a weekly plan (JSON spec) to a single self-contained HTML file.

Presentation only — it does **no** load math. The model supplies the judgment and
pastes the calculator's load lines verbatim into the spec; this script lays out:

  1. a Week Summary — columns Mon..Sun, rows AM/PM, each cell the training
     stream(s) for that slot (WL / Perf / Comp / Fitness, or a combo like
     "Performance + WL"), with an optional effort tag. On a phone this reflows to
     a tap-to-jump day list;
  2. Training Days — per day, each stream's workout text reproduced **verbatim**
     from the gym's programming, with the calculated %-loads listed underneath.

Built for the gym, on a phone: a sticky day-nav jumps straight to a day, today's
session is highlighted and scrolled into view on open, and the page honours the
device's dark-mode preference. All of that is self-contained (inline CSS + a tiny
inline script) — no network, no build step.

To enable the "today" highlight and per-day jump links, give the spec an optional
top-level `week_start` (the ISO date of the first entry in `days`, e.g.
"2026-06-08"); each day's date is derived from it by offset. Without it the page
still renders — it just won't know which day is today.

Usage:
    python3 render_week.py plan.json -o week.html      # from a file
    python3 render_week.py - -o week.html < plan.json  # from stdin
    python3 render_week.py plan.json                   # to stdout

See references/examples/weekly-plan.json for the input shape.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import re
import sys

DAYS = [
    ("mon", "Mon"),
    ("tue", "Tue"),
    ("wed", "Wed"),
    ("thu", "Thu"),
    ("fri", "Fri"),
    ("sat", "Sat"),
    ("sun", "Sun"),
]
_DAY_KEYS = {key for key, _ in DAYS}

EFFORT_SLUG = {"low": "low", "med": "med", "medium": "med", "high": "high"}

CSS = """
:root{--wl:#7c3aed;--perf:#2563eb;--comp:#0891b2;--fit:#0d9488;--lim:#db2777;--rest:#94a3b8;
--low:#16a34a;--med:#d97706;--high:#dc2626;--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;
--bg:#fff;--surface:#f8fafc;--chip:#f1f5f9;--today:#ea580c;--today-bg:#fff7ed;
--dec-bg:#fdf2f8;--dec-line:#fbcfe8;}
@media (prefers-color-scheme:dark){:root{
--ink:#e5e7eb;--mut:#94a3b8;--line:#334155;--bg:#0b1220;--surface:#172033;--chip:#172033;
--wl:#a78bfa;--perf:#60a5fa;--comp:#22d3ee;--fit:#2dd4bf;--lim:#f472b6;--rest:#64748b;
--low:#4ade80;--med:#fbbf24;--high:#f87171;--today:#fb923c;--today-bg:#2a1a0e;
--dec-bg:#231020;--dec-line:#7d2a52;}}
*{box-sizing:border-box}
body{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
color:var(--ink);margin:0 auto;padding:20px;max-width:880px;background:var(--bg)}
h1{font-size:22px;margin:0 0 2px}h2{font-size:15px;margin:26px 0 10px;
text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}
.src{color:var(--mut);margin:0 0 10px;font-size:13px}
.focus{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:6px}
.focus li{background:var(--chip);border-radius:999px;padding:2px 10px;font-size:12px;color:var(--mut)}
.daynav{position:sticky;top:0;z-index:9;display:flex;gap:6px;align-items:center;background:var(--bg);
padding:8px 0;margin:10px 0 0;border-bottom:1px solid var(--line)}
.dnchips{display:flex;gap:6px;overflow-x:auto;-webkit-overflow-scrolling:touch}
.dnchips::-webkit-scrollbar{display:none}
.todaybtn{flex:0 0 auto;cursor:pointer;border:1px solid var(--today);background:var(--today);color:#fff;
border-radius:999px;padding:5px 13px;font:inherit;font-size:13px;font-weight:700;white-space:nowrap}
.daynav a{flex:0 0 auto;text-decoration:none;color:var(--mut);background:var(--surface);
border:1px solid var(--line);border-radius:999px;padding:4px 11px;font-size:13px;font-weight:600;white-space:nowrap}
.daynav a .dn{font-weight:400;font-size:11px;margin-left:4px;color:var(--mut)}
.daynav a.rest{opacity:.6}
.daynav a.is-today{background:var(--today);border-color:var(--today);color:#fff}
.daynav a.is-today .dn{color:#fff}
.gridwrap{overflow-x:auto}
.summary-stack{display:none}
table{border-collapse:collapse;width:100%;min-width:600px}
th,td{border:1px solid var(--line);padding:7px 6px;text-align:center;vertical-align:middle}
thead th{background:var(--surface);font-size:13px;width:13%}
tbody th{background:var(--surface);width:42px;font-size:12px;color:var(--mut)}
.cell{display:flex;flex-direction:column;gap:2px;align-items:center;min-height:30px;justify-content:center}
.cell .type{font-weight:700;font-size:13px}
.cell .eff{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.03em}
.t-wl .type{color:var(--wl)}.t-perf .type{color:var(--perf)}
.t-comp .type{color:var(--comp)}.t-fit .type{color:var(--fit)}.t-rest .type{color:var(--rest)}
.t-combo .type{background:linear-gradient(90deg,var(--perf),var(--wl));
-webkit-background-clip:text;background-clip:text;color:transparent}
.e-low{color:var(--low)}.e-med{color:var(--med)}.e-high{color:var(--high)}
.cell .add{font-size:11px;font-weight:600;color:#fff;background:var(--lim);border-radius:999px;padding:1px 8px}
.cell.empty{color:var(--rest)}
.wkrow{display:flex;gap:10px;align-items:center;text-decoration:none;color:inherit;
border:1px solid var(--line);border-radius:10px;padding:8px 10px;margin:6px 0}
.wkrow.rest{opacity:.6}
.wkrow.is-today{border-color:var(--today);background:var(--today-bg);opacity:1}
.wkday{flex:0 0 54px;font-weight:700;font-size:14px;line-height:1.2}
.wkday .wd{display:block;font-weight:400;font-size:11px;color:var(--mut)}
.wkslots{display:flex;flex-wrap:wrap;gap:6px 14px;flex:1}
.wkslot{display:flex;align-items:center;gap:6px}
.wkslot .sl{font-size:10px;font-weight:700;color:var(--mut);letter-spacing:.04em}
.wkslot .cell{flex-direction:row;gap:6px;min-height:0}
.decisions{background:var(--dec-bg);border:1px solid var(--dec-line);border-left:4px solid var(--lim);
border-radius:8px;padding:10px 14px;margin:16px 0 0}
.decisions h2{margin:0 0 6px;color:var(--lim);font-size:13px}
.decisions ul{margin:0;padding-left:18px}.decisions li{font-size:13px;margin:2px 0}
.day{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:12px 0;scroll-margin-top:64px}
.day.rest{opacity:.7}
.day.is-today{border-color:var(--today);box-shadow:inset 0 0 0 1px var(--today);opacity:1}
.day.is-today>h3::before{content:"Today \\00b7 ";color:var(--today);font-weight:700}
.day>h3{margin:0 0 4px;font-size:16px}
.day>h3 .date{color:var(--mut);font-weight:400;font-size:13px}
.day .daynote{margin:0 0 8px;font-size:12px;color:var(--mut);font-style:italic}
.stream{margin:12px 0 0;padding-left:11px;border-left:3px solid var(--line)}
.stream.s-wl{border-color:var(--wl)}.stream.s-perf{border-color:var(--perf)}
.stream.s-comp{border-color:var(--comp)}.stream.s-fit{border-color:var(--fit)}
.stream.s-lim{border-color:var(--lim)}
.stream h4{margin:0;font-size:13px;text-transform:uppercase;letter-spacing:.04em}
.s-wl h4{color:var(--wl)}.s-perf h4{color:var(--perf)}
.s-comp h4{color:var(--comp)}.s-fit h4{color:var(--fit)}.s-lim h4{color:var(--lim)}
.s-lim h4::after{content:" \\00b7 individual";font-weight:400;text-transform:none;letter-spacing:0;color:var(--mut);font-size:11px}
.wod{white-space:pre-wrap;font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:9px 11px;margin:6px 0 0}
.loads{margin:7px 0 0}
.loads .lh{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin-bottom:3px}
.lrow{font-size:13px;padding:1px 0}
.lrow .lift{font-weight:600}.lrow .scheme{color:var(--mut)}
.lrow .load{color:var(--ink)}
footer{margin-top:24px;color:var(--mut);font-size:11px;border-top:1px solid var(--line);padding-top:8px}
@media (max-width:640px){body{padding:12px}.summary-table{display:none}.summary-stack{display:block}
h2{margin:20px 0 8px}.day{padding:11px 12px}.wod{font-size:12.5px}}
"""

# Tiny, dependency-free: highlight today's session and reveal a "Today" jump button.
# No auto-scroll — the athlete decides when to jump.
SCRIPT = """
(function(){try{
var t=new Date();var p=function(n){return (n<10?'0':'')+n;};
var iso=t.getFullYear()+'-'+p(t.getMonth()+1)+'-'+p(t.getDate());
document.querySelectorAll('[data-iso="'+iso+'"]').forEach(function(el){el.classList.add('is-today');});
var card=document.querySelector('article.day[data-iso="'+iso+'"]');
var btn=document.querySelector('.todaybtn');
if(btn&&card){btn.hidden=false;
btn.addEventListener('click',function(){card.scrollIntoView({behavior:'smooth',block:'start'});});}
}catch(e){}})();
"""


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def _effort_slug(value):
    return EFFORT_SLUG.get(str(value).strip().lower(), "med") if value else None


def _day_key(label: str) -> str:
    """Map a day label ("Mon", "Tuesday", "wed.") to a grid key (mon..sun)."""
    s = (label or "").strip().lower().replace(".", "")
    return s[:3] if s[:3] in _DAY_KEYS else s


def _day_num(date_str) -> str:
    """Leading day-of-month from a date label ("8 Jun" -> "8"), else ""."""
    m = re.match(r"\s*(\d+)", str(date_str or ""))
    return m.group(1) if m else ""


def day_isos(week_start, n: int):
    """ISO date per day, derived from week_start (date of days[0]) + offset.

    Returns a list of n ISO strings, or n Nones if week_start is missing/unparseable.
    """
    try:
        d0 = datetime.date.fromisoformat(str(week_start))
    except (TypeError, ValueError):
        return [None] * n
    return [(d0 + datetime.timedelta(days=i)).isoformat() for i in range(n)]


def grid_slugs(type_str: str):
    """Map a free-text cell type ("WL", "Performance + WL", "WOD + Comp"...) to slugs."""
    s = (type_str or "").lower()
    if "rest" in s:
        return ["rest"]
    slugs = []
    if "weightlift" in s or re.search(r"\bwl\b", s):
        slugs.append("wl")
    if "perf" in s or "wod" in s:
        slugs.append("perf")
    if "comp" in s:
        slugs.append("comp")
    if "fit" in s:
        slugs.append("fit")
    return slugs


def cell_div(cell) -> str:
    """The inner cell markup (a class stream `type` and/or fitted `add` work).

    Shared by the desktop grid and the mobile day stack.
    """
    if not cell or (not cell.get("type") and not cell.get("add")):
        return '<div class="cell empty">—</div>'
    typ = cell.get("type")
    slugs = grid_slugs(typ) if typ else []
    tclass = "t-combo" if len(slugs) > 1 else (f"t-{slugs[0]}" if slugs else "")
    parts = []
    if typ:
        parts.append(f'<span class="type">{esc(typ)}</span>')
        eff = _effort_slug(cell.get("effort"))
        if eff and "rest" not in slugs:
            parts.append(f'<span class="eff e-{eff}">{esc(cell["effort"])}</span>')
    if cell.get("add"):
        parts.append(f'<span class="add">{esc(cell["add"])}</span>')
    return f'<div class="cell {tclass}">{"".join(parts)}</div>'


def render_cell(cell) -> str:
    return f"<td>{cell_div(cell)}</td>"


def render_daynav(days, isos) -> str:
    """A sticky, horizontally scrollable row of chips jumping to each day card."""
    if not days:
        return ""
    chips = []
    for i, d in enumerate(days):
        iso = isos[i] if i < len(isos) else None
        isattr = f' data-iso="{esc(iso)}"' if iso else ""
        rest = " rest" if not d.get("streams") else ""
        num = _day_num(d.get("date"))
        numspan = f'<span class="dn">{num}</span>' if num else ""
        chips.append(
            f'<a class="dnchip{rest}" href="#day-{i}"{isattr}>{esc(d.get("day", ""))}{numspan}</a>'
        )
    # The Today button is revealed by the script only when today is in this week.
    return (
        '<nav class="daynav">'
        '<button class="todaybtn" type="button" hidden>Today</button>'
        f'<div class="dnchips">{"".join(chips)}</div>'
        "</nav>"
    )


def render_summary_table(summary) -> str:
    head = "".join(f"<th>{label}</th>" for _, label in DAYS)
    rows = []
    for slot, slabel in (("am", "AM"), ("pm", "PM")):
        cells = "".join(render_cell((summary.get(key) or {}).get(slot)) for key, _ in DAYS)
        rows.append(f"<tr><th>{slabel}</th>{cells}</tr>")
    return (
        '<div class="gridwrap summary-table"><table>'
        f"<thead><tr><th></th>{head}</tr></thead>"
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_summary_stack(summary, days, isos) -> str:
    """Phone view of the summary: one tap-to-jump row per day, AM/PM inline."""
    if not days:
        return ""
    rows = []
    for i, d in enumerate(days):
        slot = summary.get(_day_key(d.get("day", ""))) or {}
        iso = isos[i] if i < len(isos) else None
        isattr = f' data-iso="{esc(iso)}"' if iso else ""
        rest = " rest" if not d.get("streams") else ""
        date = f' <span class="wd">{esc(d["date"])}</span>' if d.get("date") else ""
        slots = "".join(
            f'<div class="wkslot"><span class="sl">{slabel}</span>{cell_div(slot.get(key))}</div>'
            for key, slabel in (("am", "AM"), ("pm", "PM"))
        )
        rows.append(
            f'<a class="wkrow{rest}" href="#day-{i}"{isattr}>'
            f'<div class="wkday">{esc(d.get("day", ""))}{date}</div>'
            f'<div class="wkslots">{slots}</div></a>'
        )
    return f'<div class="summary-stack">{"".join(rows)}</div>'


def render_summary(summary, days, isos) -> str:
    return (
        '<section><h2>Week summary</h2>'
        f"{render_summary_table(summary)}{render_summary_stack(summary, days, isos)}"
        "</section>"
    )


def _stream_slug(label: str) -> str:
    s = (label or "").lower()
    if "weightlift" in s or re.search(r"\bwl\b", s):
        return "wl"
    if "perf" in s or "wod" in s:
        return "perf"
    if "comp" in s:
        return "comp"
    if "fit" in s:
        return "fit"
    return ""


def render_loads(loads) -> str:
    if not loads:
        return ""
    rows = []
    for ld in loads:
        lift = f'<span class="lift">{esc(ld.get("lift", ""))}</span>'
        scheme = f' <span class="scheme">{esc(ld["scheme"])}</span>' if ld.get("scheme") else ""
        load = f' <span class="load">→ {esc(ld["load"])}</span>' if ld.get("load") else ""
        rows.append(f'<div class="lrow">{lift}{scheme}{load}</div>')
    return f'<div class="loads"><div class="lh">% loads</div>{"".join(rows)}</div>'


def render_stream(st) -> str:
    # `accent` (wl|perf|comp|fit|lim) overrides label-based colour — use "lim" for
    # the athlete's own fitted individual work (strict press, ring MU, knee rehab).
    slug = st.get("accent") or _stream_slug(st.get("label", ""))
    cls = f"stream s-{slug}" if slug else "stream"
    head = f'<h4>{esc(st.get("label", ""))}</h4>'
    text = f'<div class="wod">{esc(st["text"])}</div>' if st.get("text") else ""
    return f'<div class="{cls}">{head}{text}{render_loads(st.get("loads"))}</div>'


def render_day(d, idx=None, iso=None) -> str:
    anchor = f' id="day-{idx}"' if idx is not None else ""
    isattr = f' data-iso="{esc(iso)}"' if iso else ""
    date = f' <span class="date">{esc(d["date"])}</span>' if d.get("date") else ""
    head = f'<h3>{esc(d.get("day", ""))}{date}</h3>'
    note = f'<p class="daynote">{esc(d["note"])}</p>' if d.get("note") else ""
    streams = d.get("streams")
    if not streams:
        label = esc(d.get("rest_note") or "Rest")
        return f'<article class="day rest"{anchor}{isattr}>{head}<p class="daynote">{label}</p></article>'
    body = "".join(render_stream(s) for s in streams)
    return f'<article class="day"{anchor}{isattr}>{head}{note}{body}</article>'


def render(plan: dict) -> str:
    week_of = esc(plan.get("week_of", ""))
    title = f"Week of {week_of}" if week_of else "Weekly plan"
    src = f'<p class="src">{esc(plan["source"])}</p>' if plan.get("source") else ""
    focus = ""
    if plan.get("focus"):
        lis = "".join(f"<li>{esc(f)}</li>" for f in plan["focus"])
        focus = f'<ul class="focus">{lis}</ul>'

    days = plan.get("days", [])
    isos = day_isos(plan.get("week_start"), len(days))

    daynav = render_daynav(days, isos)
    summary = render_summary(plan.get("summary", {}), days, isos)
    decisions = ""
    if plan.get("decisions"):
        lis = "".join(f"<li>{esc(x)}</li>" for x in plan["decisions"])
        decisions = f'<section class="decisions"><h2>Priority decisions</h2><ul>{lis}</ul></section>'
    days_html = "".join(
        render_day(d, i, isos[i] if i < len(isos) else None) for i, d in enumerate(days)
    )
    days_section = f"<section><h2>Training days</h2>{days_html}</section>" if days_html else ""
    foot = (
        "Workout text reproduced verbatim from the gym's programming. Loads are "
        "deterministic — every kg comes from scripts/calc.py. Judgment from references/policy.md."
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body><header><h1>{title}</h1>{src}{focus}</header>
{daynav}{summary}{decisions}{days_section}
<footer>{foot}</footer>
<script>{SCRIPT}</script></body></html>
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a weekly plan JSON spec to HTML.")
    ap.add_argument("plan", help="path to the plan JSON, or '-' for stdin")
    ap.add_argument("-o", "--out", help="output HTML path (default: stdout)")
    args = ap.parse_args(argv)

    raw = sys.stdin.read() if args.plan == "-" else open(args.plan, encoding="utf-8").read()
    plan = json.loads(raw)
    out = render(plan)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
