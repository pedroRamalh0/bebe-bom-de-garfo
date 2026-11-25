"""C08 · Formato ERRADO × CERTO (tela dividida) com mosaico-contador no gancho. Áudio: audios/r3v2-final.wav
Uso: python3 tools/c08_split.py"""
import json, math, os, re, subprocess, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.environ.get("TMPDIR_BBG", "/tmp/bbg_c08"); os.makedirs(TMP, exist_ok=True)
W, H, FPS, T = 1080, 1920, 30, 0.2
AUDIO = os.path.join(ROOT, "audios/r3v2-final.wav")
WORDS = json.load(open(os.path.join(ROOT, "audios/r3v2-final.words.json")))["words"]
OUT = os.path.join(ROOT, "criativos/c08-errado-x-certo.mp4")
CREAM = "0xF6EEE1"

def run(c): subprocess.run(c, check=True)
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).decode())
def size(p):
    w, h = subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",p]).decode().strip().split(",")[:2]
    return int(w), int(h)
def src(s): return os.path.join(ROOT, s if "/" in s else f"takes/{s}.mp4")
N = [0]
def clip(s, t_in, d, w, h, yf=0.5, z=(1.0, 1.06), speed=1.0):
    """recorta (sem distorcer) para w:h, leve push-in, d segundos."""
    N[0] += 1; out = f"{TMP}/k{N[0]:03d}.mp4"; p = src(s); sw, sh = size(p)
    ar = w / h
    cw, ch = (sw, int(sw / ar)) if sw / ar <= sh else (int(sh * ar), sh)
    cy = int((sh - ch) * yf); n = max(2, int(round(d * FPS)))
    zp = f"zoompan=z='{z[0]}+({z[1]}-{z[0]})*on/{n}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s={w}x{h}:fps={FPS}"
    sp = f",setpts=PTS/{speed}" if speed != 1 else ""
    run(["ffmpeg","-v","error","-y","-ss",str(t_in),"-t",str(d*speed+0.6),"-i",p,"-vf",
         f"crop={cw}:{ch}:{(sw-cw)//2}:{cy},scale={w}:{h}:flags=lanczos,setsar=1{sp},fps={FPS},tpad=stop_mode=clone:stop_duration=4,{zp},eq=saturation=1.1:contrast=1.04,format=yuv420p",
         "-frames:v",str(n),"-an","-c:v","libx264","-preset","veryfast","-crf","17",out]); return out
def seq(parts, w, h):
    """parts: [(src, in, dur, yf)] concatenados com corte seco (ritmo)."""
    fs = [clip(s, i, d, w, h, yf) for s, i, d, yf in parts]
    N[0] += 1; lst = f"{TMP}/l{N[0]}.txt"; open(lst, "w").write("".join(f"file '{f}'\n" for f in fs))
    out = f"{TMP}/s{N[0]:03d}.mp4"; run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",lst,"-c","copy",out]); return out
def full(s, t_in, d, yf=0.5, z=(1.0, 1.07)): return clip(s, t_in, d, W, H, yf, z)
def split(top, bot, d, bar):
    a = seq(top, W, 950); b = seq(bot, W, 950); N[0] += 1; out = f"{TMP}/sp{N[0]}.mp4"
    run(["ffmpeg","-v","error","-y","-i",a,"-i",b,"-filter_complex",
         f"color=c={bar}:s={W}x{H}:r={FPS}:d={d}[bg];[bg][0:v]overlay=0:0:shortest=1[t];[t][1:v]overlay=0:970:shortest=1,format=yuv420p[v]",
         "-map","[v]","-frames:v",str(int(round(d*FPS))),"-c:v","libx264","-preset","veryfast","-crf","17",out]); return out
def grid(cells, d, starts):
    """mosaico 3x3 (cada célula 352x620, com respiro), células aparecem em starts[i]."""
    fs = [clip(s, i, d, 352, 620, 0.5, (1.0, 1.08)) for s, i in cells]
    N[0] += 1; out = f"{TMP}/g{N[0]}.mp4"; fc = f"color=c={CREAM}:s={W}x{H}:r={FPS}:d={d}[b0];"; last = "b0"
    for k, f in enumerate(fs):
        x = 6 + (k % 3) * 358; y = 10 + (k // 3) * 636; st = starts[k]
        fc += f"[{k}:v]setpts=PTS+{st}/TB,format=yuva420p{(f',fade=t=in:st={st}:d=0.18:alpha=1' if st > 0 else '')}[c{k}];[{last}][c{k}]overlay={x}:{y}:eof_action=pass:enable='gte(t,{st})'[b{k+1}];"; last = f"b{k+1}"
    fc += f"[{last}]format=yuv420p[v]"
    run(["ffmpeg","-v","error","-y",*sum([["-i",f] for f in fs],[]),"-filter_complex",fc,"-map","[v]","-frames:v",str(int(round(d*FPS))),"-c:v","libx264","-preset","veryfast","-crf","17",out]); return out
def still(img, d, z=(1.0, 1.04)):
    N[0] += 1; out = f"{TMP}/i{N[0]}.mp4"; n = int(round(d*FPS))
    run(["ffmpeg","-v","error","-y","-loop","1","-framerate",str(FPS),"-i",os.path.join(ROOT,img),"-frames:v",str(n),"-vf",
         f"scale={W}:{H},zoompan=z='{z[0]}+({z[1]}-{z[0]})*on/{n}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s={W}x{H}:fps={FPS},format=yuv420p",
         "-c:v","libx264","-preset","veryfast","-crf","17",out]); return out

VOICE = dur(AUDIO); TAIL = 1.4; TOTAL = VOICE + TAIL
B = [0.0, 5.4, 7.9, 14.9, 18.5, 23.95, TOTAL]           # fronteiras dos blocos
D = [B[i+1] - B[i] + (T if i < 5 else 0) for i in range(6)]
segs = [
  grid([("t3",60.2),("t5",53.0),("t8",8.0),("antigos/bb6.mp4",8.0),("t6",50.0),("t7",19.5),("t2",46.0),("antigos/bb4.mp4",12.0),("t2",23.5)], D[0],
       [0.0,0.0,0.0,0.15,0.3,0.45,0.6,0.75,0.9]),
  full("t1", 12.6, D[1]),
  split([("t4",31.2,2.65,0.65),("t6",29.3,2.0,0.5),("t6",37.3,2.55,0.5)], [("t1",0.3,4.7,0.35),("t1",20.0,2.5,0.35)], D[2], "0xC0392B"),
  full("t3", 13.2, D[3], 0.35),
  split([("t5",26.0,2.9,0.6),("t2",37.0,1.4,0.6),("t2",52.4,1.35,0.6)], [("antigos/bb5.mp4",37.2,2.6,0.3),("antigos/bb5.mp4",39.8,3.05,0.3)], D[4], "0x2E9E5B"),
  still("tools/assets/endcard.png", D[5], (1.0, 1.05)),
]
inputs = sum([["-i", f] for f in segs], []); fc = ""; prev = "0:v"; off = 0.0
for i in range(1, len(segs)):
    off += D[i-1] - T; fc += f"[{prev}][{i}:v]xfade=transition={'circleopen' if i==5 else 'fade'}:duration={T}:offset={off:.3f}[x{i}];"; prev = f"x{i}"

# ---------------- ASS: legendas, headlines, selos, contador, checklist ----------------
def ts(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat Black,84,&H00FFFFFF,&H00FFFFFF,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,9,4,5,60,60,0
Style: Head,Montserrat Black,90,&H002A4417,&H00FFFFFF,&H00E1EEF6,&H00E1EEF6,0,0,0,0,100,100,0,0,3,22,0,8,70,70,0
Style: Count,Anton,300,&H00FFFFFF,&H00FFFFFF,&H001C73E8,&H64000000,0,0,0,0,100,100,2,0,1,16,8,5,0,0,0
Style: Tag,Montserrat Black,60,&H00FFFFFF,&H00FFFFFF,&H002B39C0,&H002B39C0,0,0,0,0,100,100,0,0,3,16,0,7,40,40,0
Style: TagG,Montserrat Black,60,&H00FFFFFF,&H00FFFFFF,&H005B9E2E,&H005B9E2E,0,0,0,0,100,100,0,0,3,16,0,7,40,40,0
Style: Chk,Montserrat Black,58,&H002A4417,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,3,16,0,4,40,40,0
Style: Stk,Anton,96,&H00102030,&H00FFFFFF,&H004DD8FF,&H004DD8FF,0,0,0,0,100,100,1,0,3,26,0,5,0,0,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
CHK = r"{\c&H005B9E2E&\p1}m 0 22 l 10 12 l 22 26 l 48 0 l 58 10 l 22 46{\p0\c&H002A4417&}  "
pop = r"{\fscx60\fscy60\t(0,140,\fscx108\fscy108)\t(140,220,\fscx100\fscy100)}"
ev = []
def E(st, en, style, txt, layer=1): ev.append(f"Dialogue: {layer},{ts(st)},{ts(en)},{style},,0,0,0,,{txt}")
# gancho: headline + contador 0 → 2.000 sincronizado com "2 mil" (3.58 s)
E(0.0, 5.3, "Head", r"{\pos(540,150)" + pop[1:] + "SEU BEBÊ VAI FAZER")
E(4.0, 5.3, "Head", r"{\pos(540,1640)" + pop[1:] + r"REFEIÇÕES ATÉ OS 3 ANOS")
steps = 24
for k in range(steps):
    a = 1.1 + k * (2.5 / steps); b = a + 2.5 / steps
    v = int(round(2000 * (1 - (1 - (k + 1) / steps) ** 2.2), -1)); v = 2000 if k == steps - 1 else v
    E(a, b if k < steps - 1 else 5.3, "Count", r"{\pos(540,960)}" + f"{v:,}".replace(",", "."), 2)
E(5.45, 7.9, "Head", r"{\pos(540,170)" + pop[1:] + "POR QUE ELE TRAVA?")
# bloco ERRADO
E(8.1, 10.55, "Tag", r"{\pos(40,40)" + pop[1:] + "ERRADO: SEMPRE A MESMA PAPINHA")
E(10.6, 14.9, "Tag", r"{\pos(40,40)" + pop[1:] + "ERRADO: TEXTURA ERRADA PRA IDADE")
E(12.9, 14.9, "Tag", r"{\pos(40,1010)" + pop[1:] + "RESULTADO: ENJOA E RECUSA")
E(14.95, 18.45, "Head", r"{\pos(540,170)" + pop[1:] + "O PROBLEMA NÃO É VOCÊ")
# bloco CERTO
E(18.55, 23.9, "TagG", r"{\pos(40,40)" + pop[1:] + "CERTO: O CAMINHO PRONTO")
E(21.25, 23.9, "TagG", r"{\pos(40,1010)" + pop[1:] + "RESULTADO: COME DE TUDO")
for t, txt, y in ((21.3, CHK + "RECEITA", 380), (22.1, CHK + "TEXTURA", 480), (22.85, CHK + "CARDÁPIO", 580)):
    E(t, 23.9, "Chk", r"{\pos(40," + str(y) + ")" + pop[1:] + txt, 3)
# oferta
E(25.85, TOTAL, "Stk", r"{\pos(830,700)\frz-10" + pop[1:] + "+7 BÔNUS", 3)
# legendas palavra a palavra (ocultas no gancho e na oferta, onde há texto grande)
ws = [[s, e, t.strip()] for s, e, t in WORDS]
lines, cur = [], []
for w in ws:
    cur.append(w)
    if len(cur) >= 3 or len(" ".join(x[2] for x in cur)) >= 13 or re.search(r"[.,?!]$", w[2]): lines.append(cur); cur = []
if cur: lines.append(cur)
mg = []
for ln in lines:
    if mg and len(ln) == 1 and not re.search(r"[.?!]$", mg[-1][-1][2]) and len(mg[-1]) <= 3: mg[-1] = mg[-1] + ln
    else: mg.append(ln)
KW = {"2", "mil", "trava", "repete", "errada", "recusar", "você", "pronto", "bebê", "bom", "garfo", "receita", "textura", "cardápio", "300", "7", "30"}
for i, ln in enumerate(mg):
    st = ln[0][0]; en = min(mg[i+1][0][0] if i+1 < len(mg) else ln[-1][1]+0.4, ln[-1][1]+0.5)
    if st < 5.4 or st >= 23.95: continue
    y = 1800 if 18.6 <= st < 21.25 else (960 if (7.9 <= st < 14.9 or 18.5 <= st < 23.95) else 1380)
    parts = [(r"{\c&H004DD8FF&}" + re.sub(r"[.,!]", "", w[2]).upper() + r"{\c&H00FFFFFF&}") if re.sub(r"[^\wÀ-ú]", "", w[2]).lower() in KW else re.sub(r"[.,!]", "", w[2]).upper() for w in ln]
    E(st, en, "Cap", r"{\pos(540," + str(y) + r")\fscx78\fscy78\t(0,110,\fscx104\fscy104)\t(110,170,\fscx100\fscy100)}" + " ".join(parts), 4)
subs = f"{TMP}/c08.ass"; open(subs, "w").write(hdr + "\n".join(ev) + "\n")

# ---------------- card do produto com pop (reaproveita o card do reveal_pop) ----------------
card = os.path.join(os.environ.get("POP_DIR", ""), "anim.mov")
# ---------------- sons: plin no produto, clique nos checks, whoosh nas trocas ----------------
SR = 44100
def wav(name, x):
    p = f"{TMP}/{name}.wav"; w_ = wave.open(p, "w"); w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(SR)
    w_.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()); w_.close(); return p
tt = np.arange(int(1.2*SR))/SR
plin = sum(a*np.sin(2*np.pi*f*tt)*np.exp(-tt*k) for f, a, k in ((1568,.6,5),(2093,.45,6),(3136,.2,9),(4186,.12,12))); plin = plin/np.max(np.abs(plin))*0.7
tc = np.arange(int(0.12*SR))/SR; click = (np.sin(2*np.pi*1200*tc)*np.exp(-tc*60) + 0.4*np.random.uniform(-1,1,len(tc))*np.exp(-tc*120))*0.6
tw = np.arange(int(0.45*SR))/SR; whoosh = np.random.uniform(-1,1,len(tw)) * np.sin(np.pi*tw/0.45)**2 * 0.25
f_plin, f_click, f_wh = wav("plin", plin), wav("click", click), wav("whoosh", whoosh)

fc += f"[{prev}]ass={subs}:fontsdir={os.path.join(ROOT,'tools','fonts')}[vs];"
ai = len(segs); extra = ["-i", AUDIO, "-stream_loop", "-1", "-i", os.path.join(ROOT, "musica/life-of-riley.mp3")]
if os.path.exists(card):
    extra += ["-i", card]; ci = ai + 2
    fc += f"[{ci}:v]setpts=PTS+18.72/TB[cd];[vs][cd]overlay=0:610:eof_action=pass:enable='between(t,18.72,21.2)'[v];"
else:
    fc += "[vs]null[v];"
sfx = [(f_plin, 18.8, 0.9)] + [(f_click, t, 0.8) for t in (21.3, 22.1, 22.85, 25.85)] + [(f_wh, t - 0.15, 0.7) for t in (7.9, 18.5, 23.95)]
base = len(segs) + 2 + (1 if os.path.exists(card) else 0)
for k, (f, t, v) in enumerate(sfx):
    extra += ["-i", f]; fc += f"[{base+k}:a]adelay={int(t*1000)}|{int(t*1000)},volume={v},aformat=channel_layouts=stereo[s{k}];"
fc += (f"[{ai}:a]apad=whole_dur={TOTAL:.3f},aformat=sample_rates=44100:channel_layouts=stereo,asplit[vo][sc];"
       f"[{ai+1}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.2,afade=t=out:st={TOTAL-1.5:.2f}:d=1.5[mu];"
       f"[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[du];"
       f"[vo][du]{''.join(f'[s{k}]' for k in range(len(sfx)))}amix=inputs={2+len(sfx)}:normalize=0,alimiter=limit=0.95[a]")
run(["ffmpeg","-v","error","-y",*inputs,*extra,"-filter_complex",fc,"-map","[v]","-map","[a]","-t",f"{TOTAL:.3f}",
     "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",OUT])
print("ok", OUT, round(dur(OUT), 2))
