from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from random import Random

from lockerfit.layout import LockerLayout
from lockerfit.models import ActiveSession, AssignmentRequest, VisitRecord
from lockerfit.optimizer import LockerAssigner, TimeWindow
from lockerfit.predictor import DurationPredictor


@dataclass(frozen=True)
class PlannedVisit:
    visitor_hash: str
    check_in: datetime
    check_out: datetime


@dataclass(frozen=True)
class AssignedVisit:
    visitor_hash: str
    locker_id: int
    check_in: datetime
    check_out: datetime
    expected_check_out: datetime


@dataclass(frozen=True)
class SimulationResult:
    strategy: str
    assigned: int
    close_overlap_events: int
    overlap_windows: int
    close_overlap_rate: float
    average_nearest_distance: float


def generate_visits(
    *,
    days: int,
    visitors_per_day: int,
    seed: int = 7,
    start_day: date | None = None,
) -> list[PlannedVisit]:
    if days <= 0:
        raise ValueError("days must be positive")
    if visitors_per_day <= 0:
        raise ValueError("visitors_per_day must be positive")

    rng = Random(seed)
    start_day = start_day or date(2026, 1, 5)
    visitor_pool = [f"anon-{index:04d}" for index in range(max(80, visitors_per_day * 3))]
    visits: list[PlannedVisit] = []

    for day_index in range(days):
        current_day = start_day + timedelta(days=day_index)
        weekday = current_day.weekday()
        day_multiplier = 0.78 if weekday >= 5 else 1.0
        total_visitors = max(1, int(visitors_per_day * day_multiplier))
        for _ in range(total_visitors):
            visitor_hash = rng.choice(visitor_pool)
            arrival_minutes = _sample_arrival_minutes(rng)
            duration = _sample_duration_minutes(rng, visitor_hash, weekday)
            check_in = datetime.combine(current_day, time()) + timedelta(minutes=arrival_minutes)
            check_out = check_in + timedelta(minutes=duration)
            visits.append(PlannedVisit(visitor_hash, check_in, check_out))

    visits.sort(key=lambda visit: visit.check_in)
    return visits


def compare_strategies(
    layout: LockerLayout,
    visits: list[PlannedVisit],
    *,
    seed: int = 11,
) -> list[SimulationResult]:
    return [
        run_strategy(layout, visits, strategy="random", seed=seed),
        run_strategy(layout, visits, strategy="smart", seed=seed),
    ]


def run_strategy(
    layout: LockerLayout,
    visits: list[PlannedVisit],
    *,
    strategy: str,
    seed: int = 11,
) -> SimulationResult:
    if strategy not in {"random", "smart"}:
        raise ValueError("strategy must be 'random' or 'smart'")

    rng = Random(seed)
    assigned: list[AssignedVisit] = []
    recorded: set[int] = set()
    predictor = DurationPredictor()
    assignable_ids = layout.assignable_ids()

    for visit in visits:
        for index, prior in enumerate(assigned):
            if index not in recorded and prior.check_out <= visit.check_in:
                predictor.add(
                    VisitRecord(
                        visitor_hash=prior.visitor_hash,
                        check_in=prior.check_in,
                        check_out=prior.check_out,
                    )
                )
                recorded.add(index)

        active = [prior for prior in assigned if prior.check_out > visit.check_in]
        occupied = {prior.locker_id for prior in active}
        available = [locker_id for locker_id in assignable_ids if locker_id not in occupied]
        if not available:
            continue

        active_sessions = [
            ActiveSession(
                session_id=f"session-{index}",
                locker_id=prior.locker_id,
                check_in=prior.check_in,
                visitor_hash=prior.visitor_hash,
                expected_check_out=prior.expected_check_out,
            )
            for index, prior in enumerate(active)
        ]

        if strategy == "random":
            locker_id = rng.choice(available)
            expected_check_out = predictor.expected_checkout(visit.check_in, visit.visitor_hash)
        else:
            assigner = LockerAssigner(layout=layout, predictor=predictor)
            option = assigner.assign(
                AssignmentRequest(
                    arrived_at=visit.check_in,
                    visitor_hash=visit.visitor_hash,
                    preferred_tier="top",
                ),
                active_sessions,
                explain=False,
            )
            locker_id = option.locker_id
            expected_check_out = option.expected_check_out

        assigned.append(
            AssignedVisit(
                visitor_hash=visit.visitor_hash,
                locker_id=locker_id,
                check_in=visit.check_in,
                check_out=visit.check_out,
                expected_check_out=expected_check_out,
            )
        )

    return evaluate_assignments(layout, assigned, strategy=strategy)


def evaluate_assignments(
    layout: LockerLayout,
    assigned: list[AssignedVisit],
    *,
    strategy: str,
    close_radius: float = 2.0,
) -> SimulationResult:
    windows: list[tuple[int, int, TimeWindow]] = []
    for index, visit in enumerate(assigned):
        windows.extend(_actual_windows(index, visit))

    close_events = 0
    overlap_windows = 0
    nearest_distances: list[float] = []

    for left_index, (left_visit, left_locker, left_window) in enumerate(windows):
        nearest = None
        for right_visit, right_locker, right_window in windows[left_index + 1 :]:
            if left_visit == right_visit:
                continue
            if left_window.overlap_minutes(right_window) <= 0:
                continue
            overlap_windows += 1
            distance = layout.distance(left_locker, right_locker)
            nearest = distance if nearest is None else min(nearest, distance)
            if distance <= close_radius:
                close_events += 1
        if nearest is not None:
            nearest_distances.append(nearest)

    close_rate = close_events / overlap_windows if overlap_windows else 0.0
    average_nearest = (
        sum(nearest_distances) / len(nearest_distances) if nearest_distances else 0.0
    )
    return SimulationResult(
        strategy=strategy,
        assigned=len(assigned),
        close_overlap_events=close_events,
        overlap_windows=overlap_windows,
        close_overlap_rate=close_rate,
        average_nearest_distance=average_nearest,
    )


def _actual_windows(index: int, visit: AssignedVisit) -> list[tuple[int, int, TimeWindow]]:
    return [
        (
            index,
            visit.locker_id,
            TimeWindow(visit.check_in, visit.check_in + timedelta(minutes=10)),
        ),
        (
            index,
            visit.locker_id,
            TimeWindow(visit.check_out - timedelta(minutes=15), visit.check_out),
        ),
    ]


def _sample_arrival_minutes(rng: Random) -> int:
    roll = rng.random()
    if roll < 0.28:
        center = 7 * 60 + 40
        spread = 55
    elif roll < 0.47:
        center = 12 * 60 + 40
        spread = 45
    else:
        center = 18 * 60 + 30
        spread = 70
    return min(23 * 60, max(6 * 60, int(rng.gauss(center, spread))))


def _sample_duration_minutes(rng: Random, visitor_hash: str, weekday: int) -> int:
    stable_offset = (sum(ord(char) for char in visitor_hash) % 35) - 12
    weekday_offset = -8 if weekday >= 5 else 0
    duration = int(rng.gauss(92 + stable_offset + weekday_offset, 24))
    return min(210, max(35, duration))
