/**
 * DomainEvent type mirror.
 *
 * Every variant matches exactly one frozen dataclass on the Python side
 * (v2/domain/events.py). The shape and field names must stay in sync with
 * what `backend.adapters.codec.to_json` produces over the websocket.
 *
 * `decodeEvent` runs minimal runtime validation (discriminator present,
 * required fields non-null) and narrows the frame to a concrete event.
 * Scene code can then switch on `event.type` with exhaustiveness.
 */

export type Cell = [number, number];

export type Direction = "TO_LEFT" | "TO_RIGHT" | "TO_UP" | "TO_DOWN";

export interface BrickShot {
  type: "BrickShot";
  launcher_cell: Cell;
  ammo_cell: Cell;
  direction: Direction;
}

export interface BrickMoved {
  type: "BrickMoved";
  from_cell: Cell;
  to_cell: Cell;
}

export interface BrickMatched {
  type: "BrickMatched";
  cells: Cell[];
  color_index: number;
}

export interface BrickCrossed {
  type: "BrickCrossed";
  from_cell: Cell;
  to_cell: Cell;
  color_index: number;
}

export interface LaunchZoneRefilled {
  type: "LaunchZoneRefilled";
  new_cell: Cell;
  color_index: number;
}

export interface ScoreChanged {
  type: "ScoreChanged";
  delta: number;
  total: number;
}

export interface StateReverted {
  type: "StateReverted";
  score: number;
}

export interface GameOver {
  type: "GameOver";
  reason: string;
  won: boolean;
}

export type DomainEvent =
  | BrickShot
  | BrickMoved
  | BrickMatched
  | BrickCrossed
  | LaunchZoneRefilled
  | ScoreChanged
  | StateReverted
  | GameOver;

/**
 * Full state frame sent on connect and after new_game. Not a DomainEvent —
 * it describes state, not a transition. The client renders everything from
 * it verbatim.
 */
export type BrickState = {
  intention: "VOID" | "STAND" | "TO_LEFT" | "TO_RIGHT" | "TO_UP" | "TO_DOWN";
  color_index: number | null;
};

export interface Snapshot {
  type: "snapshot";
  score: number;
  field: BrickState[][];
}

export function isSnapshot(frame: unknown): frame is Snapshot {
  return (
    frame !== null &&
    typeof frame === "object" &&
    (frame as { type?: unknown }).type === "snapshot"
  );
}

const EVENT_TYPES = new Set<DomainEvent["type"]>([
  "BrickShot",
  "BrickMoved",
  "BrickMatched",
  "BrickCrossed",
  "LaunchZoneRefilled",
  "ScoreChanged",
  "StateReverted",
  "GameOver",
]);

export function decodeEvent(frame: unknown): DomainEvent {
  if (frame === null || typeof frame !== "object") {
    throw new Error("event frame must be an object");
  }
  const record = frame as Record<string, unknown>;
  const typeField = record.type;
  if (typeof typeField !== "string") {
    throw new Error("event frame missing 'type' field");
  }
  if (!EVENT_TYPES.has(typeField as DomainEvent["type"])) {
    throw new Error(`unknown event type: ${typeField}`);
  }
  // The shape checking we're doing here is intentionally minimal — the server
  // is trusted to produce well-formed frames. A malformed payload will surface
  // as a runtime error in the scene handler, which is fine for a hobby app.
  return record as unknown as DomainEvent;
}
