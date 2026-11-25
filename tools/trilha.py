"""Gera uma trilha leve e alegre (sem direitos autorais): dedilhado tipo ukulele + piano suave + batida leve.
Uso: python3 tools/trilha.py saida.wav [segundos] [bpm]"""
import sys, wave, numpy as np
out = sys.argv[1]; secs = float(sys.argv[2]) if len(sys.argv) > 2 else 70; bpm = float(sys.argv[3]) if len(sys.argv) > 3 else 100
SR = 44100; N = int(secs * SR); mix = np.zeros(N)
beat = 60 / bpm
def note(f, t0, dur, amp, kind="pluck"):
    i0 = int(t0 * SR); n = int(dur * SR)
    if i0 >= N: return
    n = min(n, N - i0); t = np.arange(n) / SR
    if kind == "pluck":  # Karplus-Strong simplificado
        per = max(2, int(SR / f)); buf = np.random.uniform(-1, 1, per); y = np.zeros(n)
        for k in range(n):
            y[k] = buf[k % per]; buf[k % per] = 0.5 * (buf[k % per] + buf[(k + 1) % per]) * 0.996
        y *= np.exp(-t * 2.2)
    elif kind == "piano":
        y = (np.sin(2*np.pi*f*t) + 0.35*np.sin(4*np.pi*f*t) + 0.12*np.sin(6*np.pi*f*t)) * np.exp(-t * 1.6)
    elif kind == "kick":
        y = np.sin(2*np.pi*(55 + 70*np.exp(-t*30))*t) * np.exp(-t * 9)
    elif kind == "shaker":
        y = np.random.uniform(-1, 1, n) * np.exp(-t * 40)
    a = np.minimum(1, t / 0.004)
    mix[i0:i0+n] += amp * y * a
mid = lambda m: 440 * 2 ** ((m - 69) / 12)
prog = [[60, 64, 67], [67, 71, 74], [69, 72, 76], [65, 69, 72]]  # C G Am F
patt = [0, 1, 2, 1, 2, 1, 0, 2]
bar = 0; t = 0.0
while t < secs:
    ch = prog[bar % 4]
    for s in range(8):  # colcheias
        tt = t + s * beat / 2
        note(mid(ch[patt[s]] + (12 if s in (2, 5) else 0)), tt, beat * 1.5, 0.22)
        if s % 2 == 1: note(0, tt, 0.06, 0.05, "shaker")
    note(mid(ch[0] - 12), t, beat * 4, 0.10, "piano")
    note(mid(ch[2]), t + beat * 2, beat * 2, 0.06, "piano")
    if bar >= 1:
        for k in (0, 2): note(0, t + k * beat, 0.4, 0.35, "kick")
    t += beat * 4; bar += 1
mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.8
fade = int(2.5 * SR); mix[-fade:] *= np.linspace(1, 0, fade); mix[:int(0.6*SR)] *= np.linspace(0, 1, int(0.6*SR))
w = wave.open(out, "w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close(); print("ok", out)
