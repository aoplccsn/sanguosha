"""Procedurally generated original soundtrack.
No external samples or copyrighted music used.

群雄夜战: a quiet, loopable pentatonic battle theme synthesized with stdlib only.
"""

from __future__ import annotations

import argparse
import math
import random
import struct
import wave
from array import array
from pathlib import Path


RATE = 22_050
BPM = 76
BEAT = 60 / BPM
BARS = 32
DURATION = BARS * 4 * BEAT
COUNT = round(DURATION * RATE)
SEED = 19176
TAU = 2 * math.pi
SCALE = {"D2": 73.416, "A2": 110.0, "C3": 130.813, "D3": 146.832,
         "F3": 174.614, "G3": 195.998, "A3": 220.0, "C4": 261.626,
         "D4": 293.665, "F4": 349.228, "G4": 391.995, "A4": 440.0,
         "C5": 523.251, "D5": 587.330}


def add_pluck(buf: array, when: float, note: str, strength: float, rng: random.Random) -> None:
    freq = SCALE[note] * (1 + rng.uniform(-0.0015, 0.0015))
    start = round(when * RATE)
    length = round(2.6 * RATE)
    phase = rng.uniform(0, TAU)
    for j in range(length):
        t = j / RATE
        attack = min(1.0, t / 0.012)
        decay = math.exp(-2.8 * t)
        # Slight inharmonicity and a soft finger noise at the onset.
        tone = (math.sin(TAU * freq * t + phase)
                + 0.30 * math.sin(TAU * 2.01 * freq * t + phase * 0.7)
                + 0.10 * math.sin(TAU * 3.02 * freq * t))
        finger = rng.uniform(-1, 1) * math.exp(-48 * t) * 0.018
        buf[(start + j) % COUNT] += strength * attack * decay * (tone / 1.4 + finger)


def add_flute(buf: array, when: float, note: str, beats: float, strength: float,
              rng: random.Random) -> None:
    freq = SCALE[note]
    start = round(when * RATE)
    length = round((beats * BEAT + 0.28) * RATE)
    release = beats * BEAT
    phase = 0.0
    for j in range(length):
        t = j / RATE
        envelope = min(1.0, t / 0.22) * min(1.0, max(0.0, (length / RATE - t) / 0.30))
        if t > release:
            envelope *= math.exp(-8 * (t - release))
        vibrato = 1 + 0.0022 * math.sin(TAU * 4.6 * t)
        phase += TAU * freq * vibrato / RATE
        tone = 0.88 * math.sin(phase) + 0.12 * math.sin(3 * phase)
        breath = rng.uniform(-1, 1) * 0.004
        buf[(start + j) % COUNT] += strength * envelope * (tone + breath)


def add_drum(buf: array, when: float, strength: float, rng: random.Random) -> None:
    start = round(when * RATE)
    phase = 0.0
    for j in range(round(0.72 * RATE)):
        t = j / RATE
        phase += TAU * (68 + 45 * math.exp(-17 * t)) / RATE
        body = math.sin(phase) * math.exp(-8.5 * t)
        skin = rng.uniform(-1, 1) * math.exp(-45 * t) * 0.12
        buf[(start + j) % COUNT] += strength * (body + skin)


def synthesize() -> array:
    rng = random.Random(SEED)
    audio = array("f", [0.0]) * COUNT
    # Quantized cycle counts make the soft drone itself periodic at the seam.
    drone = [("D2", 0.036), ("A2", 0.018), ("D3", 0.010)]
    for name, amplitude in drone:
        cycles = round(SCALE[name] * DURATION)
        for i in range(COUNT):
            audio[i] += amplitude * math.sin(TAU * cycles * i / COUNT)

    arpeggio = ["D3", "A3", "F3", "C4", "A3", "G3", "F3", "A3"]
    theme = [("D4", 1.5), ("F4", 0.5), ("G4", 1), ("A4", 1),
             ("G4", 1), ("F4", 1), ("D4", 2)]
    answer = [("A4", 1), ("C5", 1), ("A4", 1.5), ("G4", 0.5),
              ("F4", 1), ("G4", 1), ("D4", 2)]
    for bar in range(BARS):
        base = bar * 4 * BEAT
        returning = bar >= 26
        opening = bar < 6
        weight = 0.73 if opening or returning else (1.0 if bar < 18 else 1.13)
        # A recurring eight-beat figure carries the piece through all sections.
        steps = (0, 2) if opening or returning else (0, 1, 2, 3)
        for step in steps:
            name = arpeggio[(bar * 4 + step) % len(arpeggio)]
            add_pluck(audio, base + step * BEAT, name, 0.081 * weight, rng)
        if bar % 2 == 0 and not opening and not returning:
            add_pluck(audio, base + 2.5 * BEAT, "D4" if bar % 4 == 0 else "C4",
                      0.031 * weight, rng)
        if 3 <= bar < 29:
            phrase = theme if (bar // 2) % 2 == 0 else answer
            # Phrase spans two bars. Each return is recognisable, with restrained growth.
            if bar % 2 == 0:
                cursor = base
                for note, beats in phrase:
                    add_flute(audio, cursor, note, beats * 0.91,
                              0.039 * (1.15 if 18 <= bar < 26 else 1.0), rng)
                    cursor += beats * BEAT
        if 6 <= bar < 26:
            add_drum(audio, base, 0.071 if bar < 18 else 0.094, rng)
            if bar >= 18 and bar % 2 == 0:
                add_drum(audio, base + 2 * BEAT, 0.042, rng)
    # The beginning and ending share sparse texture; ease the final 0.18 s
    # toward the first sample to eliminate a boundary discontinuity.
    seam = round(0.18 * RATE)
    for j in range(seam):
        blend = (j / (seam - 1)) ** 2
        i = COUNT - seam + j
        audio[i] = audio[i] * (1 - blend) + audio[0] * blend
    return audio


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1]
                        / "assets/audio/bgm/main_bgm.wav")
    args = parser.parse_args()
    audio = synthesize()
    peak = max(abs(sample) for sample in audio)
    gain = 10 ** (-3 / 20) / peak
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(args.output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        for start in range(0, COUNT, 8192):
            chunk = audio[start:start + 8192]
            wav.writeframesraw(struct.pack("<" + "h" * len(chunk),
                                           *(round(max(-1, min(1, x * gain)) * 32767)
                                             for x in chunk)))
    print(f"{args.output}: {DURATION:.2f}s, {RATE}Hz mono, peak={peak * gain:.4f}")


if __name__ == "__main__":
    main()
