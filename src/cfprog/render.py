"""Render a `WeeklyPlan` to Markdown.

Rendering is deliberately separate from generation (spec Section 5a): the plan
is a structured object, and Markdown is the first of several swappable output
adapters (Google Calendar / Slack DM come later). This module is pure
formatting — it reads the plan, it never computes anything.
"""

from __future__ import annotations

from typing import List

from cfprog.generator import DayPlan, PlannedSession, ResolvedStrength, WeeklyPlan

_TIER_BADGE = {
    "PROTECT": "🔴 PUSH (PROTECT)",
    "CRUISE": "🟡 CRUISE",
    "ACCESSORY": "🟣 ACCESSORY (support — flex)",
    "SKILL": "🟢 SKILL / skip-eligible (flex)",
    "DELOAD": "🔵 DELOAD",
}

_BUCKET_HEADING = {
    "PUSH": "PUSH (protect — priority #1)",
    "CRUISE": "CRUISE (class — autoregulate)",
    "FLEX": "FLEX (support / skill — first to cut)",
}


def _strength_line(rs: ResolvedStrength) -> str:
    r = rs.result
    star = " ⭐" if rs.is_top_set else ""
    head = f"**{rs.label}** — {rs.scheme}{star}"
    load = (
        f"`{r.loadout.achieved_kg:g} kg` "
        f"({r.target_fraction * 100:.0f}% of {r.one_rm_kg:g}) — "
        f"per side: {r.loadout.per_side_str()}"
    )
    if not r.loadout.exact:
        sign = "+" if r.loadout.delta_kg >= 0 else ""
        load += f" _(Δ{sign}{r.loadout.delta_kg:g})_"
    return f"{head}<br>    ↳ {load}"


def _session_md(s: PlannedSession) -> List[str]:
    lines = [f"- **[{_TIER_BADGE.get(s.tier, s.tier)}]** {s.name}  _({s.stimulus})_"]
    if s.emphasis:
        lines.append(f"  - 🎯 _Focus: {s.emphasis}_")
    for m in s.movements:
        lines.append(f"  - {m}")
    for rs in s.prescriptions:
        lines.append(f"  - {_strength_line(rs)}")
    for item in s.skill_items:
        lines.append(f"  - ◦ {item}")
    for note in s.notes:
        lines.append(f"  - ⚠ _{note}_")
    return lines


def _day_md(d: DayPlan) -> List[str]:
    if d.is_rest:
        return [f"### {d.day} {d.date} — REST DAY", ""]
    head = f"### {d.day} {d.date} — class: **{d.class_stimulus}**"
    if d.also_taxes:
        head += f" _(also taxes: {', '.join(d.also_taxes)})_"
    lines = [head, ""]
    for s in d.ordered_sessions():
        lines.extend(_session_md(s))
    if d.interference:
        lines.append("")
        for note in d.interference:
            lines.append(f"> ⚠ **Interference:** {note}")
    lines.append("")
    return lines


def render_weekly_plan(plan: WeeklyPlan) -> str:
    """Return the full Markdown weekly plan."""
    out: List[str] = []
    out.append(f"# Weekly Plan — week of {plan.week_start}")
    out.append("")
    out.append(f"_Source: {plan.source_label}_")
    out.append("")

    out.append("## Focus blocks")
    for ctx in plan.block_context:
        out.append(f"- {ctx}")
    if plan.latest_known_readiness:
        out.append(f"- _Latest logged readiness:_ **{plan.latest_known_readiness}** "
                   "(future days planned GREEN; adjust each morning).")
    else:
        out.append("- _No readiness logged yet — future days planned GREEN; "
                   "adjust each morning._")
    out.append("")

    # What to push / cruise / skip
    out.append("## What to push, cruise, or skip")
    groups = plan.push_cruise_skip()
    for key in ("PUSH", "CRUISE", "FLEX"):
        items = groups.get(key, [])
        out.append(f"**{_BUCKET_HEADING.get(key, key)}**")
        if items:
            for it in items:
                out.append(f"- {it}")
        else:
            out.append("- _(none this week)_")
        out.append("")

    if plan.triage:
        out.append("## Priority when squeezed (time / energy)")
        for line in plan.triage:
            out.append(f"- {line}")
        out.append("")

    if plan.decisions:
        out.append("## Policy decisions this week")
        for d in plan.decisions:
            out.append(f"- {d}")
        out.append("")

    if plan.flags:
        out.append("## Interference flags")
        for f in plan.flags:
            out.append(f"- ⚠ {f}")
        out.append("")

    out.append("## Schedule")
    out.append("")
    for d in plan.days:
        out.extend(_day_md(d))

    out.append("---")
    out.append("_Loads are deterministic (calculator + plate solver); maxes read "
               "from the Sheet snapshot via MaxesProvider. Policy applied from "
               "programming-policy SKILL.md — not re-improvised._")
    return "\n".join(out)


def render_day_plan(day: DayPlan, heading: str | None = None) -> str:
    """Render a single (e.g. readiness-adjusted) day to Markdown."""
    out: List[str] = []
    if heading:
        out.append(f"## {heading}")
        out.append("")
    out.extend(_day_md(day))
    return "\n".join(out)
