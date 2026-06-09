"""Deterministic plate-loading solver.

Given a target total weight, a bar, and a plate inventory, compute the loadable
total nearest to the target and the exact plates per side. This is the heart of
the spec's single most important constraint (Section 8): plate math is
deterministic, tested code — the model never does this arithmetic.

Design notes
------------
* All math is done in integer "centi-kg" (kg * 100) to avoid binary-float
  error on values like 1.25 and 0.5. Inputs are quantised once on the way in.
* A bar loads symmetrically, so achievable totals are
  `bar + 2 * (per-side sum)`. We search achievable per-side sums.
* A bounded-knapsack DP gives, for every reachable per-side sum, the minimum
  plate count. Unlimited supply (count is None) is treated as "as many as fit
  under the search bound".
* Target selection (deterministic, in order):
      1. smallest |achieved - target|
      2. fewest plates per side
      3. prefer not overshooting (round down on an exact-distance tie)
      4. smaller sum (final defensive tie-break)
* Reconstruction loads heaviest plates first among the min-count solutions
  (the conventional way a lifter loads a bar), while respecting per-denom
  counts. It is count-safe by construction: each denomination is committed
  exactly once, heaviest-first, capped at its available count.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from cfprog.models import Loadout, PlateCount, PlateInventory

_SCALE = 100  # centi-kg
_INF = float("inf")


def _to_centi(kg: float) -> int:
    return int(round(kg * _SCALE))


def _from_centi(centi: int) -> float:
    return centi / _SCALE


def best_loadout(target_kg: float, inventory: PlateInventory) -> Loadout:
    """Solve plate math for a single target weight. Pure and deterministic."""
    bar_c = _to_centi(inventory.bar_weight_kg)
    target_c = _to_centi(target_kg)

    # Sub-bar / at-bar load: can't remove weight from an empty bar.
    if target_c <= bar_c:
        return Loadout(
            target_kg=target_kg,
            achieved_kg=inventory.bar_weight_kg,
            bar_weight_kg=inventory.bar_weight_kg,
            per_side=(),
            exact=(target_c == bar_c),
            below_bar=(target_c < bar_c),
        )

    # Per-side denominations (centi-kg) with per-side counts, heaviest first.
    denoms: List[Tuple[int, Optional[int]]] = sorted(
        ((_to_centi(p.weight_kg), p.count) for p in inventory.plates),
        key=lambda d: -d[0],
    )
    max_denom = denoms[0][0]

    # Search per-side sums up to the half-target plus one plate, so we can round
    # either down or up to the nearest loadable weight.
    half_target_c = (target_c - bar_c) / 2.0
    bound = int(half_target_c) + max_denom + 1

    min_count = _min_count_table(denoms, bound)

    # Pick the reachable per-side sum giving the best total under the rules.
    best_key: Optional[Tuple[int, float, int, int]] = None
    best_sum = 0
    for s in range(bound + 1):
        if min_count[s] == _INF:
            continue
        total_c = bar_c + 2 * s
        abs_delta = abs(total_c - target_c)
        overshoot = 1 if total_c > target_c else 0  # prefer rounding down on ties
        key = (abs_delta, min_count[s], overshoot, s)
        if best_key is None or key < best_key:
            best_key = key
            best_sum = s

    per_side = _reconstruct(denoms, min_count, best_sum)
    achieved_c = bar_c + 2 * best_sum
    return Loadout(
        target_kg=target_kg,
        achieved_kg=_from_centi(achieved_c),
        bar_weight_kg=inventory.bar_weight_kg,
        per_side=per_side,
        exact=(achieved_c == target_c),
        below_bar=False,
    )


def _min_count_table(
    denoms: List[Tuple[int, Optional[int]]], bound: int
) -> List[float]:
    """min_count[s] = fewest plates (per side) to reach exactly s, else inf.

    Bounded knapsack: each denomination is added in a single layer using a
    snapshot of the pre-denomination state, so its multiplicity is respected.
    """
    min_count: List[float] = [_INF] * (bound + 1)
    min_count[0] = 0
    for denom_c, avail in denoms:
        max_k = bound // denom_c
        if avail is not None:
            max_k = min(max_k, avail)
        if max_k <= 0:
            continue
        prev = min_count[:]
        for s in range(bound + 1):
            base = prev[s]
            if base == _INF:
                continue
            for k in range(1, max_k + 1):
                ns = s + k * denom_c
                if ns > bound:
                    break
                cand = base + k
                if cand < min_count[ns]:
                    min_count[ns] = cand
    return min_count


def _reconstruct(
    denoms: List[Tuple[int, Optional[int]]],
    min_count: List[float],
    total_sum: int,
) -> Tuple[PlateCount, ...]:
    """Heaviest-first reconstruction of a min-count solution for total_sum.

    For each denomination (heaviest first) take the largest k such that the
    remaining weight is still achievable in exactly the remaining plate budget
    (validated against min_count). Count-safe: each denom committed once, k<=avail.
    """
    counts: Dict[int, int] = {}
    remaining = total_sum
    count_left = int(min_count[total_sum]) if min_count[total_sum] != _INF else 0
    for denom_c, avail in denoms:
        if remaining == 0:
            break
        max_k = remaining // denom_c
        if avail is not None:
            max_k = min(max_k, avail)
        for k in range(max_k, 0, -1):
            rest = remaining - k * denom_c
            if min_count[rest] == count_left - k:
                counts[denom_c] = k
                remaining = rest
                count_left -= k
                break
    ordered = sorted(counts.items(), key=lambda kv: -kv[0])
    return tuple(PlateCount(weight_kg=_from_centi(d), count=k) for d, k in ordered)
