/**
 * Thin WebSocket client wrapper.
 *
 * The real browser `WebSocket` is narrowed to `WebSocketLike` so tests can
 * inject a fake. On message, a frame is either a `Snapshot` (routed to
 * snapshot handlers) or a `DomainEvent` (routed through `decodeEvent`).
 *
 * Reconnect is simple: after an unexpected close, wait `reconnectDelayMs`
 * and reopen. `close()` disables reconnect so deliberate shutdowns don't
 * bounce back.
 */

import { decodeEvent, isSession, isSnapshot, type DomainEvent, type Snapshot } from "./events";

export interface WebSocketLike {
  readonly readyState: number;
  onopen: ((ev: Event) => void) | null;
  onmessage: ((ev: MessageEvent) => void) | null;
  onerror: ((ev: Event) => void) | null;
  onclose: ((ev: CloseEvent) => void) | null;
  send(data: string): void;
  close(): void;
}

export type SocketFactory = (url: string) => WebSocketLike;

export type SnapshotHandler = (snapshot: Snapshot) => void;
export type EventHandler = (event: DomainEvent) => void;
export type SessionHandler = (sessionId: string) => void;
export type RawHandler = (frame: unknown) => void;

export interface GameSocketOptions {
  reconnectDelayMs?: number;
}

const defaultFactory: SocketFactory = (url) => new WebSocket(url) as unknown as WebSocketLike;

export class GameSocket {
  private ws: WebSocketLike | null = null;
  private snapshotHandlers: SnapshotHandler[] = [];
  private eventHandlers: EventHandler[] = [];
  private sessionHandlers: SessionHandler[] = [];
  private rawHandlers: RawHandler[] = [];
  private closed = false;
  private readonly reconnectDelayMs: number;

  constructor(
    private readonly url: string,
    private readonly factory: SocketFactory = defaultFactory,
    options: GameSocketOptions = {},
  ) {
    this.reconnectDelayMs = options.reconnectDelayMs ?? 1000;
  }

  connect(): void {
    this.closed = false;
    const ws = this.factory(this.url);
    this.ws = ws;
    ws.onmessage = (ev) => this.dispatch(ev.data);
    ws.onclose = () => this.handleClose();
  }

  onSnapshot(handler: SnapshotHandler): void {
    this.snapshotHandlers.push(handler);
  }

  onEvent(handler: EventHandler): void {
    this.eventHandlers.push(handler);
  }

  onSession(handler: SessionHandler): void {
    this.sessionHandlers.push(handler);
  }

  /**
   * Catch-all for protocol frames that aren't a DomainEvent or a Snapshot
   * (currently the `scores` reply). Handlers receive the parsed JSON object
   * as-is and do their own typeguard.
   */
  onRaw(handler: RawHandler): void {
    this.rawHandlers.push(handler);
  }

  send(message: object): void {
    if (!this.ws) throw new Error("socket not connected");
    this.ws.send(JSON.stringify(message));
  }

  close(): void {
    this.closed = true;
    this.ws?.close();
    this.ws = null;
  }

  private dispatch(data: unknown): void {
    const text = typeof data === "string" ? data : String(data);
    let frame: unknown;
    try {
      frame = JSON.parse(text);
    } catch {
      return; // ignore malformed JSON
    }
    if (isSession(frame)) {
      for (const h of this.sessionHandlers) h(frame.id);
      return;
    }
    if (isSnapshot(frame)) {
      for (const h of this.snapshotHandlers) h(frame);
      return;
    }
    // Frames the client knows about but aren't DomainEvents (e.g. scores
    // reply, error frames). Give raw handlers a chance first; if any of them
    // recognise it, stop. Otherwise fall through to decodeEvent and hope it's
    // a DomainEvent — a genuinely-unknown frame raises there.
    const typeField = (frame as { type?: unknown }).type;
    if (typeField === "scores" || typeField === "error") {
      for (const h of this.rawHandlers) h(frame);
      return;
    }
    const event = decodeEvent(frame);
    for (const h of this.eventHandlers) h(event);
  }

  private handleClose(): void {
    this.ws = null;
    if (this.closed) return;
    setTimeout(() => {
      if (!this.closed) this.connect();
    }, this.reconnectDelayMs);
  }
}
