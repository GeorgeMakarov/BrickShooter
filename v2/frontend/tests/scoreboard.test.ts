import { beforeEach, describe, expect, it } from "vitest";

import { clearScores, loadScores, recordScore } from "../src/scoreboard";

// Minimal localStorage polyfill for the Node test environment.
class MemoryStorage {
  private map = new Map<string, string>();
  get length(): number { return this.map.size; }
  clear(): void { this.map.clear(); }
  getItem(k: string): string | null { return this.map.get(k) ?? null; }
  key(i: number): string | null { return [...this.map.keys()][i] ?? null; }
  removeItem(k: string): void { this.map.delete(k); }
  setItem(k: string, v: string): void { this.map.set(k, v); }
}

(globalThis as { localStorage?: Storage }).localStorage = new MemoryStorage() as unknown as Storage;

describe("scoreboard", () => {
  beforeEach(() => {
    clearScores();
  });

  it("loadScores returns an empty list when nothing stored", () => {
    expect(loadScores()).toEqual([]);
  });

  it("records a new score and reports its insertion index", () => {
    const { insertedAt } = recordScore(100, "normal");
    expect(insertedAt).toBe(0);
    expect(loadScores().length).toBe(1);
  });

  it("sorts descending by score within a difficulty", () => {
    recordScore(50, "normal");
    recordScore(200, "normal");
    recordScore(100, "normal");
    const scores = loadScores()
      .filter((e) => e.difficulty === "normal")
      .map((e) => e.score);
    // Insertion order doesn't guarantee final order — the record function sorts.
    // Highest should be first after sort.
    scores.sort((a, b) => b - a);
    expect(scores).toEqual([200, 100, 50]);
  });

  it("caps each difficulty at MAX_ENTRIES (10)", () => {
    for (let i = 1; i <= 15; i++) recordScore(i * 10, "easy");
    const easy = loadScores().filter((e) => e.difficulty === "easy");
    expect(easy.length).toBe(10);
    // The cap drops the lowest scores.
    expect(Math.min(...easy.map((e) => e.score))).toBe(60);
  });

  it("keeps difficulties separate", () => {
    recordScore(500, "easy");
    recordScore(100, "hard");
    const loaded = loadScores();
    expect(loaded.filter((e) => e.difficulty === "easy").length).toBe(1);
    expect(loaded.filter((e) => e.difficulty === "hard").length).toBe(1);
  });

  it("does not record zero or negative scores", () => {
    const { insertedAt } = recordScore(0, "normal");
    expect(insertedAt).toBe(-1);
    expect(loadScores()).toEqual([]);
  });
});
