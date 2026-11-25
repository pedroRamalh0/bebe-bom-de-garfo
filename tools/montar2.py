"""NAO USAR blur nem hook: o usuario reprovou desfoque e tarja preta. Prefira trechos limpos.
Montador v2: imagem cheia (sem zoom de recorte), faixas de texto antigo desfocadas, leve push-in em cada cena,
transições suaves (xfade), gancho escrito nos primeiros segundos, legendas no terço inferior e tela final animada.

EDL JSON:
{"audio","words","out","hook":"TEXTO DO GANCHO","hook_until":3.2,"fix":{},"keywords":[],
 "clips":[{"at":0.0,"take":"t4","in":42.0,"blur":[[0.62,0.82]],"zoom":[1.0,1.08],"x":0.5,"speed":1.0}
          |{"at":..,"image":"tools/assets/reveal.png","zoom":[1.0,1.06]}],
 "trans":0.22}
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.environ.get("TMPDIR_BBG", "/tmp/bbg_build2"); os.makedirs(TMP, exist_ok=True)
W, H, FPS = 1080, 1920, 30

def run(c): subprocess.run(c, check=True)
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).decode())
def size(p):
    w, h = subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",p]).decode().strip().split(",")[:2]
    return int(w), int(h)

def render(c, d, i):
    out = f"{TMP}/c{i:02d}.mp4"; n = max(2, int(round(d * FPS)))
    z0, z1 = c.get("zoom", [1.0, 1.07])
    zexpr = f"{z0}+({z1}-{z0})*on/{n}"
    xf = c.get("x", 0.5); yf = c.get("y", 0.5)
    zp = f"zoompan=z='{zexpr}':x='(iw-iw/zoom)*{xf}':y='(ih-ih/zoom)*{yf}':d=1:s={W}x{H}:fps={FPS}"
    if "image" in c:
        run(["ffmpeg","-v","error","-y","-loop","1","-framerate",str(FPS),"-i",os.path.join(ROOT,c["image"]),"-frames:v",str(n),
             "-vf",f"scale={W}:{H},{zp},format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","18",out]); return out
    src = os.path.join(ROOT, c["src"]) if "src" in c else os.path.join(ROOT, "takes", c["take"] + ".mp4"); sw, sh = size(src)
    # enquadra em 9:16 sem recorte agressivo
    cw, ch = (sw, int(sw*16/9)) if sw*16/9 <= sh else (int(sh*9/16), sh)
    base = f"crop={cw}:{ch}:{(sw-cw)//2}:{(sh-ch)//2},scale={W}:{H}:flags=lanczos,setsar=1"
    sp = c.get("speed", 1.0)
    if sp != 1.0: base += f",setpts=PTS/{sp}"
    fc = f"[0:v]{base},fps={FPS}[b]"; last = "b"
    for k, (y0, y1) in enumerate(c.get("blur", [])):
        Y0, BH = int(H*y0), int(H*(y1-y0))
        en = f":enable='lt(t,{c['blur_until']})'" if "blur_until" in c else ""
        fc += f";[{last}]split[m{k}][s{k}];[s{k}]crop={W}:{BH}:0:{Y0},boxblur=28:3[bb{k}];[m{k}][bb{k}]overlay=0:{Y0}{en}[o{k}]"; last = f"o{k}"
    fc += f";[{last}]tpad=stop_mode=clone:stop_duration=6,{zp},eq=saturation=1.1:contrast=1.04:brightness=0.01,format=yuv420p[v]"
    run(["ffmpeg","-v","error","-y","-ss",str(c["in"]),"-t",str(d*sp+0.5),"-i",src,"-filter_complex",fc,"-map","[v]",
         "-frames:v",str(n),"-an","-c:v","libx264","-preset","veryfast","-crf","18",out]); return out

def t_ass(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
def clean(w): return re.sub(r"[^\wÀ-úº]", "", w)

def ass(E, words, total):
    kw = {k.lower() for k in E.get("keywords", [])}; fix = {k.lower(): v for k, v in E.get("fix", {}).items()}
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat Black,92,&H00FFFFFF,&H00FFFFFF,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,9,4,5,70,70,0
Style: Hook,Montserrat Black,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H001C73E8,0,0,0,0,100,100,0,0,3,26,0,8,90,90,150

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ws = []
    for s, e, t in words:
        t = t.strip(); k = clean(t).lower()
        if k in fix: t = t.replace(clean(t), fix[k]) if fix[k] else ""
        if t: ws.append([s, e, t])
    lines, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) >= 3 or len(" ".join(x[2] for x in cur)) >= 13 or re.search(r"[.,?!]$", w[2]): lines.append(cur); cur = []
    if cur: lines.append(cur)
    # nunca deixa uma palavra sozinha: junta com a linha anterior se ela não terminou frase
    merged = []
    for ln in lines:
        if merged and len(ln) == 1 and not re.search(r"[.?!]$", merged[-1][-1][2]) and len(merged[-1]) <= 3:
            merged[-1] = merged[-1] + ln
        else:
            merged.append(ln)
    lines = merged
    ev = []
    if E.get("hook"):
        ev.append(f"Dialogue: 2,{t_ass(0)},{t_ass(E.get('hook_until',3.2))},Hook,,0,0,0,,{{\\fad(120,200)}}{E['hook']}")
    for i, ln in enumerate(lines):
        st = ln[0][0]; en = min(lines[i+1][0][0] if i+1 < len(lines) else ln[-1][1]+0.4, ln[-1][1]+0.5)
        if E.get("end_at") and st >= E["end_at"]: continue
        parts = []
        for w in ln:
            tx = re.sub(r"[.,!]", "", w[2]).upper()
            parts.append(r"{\c&H004DD8FF&}" + tx + r"{\c&H00FFFFFF&}" if clean(w[2]).lower() in kw else tx)
        ev.append(f"Dialogue: 0,{t_ass(st)},{t_ass(en)},Cap,,0,0,0,,{{\\pos(540,1380)\\fscx78\\fscy78\\t(0,110,\\fscx104\\fscy104)\\t(110,170,\\fscx100\\fscy100)}}" + " ".join(parts))
    return hdr + "\n".join(ev) + "\n"

def main(p):
    E = json.load(open(p)); audio = os.path.join(ROOT, E["audio"]); voice = dur(audio); total = voice + E.get("tail", 0.0); T = E.get("trans", 0.22)
    cl = E["clips"]; files, durs = [], []
    for i, c in enumerate(cl):
        end = cl[i+1]["at"] if i+1 < len(cl) else total
        d = end - c["at"] + (T if i+1 < len(cl) else 0.0)
        files.append(render(c, d, i)); durs.append(d)
    # encadeia xfade
    inputs = sum([["-i", f] for f in files], []); fc = ""; prev = "0:v"; off = 0.0; ov_inputs = []
    for i in range(1, len(files)):
        off += durs[i-1] - T
        tr = cl[i].get("t", "fade")
        fc += f"[{prev}][{i}:v]xfade=transition={tr}:duration={T}:offset={off:.3f}[x{i}];"; prev = f"x{i}"
    subs = f"{TMP}/subs.ass"; open(subs, "w").write(ass(E, json.load(open(os.path.join(ROOT, E["words"])))["words"], total))
    for k, o in enumerate(E.get("overlays", [])):
        fi = len(files) + 1 + (1 if E.get("music") else 0) + k
        ov_inputs.append(["-loop","1","-i",os.path.join(ROOT,o["image"])])
        a, b2 = o["from"], o["to"]
        fc += (f"[{fi}:v]scale={o.get('w',760)}:-1,format=rgba,fade=t=in:st={a}:d=0.25:alpha=1,fade=t=out:st={b2-0.25}:d=0.25:alpha=1[ov{k}];"
               f"[{prev}][ov{k}]overlay=(W-w)/2:{o.get('y',230)}:enable='between(t,{a},{b2})'[ovo{k}];"); prev = f"ovo{k}"
    fc += f"[{prev}]ass={subs}:fontsdir={os.path.join(ROOT,'tools','fonts')}[v]"
    out = os.path.join(ROOT, E["out"])
    music = E.get("music"); amap = f"[{len(files)}:a]apad=whole_dur={total:.3f}[vp]"; extra = []
    if music:
        extra = ["-stream_loop","-1","-i",os.path.join(ROOT, music)]
        mv = E.get("music_vol", 0.22)
        fc += (f";[{len(files)}:a]apad=whole_dur={total:.3f},aformat=sample_rates=44100:channel_layouts=stereo,asplit[vo][sc];"
               f"[{len(files)+1}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={mv},afade=t=out:st={total-1.8:.2f}:d=1.8[mu];"
               f"[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[duck];[vo][duck]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
        amap = "[a]"
    else:
        fc += ";" + amap; amap = "[vp]"
    run(["ffmpeg","-v","error","-y",*inputs,"-i",audio,*extra,*sum(ov_inputs, []),"-filter_complex",fc,"-map","[v]","-map",amap,"-t",f"{total:.3f}",
         "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",out])
    print("ok", out, round(dur(out), 2))

if __name__ == "__main__": main(sys.argv[1])
