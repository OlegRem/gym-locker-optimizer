from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from lockerfit.layout import LockerLayout
from lockerfit.models import ActiveSession, AssignmentRequest, CandidateOption
from lockerfit.predictor import DurationPredictor


@dataclass(frozen=True)
class AssignmentConfig:
    arrival_window_minutes: int = 10
    departure_window_minutes: int = 15
    passive_crowding_weight: float = 1.5
    overlap_weight: float = 85.0
    nearest_weight: float = 2.0
    average_near_weight: float = 0.8
    preferred_tier_bonus: float = 2.5
    avoided_tier_penalty: float = 7.5


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime

    def overlap_minutes(self, other: "TimeWindow") -> float:
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        if end <= start:
            return 0.0
        return (end - start).total_seconds() / 60.0

    @property
    def minutes(self) -> float:
        return max((self.end - self.start).total_seconds() / 60.0, 1.0)


class LockerAssigner:
    def __init__(
        self,
        layout: LockerLayout,
        predictor: DurationPredictor | None = None,
        config: AssignmentConfig | None = None,
    ) -> None:
        self.layout = layout
        self.predictor = predictor or DurationPredictor()
        self.config = config or AssignmentConfig()

    def recommend(
        self,
        request: AssignmentRequest,
        active_sessions: list[ActiveSession],
        *,
        top_k: int = 5,
        skip_locker_ids: set[int] | None = None,
        explain: bool = True,
    ) -> list[CandidateOption]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        occupied = {session.locker_id for session in active_sessions}
        skipped = skip_locker_ids or set()
        candidate_ids = [
            locker_id
            for locker_id in self.layout.assignable_ids()
            if locker_id not in occupied and locker_id not in skipped
        ]

        expected_check_out = self.predictor.expected_checkout(
            request.arrived_at,
            request.visitor_hash,
        )
        candidate_windows = self._changing_windows(request.arrived_at, expected_check_out)
        session_profiles = [
            (
                session,
                self._temporal_overlap_weight(candidate_windows, self._session_windows(session)),
            )
            for session in active_sessions
        ]

        scored = [
            self._score_candidate(
                locker_id,
                request,
                expected_check_out,
                candidate_windows,
                session_profiles,
                include_reasons=False,
            )
            for locker_id in candidate_ids
        ]
        scored.sort(key=lambda option: (-option.score, option.locker_id))
        top = scored[:top_k]
        if not explain:
            return top

        return [
            self._score_candidate(
                option.locker_id,
                request,
                expected_check_out,
                candidate_windows,
                session_profiles,
                include_reasons=True,
            )
            for option in top
        ]

    def assign(
        self,
        request: AssignmentRequest,
        active_sessions: list[ActiveSession],
        *,
        skip_locker_ids: set[int] | None = None,
        explain: bool = True,
    ) -> CandidateOption:
        options = self.recommend(
            request,
            active_sessions,
            top_k=1,
            skip_locker_ids=skip_locker_ids,
            explain=explain,
        )
        if not options:
            raise RuntimeError("no available lockers")
        return options[0]

    def _score_candidate(
        self,
        locker_id: int,
        request: AssignmentRequest,
        expected_check_out: datetime,
        candidate_windows: tuple[TimeWindow, TimeWindow],
        session_profiles: list[tuple[ActiveSession, float]],
        *,
        include_reasons: bool,
    ) -> CandidateOption:
        locker = self.layout.get(locker_id)
        distances = [
            (session, temporal_weight, self.layout.distance(locker_id, session.locker_id))
            for session, temporal_weight in session_profiles
        ]
        distances.sort(key=lambda item: item[2])

        nearest_distance = distances[0][2] if distances else None
        average_near = self._average_nearest(distances, limit=5)
        passive_crowding = sum(1.0 / (distance + 1.0) for _, _, distance in distances)
        overlap_risk = sum(
            self._overlap_risk(temporal_weight, distance)
            for _, temporal_weight, distance in distances
        )

        score = 0.0
        if nearest_distance is not None:
            score += nearest_distance * self.config.nearest_weight
        if average_near is not None:
            score += average_near * self.config.average_near_weight

        score -= passive_crowding * self.config.passive_crowding_weight
        score -= overlap_risk * self.config.overlap_weight

        if request.preferred_tier and locker.tier == request.preferred_tier:
            score += self.config.preferred_tier_bonus
        if locker.tier in request.avoided_tiers:
            score -= self.config.avoided_tier_penalty

        return CandidateOption(
            locker_id=locker_id,
            score=round(score, 4),
            nearest_active_distance=None if nearest_distance is None else round(nearest_distance, 3),
            overlap_risk=round(overlap_risk, 4),
            expected_check_out=expected_check_out,
            reasons=(
                self._reasons(locker_id, distances, overlap_risk, request)
                if include_reasons
                else ()
            ),
        )

    def _overlap_risk(
        self,
        temporal_weight: float,
        distance: float,
    ) -> float:
        return temporal_weight * (1.0 / (distance + 1.0))

    def _temporal_overlap_weight(
        self,
        candidate_windows: tuple[TimeWindow, TimeWindow],
        session_windows: tuple[TimeWindow, TimeWindow],
    ) -> float:
        overlap = 0.0
        for candidate_window in candidate_windows:
            for session_window in session_windows:
                overlap += candidate_window.overlap_minutes(session_window) / candidate_window.minutes
        return overlap

    def _changing_windows(
        self,
        check_in: datetime,
        expected_check_out: datetime,
    ) -> tuple[TimeWindow, TimeWindow]:
        arrival_end = check_in + timedelta(minutes=self.config.arrival_window_minutes)
        departure_start = expected_check_out - timedelta(minutes=self.config.departure_window_minutes)
        if departure_start < arrival_end:
            departure_start = arrival_end
        return (
            TimeWindow(check_in, arrival_end),
            TimeWindow(departure_start, expected_check_out),
        )

    def _session_windows(self, session: ActiveSession) -> tuple[TimeWindow, TimeWindow]:
        session_checkout = session.expected_check_out or self.predictor.expected_checkout(
            session.check_in,
            session.visitor_hash,
        )
        return self._changing_windows(session.check_in, session_checkout)

    @staticmethod
    def _average_nearest(
        distances: list[tuple[ActiveSession, float, float]],
        *,
        limit: int,
    ) -> float | None:
        if not distances:
            return None
        subset = [distance for _, _, distance in distances[:limit]]
        return sum(subset) / len(subset)

    def _reasons(
        self,
        locker_id: int,
        distances: list[tuple[ActiveSession, float, float]],
        overlap_risk: float,
        request: AssignmentRequest,
    ) -> tuple[str, ...]:
        locker = self.layout.get(locker_id)
        reasons: list[str] = [f"{locker.zone}, {locker.tier} tier"]
        if distances:
            nearest_session, _, nearest_distance = distances[0]
            reasons.append(
                f"nearest occupied locker is {nearest_session.locker_id} "
                f"at distance {nearest_distance:.1f}"
            )
        else:
            reasons.append("no occupied lockers in the current layout")
        if overlap_risk < 0.05:
            reasons.append("low predicted changing-window overlap")
        else:
            reasons.append(f"predicted overlap risk {overlap_risk:.2f}")
        if request.preferred_tier and locker.tier == request.preferred_tier:
            reasons.append(f"matches preferred tier {request.preferred_tier}")
        return tuple(reasons)
