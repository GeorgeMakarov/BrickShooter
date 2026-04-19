/**
 * Server-side scoreboard client.
 *
 * Keeps only the *display name* in localStorage; the actual high-score list
 * lives on the server (see backend/scoreboard.py). The client asks for the
 * top-N via a {"type":"scores"} WS message and renders the reply.
 *
 * Display name prompt on first visit (if no name stored), then sent to the
 * server via {"type":"set_name"} on every connect + whenever the user
 * updates it.
 */

export type Difficulty = "easy" | "normal" | "hard";

export interface ScoreEntry {
  name: string;
  score: number;
  level: number;
  difficulty: Difficulty;
  date: string;
}

const NAME_KEY = "brickshooter.name";
const MAX_NAME_LENGTH = 24;

export function getStoredName(): string | null {
  const raw = localStorage.getItem(NAME_KEY);
  if (!raw) return null;
  const cleaned = raw.trim().slice(0, MAX_NAME_LENGTH);
  return cleaned || null;
}

export function storeName(name: string): string {
  const cleaned = name.trim().slice(0, MAX_NAME_LENGTH) || "Anonymous";
  localStorage.setItem(NAME_KEY, cleaned);
  return cleaned;
}

/**
 * Render a list of ScoreEntry into the target element. `highlightIndex`
 * marks a single entry (usually the player's just-landed one) in accent.
 */
export function renderServerScores(
  target: HTMLElement,
  difficulty: Difficulty,
  entries: ScoreEntry[],
  highlightIndex = -1,
): void {
  const header = `<h3>Top scores — ${difficulty}</h3>`;
  if (entries.length === 0) {
    target.innerHTML =
      header + "<p style='opacity:0.6;font-size:13px;margin:0'>no scores yet — be the first!</p>";
    return;
  }
  const items = entries
    .map((e, i) => {
      const cls = i === highlightIndex ? ' class="fresh"' : "";
      const date = new Date(e.date).toLocaleDateString();
      return `<li${cls}><span>${escapeHTML(e.name)}</span><span>L${e.level}</span><span>${e.score}</span><span style="opacity:0.6">${date}</span></li>`;
    })
    .join("");
  target.innerHTML = header + `<ol>${items}</ol>`;
}

function escapeHTML(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
