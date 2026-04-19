/**
 * App entry point. Boots Phaser, opens the WS connection, wires the DOM
 * overlay (score, level, buttons, game-over banner, server-scoreboard view).
 */

import * as Phaser from "phaser";

import { GridScene } from "./scenes/GridScene";
import { GameSocket } from "./transport/ws_client";
import {
  getStoredName,
  renderServerScores,
  storeName,
  type Difficulty,
  type ScoreEntry,
} from "./scoreboard";

const FIELD_SIZE = 16;
const CELL_SIZE = 32;
const BOARD_SIZE = FIELD_SIZE * CELL_SIZE;

const SID_KEY = "brickshooter.sid";
const DIFFICULTY_KEY = "brickshooter.difficulty";

// --- DOM refs -------------------------------------------------------------

const scoreEl = document.getElementById("score") as HTMLSpanElement;
const levelEl = document.getElementById("level") as HTMLSpanElement;
const overlayEl = document.getElementById("overlay") as HTMLDivElement;
const overlayMsgEl = document.getElementById("overlay-msg") as HTMLParagraphElement;
const overlayScoresEl = document.getElementById("overlay-scores") as HTMLDivElement;
const overlayActionsEl = document.getElementById("overlay-actions") as HTMLDivElement;
const newGameBtn = document.getElementById("new-game") as HTMLButtonElement;
const undoBtn = document.getElementById("undo") as HTMLButtonElement;
const scoresBtn = document.getElementById("scores") as HTMLButtonElement;
const difficultyEl = document.getElementById("difficulty") as HTMLSelectElement;

// --- state ---------------------------------------------------------------

let currentScore = 0;
let currentLevel = 1;
let hasProgress = false;
let difficulty: Difficulty = (localStorage.getItem(DIFFICULTY_KEY) as Difficulty | null) ?? "normal";
difficultyEl.value = difficulty;

/** Pending { resolve } callback awaiting the server's scores reply. */
let pendingScoresResolver: ((entries: ScoreEntry[]) => void) | null = null;

// --- player name ---------------------------------------------------------

function ensureName(): string {
  let name = getStoredName();
  if (name) return name;
  // First visit — ask. Keep using prompt for simplicity here (modal input in
  // the overlay would be nicer but doesn't block like prompt).
  const entered = window.prompt("Your name?", "Player");
  name = storeName(entered ?? "");
  return name;
}

const playerName = ensureName();

// --- WS ------------------------------------------------------------------

const baseWsUrl = import.meta.env.DEV
  ? `ws://${location.hostname}:8000/ws`
  : `ws://${location.host}/ws`;
const savedSid = localStorage.getItem(SID_KEY);
const wsUrl = savedSid ? `${baseWsUrl}?sid=${encodeURIComponent(savedSid)}` : baseWsUrl;

const socket = new GameSocket(wsUrl);
socket.onSession((id) => {
  localStorage.setItem(SID_KEY, id);
  // Tell the server who we are so score records carry a display name.
  socket.send({ type: "set_name", name: playerName });
});
socket.onSnapshot(() => {
  hasProgress = false;
});
socket.onEvent((event) => {
  if (event.type === "BrickShot") hasProgress = true;
});

// The server's reply to a `{"type":"scores"}` message looks like
// `{type:"scores", difficulty, entries}`. Route it via a lightweight
// pending-resolver pattern instead of a full request-id scheme.
socket.onRaw((frame) => {
  if (!isScoresReply(frame)) return;
  const resolver = pendingScoresResolver;
  pendingScoresResolver = null;
  if (resolver) resolver(frame.entries);
});

function requestScores(diff: Difficulty): Promise<ScoreEntry[]> {
  return new Promise<ScoreEntry[]>((resolve) => {
    pendingScoresResolver = resolve;
    socket.send({ type: "scores", difficulty: diff });
    // Safety net: 2s timeout.
    setTimeout(() => {
      if (pendingScoresResolver === resolve) {
        pendingScoresResolver = null;
        resolve([]);
      }
    }, 2000);
  });
}

function isScoresReply(frame: unknown): frame is { type: "scores"; difficulty: Difficulty; entries: ScoreEntry[] } {
  return (
    frame !== null &&
    typeof frame === "object" &&
    (frame as { type?: unknown }).type === "scores" &&
    Array.isArray((frame as { entries?: unknown }).entries)
  );
}

// --- overlay -------------------------------------------------------------

interface OverlayAction {
  label: string;
  handler: () => void;
  primary?: boolean;
}

interface OverlayOptions {
  message: string;
  scoresHtml?: string; //!< pre-rendered by renderServerScores
  dismissable?: boolean;
  actions: OverlayAction[];
}

let dismissableOpen = false;

function showOverlay(opts: OverlayOptions): void {
  overlayMsgEl.textContent = opts.message;
  if (opts.scoresHtml !== undefined) {
    overlayScoresEl.innerHTML = opts.scoresHtml;
    overlayScoresEl.classList.remove("hidden");
  } else {
    overlayScoresEl.classList.add("hidden");
  }
  overlayActionsEl.innerHTML = "";
  for (const action of opts.actions) {
    const btn = document.createElement("button");
    btn.textContent = action.label;
    if (action.primary) btn.classList.add("primary");
    btn.addEventListener("click", action.handler);
    overlayActionsEl.appendChild(btn);
  }
  dismissableOpen = !!opts.dismissable;
  overlayEl.classList.remove("hidden");
}

function hideOverlay(): void {
  dismissableOpen = false;
  overlayEl.classList.add("hidden");
}

function requestNewGame(): void {
  hideOverlay();
  hasProgress = false;
  socket.send({ type: "new_game", difficulty });
}

function confirmAndNewGame(): void {
  if (!hasProgress) {
    requestNewGame();
    return;
  }
  showOverlay({
    message: "Start a new game? Current progress will be lost.",
    dismissable: true,
    actions: [
      { label: "Keep Playing", handler: hideOverlay },
      { label: "Start New Game", handler: requestNewGame, primary: true },
    ],
  });
}

// --- callbacks from the Phaser scene -------------------------------------

function onScore(total: number): void {
  currentScore = total;
  scoreEl.textContent = total.toString();
}

function onLevel(level: number): void {
  currentLevel = level;
  levelEl.textContent = level.toString();
}

function onLevelCleared(_level: number): void {
  // Session continues — in-canvas banner shown by GridScene, no DOM action.
}

async function onGameOver(reason: string, won: boolean, level: number, score: number): Promise<void> {
  const finalScore = score || currentScore;
  const finalLevel = level || currentLevel;
  hasProgress = false;

  // Server has already recorded the score; fetch the fresh top-N and
  // highlight the player's entry (matching name + score + level).
  const entries = await requestScores(difficulty);
  const highlightIndex = entries.findIndex(
    (e) => e.name === playerName && e.score === finalScore && e.level === finalLevel,
  );
  const target = document.createElement("div");
  renderServerScores(target, difficulty, entries, highlightIndex);

  showOverlay({
    message: `${won ? "🎉" : "💀"}  ${reason} Level ${finalLevel}, score ${finalScore}.`,
    scoresHtml: target.innerHTML,
    actions: [{ label: "New Game", handler: requestNewGame, primary: true }],
  });
}

async function openScoresModal(): Promise<void> {
  const entries = await requestScores(difficulty);
  const target = document.createElement("div");
  renderServerScores(target, difficulty, entries);
  showOverlay({
    message: "High Scores",
    scoresHtml: target.innerHTML,
    dismissable: true,
    actions: [{ label: "Close", handler: hideOverlay }],
  });
}

// --- button wiring -------------------------------------------------------

newGameBtn.addEventListener("click", confirmAndNewGame);
undoBtn.addEventListener("click", () => socket.send({ type: "undo" }));
scoresBtn.addEventListener("click", openScoresModal);

overlayEl.addEventListener("click", (event) => {
  if (event.target === overlayEl && dismissableOpen) hideOverlay();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && dismissableOpen) hideOverlay();
});

difficultyEl.addEventListener("change", () => {
  difficulty = difficultyEl.value as Difficulty;
  localStorage.setItem(DIFFICULTY_KEY, difficulty);
});

// --- Phaser boot ---------------------------------------------------------

new Phaser.Game({
  type: Phaser.AUTO,
  width: BOARD_SIZE,
  height: BOARD_SIZE,
  parent: "game",
  backgroundColor: "#0f1b2d",
  scene: [GridScene],
  scale: { mode: Phaser.Scale.NONE },
  callbacks: {
    preBoot: (game) => {
      game.scene.start("GridScene", { socket, onScore, onLevel, onLevelCleared, onGameOver });
    },
  },
});

socket.connect();
