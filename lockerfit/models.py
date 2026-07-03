from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Locker:
    id: int
    x: float
    y: float
    tier: str = "single"
    zone: str = "main"
    status: str = "available"

    @property
    def is_assignable(self) -> bool:
        return self.status == "available"


@dataclass(frozen=True)
class VisitRecord:
    visitor_hash: str | None
    check_in: datetime
    check_out: datetime

    @property
    def duration(self) -> timedelta:
        return self.check_out - self.check_in

    @property
    def weekday(self) -> int:
        return self.check_in.weekday()


@dataclass(frozen=True)
class ActiveSession:
    session_id: str
    locker_id: int
    check_in: datetime
    visitor_hash: str | None = None
    expected_check_out: datetime | None = None


@dataclass(frozen=True)
class AssignmentRequest:
    arrived_at: datetime
    visitor_hash: str | None = None
    preferred_tier: str | None = None
    avoided_tiers: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CandidateOption:
    locker_id: int
    score: float
    nearest_active_distance: float | None
    overlap_risk: float
    expected_check_out: datetime
    reasons: tuple[str, ...] = ()
