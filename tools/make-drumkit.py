#!/usr/bin/env python3
"""Synthesize a 16-pad electronic drum kit (909/808-flavoured) to WAV.

Pure stdlib, 44.1 kHz mono 16-bit, peak-normalized with declick fades.
Output: ~/.local/share/padspace/drumkit/*.wav

The padSpace daemon maps pads to these filenames — replace any file with your
own sample of the same name to upgrade that pad (then re-toggle drum mode).
"""

import math
import os
import random
import struct
import wave

SR = 44100
OUT = os.path.expanduser("~/.local/share/padspace/drumkit")


def sine_sweep(dur, f0, f1, tau_f, tau_a, sat=1.0):
    out, ph = [], 0.0
    for i in range(int(SR * dur)):
        t = i / SR
        f = f1 + (f0 - f1) * math.exp(-t / tau_f)
        ph += 2 * math.pi * f / SR
        out.append(math.tanh(sat * math.sin(ph)) * math.exp(-t / tau_a))
    return out


def tone(dur, f, tau_a, g=1.0):
    return [g * math.sin(2 * math.pi * f * i / SR) * math.exp(-(i / SR) / tau_a)
            for i in range(int(SR * dur))]


def noise(dur, g=1.0):
    return [g * random.uniform(-1, 1) for _ in range(int(SR * dur))]


def decay(sig, tau):
    return [x * math.exp(-(i / SR) / tau) for i, x in enumerate(sig)]


def hp(sig, a=0.95, passes=1):
    for _ in range(passes):
        out, prev_x, y = [], 0.0, 0.0
        for x in sig:
            y = a * (y + x - prev_x)
            prev_x = x
            out.append(y)
        sig = out
    return sig


def lp(sig, a=0.25, passes=1):
    for _ in range(passes):
        out, y = [], 0.0
        for x in sig:
            y += a * (x - y)
            out.append(y)
        sig = out
    return sig


def mix(*sigs):
    n = max(len(s) for s in sigs)
    return [sum(s[i] for s in sigs if i < len(s)) for i in range(n)]


def gain(sig, g):
    return [x * g for x in sig]


def metal(dur, freqs, g, tau):
    out = []
    for i in range(int(SR * dur)):
        t = i / SR
        v = sum(1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0 for f in freqs)
        out.append(g * v / len(freqs) * math.exp(-t / tau))
    return out


def pluck(dur, f, damp=0.996):
    L = max(2, int(SR / f))
    buf = [random.uniform(-1, 1) for _ in range(L)]
    out = []
    for i in range(int(SR * dur)):
        j = i % L
        out.append(buf[j])
        buf[j] = 0.5 * (buf[j] + buf[(j + 1) % L]) * damp
    return out


def write(name, sig, peak=0.9):
    m = max(abs(x) for x in sig) or 1.0
    sig = [x * peak / m for x in sig]
    n = int(SR * 0.008)
    for i in range(n):  # declick fade-out
        sig[-n + i] *= 1 - i / n
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(
            struct.pack("<h", int(max(-1.0, min(1.0, x)) * 32767)) for x in sig))
    print(f"  {name}.wav ({len(sig)/SR:.2f}s)")


def clap():
    buf = [0.0] * int(SR * 0.35)
    for start, g in ((0.0, 1.0), (0.011, 0.85), (0.023, 0.7)):
        s = int(SR * start)
        for i, x in enumerate(noise(0.007, g)):
            buf[s + i] += x
    tail_start = int(SR * 0.033)
    for i, x in enumerate(decay(noise(0.3, 0.9), 0.075)):
        if tail_start + i < len(buf):
            buf[tail_start + i] += x
    return hp(lp(buf, 0.4), 0.88)


random.seed(909)
os.makedirs(OUT, exist_ok=True)
HATS = [3123, 4133, 5412, 6673, 7981, 9440]

kits = {
    # EDM kick family: punch (main four-on-the-floor), sub (808 tail), hard
    # (clipped festival kick). Plus a long sub-drop one-shot.
    "kick-punch": mix(sine_sweep(0.42, 215, 50, 0.018, 0.20, sat=2.6),
                      sine_sweep(0.42, 420, 60, 0.008, 0.045, sat=2.0)[:int(SR * 0.42)],
                      hp(noise(0.005, 0.8), 0.9)),
    "kick-sub": sine_sweep(1.2, 92, 38, 0.04, 0.55, sat=3.0),
    "kick-hard": [math.tanh(2.4 * x) for x in
                  mix(sine_sweep(0.45, 260, 52, 0.015, 0.18, sat=5.0),
                      hp(noise(0.006, 0.9), 0.85))],
    "sub-drop": sine_sweep(1.5, 64, 29, 0.55, 0.9, sat=1.6),
    "snare": mix(tone(0.22, 200, 0.045), tone(0.22, 330, 0.03, 0.5),
                 hp(decay(noise(0.26, 1.0), 0.07), 0.9, 2)),
    "clap": clap(),
    "hat-closed": hp(mix(metal(0.08, HATS, 0.6, 0.015),
                         decay(noise(0.08, 0.55), 0.015)), 0.97, 2),
    "hat-open": hp(mix(metal(0.55, HATS, 0.6, 0.13),
                       decay(noise(0.55, 0.55), 0.13)), 0.97, 2),
    "crash": hp(mix(decay(noise(1.6, 0.8), 0.45),
                    metal(1.6, [4200, 5900, 7300, 8100], 0.35, 0.5)), 0.9),
    "tom-low": mix(sine_sweep(0.45, 160, 95, 0.025, 0.22, 1.3), hp(noise(0.003, 0.3), 0.9)),
    "tom-high": mix(sine_sweep(0.35, 320, 190, 0.025, 0.16, 1.3), hp(noise(0.003, 0.3), 0.9)),
    "shaker": hp([x * (min(1.0, t / 0.015) if (t := i / SR) < 0.015
                       else math.exp(-(t - 0.015) / 0.045))
                  for i, x in enumerate(noise(0.14))], 0.96, 2),
    "pluck": pluck(0.5, 220),
    "snap": mix(hp(noise(0.004, 0.9), 0.8), tone(0.09, 1900, 0.012, 0.7)),
    "ride": hp(mix(tone(0.9, 3520, 0.3, 0.35), tone(0.9, 5270, 0.28, 0.3),
                   tone(0.9, 6800, 0.25, 0.25), decay(noise(0.9, 0.3), 0.3)), 0.93),
}
kits["reverse-cymbal"] = kits["crash"][::-1]

print(f"writing to {OUT}:")
for name, sig in kits.items():
    write(name, sig)
print("done")
