/**
 * App entry point. Boots Phaser, opens the WS connection, wires the DOM
 * overlay (score, level, buttons, game-over banner, server-scoreboard view).
 */

import * as Phaser from "phaser";

import { getA11y, setA11y } from "./a11y";
import { Sfx } from "./audio/sfx";
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
const overlayInputEl = document.getElementById("overlay-input") as HTMLInputElement;
const newGameBtn = document.getElementById("new-game") as HTMLButtonElement;
const undoBtn = document.getElementById("undo") as HTMLButtonElement;
const scoresBtn = document.getElementById("scores") as HTMLButtonElement;
const nameBtn = document.getElementById("name-btn") as HTMLButtonElement;
const playerNameEl = document.getElementById("player-name") as HTMLSpanElement;
const muteBtn = document.getElementById("mute-btn") as HTMLButtonElement;
const settingsBtn = document.getElementById("settings-btn") as HTMLButtonElement;
const difficultyEl = document.getElementById("difficulty") as HTMLSelectElement;

// --- state ---------------------------------------------------------------

let currentScore = 0;
let currentLevel = 1;
let hasProgress = false;
// Set when the player confirms Abandon & Start New: the server's resulting
// GameOver is the closure for the abandon flow (already previewed inline in
// the confirm dialog), not a fresh event to surface again. onGameOver
// consumes this flag and skips its usual overlay.
let suppressNextGameOver = false;
let difficulty: Difficulty = (localStorage.getItem(DIFFICULTY_KEY) as Difficulty | null) ?? "normal";
difficultyEl.value = difficulty;

const sfx = new Sfx();
function updateMuteButton(): void {
  muteBtn.textContent = sfx.isMuted ? "🔇" : "🔊";
  muteBtn.classList.toggle("muted", sfx.isMuted);
}
updateMuteButton();
muteBtn.addEventListener("click", () => {
  sfx.toggleMuted();
  updateMuteButton();
});

/** Pending { resolve } callback awaiting the server's scores reply. */
let pendingScoresResolver: ((entries: ScoreEntry[]) => void) | null = null;

// --- player name ---------------------------------------------------------

function askForName(opts: { currentName?: string; dismissable: boolean }): Promise<string | null> {
  return new Promise<string | null>((resolve) => {
    const actions: OverlayAction[] = [];
    if (opts.dismissable) {
      actions.push({
        label: "Cancel",
        handler: () => {
          hideOverlay();
          resolve(null);
        },
      });
    }
    actions.push({
      label: "OK",
      primary: true,
      handler: () => {
        const raw = overlayInputEl.value;
        const stored = storeName(raw);
        hideOverlay();
        resolve(stored);
      },
    });
    showOverlay({
      message: opts.currentName ? "Change your name" : "What's your name?",
      input: { placeholder: "Your name", value: opts.currentName ?? "" },
      dismissable: opts.dismissable,
      actions,
    });
  });
}

function setPlayerName(name: string): void {
  playerName = name;
  playerNameEl.textContent = name;
}

// --- WS ------------------------------------------------------------------

const baseWsUrl = import.meta.env.DEV
  ? `ws://${location.hostname}:8000/ws`
  : `ws://${location.host}/ws`;
const savedSid = localStorage.getItem(SID_KEY);
const wsUrl = savedSid ? `${baseWsUrl}?sid=${encodeURIComponent(savedSid)}` : baseWsUrl;

/** Filled in before socket.connect() is called, guaranteed non-null after boot. */
let playerName = "";

const socket = new GameSocket(wsUrl);
socket.onSession((id) => {
  localStorage.setItem(SID_KEY, id);
  // Tell the server who we are so score records carry a display name.
  socket.send({ type: "set_name", name: playerName });
});
socket.onSnapshot((s) => {
  // A snapshot replaces the board wholesale — after new_game, undo, or
  // LevelCleared. "Has progress" tracks whether abandoning would lose
  // something worth warning about, so key it off the incoming score:
  // fresh boards reset it, ongoing sessions (e.g. level-cleared with
  // carried score) keep it set.
  hasProgress = s.score > 0;
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
  input?: { placeholder?: string; value?: string };
  actions: OverlayAction[];
}

let dismissableOpen = false;
/** Set while an input-bearing overlay is open so Enter triggers the primary action. */
let primaryActionHandler: (() => void) | null = null;

function showOverlay(opts: OverlayOptions): void {
  overlayMsgEl.textContent = opts.message;

  if (opts.input !== undefined) {
    overlayInputEl.value = opts.input.value ?? "";
    overlayInputEl.placeholder = opts.input.placeholder ?? "";
    overlayInputEl.classList.remove("hidden");
  } else {
    overlayInputEl.classList.add("hidden");
  }

  if (opts.scoresHtml !== undefined) {
    overlayScoresEl.innerHTML = opts.scoresHtml;
    overlayScoresEl.classList.remove("hidden");
  } else {
    overlayScoresEl.classList.add("hidden");
  }

  overlayActionsEl.innerHTML = "";
  primaryActionHandler = null;
  for (const action of opts.actions) {
    const btn = document.createElement("button");
    btn.textContent = action.label;
    if (action.primary) {
      btn.classList.add("primary");
      primaryActionHandler = action.handler;
    }
    btn.addEventListener("click", action.handler);
    overlayActionsEl.appendChild(btn);
  }

  dismissableOpen = !!opts.dismissable;
  overlayEl.classList.remove("hidden");

  if (opts.input !== undefined) {
    // Wait a frame so the input is actually visible before focusing.
    requestAnimationFrame(() => {
      overlayInputEl.focus();
      overlayInputEl.select();
    });
  }
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

function abandonAndNewGame(): void {
  // Single-click commit: record the abandoned game, then start the new
  // one at the current difficulty. The resulting GameOver event is
  // suppressed on arrival (see onGameOver) because the confirm dialog
  // already previewed the final state.
  hideOverlay();
  hasProgress = false;
  suppressNextGameOver = true;
  socket.send({ type: "end_game" });
  socket.send({ type: "new_game", difficulty });
}

async function confirmAndNewGame(): Promise<void> {
  if (!hasProgress) {
    requestNewGame();
    return;
  }
  // Preview the final result (current score + leaderboard) in the same
  // dialog as the Keep / Abandon choice, so one click commits.
  const entries = await requestScores(difficulty);
  const target = document.createElement("div");
  renderServerScores(target, difficulty, entries);
  showOverlay({
    message: `End current game? Level ${currentLevel}, score ${currentScore} will be recorded.`,
    scoresHtml: target.innerHTML,
    dismissable: true,
    actions: [
      { label: "Keep Playing", handler: hideOverlay },
      { label: "Abandon & Start New", handler: abandonAndNewGame, primary: true },
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

  // Abandon flow: the confirm dialog already showed the final score and
  // the leaderboard; the follow-up new_game snapshot will repaint the
  // board. Nothing more to do here.
  if (suppressNextGameOver) {
    suppressNextGameOver = false;
    return;
  }

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

function openSettingsModal(): void {
  // Three independent toggles, each applying an additional visual cue.
  // Saved to localStorage and pushed to subscribers (Phaser scene) the
  // moment the checkbox changes — no Apply button needed.
  const current = getA11y();
  const rows: Array<{ key: keyof typeof current; label: string; hint: string }> = [
    {
      key: "palette",
      label: "High-contrast colours",
      hint: "Swap the palette for one where every colour sits at a distinct brightness level.",
    },
    {
      key: "glyphs",
      label: "Shape glyphs",
      hint: "Draw a small shape in the corner of each brick — shape identifies the colour.",
    },
    {
      key: "patterns",
      label: "Pattern overlay",
      hint: "Fill each brick colour with its own pattern (stripes, dots, hatching…).",
    },
  ];

  const list = document.createElement("div");
  list.className = "a11y-list";
  for (const row of rows) {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = current[row.key];
    checkbox.addEventListener("change", () => {
      setA11y({ ...getA11y(), [row.key]: checkbox.checked });
    });
    const text = document.createElement("span");
    const title = document.createElement("span");
    title.textContent = row.label;
    const hint = document.createElement("small");
    hint.textContent = row.hint;
    text.appendChild(title);
    text.appendChild(hint);
    label.appendChild(checkbox);
    label.appendChild(text);
    list.appendChild(label);
  }

  showOverlay({
    message: "Accessibility",
    scoresHtml: list.outerHTML,
    dismissable: true,
    actions: [{ label: "Close", handler: hideOverlay }],
  });

  // showOverlay sets innerHTML from the string, so the live DOM references
  // and their listeners are lost. Replace the rendered copy with the live
  // list so toggles actually fire handlers.
  overlayScoresEl.innerHTML = "";
  overlayScoresEl.appendChild(list);
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
settingsBtn.addEventListener("click", openSettingsModal);

nameBtn.addEventListener("click", async () => {
  const next = await askForName({ currentName: playerName, dismissable: true });
  if (next !== null && next !== playerName) {
    setPlayerName(next);
    socket.send({ type: "set_name", name: next });
  }
});

overlayEl.addEventListener("click", (event) => {
  if (event.target === overlayEl && dismissableOpen) hideOverlay();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && dismissableOpen) hideOverlay();
});
overlayInputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && primaryActionHandler) {
    event.preventDefault();
    primaryActionHandler();
  }
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
      game.scene.start("GridScene", { socket, sfx, onScore, onLevel, onLevelCleared, onGameOver });
    },
  },
});

// Resolve the player name (from localStorage or an in-app modal prompt),
// then open the socket. The scene is already running and will receive the
// session + snapshot as soon as the server sends them.
(async () => {
  const stored = getStoredName();
  const resolved =
    stored ??
    (await askForName({ dismissable: false }))!; // not dismissable → always non-null
  setPlayerName(resolved);
  socket.connect();
})();
