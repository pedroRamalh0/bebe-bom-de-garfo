"""Animação do produto entrando com "pop" + som de "plin", sobre um vídeo, sem alterar o vídeo/áudio original.
Uso: python3 tools/reveal_pop.py video.mp4 words.json t_inicio duracao saida.mp4 [palavras-chave...]
Gera: card do produto (Playwright), quadros com animação (PIL), plin sintetizado, legenda ASS, e compõe com ffmpeg."""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import montar2  # reaproveita a legenda

video, words, t0, d, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
kw = sys.argv[6:]
TMP = os.environ.get("TMPDIR_BBG", "/tmp/bbg_pop"); os.makedirs(TMP, exist_ok=True)
FPS = 30

# 1) card do produto (PNG transparente)
card = os.path.join(TMP, "card.png")
subprocess.run(["node", "-e", r"""
const fs=require('fs'),path=require('path'),{chromium}=require('playwright');
const A=process.argv[1], out=process.argv[2];
const b=f=>'data:image/png;base64,'+fs.readFileSync(path.join(A,f)).toString('base64');
(async()=>{const br=await chromium.launch();const p=await br.newPage({viewport:{width:900,height:900}});
await p.setContent(`<html><head><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@800&display=block" rel="stylesheet"></head>
<body style="margin:0;background:transparent;display:flex;justify-content:center;align-items:flex-start">
<div id=c style="margin:30px;padding:34px 34px 26px;border-radius:44px;background:linear-gradient(180deg,#FFFDF7,#F6EEE1);box-shadow:0 30px 60px rgba(0,0,0,.35);display:flex;flex-direction:column;align-items:center;width:760px">
<img src="${b('logo.png')}" style="height:92px">
<img src="${b('hero-kit.png')}" style="width:700px;margin-top:8px">
<div style="margin-top:6px;padding:12px 28px;border-radius:99px;background:#2E9E5B;color:#fff;font:800 30px 'DM Sans'">300 receitinhas por idade ✨</div>
</div><script>document.fonts.ready.then(()=>window.r=1)</script></body></html>`);
await p.waitForFunction(()=>window.r);await (await p.$('#c')).screenshot({path:out,omitBackground:true});await br.close();})();
""", os.path.join(ROOT, "tools", "assets"), card], check=True)

# 2) quadros da animação: pop (ease-out-back), flutuação leve, saída com fade + subida
im = Image.open(card).convert("RGBA"); W0 = 860; im = im.resize((W0, int(im.height * W0 / im.width)), Image.LANCZOS)
fdir = os.path.join(TMP, "frames"); os.makedirs(fdir, exist_ok=True)
for f in os.listdir(fdir): os.remove(os.path.join(fdir, f))
n = int(d * FPS); CW, CH = 1080, im.height + 160
def back(x, s=1.9): x -= 1; return x * x * ((s + 1) * x + s) + 1
for i in range(n):
    t = i / FPS
    a_in = min(1, t / 0.38); sc = 0.35 + 0.65 * back(a_in) if a_in < 1 else 1.0
    out_t = max(0, (t - (d - 0.35)) / 0.35); alpha = 1 - out_t
    dy = -8 * math.sin(t * 3.2) - 60 * out_t
    fr = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    w = max(2, int(W0 * sc)); h = max(2, int(im.height * sc))
    cur = im.resize((w, h), Image.LANCZOS)
    if alpha < 1: cur.putalpha(cur.getchannel("A").point(lambda v: int(v * alpha)))
    fr.alpha_composite(cur, ((CW - w) // 2, int((CH - h) / 2 + dy)))
    fr.save(os.path.join(fdir, f"{i:04d}.png"))
anim = os.path.join(TMP, "anim.mov")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(fdir, "%04d.png"), "-c:v", "qtrle", anim], check=True)

# 3) som de "plin" (sino suave)
SR = 44100; tt = np.arange(int(1.2 * SR)) / SR
pl = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * k) for f, a, k in ((1568, .6, 5), (2093, .45, 6), (3136, .2, 9), (4186, .12, 12)))
pl += 0.25 * np.sin(2 * np.pi * 2349 * tt) * np.exp(-tt * 7) * (tt > 0.07)
pl = pl / np.max(np.abs(pl)) * 0.7
plin = os.path.join(TMP, "plin.wav"); w_ = wave.open(plin, "w"); w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(SR)
w_.writeframes((pl * 32767).astype(np.int16).tobytes()); w_.close()

# 4) legenda
total = montar2.dur(video)
subs = os.path.join(TMP, "subs.ass")
open(subs, "w").write(montar2.ass({"keywords": kw}, json.load(open(words))["words"], total))

# 5) composição: vídeo original intacto + card + legenda; áudio original + plin
fonts = os.path.join(ROOT, "tools", "fonts")
fc = (f"[0:v]scale=1080:1920:flags=lanczos,setsar=1[v0];"
      f"[1:v]setpts=PTS+{t0}/TB[an];[v0][an]overlay=0:170:eof_action=pass:enable='between(t,{t0},{t0+d})'[v1];"
      f"[v1]ass={subs}:fontsdir={fonts}[v];"
      f"[2:a]adelay={int(t0*1000)}|{int(t0*1000)},volume=0.9[p];[0:a][p]amix=inputs=2:normalize=0:duration=first[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", anim, "-i", plin, "-filter_complex", fc,
                "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)
print("ok", out)
