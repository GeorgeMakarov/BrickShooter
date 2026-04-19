/**
 * App entry point. Boots Phaser, opens the WS connection, wires the DOM
 * overlay (score, buttons, game-over banner, scoreboard).
 */

import * as Phaser from "phaser";

import { GridScene } from "./scenes/GridScene";
import { GameSocket } from "./transport/ws_client";
import { loadScores, recordScore, renderScores, type Difficulty } from "./scoreboard";

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
const newGameBtn = document.getElementById("new-game") as HTMLButtonElement;
const undoBtn = document.getElementById("undo") as HTMLButtonElement;
const scoresBtn = document.getElementById("scores") as HTMLButtonElement;
const overlayActionsEl = document.getElementById("overlay-actions") as HTMLDivElement;
const difficultyEl = document.getElementById("difficulty") as HTMLSelectElement;

// --- state ---------------------------------------------------------------

let currentScore = 0;
let currentLevel = 1;
let hasProgress = false; //!< true after the first shot of the current game
let difficulty: Difficulty = (localStorage.getItem(DIFFICULTY_KEY) as Difficulty | null) ?? "normal";
difficultyEl.value = difficulty;

// --- WS ------------------------------------------------------------------

const baseWsUrl = import.meta.env.DEV
  ? `ws://${location.hostname}:8000/ws`
  : `ws://${location.host}/ws`;
const savedSid = localStorage.getItem(SID_KEY);
const wsUrl = savedSid ? `${baseWsUrl}?sid=${encodeURIComponent(savedSid)}` : baseWsUrl;

const socket = new GameSocket(wsUrl);
socket.onSession((id) => localStorage.setItem(SID_KEY, id));

// Track whether the current game has any progress worth protecting.
// Any snapshot resets it (new_game / restore); any BrickShot sets it.
socket.onSnapshot(() => {
  hasProgress = false;
});
socket.onEvent((event) => {
  if (event.type === "BrickShot") hasProgress = true;
});

// --- UI callbacks --------------------------------------------------------

function onScore(total: number): void {
  currentScore = total;
  scoreEl.textContent = total.toString();
}

function onLevel(level: number): void {
  currentLevel = level;
  levelEl.textContent = level.toString();
}

function onLevelCleared(_level: number): void {
  // Keep hasProgress true — the session continues. Banner is shown by the
  // Phaser scene; no DOM overlay to open.
}

interface OverlayAction {
  label: string;
  handler: () => void;
  primary?: boolean;
}

interface OverlayOptions {
  message: string;
  showScores?: boolean;
  highlightIndex?: number;
  dismissable?: boolean; //!< Escape / backdrop click closes the overlay
  actions: OverlayAction[];
}

let dismissableOpen = false;

function showOverlay(opts: OverlayOptions): void {
  overlayMsgEl.textContent = opts.message;

  if (opts.showScores) {
    renderScores(overlayScoresEl, difficulty, opts.highlightIndex ?? -1);
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

function onGameOver(reason: string, won: boolean, level: number, score: number): void {
  // The server is authoritative for the final score/level — prefer its values
  // over currentScore/currentLevel in case events were still in-flight.
  const finalScore = score || currentScore;
  const finalLevel = level || currentLevel;
  const { insertedAt } = recordScore(finalScore, difficulty);
  hasProgress = false; // game already over — no progress to protect
  showOverlay({
    message: `${won ? "🎉" : "💀"}  ${reason} Level ${finalLevel}, score ${finalScore}.`,
    showScores: true,
    highlightIndex: insertedAt,
    actions: [
      { label: "New Game", handler: requestNewGame, primary: true },
    ],
  });
}

function openScoresModal(): void {
  showOverlay({
    message: "High Scores",
    showScores: true,
    dismissable: true,
    actions: [{ label: "Close", handler: hideOverlay }],
  });
}

// --- button wiring -------------------------------------------------------

newGameBtn.addEventListener("click", confirmAndNewGame);

undoBtn.addEventListener("click", () => {
  socket.send({ type: "undo" });
});

scoresBtn.addEventListener("click", openScoresModal);

// Backdrop click + Escape dismiss the overlay only when it's marked dismissable
// (scores-browsing, confirmation). Game-over isn't dismissable — user must
// choose.
overlayEl.addEventListener("click", (event) => {
  if (event.target === overlayEl && dismissableOpen) {
    hideOverlay();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && dismissableOpen) {
    hideOverlay();
  }
});

difficultyEl.addEventListener("change", () => {
  difficulty = difficultyEl.value as Difficulty;
  localStorage.setItem(DIFFICULTY_KEY, difficulty);
  // Changing difficulty doesn't touch the running game — takes effect on the
  // next New Game. This matches what the label implies.
});

// Load any stored scores so the Scores button immediately has something to show.
loadScores();

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
