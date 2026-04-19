/**
 * App entry point. Boots Phaser, opens the WS connection, wires the DOM
 * overlay (score, buttons, game-over banner) to the scene.
 */

import Phaser from "phaser";

import { GridScene } from "./scenes/GridScene";
import { GameSocket } from "./transport/ws_client";

const FIELD_SIZE = 16;
const CELL_SIZE = 32;
const BOARD_SIZE = FIELD_SIZE * CELL_SIZE;

const scoreEl = document.getElementById("score") as HTMLSpanElement;
const overlayEl = document.getElementById("overlay") as HTMLDivElement;
const overlayMsgEl = document.getElementById("overlay-msg") as HTMLParagraphElement;
const newGameBtn = document.getElementById("new-game") as HTMLButtonElement;
const undoBtn = document.getElementById("undo") as HTMLButtonElement;
const overlayNewGameBtn = document.getElementById("overlay-new-game") as HTMLButtonElement;

const wsUrl = import.meta.env.DEV
  ? `ws://${location.hostname}:8000/ws`
  : `ws://${location.host}/ws`;
const socket = new GameSocket(wsUrl);

function onScore(total: number): void {
  scoreEl.textContent = total.toString();
}

function onGameOver(reason: string, won: boolean): void {
  overlayMsgEl.textContent = (won ? "🎉  " : "💀  ") + reason;
  overlayEl.classList.remove("hidden");
}

function hideOverlay(): void {
  overlayEl.classList.add("hidden");
}

newGameBtn.addEventListener("click", () => {
  hideOverlay();
  socket.send({ type: "new_game" });
});

undoBtn.addEventListener("click", () => {
  socket.send({ type: "undo" });
});

overlayNewGameBtn.addEventListener("click", () => {
  hideOverlay();
  socket.send({ type: "new_game" });
});

new Phaser.Game({
  type: Phaser.AUTO,
  width: BOARD_SIZE,
  height: BOARD_SIZE,
  parent: "game",
  backgroundColor: "#0f1b2d",
  scene: [GridScene],
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
  callbacks: {
    preBoot: (game) => {
      game.scene.start("GridScene", {
        socket,
        onScore,
        onGameOver,
      });
    },
  },
});

socket.connect();
