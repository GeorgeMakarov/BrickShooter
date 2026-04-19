/**
 * GameSocket tests. A fake WebSocket lets us drive the client deterministically
 * without a real network.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";

import { GameSocket, type WebSocketLike } from "../src/transport/ws_client";
import type { DomainEvent, Snapshot } from "../src/transport/events";

class FakeSocket implements WebSocketLike {
  readyState = 0;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  sent: string[] = [];

  constructor(public readonly url: string) {}

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = 3;
    this.onclose?.(new CloseEvent("close"));
  }

  // Helpers used only by tests:
  simulateOpen(): void {
    this.readyState = 1;
    this.onopen?.(new Event("open"));
  }

  simulateMessage(frame: unknown): void {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(frame) }));
  }

  simulateRemoteClose(): void {
    this.readyState = 3;
    this.onclose?.(new CloseEvent("close"));
  }
}

describe("GameSocket", () => {
  let created: FakeSocket[];
  let factory: (url: string) => WebSocketLike;

  beforeEach(() => {
    created = [];
    factory = (url: string) => {
      const s = new FakeSocket(url);
      created.push(s);
      return s;
    };
  });

  it("opens a socket to the given URL on connect()", () => {
    const sock = new GameSocket("ws://x/ws", factory);
    sock.connect();
    expect(created.length).toBe(1);
    expect(created[0].url).toBe("ws://x/ws");
  });

  it("dispatches snapshot frames to snapshot handlers", () => {
    const sock = new GameSocket("ws://x/ws", factory);
    const received: Snapshot[] = [];
    sock.onSnapshot((s) => received.push(s));
    sock.connect();

    const snap: Snapshot = { type: "snapshot", score: 0, field: [] };
    created[0].simulateMessage(snap);

    expect(received).toEqual([snap]);
  });

  it("dispatches non-snapshot frames through decodeEvent to event handlers", () => {
    const sock = new GameSocket("ws://x/ws", factory);
    const received: DomainEvent[] = [];
    sock.onEvent((e) => received.push(e));
    sock.connect();

    created[0].simulateMessage({
      type: "BrickMoved",
      from_cell: [1, 2],
      to_cell: [3, 4],
    });

    expect(received.length).toBe(1);
    expect(received[0].type).toBe("BrickMoved");
  });

  it("preserves event order across multiple frames", () => {
    const sock = new GameSocket("ws://x/ws", factory);
    const order: string[] = [];
    sock.onEvent((e) => order.push(e.type));
    sock.connect();

    created[0].simulateMessage({ type: "BrickShot", launcher_cell: [0, 0], ammo_cell: [0, 0], direction: "TO_RIGHT" });
    created[0].simulateMessage({ type: "BrickMoved", from_cell: [0, 0], to_cell: [0, 1] });
    created[0].simulateMessage({ type: "ScoreChanged", delta: 10, total: 10 });

    expect(order).toEqual(["BrickShot", "BrickMoved", "ScoreChanged"]);
  });

  it("send() serialises message to JSON on the socket", () => {
    const sock = new GameSocket("ws://x/ws", factory);
    sock.connect();
    created[0].simulateOpen();
    sock.send({ type: "shoot", cell: [2, 5] });

    expect(created[0].sent).toEqual([JSON.stringify({ type: "shoot", cell: [2, 5] })]);
  });

  it("close() closes the underlying socket and stops reconnecting", () => {
    const sock = new GameSocket("ws://x/ws", factory);
    sock.connect();
    sock.close();
    expect(created[0].readyState).toBe(3);
    created[0].simulateRemoteClose();
    // No additional socket created — close() disabled reconnect.
    expect(created.length).toBe(1);
  });

  it("reconnects after a remote close", async () => {
    vi.useFakeTimers();
    try {
      const sock = new GameSocket("ws://x/ws", factory, { reconnectDelayMs: 100 });
      sock.connect();
      created[0].simulateRemoteClose();
      await vi.advanceTimersByTimeAsync(150);
      expect(created.length).toBe(2);
    } finally {
      vi.useRealTimers();
    }
  });
});
