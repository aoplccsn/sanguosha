"""Procedurally generated original soundtrack.
No external samples or copyrighted music used.

暗局·夜阵: a restrained, loopable battlefield strategy texture synthesized with stdlib only.
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
BPM = 72
BEAT = 60 / BPM
BARS = 36
DURATION = BARS * 4 * BEAT
COUNT = round(DURATION * RATE)
SEED = 20272
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
        buf[(start + j) % COUNT] += strength * min(1,t/.006) * (body + skin)


def synthesize() -> array:
    rng = random.Random(SEED)
    audio = array("f", [0.0]) * COUNT
    # Quantized cycle counts make the soft drone itself periodic at the seam.
    drone = [("D2", 0.036), ("A2", 0.018), ("D3", 0.010)]
    for name, amplitude in drone:
        cycles = round(SCALE[name] * DURATION)
        for i in range(COUNT):
            audio[i] += amplitude * math.sin(TAU * cycles * i / COUNT)

    # Low register, irregular silences and unresolved fourths; no bright melody.
    cells=[('D3','A2','G3'),('D3','C3','A2'),('F3','D3','G3'),('C3','A2','D3')]
    for bar in range(BARS):
        base=bar*4*BEAT
        sparse=bar<8 or bar>=30
        tense=20<=bar<30
        cell=cells[(bar//3)%len(cells)]
        weight=.68 if sparse else .88 if not tense else 1.0
        for step,note in zip((0,2.5) if sparse else (0,1.5,3.25),cell):
            add_pluck(audio,base+step*BEAT,note,.061*weight,rng)
        # Occasional quiet pipa-like double stroke, never a constant arpeggio.
        if 10<=bar<29 and bar%3==1:
            add_pluck(audio,base+2*BEAT,'C4',.018,rng)
            add_pluck(audio,base+2.16*BEAT,'G3',.014,rng)
        if bar in (3,6,11,15,19,23,27,32):
            add_flute(audio,base+.4*BEAT,('D3','C3','G3','A2')[(bar//3)%4],3.1,.022 if sparse else .028,rng)
        if 8<=bar<30 and bar%2==0:
            add_drum(audio,base+.12*BEAT,.048 if not tense else .067,rng)
            if tense and bar%4==0: add_drum(audio,base+2.75*BEAT,.032,rng)
        # Dry wood/stone ticks, synthesized without samples or modern drum kit.
        if 10<=bar<30 and bar%3!=0:
            when=round((base+3.5*BEAT)*RATE)
            for j in range(round(.22*RATE)):
                t=j/RATE
                tone=math.sin(TAU*740*t)+.25*math.sin(TAU*1187*t)
                audio[(when+j)%COUNT]+=.009*min(1,t/.003)*math.exp(-28*t)*tone
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
    gain = 10 ** (-9 / 20) / peak
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
