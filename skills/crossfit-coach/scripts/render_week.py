#!/usr/bin/env python3
"""Render a weekly plan (JSON spec) to a single self-contained HTML file.

This is presentation only — it does **no** load math. The model supplies the
judgment (what to train, the tier, the effort) and pastes the calculator's load
lines verbatim into the spec; this script just lays them out as:

  1. a Week Summary grid — columns Mon..Sun, rows AM/PM, each cell a training
     type (CrossFit / Weightlifting / Comp / Limiter / Rest) + effort (Low/Med/High);
  2. a Training Days section — per day, the workouts with their pre-calculated %s.

Usage:
    python3 render_week.py plan.json -o week.html      # from a file
    python3 render_week.py - -o week.html < plan.json  # from stdin
    python3 render_week.py plan.json                   # to stdout

See references/examples/weekly-plan.json for the input shape.
"""
from __future__ import annotations

import argparse
import html
import json
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

# normalise free-text effort / type into a css-friendly slug
EFFORT_SLUG = {"low": "low", "med": "med", "medium": "med", "high": "high"}
TYPE_SLUG = {
    "crossfit": "cf",
    "cf": "cf",
    "weightlifting": "wl",
    "wl": "wl",
    "comp": "comp",
    "comp programming": "comp",
    "comp class": "comp",
    "limiter": "lim",
    "limiter work": "lim",
    "individual limiter work": "lim",
    "rest": "rest",
}

CSS = """
:root{--cf:#2563eb;--wl:#7c3aed;--comp:#0891b2;--lim:#db2777;--rest:#94a3b8;
--low:#16a34a;--med:#d97706;--high:#dc2626;--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;}
*{box-sizing:border-box}
body{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
color:var(--ink);margin:0;padding:20px;max-width:860px;margin:0 auto;background:#fff}
h1{font-size:22px;margin:0 0 2px}h2{font-size:16px;margin:28px 0 10px;
text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
.src{color:var(--mut);margin:0 0 10px;font-size:13px}
.focus{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:6px}
.focus li{background:#f1f5f9;border-radius:999px;padding:2px 10px;font-size:12px;color:var(--mut)}
.gridwrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:560px}
th,td{border:1px solid var(--line);padding:6px;text-align:center;vertical-align:top}
thead th{background:#f8fafc;font-size:13px}
tbody th{background:#f8fafc;width:42px;font-size:12px;color:var(--mut)}
.cell{display:flex;flex-direction:column;gap:3px;align-items:center;min-height:34px;justify-content:center}
.cell .type{font-weight:600;font-size:13px}
.cell .eff{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.03em}
.t-cf .type{color:var(--cf)}.t-wl .type{color:var(--wl)}
.t-comp .type{color:var(--comp)}.t-lim .type{color:var(--lim)}.t-rest .type{color:var(--rest)}
.e-low{color:var(--low)}.e-med{color:var(--med)}.e-high{color:var(--high)}
.cell.empty{color:#cbd5e1}
.day{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.day.rest{opacity:.7}
.day h3{margin:0 0 8px;font-size:15px}
.day h3 .klass{color:var(--mut);font-weight:400;font-size:13px}
.session{margin:8px 0;padding-left:10px;border-left:3px solid var(--line)}
.session.p-protect{border-color:var(--high)}.session.p-cruise{border-color:var(--med)}
.session.p-accessory{border-color:var(--lim)}.session.p-skill{border-color:var(--low)}
.session h4{margin:0 0 4px;font-size:14px}
.tier{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.03em;
padding:1px 6px;border-radius:4px;color:#fff;margin-right:6px;vertical-align:1px}
.p-protect .tier{background:var(--high)}.p-cruise .tier{background:var(--med)}
.p-accessory .tier{background:var(--lim)}.p-skill .tier{background:var(--low)}
.items{margin:4px 0 0;padding:0;list-style:none}
.items li{padding:2px 0;border-bottom:1px dashed #f1f5f9}
.mv{font-weight:600}.scheme{color:var(--mut)}
.load{display:block;font-size:13px;color:var(--ink)}
.load .pct{color:var(--mut)}
.note{margin:6px 0 0;font-size:12px;color:var(--mut);font-style:italic}
footer{margin-top:24px;color:#94a3b8;font-size:11px;border-top:1px solid var(--line);padding-top:8px}
"""


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def _slug(value, table, default=""):
    if not value:
        return default
    return table.get(str(value).strip().lower(), default)


def render_cell(cell) -> str:
    """One AM/PM grid cell."""
    if not cell or not cell.get("type"):
        return '<td><div class="cell empty">—</div></td>'
    typ = cell["type"]
    tslug = _slug(typ, TYPE_SLUG, "")
    eff = cell.get("effort")
    parts = [f'<span class="type">{esc(typ)}</span>']
    if eff and tslug != "rest":
        eslug = _slug(eff, EFFORT_SLUG, "med")
        parts.append(f'<span class="eff e-{eslug}">{esc(eff)}</span>')
    cls = f"cell t-{tslug}" if tslug else "cell"
    return f'<td><div class="{cls}">{"".join(parts)}</div></td>'


def render_summary(summary) -> str:
    head = "".join(f"<th>{label}</th>" for _, label in DAYS)
    rows = []
    for slot, slabel in (("am", "AM"), ("pm", "PM")):
        cells = "".join(render_cell((summary.get(key) or {}).get(slot)) for key, _ in DAYS)
        rows.append(f"<tr><th>{slabel}</th>{cells}</tr>")
    return (
        '<section><h2>Week summary</h2><div class="gridwrap"><table>'
        f"<thead><tr><th></th>{head}</tr></thead>"
        f'<tbody>{"".join(rows)}</tbody></table></div></section>'
    )


def render_item(it) -> str:
    name = f'<span class="mv">{esc(it.get("name", ""))}</span>'
    scheme = f' <span class="scheme">{esc(it["scheme"])}</span>' if it.get("scheme") else ""
    load = ""
    if it.get("load"):
        load = f'<span class="load">↳ {esc(it["load"])}</span>'
    elif it.get("detail"):
        load = f'<span class="load">{esc(it["detail"])}</span>'
    return f"<li>{name}{scheme}{load}</li>"


def render_session(s) -> str:
    tier = (s.get("tier") or "").upper()
    pslug = tier.lower() if tier.lower() in {"protect", "cruise", "accessory", "skill"} else ""
    tier_badge = f'<span class="tier">{esc(tier)}</span>' if tier else ""
    items = "".join(render_item(it) for it in s.get("items", []))
    items_html = f'<ul class="items">{items}</ul>' if items else ""
    notes = "".join(f'<p class="note">{esc(n)}</p>' for n in s.get("notes", []))
    cls = f"session p-{pslug}" if pslug else "session"
    return (
        f'<div class="{cls}"><h4>{tier_badge}{esc(s.get("title", ""))}'
        f'{(" · " + esc(s["stimulus"])) if s.get("stimulus") else ""}</h4>'
        f"{items_html}{notes}</div>"
    )


def render_day(d) -> str:
    is_rest = not d.get("sessions")
    klass = f' · <span class="klass">class: {esc(d["class"])}</span>' if d.get("class") else ""
    head = f'<h3>{esc(d.get("day", ""))} · {esc(d.get("date", ""))}{klass}</h3>'
    if is_rest:
        label = esc(d.get("rest_note") or "Rest")
        return f'<article class="day rest">{head}<p class="note">{label}</p></article>'
    body = "".join(render_session(s) for s in d["sessions"])
    return f'<article class="day">{head}{body}</article>'


def render(plan: dict) -> str:
    week_of = esc(plan.get("week_of", ""))
    title = f"Week of {week_of}" if week_of else "Weekly plan"
    src = f'<p class="src">{esc(plan["source"])}</p>' if plan.get("source") else ""
    focus = ""
    if plan.get("focus"):
        lis = "".join(f"<li>{esc(f)}</li>" for f in plan["focus"])
        focus = f'<ul class="focus">{lis}</ul>'
    summary = render_summary(plan.get("summary", {}))
    days = "".join(render_day(d) for d in plan.get("days", []))
    days_section = f"<section><h2>Training days</h2>{days}</section>" if days else ""
    foot = "Loads are deterministic — every kg comes from scripts/calc.py. Judgment from references/policy.md."
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body><header><h1>{title}</h1>{src}{focus}</header>
{summary}{days_section}
<footer>{foot}</footer></body></html>
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
