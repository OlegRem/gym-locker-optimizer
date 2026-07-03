import type { Locker } from "./types.js";

export class LockerLayout {
  private readonly byId: Map<number, Locker>;
  private readonly distances = new Map<string, number>();

  constructor(
    lockers: Locker[],
    private readonly tierWeight = 0.35,
  ) {
    if (lockers.length === 0) {
      throw new Error("layout must contain at least one locker");
    }
    this.byId = new Map(lockers.map((locker) => [locker.id, locker]));
  }

  static oddEven(options: {
    numberOfLockers?: number;
    startId?: number;
    pairsPerRow?: number;
    rowGap?: number;
    tierWeight?: number;
  } = {}): LockerLayout {
    const numberOfLockers = options.numberOfLockers ?? 530;
    const startId = options.startId ?? 1;
    const pairsPerRow = options.pairsPerRow ?? 53;
    const rowGap = options.rowGap ?? 3;
    const lockers: Locker[] = [];

    for (let lockerId = startId; lockerId < startId + numberOfLockers; lockerId += 1) {
      const zeroBased = lockerId - startId;
      const pairIndex = Math.floor(zeroBased / 2);
      const row = Math.floor(pairIndex / pairsPerRow);
      const col = pairIndex % pairsPerRow;
      const tier = zeroBased % 2 === 0 ? "top" : "bottom";
      lockers.push({
        id: lockerId,
        x: col,
        y: row * rowGap,
        tier,
        zone: `row-${row + 1}`,
        status: "available",
      });
    }

    return new LockerLayout(lockers, options.tierWeight ?? 0.35);
  }

  get(lockerId: number): Locker {
    const locker = this.byId.get(lockerId);
    if (!locker) {
      throw new Error(`unknown locker id: ${lockerId}`);
    }
    return locker;
  }

  assignableIds(): number[] {
    return [...this.byId.values()]
      .filter((locker) => (locker.status ?? "available") === "available")
      .map((locker) => locker.id)
      .sort((a, b) => a - b);
  }

  distance(aId: number, bId: number): number {
    const key = aId <= bId ? `${aId}:${bId}` : `${bId}:${aId}`;
    const cached = this.distances.get(key);
    if (cached !== undefined) {
      return cached;
    }

    const a = this.get(aId);
    const b = this.get(bId);
    const tierDelta = a.tier === b.tier ? 0 : this.tierWeight;
    const distance = Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + tierDelta ** 2);
    this.distances.set(key, distance);
    return distance;
  }
}
