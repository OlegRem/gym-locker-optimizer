from __future__ import annotations

from dataclasses import replace
from math import sqrt
from typing import Iterable

from lockerfit.models import Locker


class LockerLayout:
    def __init__(self, lockers: Iterable[Locker], tier_weight: float = 0.35) -> None:
        self.lockers = {locker.id: locker for locker in lockers}
        self.tier_weight = tier_weight
        self._assignable_ids = sorted(
            locker.id for locker in self.lockers.values() if locker.is_assignable
        )
        self._distance_cache: dict[tuple[int, int], float] = {}
        if not self.lockers:
            raise ValueError("layout must contain at least one locker")

    @classmethod
    def odd_even(
        cls,
        number_of_lockers: int = 530,
        *,
        start_id: int = 1,
        pairs_per_row: int = 53,
        row_gap: float = 3.0,
        tier_weight: float = 0.35,
    ) -> "LockerLayout":
        if number_of_lockers <= 0:
            raise ValueError("number_of_lockers must be positive")
        if pairs_per_row <= 0:
            raise ValueError("pairs_per_row must be positive")

        lockers: list[Locker] = []
        for locker_id in range(start_id, start_id + number_of_lockers):
            zero_based = locker_id - start_id
            pair_index = zero_based // 2
            row = pair_index // pairs_per_row
            col = pair_index % pairs_per_row
            is_upper = zero_based % 2 == 0
            tier = "top" if is_upper else "bottom"
            lockers.append(
                Locker(
                    id=locker_id,
                    x=float(col),
                    y=float(row) * row_gap,
                    tier=tier,
                    zone=f"row-{row + 1}",
                )
            )
        return cls(lockers=lockers, tier_weight=tier_weight)

    def with_status(self, locker_id: int, status: str) -> "LockerLayout":
        locker = self.get(locker_id)
        updated = dict(self.lockers)
        updated[locker_id] = replace(locker, status=status)
        return LockerLayout(updated.values(), tier_weight=self.tier_weight)

    def get(self, locker_id: int) -> Locker:
        try:
            return self.lockers[locker_id]
        except KeyError as exc:
            raise KeyError(f"unknown locker id: {locker_id}") from exc

    def assignable_ids(self) -> list[int]:
        return list(self._assignable_ids)

    def distance(self, a_id: int, b_id: int) -> float:
        key = (a_id, b_id) if a_id <= b_id else (b_id, a_id)
        if key in self._distance_cache:
            return self._distance_cache[key]

        a = self.get(a_id)
        b = self.get(b_id)
        tier_delta = 0.0 if a.tier == b.tier else self.tier_weight
        distance = sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + tier_delta**2)
        self._distance_cache[key] = distance
        return distance

    def nearest(self, locker_id: int, other_ids: Iterable[int]) -> tuple[int, float] | None:
        distances = [(other_id, self.distance(locker_id, other_id)) for other_id in other_ids]
        if not distances:
            return None
        return min(distances, key=lambda item: item[1])
