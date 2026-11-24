"""Monta um criativo 9:16 (1080x1920) a partir de uma EDL JSON.

EDL: {"audio": "...wav", "words": "...words.json", "out": "...mp4",
      "clips": [{"at": seg_inicio_no_audio, "take": "t4", "in": seg_no_take, "crop": "top"|"full", "zoom": 1.0}
                 | {"at": ..., "image": "assets/hero-kit.png", "bg": "#F6EEE1"}],
      "fix": {"palavra errada": "certa"}, "keywords": ["..."], "end_cta": "texto"}
Cada clipe dura até o "at" do próximo (o último até o fim do áudio).
Uso: python3 tools/montar.py criativos/c01.json
"""
import json, os, subprocess, sys, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.environ.get("TMPDIR_BBG", "/tmp/bbg_build")
os.makedirs(TMP, exist_ok=True)
W, H, FPS = 1080, 1920, 30

def run(cmd):
    subprocess.run(cmd, check=True)

def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).decode())

def size(path):
    s = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", path]).decode().strip()
    w, h = s.split(",")[:2]
    return int(w), int(h)

def render_clip(c, d, i):
    out = f"{TMP}/clip{i:02d}.mp4"
    if "image" in c:
        img = os.path.join(ROOT, c["image"])
        bg = c.get("bg", "#F6EEE1")
        vf = (f"color=c={bg}:s={W}x{H}:r={FPS}:d={d}[bg];"
              f"[0]scale={int(W*0.95)}:-1,format=rgba[im];"
              f"[bg][im]overlay=(W-w)/2:(H-h)/2-120:shortest=1,"
              f"zoompan=z='1+0.0009*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", img, "-filter_complex", vf, "-t", str(d), "-an",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out])
        return out
    src = os.path.join(ROOT, "takes", c["take"] + ".mp4")
    sw, sh = size(src)
    crop = c.get("crop", "full")
    if crop == "top":   # evita legendas antigas no terço inferior
        ch = int(sh * c.get("h", 0.66)); cw = int(ch * 9 / 16)
        cx = max(0, (sw - cw) // 2 + int(c.get("dx", 0))); cy = int(c.get("dy", 0))
        cr = f"crop={cw}:{ch}:{cx}:{cy},"
    elif crop == "bottom":
        ch = int(sh * 0.70); cw = int(ch * 9 / 16)
        cr = f"crop={cw}:{ch}:{(sw-cw)//2}:{sh-ch},"
    else:
        cw = min(sw, int(sh * 9 / 16)); cr = f"crop={cw}:{int(cw*16/9)}:{(sw-cw)//2}:{(sh-int(cw*16/9))//2},"
    z = c.get("zoom", 1.0)
    vf = f"{cr}scale={int(W*z)}:{int(H*z)}:flags=lanczos,crop={W}:{H},fps={FPS},setsar=1,eq=saturation=1.08:contrast=1.03"
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["in"]), "-i", src, "-t", str(d), "-vf", vf, "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out])
    return out

def ass_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass(words, fix, keywords, total, cta):
    kw = {k.lower() for k in keywords}
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Anton,168,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,3,5,60,60,0
Style: Cta,Montserrat Black,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00178BE8,0,0,0,0,100,100,0,0,3,22,0,2,80,80,170

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # corrige palavras e agrupa em blocos de até 3 palavras / 16 caracteres
    ws = []
    for s, e, t in words:
        t = t.strip()
        key = re.sub(r"[^\wÀ-ú]", "", t).lower()
        if key in fix:
            t = re.sub(re.escape(re.sub(r"[^\wÀ-ú]", "", t)), fix[key], t, flags=re.I)
        if t:
            ws.append([s, e, t])
    lines, cur = [], []
    for w in ws:
        cur.append(w)
        txt = " ".join(x[2] for x in cur)
        if len(cur) >= 3 or len(txt) >= 15 or re.search(r"[.,?!]$", w[2]):
            lines.append(cur); cur = []
    if cur: lines.append(cur)
    ev = []
    for i, ln in enumerate(lines):
        st = ln[0][0]; en = lines[i + 1][0][0] if i + 1 < len(lines) else ln[-1][1] + 0.3
        en = min(en, ln[-1][1] + 0.6)
        parts = []
        for w in ln:
            clean = re.sub(r"[.,!]", "", w[2]).upper()
            if re.sub(r"[^\wÀ-ú]", "", w[2]).lower() in kw:
                parts.append(r"{\c&H00F2E04A&}" + clean + r"{\c&H00FFFFFF&}")
            else:
                parts.append(clean)
        ev.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Cap,,0,0,0,,{{\\pos(540,1230)\\fscx92\\fscy92\\t(0,90,\\fscx100\\fscy100)}}" + " ".join(parts))
    if cta:
        ev.append(f"Dialogue: 1,{ass_time(max(0,total-4.2))},{ass_time(total)},Cta,,0,0,0,,{cta}")
    return head + "\n".join(ev) + "\n"

def main(edl_path):
    E = json.load(open(edl_path))
    audio = os.path.join(ROOT, E["audio"])
    total = dur(audio)
    clips = E["clips"]
    parts = []
    for i, c in enumerate(clips):
        end = clips[i + 1]["at"] if i + 1 < len(clips) else total
        parts.append(render_clip(c, round(end - c["at"], 3), i))
    lst = f"{TMP}/list.txt"
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", f"{TMP}/video.mp4"])
    words = json.load(open(os.path.join(ROOT, E["words"])))["words"]
    ass = f"{TMP}/subs.ass"
    open(ass, "w").write(build_ass(words, {k.lower(): v for k, v in E.get("fix", {}).items()}, E.get("keywords", []), total, E.get("end_cta")))
    out = os.path.join(ROOT, E["out"])
    fonts = os.path.join(ROOT, "tools", "fonts")
    run(["ffmpeg", "-v", "error", "-y", "-i", f"{TMP}/video.mp4", "-i", audio,
         "-vf", f"ass={ass}:fontsdir={fonts}", "-map", "0:v", "-map", "1:a", "-shortest",
         "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", out])
    print("ok", out, round(dur(out), 2), "s")

if __name__ == "__main__":
    main(sys.argv[1])
