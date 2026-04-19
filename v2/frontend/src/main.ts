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
const overlayEl = document.getElementById("overlay") as HTMLDivElement;
const overlayMsgEl = document.getElementById("overlay-msg") as HTMLParagraphElement;
const overlayScoresEl = document.getElementById("overlay-scores") as HTMLDivElement;
const newGameBtn = document.getElementById("new-game") as HTMLButtonElement;
const undoBtn = document.getElementById("undo") as HTMLButtonElement;
const scoresBtn = document.getElementById("scores") as HTMLButtonElement;
const overlayNewGameBtn = document.getElementById("overlay-new-game") as HTMLButtonElement;
const difficultyEl = document.getElementById("difficulty") as HTMLSelectElement;

// --- state ---------------------------------------------------------------

let currentScore = 0;
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

// --- UI callbacks --------------------------------------------------------

function onScore(total: number): void {
  currentScore = total;
  scoreEl.textContent = total.toString();
}

function onGameOver(reason: string, won: boolean): void {
  const { insertedAt } = recordScore(currentScore, difficulty);
  overlayMsgEl.textContent = (won ? "🎉  " : "💀  ") + reason;
  renderScores(overlayScoresEl, difficulty, insertedAt);
  overlayEl.classList.remove("hidden");
}

function openScoresModal(): void {
  overlayMsgEl.textContent = "High Scores";
  renderScores(overlayScoresEl, difficulty);
  overlayEl.classList.remove("hidden");
}

function hideOverlay(): void {
  overlayEl.classList.add("hidden");
}

function requestNewGame(): void {
  socket.send({ type: "new_game", difficulty });
}

// --- button wiring -------------------------------------------------------

newGameBtn.addEventListener("click", () => {
  hideOverlay();
  requestNewGame();
});

undoBtn.addEventListener("click", () => {
  socket.send({ type: "undo" });
});

scoresBtn.addEventListener("click", openScoresModal);

overlayNewGameBtn.addEventListener("click", () => {
  hideOverlay();
  requestNewGame();
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
      game.scene.start("GridScene", { socket, onScore, onGameOver });
    },
  },
});

socket.connect();
