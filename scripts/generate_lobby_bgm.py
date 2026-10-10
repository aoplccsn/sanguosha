"""山河将起: deterministic original lobby music, no samples or external audio.

Reuses the project's acoustic-style synthesis primitives. Sparse pentatonic
plucks, breath tones and quiet bowed harmonics contrast with 暗局·夜阵.
"""
from array import array
from pathlib import Path
import math
import random
import struct
import wave
import generate_bgm as synth

def synthesize():
    synth.BPM = 60
    synth.BEAT = 1.0
    synth.BARS = 16
    synth.DURATION = 64.0
    synth.COUNT = round(synth.DURATION * synth.RATE)
    audio = array('f', [0.0]) * synth.COUNT
    rng = random.Random(2142026)
    # Sustain a low, softly bowed open fifth; integer cycles preserve the loop.
    for note, level in [('D3', .014), ('A3', .009), ('D4', .004)]:
        cycles = round(synth.SCALE[note] * synth.DURATION)
        for i in range(synth.COUNT):
            phase = synth.TAU * cycles * i / synth.COUNT
            swell = .78 + .22 * math.cos(synth.TAU * i / synth.COUNT * 4)
            audio[i] += level * swell * (math.sin(phase) + .12 * math.sin(2 * phase))
    cells = [('D3', 'A3'), ('G3', 'D4'), ('A3', 'C4'), ('G3', 'D3')]
    melody = [(0, 'D4', 3), (2, 'G4', 4), (4, 'A4', 3), (6, 'G4', 4),
              (8, 'D5', 3), (10, 'C5', 3), (12, 'A4', 4), (14, 'D4', 4)]
    for bar in range(16):
        first, second = cells[(bar // 2) % 4]
        synth.add_pluck(audio, bar * 4 + .15, first, .072, rng)
        if bar % 2 == 0:
            synth.add_pluck(audio, bar * 4 + 2.5, second, .032, rng)
        if bar in (3, 7, 11, 15):
            synth.add_drum(audio, bar * 4 + .2, .016, rng)
    for bar, note, beats in melody:
        synth.add_flute(audio, bar * 4 + .7, note, beats, .035, rng)
    # Circular reflection/reverb carries tails into the next loop naturally.
    dry = audio[:]
    for delay, level in [(.19, .12), (.37, .08), (.61, .045)]:
        shift = round(delay * synth.RATE)
        for i in range(synth.COUNT):
            audio[i] += dry[(i - shift) % synth.COUNT] * level
    # Match the last 10ms to the actual opening waveform, rather than silence.
    seam = round(.01 * synth.RATE)
    for j in range(seam):
        blend = (j / (seam - 1)) ** 2
        i = synth.COUNT - seam + j
        audio[i] = audio[i] * (1 - blend) + audio[0] * blend
    return audio

if __name__ == '__main__':
    audio = synthesize()
    gain = 10 ** (-9 / 20) / max(abs(x) for x in audio)
    target = Path(__file__).resolve().parents[1] / 'assets/audio/bgm/lobby_bgm.wav'
    with wave.open(str(target), 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(synth.RATE)
        for start in range(0, len(audio), 8192):
            chunk = audio[start:start + 8192]
            wav.writeframesraw(struct.pack('<' + 'h' * len(chunk), *(round(x * gain * 32767) for x in chunk)))
    print(f'{target}: 64s, 22050Hz mono PCM, -9dBFS peak, {target.stat().st_size} bytes')
