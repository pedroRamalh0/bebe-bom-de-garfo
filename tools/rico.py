"""Edição "rica" no estilo do C08/C09: títulos animados, contador, tela dividida, mosaico, faixas por fase,
card do produto com plin, checklist com clique, selos, tela final com preço e efeitos sonoros.
Uso: POP_DIR=/tmp/bbg_pop8 python3 tools/rico.py criativos/s1-rico.json"""
import json, os, re, subprocess, sys, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOVOS = os.path.join(ROOT, "takes", "novos")
W, H, FPS, T = 1080, 1920, 30, 0.2
CREAM = "0xF6EEE1"

def run(c): subprocess.run(c, check=True)
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).decode())
def size(p):
    w, h = subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",p]).decode().strip().split(",")[:2]
    return int(w), int(h)
def src(s):
    if s.startswith(("S1-","S2-","S3-")): return f"{NOVOS}/{s}.mp4"
    return os.path.join(ROOT, s if "/" in s else f"takes/{s}.mp4")

class B:
    def __init__(s, tmp): s.tmp = tmp; s.n = 0; os.makedirs(tmp, exist_ok=True)
    def f(s, p): s.n += 1; return f"{s.tmp}/{p}{s.n:03d}.mp4"
    def clip(s, sname, t_in, d, w, h, yf=0.5, z=(1.0, 1.06)):
        out = s.f("k"); n = max(2, int(round(d * FPS)))
        zp = f"zoompan=z='{z[0]}+({z[1]}-{z[0]})*on/{n}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s={w}x{h}:fps={FPS}"
        if sname.endswith(".png"):
            iw, ih = size(os.path.join(ROOT, sname)); ar = w / h
            cw, ch = (iw, int(iw / ar)) if iw / ar <= ih else (int(ih * ar), ih)
            run(["ffmpeg","-v","error","-y","-loop","1","-framerate",str(FPS),"-i",os.path.join(ROOT,sname),"-frames:v",str(n),"-vf",
                 f"crop={cw}:{ch}:{(iw-cw)//2}:{int((ih-ch)*yf)},scale={w}:{h},{zp},format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","16",out]); return out
        p = src(sname); sw, sh = size(p); ar = w / h
        cw, ch = (sw, int(sw / ar)) if sw / ar <= sh else (int(sh * ar), sh)
        cw -= cw % 2; ch -= ch % 2
        run(["ffmpeg","-v","error","-y","-ss",str(t_in),"-t",str(d+0.6),"-i",p,"-vf",
             f"crop={cw}:{ch}:{(sw-cw)//2}:{int((sh-ch)*yf)},scale={w}:{h}:flags=lanczos,setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration=4,{zp},eq=saturation=1.1:contrast=1.04,format=yuv420p",
             "-frames:v",str(n),"-an","-c:v","libx264","-preset","veryfast","-crf","16",out]); return out
    def seq(s, parts, w, h, total):
        """parts: [[src, in, at_rel(opcional)]] — cortes secos; durações saem dos 'at' relativos."""
        ats = [p[2] if len(p) > 2 else None for p in parts]
        if any(a is None for a in ats): ats = [i * total / len(parts) for i in range(len(parts))]
        fs = []
        for i, p in enumerate(parts):
            d = (ats[i+1] if i + 1 < len(parts) else total) - ats[i]
            fs.append(s.clip(p[0], p[1], d, w, h, p[3] if len(p) > 3 else 0.5))
        lst = f"{s.tmp}/l{s.n}.txt"; open(lst, "w").write("".join(f"file '{f}'\n" for f in fs))
        out = s.f("s"); run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",lst,"-c","copy",out]); return out
    def bands(s, rows, d, starts, bar=CREAM):
        """rows: lista de seq-parts por faixa (de cima pra baixo); starts: quando cada faixa aparece."""
        N = len(rows); g = 8; bh = (H - g * (N - 1)) // N; bh -= bh % 2
        fs = [s.seq(r, W, bh, d) for r in rows]; out = s.f("b")
        fc = f"color=c={bar}:s={W}x{H}:r={FPS}:d={d}[b0];"; last = "b0"
        for k, f in enumerate(fs):
            st = starts[k]; y = k * (bh + g)
            fade = f",fade=t=in:st={st}:d=0.15:alpha=1" if st > 0 else ""
            fc += f"[{k}:v]setpts=PTS+{st}/TB,format=yuva420p{fade}[c{k}];[{last}][c{k}]overlay=0:{y}:eof_action=pass:enable='gte(t,{st})'[b{k+1}];"; last = f"b{k+1}"
        run(["ffmpeg","-v","error","-y",*sum([["-i", f] for f in fs], []),"-filter_complex",fc+f"[{last}]format=yuv420p[v]","-map","[v]",
             "-frames:v",str(int(round(d*FPS))),"-c:v","libx264","-preset","veryfast","-crf","16",out]); return out
    def grid(s, cells, d, starts, cols, rows):
        g = 8; cw = (W - g * (cols + 1)) // cols; chh = (H - g * (rows + 1)) // rows; cw -= cw % 2; chh -= chh % 2
        fs = [s.clip(c[0], c[1], d, cw, chh, 0.5, (1.0, 1.08)) for c in cells]; out = s.f("g")
        fc = f"color=c={CREAM}:s={W}x{H}:r={FPS}:d={d}[b0];"; last = "b0"
        for k, f in enumerate(fs):
            x = g + (k % cols) * (cw + g); y = g + (k // cols) * (chh + g); st = starts[k]
            fade = f",fade=t=in:st={st}:d=0.18:alpha=1" if st > 0 else ""
            fc += f"[{k}:v]setpts=PTS+{st}/TB,format=yuva420p{fade}[c{k}];[{last}][c{k}]overlay={x}:{y}:eof_action=pass:enable='gte(t,{st})'[b{k+1}];"; last = f"b{k+1}"
        run(["ffmpeg","-v","error","-y",*sum([["-i", f] for f in fs], []),"-filter_complex",fc+f"[{last}]format=yuv420p[v]","-map","[v]",
             "-frames:v",str(int(round(d*FPS))),"-c:v","libx264","-preset","veryfast","-crf","16",out]); return out
    def still(s, img, d, z=(1.0, 1.05)):
        return s.clip(img, 0, d, W, H, 0.5, z)

def ts(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
def clean(w): return re.sub(r"[^\wÀ-úº]", "", w).lower()
HDR = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat Black,84,&H00FFFFFF,&H00FFFFFF,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,9,4,5,60,60,0
Style: Head,Montserrat Black,88,&H002A4417,&H00FFFFFF,&H00E1EEF6,&H00E1EEF6,0,0,0,0,100,100,0,0,3,22,0,8,70,70,0
Style: Count,Anton,300,&H00FFFFFF,&H00FFFFFF,&H001C73E8,&H64000000,0,0,0,0,100,100,2,0,1,16,8,5,0,0,0
Style: TagR,Montserrat Black,58,&H00FFFFFF,&H00FFFFFF,&H002B39C0,&H002B39C0,0,0,0,0,100,100,0,0,3,16,0,7,40,40,0
Style: TagG,Montserrat Black,58,&H00FFFFFF,&H00FFFFFF,&H005B9E2E,&H005B9E2E,0,0,0,0,100,100,0,0,3,16,0,7,40,40,0
Style: TagO,Montserrat Black,58,&H00FFFFFF,&H00FFFFFF,&H001C73E8,&H001C73E8,0,0,0,0,100,100,0,0,3,16,0,7,40,40,0
Style: TagB,Montserrat Black,58,&H00FFFFFF,&H00FFFFFF,&H00D16F2F,&H00D16F2F,0,0,0,0,100,100,0,0,3,16,0,7,40,40,0
Style: TagP,Montserrat Black,58,&H00FFFFFF,&H00FFFFFF,&H007A45D6,&H007A45D6,0,0,0,0,100,100,0,0,3,16,0,7,40,40,0
Style: Chk,Montserrat Black,58,&H002A4417,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,3,16,0,4,40,40,0
Style: Stk,Anton,110,&H00102030,&H00FFFFFF,&H004DD8FF,&H004DD8FF,0,0,0,0,100,100,1,0,3,26,0,5,0,0,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
POP = r"\fscx60\fscy60\t(0,140,\fscx108\fscy108)\t(140,220,\fscx100\fscy100)"
CHK = r"{\c&H005B9E2E&\p1}m 0 22 l 10 12 l 22 26 l 48 0 l 58 10 l 22 46{\p0\c&H002A4417&}  "

def build_ass(E, segs_at, total):
    ev = []
    def add(st, en, style, txt, layer=1): ev.append(f"Dialogue: {layer},{ts(st)},{ts(en)},{style},,0,0,0,,{txt}")
    for h in E.get("heads", []): add(h["from"], h["to"], "Head", r"{\pos(540," + str(h.get("y", 150)) + ")" + POP + "}" + h["text"])
    for t in E.get("tags", []): add(t["from"], t["to"], t.get("style", "TagG"), r"{\pos(" + f"{t.get('x',40)},{t.get('y',40)}" + ")" + POP + "}" + t["text"], 2)
    for c in E.get("checks", []): add(c["at"], c["to"], "Chk", r"{\pos(40," + str(c["y"]) + ")" + POP + "}" + CHK + c["text"], 3)
    for s in E.get("stickers", []): add(s["from"], s["to"], "Stk", r"{\pos(" + f"{s.get('x',540)},{s.get('y',820)}" + r")\frz" + str(s.get("rot", -6)) + POP + "}" + s["text"], 3)
    cn = E.get("counter")
    if cn:
        steps = 22; a0, a1 = cn["from"], cn["reach"]
        for k in range(steps):
            a = a0 + k * (a1 - a0) / steps; b = a + (a1 - a0) / steps
            v = int(round(cn["value"] * (1 - (1 - (k + 1) / steps) ** 2.2))); v = cn["value"] if k == steps - 1 else v
            add(a, b if k < steps - 1 else cn["to"], "Count", r"{\pos(540," + str(cn.get("y", 960)) + ")}" + f"{v:,}".replace(",", "."), 2)
    # legendas
    fix = {k.lower(): v for k, v in E.get("fix", {}).items()}; kw = {k.lower() for k in E.get("keywords", [])}
    ws = []
    for s0, e0, t in json.load(open(os.path.join(ROOT, E["words"])))["words"]:
        t = t.strip(); k = clean(t)
        if k in fix: t = fix[k]
        if t: ws.append([s0, e0, t])
    lines, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) >= 3 or len(" ".join(x[2] for x in cur)) >= 13 or re.search(r"[.,?!]$", w[2]): lines.append(cur); cur = []
    if cur: lines.append(cur)
    mg = []
    for ln in lines:
        if mg and len(ln) == 1 and not re.search(r"[.?!]$", mg[-1][-1][2]) and len(mg[-1]) <= 3: mg[-1] += ln
        else: mg.append(ln)
    for i, ln in enumerate(mg):
        st = ln[0][0]; en = min(mg[i+1][0][0] if i + 1 < len(mg) else ln[-1][1] + 0.4, ln[-1][1] + 0.5)
        k = max(j for j, a in enumerate(segs_at) if a <= st + 1e-6); y = E["segments"][k].get("cap", 1380)
        if y is None: continue
        parts = []
        for w in ln:
            tx = re.sub(r"[.,!]", "", w[2]).lstrip("-").upper()
            parts.append(r"{\c&H004DD8FF&}" + tx + r"{\c&H00FFFFFF&}" if clean(w[2]) in kw else tx)
        add(st, en, "Cap", r"{\pos(540," + str(y) + r")\fscx78\fscy78\t(0,110,\fscx104\fscy104)\t(110,170,\fscx100\fscy100)}" + " ".join(parts), 4)
    return HDR + "\n".join(ev) + "\n"

def sfx(tmp):
    SR = 44100
    def wav(name, x):
        p = f"{tmp}/{name}.wav"; w_ = wave.open(p, "w"); w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(SR)
        w_.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()); w_.close(); return p
    tt = np.arange(int(1.2*SR))/SR
    plin = sum(a*np.sin(2*np.pi*f*tt)*np.exp(-tt*k) for f, a, k in ((1568,.6,5),(2093,.45,6),(3136,.2,9),(4186,.12,12))); plin = plin/np.max(np.abs(plin))*0.7
    tc = np.arange(int(0.12*SR))/SR; rng = np.random.default_rng(7)
    click = (np.sin(2*np.pi*1200*tc)*np.exp(-tc*60) + 0.4*rng.uniform(-1,1,len(tc))*np.exp(-tc*120))*0.6
    tw = np.arange(int(0.45*SR))/SR; whoosh = rng.uniform(-1,1,len(tw)) * np.sin(np.pi*tw/0.45)**2 * 0.25
    return wav("plin", plin), wav("click", click), wav("whoosh", whoosh)

def main(p):
    E = json.load(open(p)); tmp = os.environ.get("TMPDIR_BBG", f"/tmp/bbg_rico_{os.path.basename(p)[:-5]}"); b = B(tmp)
    audio = os.path.join(ROOT, E["audio"]); total = dur(audio) + E.get("tail", 1.0)
    S = E["segments"]; at = [s["at"] for s in S]; D = [(at[i+1] if i + 1 < len(S) else total) - at[i] + (T if i + 1 < len(S) else 0) for i in range(len(S))]
    files = []
    for s, d in zip(S, D):
        t = s["type"]
        if t == "cuts": files.append(b.seq(s["clips"], W, H, d))
        elif t == "split":
            a = b.seq(s["top"], W, 950, d); c = b.seq(s["bot"], W, 950, d); out = b.f("sp")
            run(["ffmpeg","-v","error","-y","-i",a,"-i",c,"-filter_complex",
                 f"color=c={s.get('bar','0xF6EEE1')}:s={W}x{H}:r={FPS}:d={d}[bg];[bg][0:v]overlay=0:0:shortest=1[t];[t][1:v]overlay=0:970:shortest=1,format=yuv420p[v]",
                 "-map","[v]","-frames:v",str(int(round(d*FPS))),"-c:v","libx264","-preset","veryfast","-crf","16",out]); files.append(out)
        elif t == "bands": files.append(b.bands(s["rows"], d, s["starts"], s.get("bar", CREAM)))
        elif t == "grid": files.append(b.grid(s["cells"], d, s["starts"], s.get("cols", 3), s.get("rows", 3)))
        elif t == "still": files.append(b.still(s["img"], d))
    inputs = sum([["-i", f] for f in files], []); fc = ""; prev = "0:v"; off = 0.0
    for i in range(1, len(files)):
        off += D[i-1] - T; trn = S[i].get("tr", "fade")
        fc += f"[{prev}][{i}:v]xfade=transition={trn}:duration={T}:offset={off:.3f}[x{i}];"; prev = f"x{i}"
    subs = f"{tmp}/s.ass"; open(subs, "w").write(build_ass(E, at, total))
    fc += f"[{prev}]ass={subs}:fontsdir={os.path.join(ROOT,'tools','fonts')}[vs];"
    ai = len(files); extra = ["-i", audio, "-stream_loop", "-1", "-i", os.path.join(ROOT, E.get("music", "musica/life-of-riley.mp3"))]
    card = os.path.join(os.environ.get("POP_DIR", "/tmp/bbg_pop8"), "anim.mov"); pa = E.get("pop_at")
    if pa is not None and os.path.exists(card):
        extra += ["-i", card]; ci = ai + 2
        fc += f"[{ci}:v]setpts=PTS+{pa}/TB[cd];[vs][cd]overlay=0:{E.get('pop_y',610)}:eof_action=pass:enable='between(t,{pa},{pa+2.45})'[v];"
    else: fc += "[vs]null[v];"
    f_plin, f_click, f_wh = sfx(tmp)
    clicks = [c["at"] for c in E.get("checks", [])] + [s["from"] for s in E.get("stickers", [])]
    sounds = ([(f_plin, pa + 0.08, 0.9)] if pa is not None else []) + [(f_click, t, 0.8) for t in clicks] + [(f_wh, a - 0.15, 0.6) for a in at[1:]]
    base = ai + 2 + (1 if pa is not None and os.path.exists(card) else 0)
    for k, (f, t, v) in enumerate(sounds):
        extra += ["-i", f]; fc += f"[{base+k}:a]adelay={int(max(t,0)*1000)}|{int(max(t,0)*1000)},volume={v},aformat=channel_layouts=stereo[s{k}];"
    fc += (f"[{ai}:a]apad=whole_dur={total:.3f},aformat=sample_rates=44100:channel_layouts=stereo,asplit[vo][sc];"
           f"[{ai+1}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={E.get('music_vol',0.2)},afade=t=out:st={total-1.5:.2f}:d=1.5[mu];"
           f"[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[du];"
           f"[vo][du]{''.join(f'[s{k}]' for k in range(len(sounds)))}amix=inputs={2+len(sounds)}:normalize=0,alimiter=limit=0.95[a]")
    out = os.path.join(ROOT, E["out"])
    run(["ffmpeg","-v","error","-y",*inputs,*extra,"-filter_complex",fc,"-map","[v]","-map","[a]","-t",f"{total:.3f}",
         "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",out])
    print("ok", out, round(dur(out), 2))

if __name__ == "__main__": main(sys.argv[1])
