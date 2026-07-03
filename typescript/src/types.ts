export type LockerTier = "top" | "bottom" | "single";

export interface Locker {
  id: number;
  x: number;
  y: number;
  tier: LockerTier;
  zone: string;
  status?: "available" | "blocked" | "reserved";
}

export interface ActiveSession {
  sessionId: string;
  lockerId: number;
  checkIn: Date;
  expectedCheckOut?: Date;
}

export interface AssignmentRequest {
  arrivedAt: Date;
  preferredTier?: LockerTier;
  avoidedTiers?: LockerTier[];
  expectedDurationMinutes?: number;
}

export interface CandidateOption {
  lockerId: number;
  score: number;
  nearestActiveDistance: number | null;
  overlapRisk: number;
  expectedCheckOut: Date;
  reasons: string[];
}
