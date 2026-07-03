from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median

from lockerfit.models import VisitRecord


class DurationPredictor:
    def __init__(self, default_minutes: int = 90, min_samples: int = 3) -> None:
        self.default_minutes = default_minutes
        self.min_samples = min_samples
        self._global: list[int] = []
        self._weekday: dict[int, list[int]] = defaultdict(list)
        self._visitor: dict[str, list[int]] = defaultdict(list)
        self._visitor_weekday: dict[tuple[str, int], list[int]] = defaultdict(list)

    def fit(self, records: list[VisitRecord]) -> "DurationPredictor":
        for record in records:
            self.add(record)
        return self

    def add(self, record: VisitRecord) -> "DurationPredictor":
        minutes = self._clean_duration(record.duration)
        if minutes is None:
            return self
        self._global.append(minutes)
        self._weekday[record.weekday].append(minutes)
        if record.visitor_hash:
            self._visitor[record.visitor_hash].append(minutes)
            self._visitor_weekday[(record.visitor_hash, record.weekday)].append(minutes)
        return self

    def predict(self, arrived_at: datetime, visitor_hash: str | None = None) -> timedelta:
        weekday = arrived_at.weekday()
        candidates: list[list[int]] = []

        if visitor_hash:
            candidates.append(self._visitor_weekday.get((visitor_hash, weekday), []))
            candidates.append(self._visitor.get(visitor_hash, []))

        candidates.append(self._weekday.get(weekday, []))
        candidates.append(self._global)

        for sample in candidates:
            if len(sample) >= self.min_samples:
                return timedelta(minutes=int(median(sample)))

        return timedelta(minutes=self.default_minutes)

    def expected_checkout(self, arrived_at: datetime, visitor_hash: str | None = None) -> datetime:
        return arrived_at + self.predict(arrived_at, visitor_hash)

    @staticmethod
    def _clean_duration(duration: timedelta) -> int | None:
        minutes = int(duration.total_seconds() // 60)
        if minutes < 15 or minutes > 8 * 60:
            return None
        return minutes
