"""Put the vendored `cfprog` package on the path for the test run.

The scripts are invoked as `python3 scripts/<name>.py` and add this directory to
sys.path themselves; this conftest does the same for pytest so the tests under
`scripts/tests/` can `import cfprog` without an install step.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import pytest


def pytest_configure(config: "pytest.Config") -> None:
    config.addinivalue_line(
        "markers",
        "supabase: requires a running local Supabase/Postgres (DATABASE_URL)",
    )


@pytest.fixture(scope="session")
def db():
    """A psycopg connection to the local Supabase Postgres, or skip if unreachable."""
    psycopg = pytest.importorskip("psycopg")
    dsn = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )
    try:
        conn = psycopg.connect(dsn, autocommit=False)
    except psycopg.OperationalError as exc:  # DB not running -> skip, don't fail
        pytest.skip(f"no Supabase DB reachable at {dsn}: {exc}")
    yield conn
    conn.rollback()
    conn.close()
