"""Logged-actuals store: recorded sets, RPE, and daily readiness.

This is the *database* for the system — the thing analytics queries. It is
deliberately separate from the maxes source of truth: the Google Sheet stays a
read-only snapshot of current XRMs (via `MaxesProvider`), while everything you
actually perform is logged here.

Storage sits behind the `LogStore` interface (same pattern as `MaxesProvider`),
so the SQLite backend can later be swapped for Postgres or a hosted DB without
touching callers. SQLite is the default: one local file, zero infra, full SQL
for analytics.

No load arithmetic happens here — weights come from the deterministic
calculator and are recorded verbatim.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

from cfprog.maxes import normalize_lift
from cfprog.models import PrescriptionResult

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "cfprog.db"

READINESS_TIERS = ("green", "amber", "red")


def _today_iso() -> str:
    return date.today().isoformat()


def _coerce_date(value: "date | str | None") -> str:
    if value is None:
        return _today_iso()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class LoggedSet:
    """A single performed set (or a representative set of a group)."""

    lift: str
    weight_kg: float
    reps: int
    date: str = field(default_factory=_today_iso)  # ISO YYYY-MM-DD
    rpe: Optional[float] = None
    set_index: int = 1
    target_desc: Optional[str] = None         # prescription, e.g. "85% of 1RM"
    prescribed_weight_kg: Optional[float] = None  # working weight before rounding
    readiness: Optional[str] = None           # green|amber|red at session time
    notes: Optional[str] = None
    id: Optional[int] = None                  # assigned on insert
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.lift = normalize_lift(self.lift)
        self.date = _coerce_date(self.date)
        if self.reps < 1:
            raise ValueError("reps must be >= 1")
        if self.weight_kg < 0:
            raise ValueError("weight_kg must be >= 0")
        if self.rpe is not None and not (1 <= self.rpe <= 10):
            raise ValueError("rpe must be in [1, 10]")
        if self.readiness is not None and self.readiness not in READINESS_TIERS:
            raise ValueError(f"readiness must be one of {READINESS_TIERS}")

    @property
    def tonnage_kg(self) -> float:
        return round(self.weight_kg * self.reps, 5)

    @classmethod
    def from_prescription(
        cls,
        result: "PrescriptionResult",
        reps: int,
        rpe: Optional[float] = None,
        weight_kg: Optional[float] = None,
        readiness: Optional[str] = None,
        date: "date | str | None" = None,
        set_index: int = 1,
        notes: Optional[str] = None,
    ) -> "LoggedSet":
        """Build a log entry from a calculator prescription + what you actually did.

        Defaults `weight_kg` to the calculator's loadable weight (the bar you'd
        actually have loaded), and records the prescription for traceability.
        """
        return cls(
            lift=result.lift,
            weight_kg=weight_kg if weight_kg is not None else result.loadout.achieved_kg,
            reps=reps,
            rpe=rpe,
            date=date,
            target_desc=result.target.describe(),
            prescribed_weight_kg=result.working_weight_kg,
            readiness=readiness,
            set_index=set_index,
            notes=notes,
        )


@dataclass
class ReadinessEntry:
    """One day's readiness signal. One row per date (latest write wins)."""

    tier: str                                 # green|amber|red
    date: str = field(default_factory=_today_iso)
    score: Optional[float] = None             # e.g. a wearable recovery score
    source: Optional[str] = None              # "wearable" | "self_report"
    notes: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.date = _coerce_date(self.date)
        if self.tier not in READINESS_TIERS:
            raise ValueError(f"tier must be one of {READINESS_TIERS}")


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

@runtime_checkable
class LogStore(Protocol):
    """Anything that can persist and query logged actuals."""

    def log_set(self, entry: LoggedSet) -> LoggedSet: ...

    def sets(
        self,
        lift: Optional[str] = None,
        since: "date | str | None" = None,
        until: "date | str | None" = None,
    ) -> List[LoggedSet]: ...

    def log_readiness(self, entry: ReadinessEntry) -> ReadinessEntry: ...

    def readiness(self, since: "date | str | None" = None) -> List[ReadinessEntry]: ...

    def latest_readiness(
        self, on_date: "date | str | None" = None
    ) -> Optional[ReadinessEntry]: ...


# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS logged_set (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    date                 TEXT    NOT NULL,
    lift                 TEXT    NOT NULL,
    set_index            INTEGER NOT NULL DEFAULT 1,
    weight_kg            REAL    NOT NULL,
    reps                 INTEGER NOT NULL,
    rpe                  REAL,
    target_desc          TEXT,
    prescribed_weight_kg REAL,
    readiness            TEXT,
    notes                TEXT,
    created_at           TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logged_set_lift ON logged_set(lift);
CREATE INDEX IF NOT EXISTS idx_logged_set_date ON logged_set(date);

CREATE TABLE IF NOT EXISTS readiness (
    date       TEXT PRIMARY KEY,
    tier       TEXT NOT NULL,
    score      REAL,
    source     TEXT,
    notes      TEXT,
    created_at TEXT NOT NULL
);
"""


class SQLiteLogStore:
    """SQLite-backed LogStore. Pass ':memory:' for an ephemeral store (tests)."""

    def __init__(self, db_path: "Path | str | None" = None) -> None:
        if db_path is None:
            db_path = _DEFAULT_DB
        self.db_path = db_path if db_path == ":memory:" else Path(db_path)
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SQLiteLogStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- sets ---------------------------------------------------------------

    def log_set(self, entry: LoggedSet) -> LoggedSet:
        entry.created_at = entry.created_at or datetime.now().isoformat(timespec="seconds")
        cur = self._conn.execute(
            """
            INSERT INTO logged_set
                (date, lift, set_index, weight_kg, reps, rpe, target_desc,
                 prescribed_weight_kg, readiness, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.date, entry.lift, entry.set_index, entry.weight_kg,
                entry.reps, entry.rpe, entry.target_desc,
                entry.prescribed_weight_kg, entry.readiness, entry.notes,
                entry.created_at,
            ),
        )
        self._conn.commit()
        entry.id = cur.lastrowid
        return entry

    def sets(
        self,
        lift: Optional[str] = None,
        since: "date | str | None" = None,
        until: "date | str | None" = None,
    ) -> List[LoggedSet]:
        clauses, params = [], []
        if lift is not None:
            clauses.append("lift = ?")
            params.append(normalize_lift(lift))
        if since is not None:
            clauses.append("date >= ?")
            params.append(_coerce_date(since))
        if until is not None:
            clauses.append("date <= ?")
            params.append(_coerce_date(until))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM logged_set{where} ORDER BY date, id", params
        ).fetchall()
        return [self._row_to_set(r) for r in rows]

    @staticmethod
    def _row_to_set(r: sqlite3.Row) -> LoggedSet:
        s = LoggedSet(
            lift=r["lift"],
            weight_kg=r["weight_kg"],
            reps=r["reps"],
            date=r["date"],
            rpe=r["rpe"],
            set_index=r["set_index"],
            target_desc=r["target_desc"],
            prescribed_weight_kg=r["prescribed_weight_kg"],
            readiness=r["readiness"],
            notes=r["notes"],
        )
        s.id = r["id"]
        s.created_at = r["created_at"]
        return s

    # -- readiness ----------------------------------------------------------

    def log_readiness(self, entry: ReadinessEntry) -> ReadinessEntry:
        entry.created_at = entry.created_at or datetime.now().isoformat(timespec="seconds")
        # One row per day; latest write wins.
        self._conn.execute(
            """
            INSERT INTO readiness (date, tier, score, source, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                tier=excluded.tier, score=excluded.score, source=excluded.source,
                notes=excluded.notes, created_at=excluded.created_at
            """,
            (entry.date, entry.tier, entry.score, entry.source, entry.notes,
             entry.created_at),
        )
        self._conn.commit()
        return entry

    def readiness(self, since: "date | str | None" = None) -> List[ReadinessEntry]:
        if since is None:
            rows = self._conn.execute(
                "SELECT * FROM readiness ORDER BY date"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM readiness WHERE date >= ? ORDER BY date",
                (_coerce_date(since),),
            ).fetchall()
        return [self._row_to_readiness(r) for r in rows]

    def latest_readiness(
        self, on_date: "date | str | None" = None
    ) -> Optional[ReadinessEntry]:
        if on_date is None:
            row = self._conn.execute(
                "SELECT * FROM readiness ORDER BY date DESC LIMIT 1"
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM readiness WHERE date <= ? ORDER BY date DESC LIMIT 1",
                (_coerce_date(on_date),),
            ).fetchone()
        return self._row_to_readiness(row) if row else None

    @staticmethod
    def _row_to_readiness(r: sqlite3.Row) -> ReadinessEntry:
        e = ReadinessEntry(
            tier=r["tier"],
            date=r["date"],
            score=r["score"],
            source=r["source"],
            notes=r["notes"],
        )
        e.created_at = r["created_at"]
        return e
