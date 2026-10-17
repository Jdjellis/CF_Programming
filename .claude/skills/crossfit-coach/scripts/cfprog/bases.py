"""Which 1RM a lift is loaded off — the athlete's base-lift rules.

    snatch variations (power, pause, hang, pulls, ...)  -> snatch 1RM
    clean variations (power, pause, hang, pulls, ...)   -> clean 1RM
    jerks are specific: push jerk -> push jerk 1RM, split jerk -> split jerk 1RM
                        (a plain "jerk" is a split jerk)
    clean + jerk complexes -> the limiter: the lower of the clean 1RM and that
                        jerk's 1RM (power clean + push jerk -> min(clean, push jerk))
    anything else        -> its own 1RM, or the 1RM of the lift with a leading
                        pause/tempo/paused modifier stripped (pause front squat
                        -> front squat)

A variation's own recorded max (e.g. power_snatch) is deliberately NOT used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from cfprog.maxes import MaxesProvider, normalize_lift

_MODIFIERS = ("pause", "paused", "tempo")


@dataclass(frozen=True)
class Base:
    """The 1RM a lift is loaded off."""

    one_rm_kg: float
    lift: str                         # the lift whose 1RM is used, e.g. "push_jerk"
    others: Tuple[Tuple[str, float], ...] = ()  # complex components it beat as the limiter

    def describe(self) -> str:
        """e.g. 'snatch 1RM 90' or 'push jerk 1RM 110, the limiter over clean 130'."""
        text = f"{self.lift.replace('_', ' ')} 1RM {self.one_rm_kg:g}"
        if self.others:
            over = ", ".join(f"{name.replace('_', ' ')} {kg:g}" for name, kg in self.others)
            text += f", the limiter over {over}"
        return text


def _jerk_base(key: str) -> str | None:
    if "push_jerk" in key:
        return "push_jerk"
    if "jerk" in key:
        return "split_jerk"
    return None


def resolve_base(lift: str, maxes: MaxesProvider) -> Base:
    key = normalize_lift(lift)
    has_clean = "clean" in key
    jerk = _jerk_base(key)

    if "snatch" in key:
        return Base(maxes.get_max("snatch"), "snatch")
    if has_clean and jerk:
        parts = sorted(((maxes.get_max(name), name) for name in ("clean", jerk)), key=lambda p: (p[0], p[1] != jerk))
        (kg, name), (other_kg, other) = parts
        return Base(kg, name, ((other, other_kg),))
    if has_clean:
        return Base(maxes.get_max("clean"), "clean")
    if jerk:
        return Base(maxes.get_max(jerk), jerk)

    stripped = key
    while True:
        head, _, rest = stripped.partition("_")
        if head in _MODIFIERS and rest:
            stripped = rest
        else:
            break
    try:
        return Base(maxes.get_max(key), key)
    except KeyError:
        if stripped == key:
            raise
        return Base(maxes.get_max(stripped), stripped)
