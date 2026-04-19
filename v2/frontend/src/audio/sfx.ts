/**
 * Programmatic sound effects.
 *
 * No audio files shipped — each sound is synthesised on demand via the Web
 * Audio API: oscillator + gain envelope. Keeps the bundle small and lets
 * match pitch track group size without needing sample libraries.
 *
 * Browser autoplay policy: AudioContext creation is deferred until the
 * first call, and `resume()` is requested — if that first call happens
 * inside a user gesture (pointerdown → shoot), Chrome/Safari unlock audio.
 * Calls before any user gesture silently no-op.
 */

const MUTED_KEY = "brickshooter.muted";

export class Sfx {
  private ctx: AudioContext | null = null;
  private muted: boolean;

  constructor() {
    this.muted = localStorage.getItem(MUTED_KEY) === "true";
  }

  get isMuted(): boolean {
    return this.muted;
  }

  setMuted(muted: boolean): void {
    this.muted = muted;
    localStorage.setItem(MUTED_KEY, String(muted));
  }

  toggleMuted(): boolean {
    this.setMuted(!this.muted);
    return this.muted;
  }

  /** Descending pitch sweep for BrickShot — short "pew" feel, not a system click. */
  playShot(): void {
    this.toneSlide({
      startFreq: 820,
      endFreq: 210,
      durMs: 110,
      type: "triangle",
      peakGain: 0.09,
    });
  }

  /** Clean tonal ping for BrickMatched, pitch climbs with group size and slides
   *  up over the note so it reads as "successful clear". */
  playMatch(groupSize: number): void {
    const base = 520 + Math.min(8, Math.max(0, groupSize - 3)) * 55;
    this.toneSlide({
      startFreq: base,
      endFreq: base * 1.25,
      durMs: 240,
      type: "sine",
      peakGain: 0.11,
    });
    // Small fifth overtone for brightness.
    this.tone({ freq: base * 1.5, durMs: 140, type: "triangle", peakGain: 0.035, delayMs: 20 });
  }

  /** Two-note ascending chime on LevelCleared (C5 → G5). */
  playLevelUp(): void {
    this.tone({ freq: 523.25, durMs: 180, type: "triangle", peakGain: 0.09 });
    this.tone({ freq: 783.99, durMs: 260, type: "triangle", peakGain: 0.09, delayMs: 160 });
  }

  private tone(opts: {
    freq: number;
    durMs: number;
    type?: OscillatorType;
    peakGain?: number;
    delayMs?: number;
  }): void {
    if (this.muted) return;
    const ctx = this.getOrCreateContext();
    if (ctx === null) return;

    const { freq, durMs, type = "sine", peakGain = 0.08, delayMs = 0 } = opts;
    const start = ctx.currentTime + delayMs / 1000;
    const end = start + durMs / 1000;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    osc.connect(gain);
    gain.connect(ctx.destination);

    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(peakGain, start + 0.005);
    gain.gain.exponentialRampToValueAtTime(0.0001, end);

    osc.start(start);
    osc.stop(end);
  }

  /** A single tone whose frequency slides from startFreq to endFreq. */
  private toneSlide(opts: {
    startFreq: number;
    endFreq: number;
    durMs: number;
    type?: OscillatorType;
    peakGain?: number;
    delayMs?: number;
  }): void {
    if (this.muted) return;
    const ctx = this.getOrCreateContext();
    if (ctx === null) return;

    const { startFreq, endFreq, durMs, type = "sine", peakGain = 0.08, delayMs = 0 } = opts;
    const start = ctx.currentTime + delayMs / 1000;
    const end = start + durMs / 1000;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(startFreq, start);
    osc.frequency.exponentialRampToValueAtTime(endFreq, end);
    osc.connect(gain);
    gain.connect(ctx.destination);

    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(peakGain, start + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.0001, end);

    osc.start(start);
    osc.stop(end);
  }


  private getOrCreateContext(): AudioContext | null {
    if (this.ctx !== null) {
      if (this.ctx.state === "suspended") {
        // Resume returns a Promise; fire-and-forget — if the call site
        // isn't inside a user gesture the resume itself may fail, which we
        // swallow (the tone just won't play).
        this.ctx.resume().catch(() => undefined);
      }
      return this.ctx;
    }
    const Ctor: typeof AudioContext | undefined =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    try {
      this.ctx = new Ctor();
      return this.ctx;
    } catch {
      return null;
    }
  }
}
