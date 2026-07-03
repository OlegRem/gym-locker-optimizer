from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from lockerfit.layout import LockerLayout
from lockerfit.models import ActiveSession, AssignmentRequest, VisitRecord
from lockerfit.optimizer import LockerAssigner
from lockerfit.predictor import DurationPredictor
from lockerfit.simulation import compare_strategies, generate_visits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lockerfit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate = subparsers.add_parser("simulate", help="compare random and smart assignment")
    simulate.add_argument("--lockers", type=int, default=530)
    simulate.add_argument("--pairs-per-row", type=int, default=53)
    simulate.add_argument("--days", type=int, default=14)
    simulate.add_argument("--visitors-per-day", type=int, default=120)
    simulate.add_argument("--seed", type=int, default=7)

    recommend = subparsers.add_parser("recommend", help="rank available lockers")
    recommend.add_argument("--active-json", type=Path, required=True)
    recommend.add_argument("--history-csv", type=Path)
    recommend.add_argument("--lockers", type=int, default=530)
    recommend.add_argument("--pairs-per-row", type=int, default=53)
    recommend.add_argument("--arrival", default=None)
    recommend.add_argument("--visitor-id", default=None)
    recommend.add_argument("--preferred-tier", default="top")
    recommend.add_argument("--avoid-tier", action="append", default=[])
    recommend.add_argument("--top", type=int, default=5)

    args = parser.parse_args(argv)
    if args.command == "simulate":
        return _simulate(args)
    if args.command == "recommend":
        return _recommend(args)
    return 1


def _simulate(args: argparse.Namespace) -> int:
    layout = LockerLayout.odd_even(
        number_of_lockers=args.lockers,
        pairs_per_row=args.pairs_per_row,
    )
    visits = generate_visits(
        days=args.days,
        visitors_per_day=args.visitors_per_day,
        seed=args.seed,
    )
    results = compare_strategies(layout, visits, seed=args.seed + 1)

    print("strategy   assigned  close_events  close_rate  avg_nearest")
    for result in results:
        print(
            f"{result.strategy:<10} "
            f"{result.assigned:<9} "
            f"{result.close_overlap_events:<13} "
            f"{result.close_overlap_rate:<10.3f} "
            f"{result.average_nearest_distance:.2f}"
        )
    return 0


def _recommend(args: argparse.Namespace) -> int:
    layout = LockerLayout.odd_even(
        number_of_lockers=args.lockers,
        pairs_per_row=args.pairs_per_row,
    )
    records = _load_history(args.history_csv) if args.history_csv else []
    predictor = DurationPredictor().fit(records)
    active_sessions = _load_active_sessions(args.active_json)
    assigner = LockerAssigner(layout=layout, predictor=predictor)
    arrived_at = datetime.fromisoformat(args.arrival) if args.arrival else datetime.now()

    options = assigner.recommend(
        AssignmentRequest(
            arrived_at=arrived_at,
            visitor_hash=args.visitor_id,
            preferred_tier=args.preferred_tier,
            avoided_tiers=frozenset(args.avoid_tier),
        ),
        active_sessions,
        top_k=args.top,
    )

    print("locker  score    nearest  risk    expected_checkout")
    for option in options:
        nearest = "-" if option.nearest_active_distance is None else f"{option.nearest_active_distance:.1f}"
        print(
            f"{option.locker_id:<7} "
            f"{option.score:<8.2f} "
            f"{nearest:<8} "
            f"{option.overlap_risk:<7.3f} "
            f"{option.expected_check_out.isoformat(timespec='minutes')}"
        )
        for reason in option.reasons:
            print(f"  - {reason}")
    return 0


def _load_active_sessions(path: Path) -> list[ActiveSession]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    sessions = []
    for item in raw:
        sessions.append(
            ActiveSession(
                session_id=str(item["session_id"]),
                locker_id=int(item["locker_id"]),
                check_in=datetime.fromisoformat(item["check_in"]),
                visitor_hash=item.get("visitor_hash"),
                expected_check_out=(
                    datetime.fromisoformat(item["expected_check_out"])
                    if item.get("expected_check_out")
                    else None
                ),
            )
        )
    return sessions


def _load_history(path: Path) -> list[VisitRecord]:
    records = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            records.append(
                VisitRecord(
                    visitor_hash=row.get("visitor_hash") or None,
                    check_in=datetime.fromisoformat(row["check_in"]),
                    check_out=datetime.fromisoformat(row["check_out"]),
                )
            )
    return records


if __name__ == "__main__":
    raise SystemExit(main())
