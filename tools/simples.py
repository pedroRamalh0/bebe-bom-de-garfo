"""Formato "simples bem feito": cortes secos rápidos de receitas, legenda de 2-3 palavras (Anton) e trilha.
Sem produto na tela. Uso: python3 tools/simples.py criativos/s1.json
EDL: {"audio","words","out","tail":0.6,"keywords":[...],"fix":{},"music":"musica/...","music_vol":0.18,
      "clips":[["S1-03",0.0,0.0], [t_inicio, "fonte", t_in, zoom?], ...]}  fonte = código da pasta novos/ ou caminho."""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOVOS = os.environ.get("NOVOS", os.path.join(ROOT, "takes", "novos"))
TMP = os.environ.get("TMPDIR_BBG", "/tmp/bbg_simples"); os.makedirs(TMP, exist_ok=True)
W, H, FPS = 1080, 1920, 30

def run(c): subprocess.run(c, check=True)
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).decode())
def size(p):
    w, h = subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",p]).decode().strip().split(",")[:2]
    return int(w), int(h)
def src(s):
    if s.startswith(("S1-","S2-","S3-")): return f"{NOVOS}/{s}.mp4"
    return os.path.join(ROOT, s if "/" in s else f"takes/{s}.mp4")

def clip(i, s, t_in, d, z=1.05, yf=0.5):
    out = f"{TMP}/c{i:03d}.mp4"; p = src(s); sw, sh = size(p); n = max(2, int(round(d * FPS)))
    cw, ch = (sw, int(sw * 16 / 9)) if sw * 16 / 9 <= sh else (int(sh * 9 / 16), sh)
    cw -= cw % 2; ch -= ch % 2
    zp = f"zoompan=z='1+({z}-1)*on/{n}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*{yf}':d=1:s={W}x{H}:fps={FPS}"
    run(["ffmpeg","-v","error","-y","-ss",str(t_in),"-t",str(d+0.6),"-i",p,"-vf",
         f"crop={cw}:{ch}:{(sw-cw)//2}:{int((sh-ch)*yf)},scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration=3,{zp},eq=saturation=1.1:contrast=1.04,format=yuv420p",
         "-frames:v",str(n),"-an","-c:v","libx264","-preset","veryfast","-crf","16",out]); return out

def ts(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
def clean(w): return re.sub(r"[^\wÀ-úº]", "", w).lower()

def ass(E, words, total):
    kw = {k.lower() for k in E.get("keywords", [])}; fix = {k.lower(): v for k, v in E.get("fix", {}).items()}
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Anton,120,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,8,5,5,50,50,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ws = []
    for s, e, t in words:
        t = t.strip(); k = clean(t)
        if k in fix: t = fix[k]
        if t: ws.append([s, e, t])
    lines, cur = [], []
    for w in ws:
        cur.append(w)
        txt = " ".join(x[2] for x in cur)
        if len(cur) >= 3 or len(txt) >= 14 or re.search(r"[.,?!]$", w[2]): lines.append(cur); cur = []
    if cur: lines.append(cur)
    mg = []
    for ln in lines:
        if mg and len(ln) == 1 and not re.search(r"[.?!]$", mg[-1][-1][2]) and len(mg[-1]) <= 2: mg[-1] += ln
        else: mg.append(ln)
    ev = []
    for i, ln in enumerate(mg):
        st = ln[0][0]; en = min(mg[i+1][0][0] if i + 1 < len(mg) else total, ln[-1][1] + 0.35)
        parts = []
        for w in ln:
            tx = re.sub(r"[.,!]", "", w[2]).lstrip("-").upper()
            parts.append(r"{\c&H004DD8FF&}" + tx + r"{\c&H00FFFFFF&}" if clean(w[2]) in kw else tx)
        ev.append(f"Dialogue: 0,{ts(st)},{ts(en)},Cap,,0,0,0,,{{\\pos(540,{E.get('cap_y',1330)})\\fscx82\\fscy82\\t(0,90,\\fscx106\\fscy106)\\t(90,150,\\fscx100\\fscy100)}}" + " ".join(parts))
    return hdr + "\n".join(ev) + "\n"

def main(p):
    E = json.load(open(p)); audio = os.path.join(ROOT, E["audio"]); total = dur(audio) + E.get("tail", 0.6)
    cl = E["clips"]; files = []; T = E.get("trans", 0.0); durs = []
    for i, c in enumerate(cl):
        end = cl[i+1][0] if i + 1 < len(cl) else total
        d = end - c[0] + (T if i + 1 < len(cl) else 0.0); durs.append(d)
        files.append(clip(i, c[1], c[2], d, *(c[3:] if len(c) > 3 else [])))
    cat = f"{TMP}/cat.mp4"
    if T > 0:  # transição suave (fade curto) entre as cenas
        fc = ""; prev = "0:v"; off = 0.0
        for i in range(1, len(files)):
            off += durs[i-1] - T; fc += f"[{prev}][{i}:v]xfade=transition=fade:duration={T}:offset={off:.3f}[x{i}];"; prev = f"x{i}"
        run(["ffmpeg","-v","error","-y",*sum([["-i", f] for f in files], []),"-filter_complex",fc.rstrip(";"),"-map",f"[{prev}]",
             "-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",cat])
    else:
        lst = f"{TMP}/list.txt"; open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
        run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",lst,"-c","copy",cat])
    subs = f"{TMP}/subs.ass"; open(subs, "w").write(ass(E, json.load(open(os.path.join(ROOT, E["words"])))["words"], total))
    mv = E.get("music_vol", 0.18)
    fc = (f"[0:v]ass={subs}:fontsdir={os.path.join(ROOT,'tools','fonts')}[v];"
          f"[1:a]apad=whole_dur={total:.3f},aformat=sample_rates=44100:channel_layouts=stereo,asplit[vo][sc];"
          f"[2:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={mv},afade=t=out:st={total-1.2:.2f}:d=1.2[mu];"
          f"[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[du];[vo][du]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
    out = os.path.join(ROOT, E["out"])
    run(["ffmpeg","-v","error","-y","-i",cat,"-i",audio,"-stream_loop","-1","-i",os.path.join(ROOT,E.get("music","musica/life-of-riley.mp3")),
         "-filter_complex",fc,"-map","[v]","-map","[a]","-t",f"{total:.3f}","-c:v","libx264","-preset","medium","-crf","19",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",out])
    print("ok", out, round(dur(out), 2), len(cl), "cortes")

if __name__ == "__main__": main(sys.argv[1])
