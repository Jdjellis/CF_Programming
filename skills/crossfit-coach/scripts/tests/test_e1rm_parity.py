import pytest

from cfprog.estimate import estimate_one_rm

# Weights spanning bar+plate realities, reps past the table's bounds (clamp path),
# and RPEs including half points (rounding path).
_WEIGHTS = (40.0, 60.0, 82.5, 100.0, 122.5, 165.0)
_REPS = tuple(range(1, 13))
_RPES = (None, 6.0, 7.0, 7.5, 8.0, 8.5, 9.0, 10.0)


@pytest.mark.supabase
def test_sql_e1rm_matches_cfprog(db):
    mismatches = []
    with db.cursor() as cur:
        for weight in _WEIGHTS:
            for reps in _REPS:
                for rpe in _RPES:
                    cur.execute("select cf_est_1rm(%s::numeric, %s::integer, %s::numeric)", (weight, reps, rpe))
                    sql_val = float(cur.fetchone()[0])
                    py_val, _notes = estimate_one_rm(weight, reps, rpe)
                    # Estimates are 2-dp, so any genuine divergence is >= 0.01; a
                    # 0.005 threshold therefore asserts exact parity while tolerating
                    # float-representation noise. cf_est_1rm rounds half-to-even to
                    # match cfprog exactly (a half-away mirror diverges by a cent on
                    # half-cent ties such as 82.5 @ 8RM = 103.125).
                    if abs(sql_val - py_val) > 0.005:
                        mismatches.append((weight, reps, rpe, sql_val, py_val))
    db.rollback()
    assert not mismatches, f"SQL/cfprog e1RM divergence: {mismatches[:5]} (+{len(mismatches)})"
