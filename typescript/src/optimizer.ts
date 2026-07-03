import { LockerLayout } from "./layout.js";
import type { ActiveSession, AssignmentRequest, CandidateOption } from "./types.js";

interface TimeWindow {
  start: Date;
  end: Date;
}

export interface AssignmentConfig {
  arrivalWindowMinutes: number;
  departureWindowMinutes: number;
  passiveCrowdingWeight: number;
  overlapWeight: number;
  nearestWeight: number;
  averageNearWeight: number;
  preferredTierBonus: number;
  avoidedTierPenalty: number;
}

const defaultConfig: AssignmentConfig = {
  arrivalWindowMinutes: 10,
  departureWindowMinutes: 15,
  passiveCrowdingWeight: 1.5,
  overlapWeight: 85,
  nearestWeight: 2,
  averageNearWeight: 0.8,
  preferredTierBonus: 2.5,
  avoidedTierPenalty: 7.5,
};

export class LockerAssigner {
  constructor(
    private readonly layout: LockerLayout,
    private readonly config: AssignmentConfig = defaultConfig,
  ) {}

  recommend(
    request: AssignmentRequest,
    activeSessions: ActiveSession[],
    topK = 5,
    skipLockerIds = new Set<number>(),
  ): CandidateOption[] {
    const occupied = new Set(activeSessions.map((session) => session.lockerId));
    const expectedCheckOut = addMinutes(
      request.arrivedAt,
      request.expectedDurationMinutes ?? 90,
    );
    const candidateWindows = this.changingWindows(request.arrivedAt, expectedCheckOut);
    const sessionProfiles = activeSessions.map((session) => ({
      session,
      temporalWeight: this.temporalOverlapWeight(
        candidateWindows,
        this.changingWindows(
          session.checkIn,
          session.expectedCheckOut ?? addMinutes(session.checkIn, 90),
        ),
      ),
    }));

    return this.layout
      .assignableIds()
      .filter((lockerId) => !occupied.has(lockerId) && !skipLockerIds.has(lockerId))
      .map((lockerId) =>
        this.scoreCandidate(lockerId, request, expectedCheckOut, sessionProfiles),
      )
      .sort((a, b) => b.score - a.score || a.lockerId - b.lockerId)
      .slice(0, topK);
  }

  private scoreCandidate(
    lockerId: number,
    request: AssignmentRequest,
    expectedCheckOut: Date,
    sessionProfiles: Array<{ session: ActiveSession; temporalWeight: number }>,
  ): CandidateOption {
    const locker = this.layout.get(lockerId);
    const distances = sessionProfiles
      .map((profile) => ({
        session: profile.session,
        temporalWeight: profile.temporalWeight,
        distance: this.layout.distance(lockerId, profile.session.lockerId),
      }))
      .sort((a, b) => a.distance - b.distance);

    const nearest = distances.length > 0 ? distances[0].distance : null;
    const near = distances.slice(0, 5).map((item) => item.distance);
    const averageNear = near.length > 0 ? near.reduce((a, b) => a + b, 0) / near.length : null;
    const passiveCrowding = distances.reduce(
      (total, item) => total + 1 / (item.distance + 1),
      0,
    );
    const overlapRisk = distances.reduce(
      (total, item) => total + this.overlapRisk(item.temporalWeight, item.distance),
      0,
    );

    let score = 0;
    if (nearest !== null) score += nearest * this.config.nearestWeight;
    if (averageNear !== null) score += averageNear * this.config.averageNearWeight;
    score -= passiveCrowding * this.config.passiveCrowdingWeight;
    score -= overlapRisk * this.config.overlapWeight;
    if (request.preferredTier && locker.tier === request.preferredTier) {
      score += this.config.preferredTierBonus;
    }
    if (request.avoidedTiers?.includes(locker.tier)) {
      score -= this.config.avoidedTierPenalty;
    }

    const reasons = [
      `${locker.zone}, ${locker.tier} tier`,
      nearest === null
        ? "no occupied lockers in the current layout"
        : `nearest occupied locker is ${distances[0].session.lockerId} at distance ${nearest.toFixed(1)}`,
      overlapRisk < 0.05
        ? "low predicted changing-window overlap"
        : `predicted overlap risk ${overlapRisk.toFixed(2)}`,
    ];

    return {
      lockerId,
      score: round(score, 4),
      nearestActiveDistance: nearest === null ? null : round(nearest, 3),
      overlapRisk: round(overlapRisk, 4),
      expectedCheckOut,
      reasons,
    };
  }

  private overlapRisk(
    temporalWeight: number,
    distance: number,
  ): number {
    return temporalWeight * (1 / (distance + 1));
  }

  private temporalOverlapWeight(
    candidateWindows: [TimeWindow, TimeWindow],
    sessionWindows: [TimeWindow, TimeWindow],
  ): number {
    let overlap = 0;

    for (const candidateWindow of candidateWindows) {
      for (const sessionWindow of sessionWindows) {
        overlap += overlapMinutes(candidateWindow, sessionWindow) / minutes(candidateWindow);
      }
    }

    return overlap;
  }

  private changingWindows(checkIn: Date, expectedCheckOut: Date): [TimeWindow, TimeWindow] {
    const arrivalEnd = addMinutes(checkIn, this.config.arrivalWindowMinutes);
    let departureStart = addMinutes(expectedCheckOut, -this.config.departureWindowMinutes);
    if (departureStart < arrivalEnd) {
      departureStart = arrivalEnd;
    }
    return [
      { start: checkIn, end: arrivalEnd },
      { start: departureStart, end: expectedCheckOut },
    ];
  }
}

function addMinutes(date: Date, minutesToAdd: number): Date {
  return new Date(date.getTime() + minutesToAdd * 60_000);
}

function overlapMinutes(a: TimeWindow, b: TimeWindow): number {
  const start = Math.max(a.start.getTime(), b.start.getTime());
  const end = Math.min(a.end.getTime(), b.end.getTime());
  return end <= start ? 0 : (end - start) / 60_000;
}

function minutes(window: TimeWindow): number {
  return Math.max((window.end.getTime() - window.start.getTime()) / 60_000, 1);
}

function round(value: number, precision: number): number {
  const multiplier = 10 ** precision;
  return Math.round(value * multiplier) / multiplier;
}
