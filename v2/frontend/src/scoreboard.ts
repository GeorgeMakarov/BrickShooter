/**
 * localStorage-backed top-N scoreboard. Per-browser, per-difficulty.
 *
 * No server state; the backend stays stateless for scores. If a user moves
 * browsers they start fresh — acceptable trade for a single-player hobby app.
 */

export type Difficulty = "easy" | "normal" | "hard";

export interface ScoreEntry {
  score: number;
  difficulty: Difficulty;
  date: string; //!< ISO 8601
}

const STORAGE_KEY = "brickshooter.scores";
const MAX_ENTRIES = 10;

export function loadScores(): ScoreEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as ScoreEntry[]) : [];
  } catch {
    return [];
  }
}

/**
 * Record a score if it qualifies for the top-N (within the same difficulty).
 * Returns the index the entry landed at (for highlighting), or -1 if the score
 * didn't make the cut.
 */
export function recordScore(score: number, difficulty: Difficulty): { entries: ScoreEntry[]; insertedAt: number } {
  if (score <= 0) return { entries: loadScores(), insertedAt: -1 };

  const existing = loadScores();
  const peers = existing.filter((e) => e.difficulty === difficulty);
  const others = existing.filter((e) => e.difficulty !== difficulty);

  const newEntry: ScoreEntry = { score, difficulty, date: new Date().toISOString() };
  peers.push(newEntry);
  peers.sort((a, b) => b.score - a.score);
  const trimmed = peers.slice(0, MAX_ENTRIES);
  const insertedAt = trimmed.indexOf(newEntry);

  const merged = [...others, ...trimmed];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  return { entries: merged, insertedAt };
}

export function clearScores(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Render the scoreboard into a target element. Shows top-N of the current
 * difficulty. `highlightIndex` marks a single entry as just-added.
 */
export function renderScores(
  target: HTMLElement,
  difficulty: Difficulty,
  highlightIndex = -1,
): void {
  const entries = loadScores()
    .filter((e) => e.difficulty === difficulty)
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_ENTRIES);

  const header = `<h3>Top scores — ${difficulty}</h3>`;
  if (entries.length === 0) {
    target.innerHTML = header + "<p style='opacity:0.6;font-size:13px;margin:0'>no scores yet</p>";
    return;
  }

  const items = entries
    .map((e, i) => {
      const cls = i === highlightIndex ? ' class="fresh"' : "";
      const date = new Date(e.date).toLocaleDateString();
      return `<li${cls}><span>${e.score}</span><span style="opacity:0.6">${date}</span></li>`;
    })
    .join("");
  target.innerHTML = header + `<ol>${items}</ol>`;
}
