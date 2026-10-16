#!/usr/bin/env python3
"""Ludogic RETRO reel engine (style v2, user decision 2026-10-16): pixel-art guide, split-screen
"slides vs game" comparisons, chiptune audio. Same spec / outputs / gates as engine/reel.py.

    python3 engine/retro.py build specs/<ID>.json out/<ID> [--preview]

Everything is drawn on a 270x480 pixel canvas and scaled x4 (nearest) to 1080x1920, so every element
is real pixel art. Palette = brand navy + coral, plus a game blue and coin gold.
Layout (canvas px): HUD y 8-30 | headline y 36-66 | panel A (SLIDES) y 72-176 | VS | panel B (GAME) y 190-296 |
dialog box with the guide's portrait (= captions) y 300-354. Safe zone x 22-212 / y 65-355 of the canvas.

Scene types: split (a.kind: slide|policy|wait|exam, b.kind: title|choice|feedback|boss), merge, end.
"""
import sys, os, json, math, time, subprocess, shutil, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel  # voice + timeline + gates are shared with the classic engine

ENGINE_VERSION = "retro-2.0.0"
W, H, K = 270, 480, 4
WD, HT, FPS, SR = W * K, H * K, 30, 48000
FONTS = os.path.expanduser("~/.cache/ludogic-reels/fonts")
FONT_URLS = {"PressStart2P-Regular.ttf": "pressstart2p/PressStart2P-Regular.ttf",
             "PixelifySans.ttf": "pixelifysans/PixelifySans%5Bwght%5D.ttf",
             "Silkscreen-Regular.ttf": "silkscreen/Silkscreen-Regular.ttf"}

def ensure_fonts():
    os.makedirs(FONTS, exist_ok=True)
    for f, u in FONT_URLS.items():
        p = os.path.join(FONTS, f)
        if not os.path.exists(p) or os.path.getsize(p) < 10000:
            subprocess.run(["curl", "-sSfL", "-o", p, "https://raw.githubusercontent.com/google/fonts/main/ofl/" + u], check=True)

PAL = {"bg": "#070B1A", "bg2": "#0E1633", "navy": "#1B2756", "navy2": "#2A3A7A", "line": "#26305A",
       "coral": "#FF5A4E", "coral2": "#FF8A7A", "coral3": "#B8322B", "blue": "#3D6BFF", "blue2": "#2A47B8",
       "sky": "#7FB2FF", "gold": "#FFC24D", "gold2": "#C98A1E", "white": "#F4F6FB", "muted": "#8A93B3",
       "dark": "#0B0F24", "skin": "#F5C9A6", "skin2": "#D99A7A", "green": "#3DDC84",
       "g0": "#D5D8DE", "g1": "#B4B8C2", "g2": "#8D929E", "g3": "#5E6370", "g4": "#3B3F49"}
def rgb(c):
    c = PAL.get(c, c).lstrip("#"); return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

# ---------------------------------------------------------------- sprites (original pixel art)
GIRL = [
    "....KKKKKKKK....",
    "...KHHHHHHHHK...",
    "..KHHHHHHHHHHK..",
    ".KHHHHHHHHHHHHK.",
    ".KHhSSSSSSSShHK.",
    ".KHSSSSSSSSSSHK.",
    ".KHSEESSSSEESHK.",
    ".KHSEESSSSEESHK.",
    ".KHSRSSSSSSRSHK.",
    ".KHHSSSMMSSSHHK.",
    ".KHKKSSSSSSKKHK.",
    "....KBBWWBBK....",
    "...KBBBBBBBBK...",
    "..KBKBBBBBBKBK..",
    "..KBKBBBBBBKBK..",
    "..KSKbbbbbbKSK..",
    "...K.KPPPPK.K...",
    ".....KPPPPK.....",
    ".....KPKKPK.....",
    ".....KPK.KPK....",
    "....KWWK.KWWK...",
    "....KKKK.KKKK...",
]
SPR_PAL = {"K": "dark", "H": "coral", "h": "coral3", "S": "skin", "s": "skin2", "E": "dark", "R": "coral2",
           "M": "coral3", "W": "white", "B": "blue", "b": "blue2", "P": "navy", "O": "white"}

def girl_rows(pose="idle", blink=False, mouth=0, walk=0):
    g = [r.ljust(16, ".") for r in GIRL]
    if blink: g[6] = ".KHSSSSSSSSSSHK."; g[7] = ".KHSKKSSSSKKSHK."
    if mouth == 1: g[9] = ".KHHSSSKKSSSHHK."
    if mouth == 2: g[9] = ".KHHSSKKKKSSHHK."; g[10] = ".KHKKSSMMSSKKHK."
    if pose == "cheer":            # both arms up
        g[11] = ".KSKBBWWBBKSK..."; g[12] = ".KBKBBBBBBKBK..."; g[13] = "..KBBBBBBBBK...."
        g[14] = "...KBBBBBBK....."; g[15] = "...KbbbbbbK....."
        g[11] = "SKK.KBWWBK.KKS.."[:16]
        g[11] = ".SK.KBWWBK.KS..."; g[12] = ".BKKBBBBBBKKB..."
    if pose == "wave":             # right arm up
        g[11] = "....KBBWWBBK.KS."; g[12] = "...KBBBBBBBBKKB."; g[13] = "..KBKBBBBBBKK..."
        g[14] = "..KBKBBBBBBK...."; g[15] = "..KSKbbbbbbK...."
    if pose == "attack":           # right arm forward
        g[13] = "..KBKBBBBBBKBBBS"; g[14] = "..KBKBBBBBBKKKKK"; g[15] = "..KSKbbbbbbK...."
    if pose == "hurt":
        g[6] = ".KHSKSKSSKSKSHK."; g[7] = ".KHSSKSSSSKSSHK."; g[9] = ".KHHSSKKKKSSHHK."
    if walk == 1: g[19] = "....KPK..KPK...."; g[20] = "...KWWK..KWWK..."; g[21] = "...KKKK..KKKK..."
    if walk == 2: g[19] = "......KPKPK....."; g[20] = ".....KWWKWWK...."; g[21] = ".....KKKKKKK...."
    return g

def blit(im, rows, x, y, s=1, pal=None, flip=False, alpha=1.0, remap=None, only=None):
    """draw an ASCII sprite with pixel size s at canvas (x, y)."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    pal = pal or SPR_PAL
    for j, r in enumerate(rows if only is None else rows[:only]):
        rr = r[::-1] if flip else r
        for i, ch in enumerate(rr):
            if ch == ".": continue
            key = pal.get(ch, "dark")
            if remap: key = remap.get(key, key)
            col = rgb(key)
            if alpha < 1:
                bgc = im.getpixel((min(W - 1, max(0, int(x + i * s))), min(H - 1, max(0, int(y + j * s)))))
                col = tuple(int(bgc[k] + (col[k] - bgc[k]) * alpha) for k in range(3))
            d.rectangle([int(x + i * s), int(y + j * s), int(x + i * s + s - 1), int(y + j * s + s - 1)], fill=col)

HEART = [".KK.KK.", "KRRKRRK", "KRRRRRK", ".KRRRK.", "..KRK..", "...K..."]
HEART_E = [".KK.KK.", "KggKggK", "KgggggK", ".KgggK.", "..KgK..", "...K..."]
COIN = ["..KKK..", ".KGGGK.", "KGGWGGK", "KGGWGGK", "KGGWGGK", ".KGGGK.", "..KKK.."]
STAR = ["...K...", "..KGK..", "KKKGKKK", ".KGGGK.", "..KGK..", ".KK.KK."]
FLOPPY = ["KKKKKKKKKKK.", "KBBWWWWWBBKK", "KBBWWWWWBBBK", "KBBWWWWWBBBK", "KBBBBBBBBBBK", "KBBBBBBBBBBK",
          "KBWWWWWWWWBK", "KBWKKKKKKWBK", "KBWWWWWWWWBK", "KBWKKKKKKWBK", "KBWWWWWWWWBK", "KKKKKKKKKKKK"]
BOLT = ["....KK", "...KGK", "..KGK.", ".KGGGK", "KKKGK.", "..KGK.", ".KGK..", ".KK..."]
QBOX = ["KKKKKKKKK", "KCCCCCCCK", "KCCKKKCCK", "KCCCCKCCK", "KCCCKKCCK", "KCCCKCCCK", "KCCCCCCCK", "KCCCKCCCK", "KKKKKKKKK"]
SWORD = ["......KK", ".....KWK", "....KWK.", "...KWK..", "K.KWK...", "KKWK....", ".KK.....", "K.KK...."]
ICON_PAL = {"K": "dark", "R": "coral", "g": "g3", "G": "gold", "W": "white", "B": "blue", "C": "coral"}

# ---------------------------------------------------------------- helpers
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def eo(x): return 1 - (1 - x) ** 3
def back(x, s=1.7): x -= 1; return x * x * ((s + 1) * x + s) + 1
def step(v, q=1): return int(round(v / q) * q)

def at(tl, i, word, frac=0.0):
    """time when `word` is spoken inside line i (char-proportional estimate)."""
    L = tl["lines"][i]; s = L["say"]; k = s.lower().find(word.lower())
    k = max(0, k) + frac * len(word)
    return L["start"] + (L["end"] - L["start"]) * k / max(1, len(s))

# ---------------------------------------------------------------- scene plans (shared by visuals and audio)
def plan_scenes(spec, tl):
    S = {l["i"]: l["start"] for l in tl["lines"]}; E = {l["i"]: l["end"] for l in tl["lines"]}
    sc = spec["scenes"]; out = []
    for k, s in enumerate(sc):
        t0 = S[s["line"]] if k else 0.0
        t1 = S[sc[k + 1]["line"]] if k + 1 < len(sc) else tl["total"] + 1
        ev = []   # (time, sfx, extra)
        if s["type"] == "split":
            a, b = s.get("a", {}), s.get("b", {})
            if a.get("kind") == "slide":
                for j in range(3): ev.append((t0 + .25 + j * .7, "click", None))
            if a.get("kind") == "policy":
                for j in range(4): ev.append((t0 + .4 + j * .9, "click", None))
            if b.get("kind") == "title":
                ev.append((S[b["start_line"]] + .05 if "start_line" in b else t0 + 1, "start", None))
                for j in range(3): ev.append(((S[b["start_line"]] if "start_line" in b else t0) + .6 + j * .28, "coin", j))
            if b.get("kind") == "choice":
                ta = at(tl, b["ask_line"], b.get("ask_word", "Ask"))
                ev.append((ta, "pop", "ask"))
                tc = at(tl, b["ask_line"], b.get("choice_word", "What"))
                ev.append((tc, "pop", "choices"))
                ev.append((tc + .45, "blip", "down")); ev.append((tc + .85, "blip", "up")); ev.append((tc + 1.25, "blip", "down"))
                ev.append((min(t1 - .35, tc + 1.7), "select", "pick"))
            if b.get("kind") == "feedback":
                tw = at(tl, b["line"], b.get("wrong_word", "Wrong"))
                tr = at(tl, b["line"], b.get("right_word", "Right"))
                ev.append((tw + .15, "select", "wrong")); ev.append((tw + .35, "hurt", "wrong"))
                ev.append((tr - .35, "blip", "down")); ev.append((tr + .05, "select", "right"))
                ev.append((tr + .25, "power", "xp"))
                for j in range(5): ev.append((tr + .3 + j * .07, "coin", j))
            if b.get("kind") == "boss":
                ev.append((t0 + .35, "alarm", "intro"))
                L = b["line"]
                hits = [at(tl, L, w) for w in b.get("hit_words", ["hit"])]
                for th in hits: ev.append((th, "hit", "hit"))
                tm = at(tl, L, b.get("miss_word", "miss"))
                ev.append((tm + .1, "whiff", "miss")); ev.append((at(tl, L, b.get("back_word", "back")) - .1, "hurt", "bosshit"))
                ev.append((min(t1 - .25, E[L] + .05), "hit", "final")); ev.append((min(t1 - .2, E[L] + .15), "explode", "ko"))
        elif s["type"] == "merge":
            ev.append((t0 + .1, "tvoff", None))
            for j, w in enumerate(s.get("item_words", [])): ev.append((at(tl, s["line"], w), "power", j))
            if s.get("cheer_word"): ev.append((at(tl, s["line"], s["cheer_word"]), "jump", None))
        elif s["type"] == "end":
            ev.append((t0 + .05, "jingle", None))
            ev.append((at(tl, s["line"], s.get("save_word", "Save")), "save", None))
        out.append({"sc": s, "t0": t0, "t1": t1, "ev": sorted(ev, key=lambda e: e[0])})
    return out

# ---------------------------------------------------------------- audio (chiptune + 8-bit sfx + voice)
def make_audio(spec, tl, plans, out):
    import soundfile as sf
    from scipy.signal import resample_poly, butter, sosfilt
    rng = np.random.default_rng(spec.get("seed", 11))
    TOTAL = tl["total"]; N = int(TOTAL * SR)
    def buf(): return np.zeros(N)
    def add(dst, sig, t, g=1.):
        i = int(t * SR)
        if i >= N or i < 0: return
        j = min(N, i + len(sig)); dst[i:j] += g * sig[: j - i]
    def env(n, a=.004, d=.15, c=3.):
        tt = np.arange(n) / SR; return np.minimum(1, tt / max(a, 1e-4)) * np.exp(-c * tt / max(d, 1e-4))
    def filt(x, kind, fc, o=2): return sosfilt(butter(o, fc, kind, fs=SR, output="sos"), x)
    def sq(f, dur, duty=.5):
        tt = np.arange(int(dur * SR)) / SR
        ph = np.cumsum(f(tt) if callable(f) else np.full(len(tt), f)) / SR
        return np.where((ph % 1) < duty, 1., -1.)
    def tri(f, dur):
        tt = np.arange(int(dur * SR)) / SR; return 2 * np.abs(2 * ((f * tt) % 1) - 1) - 1
    def noise(dur): return rng.choice([-1., 1.], int(dur * SR)) * 1.0
    mtof = lambda m: 440 * 2 ** ((m - 69) / 12)

    mu = spec.get("music", {})
    BPM = mu.get("bpm", 132); beat = 60 / BPM
    prog_ = mu.get("progression", [[48, [60, 64, 67]], [43, [59, 62, 67]], [45, [60, 64, 69]], [41, [60, 65, 69]]])
    S = {l["i"]: l["start"] for l in tl["lines"]}
    t_full = S.get(mu.get("drop_line", 2), 6.0) - .05
    t_end = plans[-1]["t0"]
    music = buf()
    for b in range(int(TOTAL / (4 * beat)) + 2):
        t0 = b * 4 * beat; root, ch = prog_[b % len(prog_)]
        if t0 >= t_end - .01: break
        full = t0 >= t_full - 1e-3
        for e in range(8):                                   # triangle bass, 8ths
            n = root + (12 if e % 2 else 0)
            add(music, tri(mtof(n), beat / 2 * .9) * env(int(beat / 2 * .9 * SR), .002, .4, 1.5), t0 + e * beat / 2, .30)
        for s16 in range(16):                                # 25% square arpeggio, 16ths
            if not full and s16 % 2: continue
            n = ch[s16 % 3] + (12 if (s16 // 4) % 2 and full else 0)
            add(music, sq(mtof(n), beat / 4 * .8, .25) * env(int(beat / 4 * .8 * SR), .001, .06, 2), t0 + s16 * beat / 4, .045)
        for k in range(4):                                   # drums
            tb = t0 + k * beat
            if full or k % 2 == 0:
                add(music, sq(lambda tt: 160 * np.exp(-tt * 25) + 40, .12) * env(int(.12 * SR), .001, .08, 2), tb, .22)
            add(music, filt(noise(.03), "high", 6000) * env(int(.03 * SR), .0005, .015, 3), tb + beat / 2, .07 if full else .04)
            if full and k in (1, 3): add(music, filt(noise(.12), "band", [1200, 5000]) * env(int(.12 * SR), .001, .05, 2.5), tb, .14)
    fo = int(.25 * SR); i_end = int(t_end * SR)
    if 0 < i_end < N: music[max(0, i_end - fo):i_end] *= np.linspace(1, 0, min(fo, i_end)); music[i_end:] = 0

    sfx = buf()
    def arp(t, notes, step_=.05, dur=.07, g=.10, duty=.5):
        for k, n in enumerate(notes): add(sfx, sq(mtof(n), dur, duty) * env(int(dur * SR), .001, dur * .7, 2), t + k * step_, g)
    SFX = {
        "click": lambda t: add(sfx, filt(noise(.015), "band", [1500, 4000]) * env(int(.015 * SR), .0005, .006, 3), t, .25),
        "blip": lambda t: arp(t, [84], dur=.04, g=.08),
        "select": lambda t: arp(t, [79, 91], .04, .05, .10),
        "pop": lambda t: arp(t, [72, 79], .03, .05, .08),
        "coin": lambda t: (arp(t, [83], dur=.05, g=.07), arp(t + .05, [88], dur=.18, g=.07)),
        "start": lambda t: arp(t, [72, 76, 79, 84, 88], .05, .09, .10),
        "hurt": lambda t: (add(sfx, sq(lambda tt: 600 * np.exp(-tt * 6) + 80, .35) * env(int(.35 * SR), .001, .3, 1.5), t, .12),
                           add(sfx, filt(noise(.2), "low", 3000) * env(int(.2 * SR), .001, .08, 2), t, .12)),
        "hit": lambda t: (add(sfx, filt(noise(.18), "low", 5000) * env(int(.18 * SR), .0005, .06, 2), t, .30),
                          add(sfx, sq(lambda tt: 220 * np.exp(-tt * 20) + 50, .15) * env(int(.15 * SR), .001, .1, 2), t, .20)),
        "whiff": lambda t: add(sfx, filt(noise(.2), "band", [2000, 6000]) * np.sin(np.linspace(0, np.pi, int(.2 * SR))), t, .10),
        "explode": lambda t: add(sfx, filt(noise(1.0), "low", 1800) * env(int(1.0 * SR), .001, .6, 2), t, .35),
        "power": lambda t: arp(t, [67, 71, 74, 79, 83, 86], .035, .06, .08),
        "alarm": lambda t: [arp(t + k * .22, [76, 70], .1, .1, .07) for k in range(3)],
        "tvoff": lambda t: add(sfx, np.sin(2 * np.pi * np.cumsum(np.linspace(1800, 60, int(.35 * SR))) / SR) * np.linspace(1, 0, int(.35 * SR)), t, .14),
        "jump": lambda t: add(sfx, sq(lambda tt: 300 + 900 * tt / .18, .18) * env(int(.18 * SR), .001, .15, 1.5), t, .08),
        "jingle": lambda t: (arp(t, [72, 76, 79, 84, 79, 84, 88], .09, .11, .11), arp(t + .7, [60, 64, 67, 72], 0, .7, .05)),
        "save": lambda t: arp(t, [84, 88, 91, 96], .06, .08, .09),
    }
    for p in plans:
        if p["t0"] > 0: add(sfx, filt(noise(.12), "high", 3000) * np.linspace(1, 0, int(.12 * SR)) ** 2, p["t0"] - .06, .06)
        for (t, name, _) in p["ev"]: SFX[name](t)
    # ending tune (soft) under the end card
    te = plans[-1]["t0"] + 1.2
    for k, n in enumerate([72, 76, 79, 84, 79, 76, 72, 76, 79, 84, 88, 84]):
        add(music, sq(mtof(n), .2, .25) * env(int(.2 * SR), .002, .15, 2), te + k * beat / 2, .035)
        if k % 4 == 0: add(music, tri(mtof(n - 24), beat * 2) * env(int(beat * 2 * SR), .002, .9, 1.5), te + k * beat / 2, .25)

    vo = buf()
    for l in tl["lines"]:
        a, sr = sf.read(f"{out}/vo/l{l['i']:02d}.wav")
        a = filt(resample_poly(a, SR, sr), "high", 80)
        add(vo, a / (np.max(np.abs(a)) + 1e-9), l["start"], .75)
    venv = np.convolve(np.abs(vo), np.ones(int(.08 * SR)) / int(.08 * SR), mode="same")
    duck = 1 - .6 * np.clip(venv / (venv.max() * .25), 0, 1)
    duck = np.convolve(duck, np.ones(int(.15 * SR)) / int(.15 * SR), mode="same")
    md = music * duck * mu.get("level", .8); sx = .8 * sfx * (1 - .35 * (1 - duck))
    d = int(.010 * SR)
    L = vo + md + sx; R = vo + np.concatenate([np.zeros(d), md[:-d]]) + sx
    st = np.stack([L, R], 1); st /= np.max(np.abs(st)) / .89
    sf.write(f"{out}/mix_raw.wav", st.astype(np.float32), SR)
    sp = np.zeros(N, bool)
    for l in tl["lines"]: sp[int(l["start"] * SR):int(l["end"] * SR)] = True
    def rms(x): return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", f"{out}/mix_raw.wav", "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-ar", str(SR), f"{out}/mix.wav"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"output_i\"[^{}]*\}", r.stderr, re.S); ln = json.loads(m.group(0)) if m else {}
    # voice envelope per video frame -> guide's mouth animation
    fr = int(SR / FPS); nfr = N // fr
    mouth = [float(np.sqrt(np.mean(vo[k * fr:(k + 1) * fr] ** 2))) for k in range(nfr)]
    mx = max(mouth) or 1; json.dump([round(m_ / mx, 3) for m_ in mouth], open(f"{out}/mouth.json", "w"))
    return {"voice_minus_bed_db": round(rms(vo[sp]) - rms((md + sx)[sp]), 1), "lufs": float(ln.get("output_i", "nan")),
            "true_peak_db": float(ln.get("output_tp", "nan")), "music_bpm": BPM, "music_drop_line": mu.get("drop_line", 2)}

# ---------------------------------------------------------------- visuals
def make_renderer(spec, tl, plans, out):
    from PIL import Image, ImageDraw, ImageFont
    F8 = ImageFont.truetype(f"{FONTS}/PressStart2P-Regular.ttf", 8)
    F16 = ImageFont.truetype(f"{FONTS}/PressStart2P-Regular.ttf", 16)
    FD = ImageFont.truetype(f"{FONTS}/PixelifySans.ttf", 10)
    FS = ImageFont.truetype(f"{FONTS}/Silkscreen-Regular.ttf", 8)
    mouth = json.load(open(f"{out}/mouth.json")) if os.path.exists(f"{out}/mouth.json") else []
    lines = tl["lines"]; LAST = len(lines) - 1; TOTAL = tl["total"]
    rng = np.random.default_rng(3)
    STARS = [(int(rng.integers(0, W)), int(rng.integers(0, H)), float(rng.random())) for _ in range(70)]
    ACC = set(w.upper().strip(".,:!?") for w in spec.get("accent_words", []))
    events = [e for p in plans for e in p["ev"]]

    def ev_time(name, tag=None, after=-1e9):
        for (t, n, x) in events:
            if n == name and (tag is None or x == tag) and t >= after: return t
        return None
    # global game state (hearts / xp) derived from events
    def hearts(t):
        h = 3
        for (te, n, x) in events:
            if n == "hurt" and t >= te: h -= 1
        if t >= plans[-1]["t0"]: h = 3
        return max(0, h)
    def xp(t):
        v = 0
        for (te, n, x) in events:
            if t < te: continue
            if n == "select" and x == "pick": v += 10
            if n == "power" and x == "xp": v += 10
            if n == "hit": v += 25 if x == "final" else 10
            if n == "jingle": v += 50
        return v

    def T(d, txt, x, y, f=F8, col="white", align="l", shadow=True, acc=None):
        w = d.textlength(txt, font=f)
        if align == "c": x = x - w / 2
        if align == "r": x = x - w
        x = int(round(x)); y = int(round(y))
        if acc is None:
            if shadow: d.text((x + 1, y + 1), txt, font=f, fill=rgb("dark"))
            d.text((x, y), txt, font=f, fill=rgb(col)); return w
        cx = x                                               # per-word colouring
        for wd in txt.split(" "):
            c = acc if wd.upper().strip(".,:!?") in ACC else col
            if shadow: d.text((cx + 1, y + 1), wd, font=f, fill=rgb("dark"))
            d.text((cx, y), wd, font=f, fill=rgb(c)); cx += d.textlength(wd + " ", font=f)
        return w
    def box(d, x0, y0, x1, y1, fill, border="dark", hi=None):
        d.rectangle([x0, y0, x1, y1], fill=rgb(fill), outline=rgb(border))
        if hi: d.line([x0 + 1, y0 + 1, x1 - 1, y0 + 1], fill=rgb(hi)); d.line([x0 + 1, y0 + 1, x0 + 1, y1 - 1], fill=rgb(hi))
    def wrap(d, txt, f, w):
        out_, cur = [], ""
        for wd in txt.split(" "):
            tst = (cur + " " + wd).strip()
            if d.textlength(tst, font=f) <= w: cur = tst
            else: out_.append(cur); cur = wd
        if cur: out_.append(cur)
        return out_

    # ---- background + HUD
    def background(im, d, t):
        d.rectangle([0, 0, W, H], fill=rgb("bg"))
        for y in range(0, H, 2):                         # vertical gradient in bands (dithered retro look)
            k = y / H
            if (y // 2) % 3 == 0 and k > .45: d.line([0, y, W, y], fill=rgb("bg2"))
        for (x, y, ph) in STARS:
            yy = int((y + t * 6 * (.3 + ph)) % H)
            tw_ = math.sin(t * 3 + ph * 9) > .2
            d.point((x, yy), fill=rgb("navy2" if not tw_ else ("muted" if ph < .7 else "coral2")))
        for x in range(0, W, 24):                        # pixel horizon grid at the bottom
            d.line([x, 410, W / 2 + (x - W / 2) * 2.2, 480], fill=rgb("bg2"))
        for k, y in enumerate([412, 418, 426, 436, 450, 466]):
            d.line([0, y, W, y], fill=rgb("bg2"))
    def hud(im, d, t):
        T(d, "ludogic", 16, 66, FS, "white")
        h = hearts(t)
        for k in range(3): blit(im, HEART if k < h else HEART_E, 196 + k * 9, 65, 1, ICON_PAL)
        blit(im, COIN, 224, 64, 1, ICON_PAL)
        T(d, f"{xp(t):03d}", 233, 65, FS, "gold")
        p = clamp(t / TOTAL)
        d.rectangle([16, 77, 254, 80], fill=rgb("navy"), outline=rgb("dark"))
        d.rectangle([17, 78, 17 + int(236 * p), 79], fill=rgb("coral"))
        for x in range(17, 253, 12): d.point((x, 78), fill=rgb("navy2"))
        T(d, "XP", 16, 29, FS, "muted", shadow=False) if False else None

    def headline(im, d, t, txt, t0, y=88, big=False):
        f = F16 if big else F8
        rows = wrap(d, txt, f, 232)
        lh = 20 if big else 12
        n = sum(len(r) for r in rows); shown = int(n * clamp((t - t0) / .35)) if t0 > -1 else n
        for k, r in enumerate(rows):
            vis_ = r[:max(0, shown)]; shown -= len(r)
            T(d, vis_, W / 2 - d.textlength(r, font=f) / 2, y + k * lh, f, "white", acc="coral")

    # ---- dialog box with the guide's portrait (= captions)
    def dialog(im, d, t):
        cur = None
        for l in lines:
            if l["start"] - .05 <= t <= (lines[l["i"] + 1]["start"] - .05 if l["i"] < LAST else l["end"] + .6): cur = l
        if cur is None: return
        y0 = 322; box(d, 14, y0, 256, y0 + 54, "dark", "white"); d.rectangle([16, y0 + 2, 254, y0 + 52], outline=rgb("navy2"))
        fi = int(t * FPS); m = mouth[fi] if fi < len(mouth) else 0
        mo = 0 if m < .12 else (1 if m < .45 else 2)
        blink = (t % 3.1) < .12
        box(d, 18, y0 + 4, 62, y0 + 50, "navy", "navy2")
        blit(im, girl_rows(blink=blink, mouth=mo)[:13], 16 + 6, y0 + 7, 2.5 if False else 2)
        d.rectangle([18, y0 + 4, 62, y0 + 50], outline=rgb("coral"))
        txt = cur["cap"]; dur = max(.3, (cur["end"] - cur["start"]) * .6)
        n = int(len(txt) * clamp((t - cur["start"]) / dur)) if t < cur["end"] else len(txt)
        rows = wrap(d, txt, FD, 184)
        yy = y0 + 6 + (3 - len(rows)) * 7 if len(rows) < 3 else y0 + 5
        for r in rows:
            vis_ = r[:max(0, n)]; n -= len(r) + 1
            T(d, vis_, 68, yy, FD, "white", acc="coral"); yy += 14
        if n >= 0 and (t * 2) % 1 < .5: d.polygon([(246, y0 + 46), (252, y0 + 46), (249, y0 + 49)], fill=rgb("coral"))

    # ---- panels
    PA = (14, 118, 256, 210); PB = (14, 224, 256, 316)
    def panel_frame(d, P, label, col, dim=False):
        x0, y0, x1, y1 = P
        d.rectangle([x0, y0, x1, y1], outline=rgb("dark"))
        d.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], outline=rgb(col))
        w = d.textlength(label, font=FS) + 8
        box(d, x0 + 4, y0 - 9, x0 + 4 + w, y0, col, "dark")
        T(d, label, x0 + 8, y0 - 8, FS, "dark" if col != "g3" else "white", shadow=False)

    def A_draw(im, d, P, a, t, t0, t1, sleep=0.):
        x0, y0, x1, y1 = P
        d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], fill=rgb("g0"))
        kind = a.get("kind")
        d.rectangle([x0 + 2, y0 + 2, x1 - 2, y0 + 12], fill=rgb("g1"))
        T(d, a.get("title", "COMPLIANCE TRAINING"), x0 + 6, y0 + 4, FS, "g4", shadow=False)
        T(d, a.get("page", "3/40"), x1 - 6, y0 + 4, FS, "g4", "r", shadow=False)
        if kind in ("slide", "policy"):
            heading = a.get("heading", "MODULE 1: INTRODUCTION")
            T(d, heading, x0 + 8, y0 + 18, FS, "g4", shadow=False)
            body = a.get("body", [])
            yy = y0 + 30
            for k in range(5):
                if k < len(body): T(d, body[k], x0 + 8, yy, FS, "g3", shadow=False)
                else: d.rectangle([x0 + 8, yy + 2, x0 + 8 + (150 - (k * 37) % 70), yy + 4], fill=rgb("g1"))
                yy += 9
            # NEXT button + cursor clicking
            bx, by = x1 - 46, y1 - 16
            ph = ((t - t0) % .7) / .7
            pressed = ph < .15
            box(d, bx, by, bx + 36, by + 10, "g2" if pressed else "g1", "g3")
            T(d, "NEXT >", bx + 4, by + 2, FS, "g4", shadow=False)
            cx, cy = bx + 30 + (0 if pressed else 2), by + 6 + (0 if pressed else 2)
            d.polygon([(cx, cy), (cx, cy + 7), (cx + 2, cy + 5), (cx + 5, cy + 5)], fill=rgb("white"), outline=rgb("dark"))
        if kind == "wait":
            T(d, a.get("heading", "FINAL QUIZ"), (x0 + x1) / 2, y0 + 20, F8, "g4", "c", shadow=False)
            cx, cy = (x0 + x1) // 2, y0 + 48
            d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=rgb("g1"), outline=rgb("g3"))
            ang = (t - t0) * 4
            d.line([cx, cy, cx + 12 * math.sin(ang), cy - 12 * math.cos(ang)], fill=rgb("g4"))
            d.line([cx, cy, cx + 7 * math.sin(ang / 12), cy - 7 * math.cos(ang / 12)], fill=rgb("g4"))
            sub = a.get("sub", ["IN 37 SLIDES"])
            for k, s_ in enumerate(sub): T(d, s_, (x0 + x1) / 2, y0 + 68 + k * 9, FS, "g3", "c", shadow=False)
        if kind == "exam":
            T(d, a.get("heading", "FINAL EXAM"), x0 + 8, y0 + 18, FS, "g4", shadow=False)
            off = int(((t - t0) * 9) % 40)
            for k in range(7):
                yy = y0 + 30 + k * 12 - off % 12
                if yy < y0 + 28 or yy > y1 - 14: continue
                q = k + 1 + off // 12
                T(d, f"Q{q}.", x0 + 8, yy, FS, "g3", shadow=False)
                d.rectangle([x0 + 30, yy + 2, x0 + 140, yy + 4], fill=rgb("g1"))
                for c in range(3): d.rectangle([x0 + 150 + c * 22, yy, x0 + 156 + c * 22, yy + 6], outline=rgb("g3"))
            T(d, a.get("foot", "20 QUESTIONS · 45 MIN"), (x0 + x1) / 2, y1 - 12, FS, "g3", "c", shadow=False)
        # sleepy learner head + Zzz
        hx, hy = x1 - 34, y0 + 18
        nod = int(2 * (math.sin((t - t0) * 2.2) > .3)) + (2 if sleep > .5 else 0)
        d.rectangle([hx, hy + nod, hx + 9, hy + 9 + nod], fill=rgb("g1"), outline=rgb("g3"))
        d.line([hx + 2, hy + 4 + nod, hx + 3, hy + 4 + nod], fill=rgb("g4")); d.line([hx + 6, hy + 4 + nod, hx + 7, hy + 4 + nod], fill=rgb("g4"))
        d.rectangle([hx - 1, hy + 11, hx + 10, hy + 17], fill=rgb("g2"))
        for k in range(3):
            ph = ((t - t0) * .8 + k / 3) % 1
            T(d, "z" if k < 2 else "Z", hx + 12 + ph * 10, hy + 2 - ph * 14, FS, "g3", shadow=False)
        # dull overlay that grows (the learner gives up)
        if sleep > 0:
            for y in range(y0 + 2, y1 - 1, 2): d.line([x0 + 2, y, x1 - 2, y], fill=rgb("g2")) if (y // 2) % 2 == int(sleep * 3) % 2 and sleep > .6 else None

    def floor(d, P, tile="navy"):
        x0, y0, x1, y1 = P
        d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], fill=rgb("bg2"))
        for (sx, sy, ph) in STARS[:25]:
            px, py = x0 + 3 + sx % (x1 - x0 - 6), y0 + 3 + sy % (y1 - y0 - 30)
            d.point((px, py), fill=rgb("navy2"))
        gy = y1 - 18
        d.rectangle([x0 + 2, gy, x1 - 2, y1 - 2], fill=rgb(tile))
        for x in range(x0 + 2, x1 - 2, 8):
            d.line([x, gy, x, y1 - 2], fill=rgb("navy2")); d.line([x0 + 2, gy, x1 - 2, gy], fill=rgb("blue"))
        for x in range(x0 + 6, x1 - 2, 16): d.rectangle([x, gy + 6, x + 3, gy + 8], fill=rgb("navy2"))
        return gy

    def B_draw(im, d, P, b, t, t0, t1, plan):
        x0, y0, x1, y1 = P; kind = b.get("kind")
        gy = floor(d, P)
        if kind == "title":
            ts = ev_time("start") or t0 + 1
            T(d, b.get("game", "COMPLIANCE"), (x0 + x1) / 2 + 14, y0 + 10, F16, "coral", "c")
            T(d, b.get("game2", "QUEST"), (x0 + x1) / 2 + 14, y0 + 30, F16, "gold", "c")
            if t < ts:
                if (t * 2.5) % 1 < .6: T(d, "PRESS START", (x0 + x1) / 2 + 14, y0 + 56, F8, "white", "c")
            else:
                for j in range(3):
                    tj = ts + .6 + j * .28
                    if t < tj: continue
                    bx = (x0 + x1) / 2 - 26 + j * 32; by = y0 + 52 - int(6 * math.sin(clamp((t - tj) / .25) * math.pi))
                    blit(im, QBOX, bx, by, 2, ICON_PAL)
                    T(d, str(j + 1), bx + 9, by + 5, F8, "white", "c")
                    if t - tj < .5: blit(im, COIN, bx + 2, by - 10 - int(20 * (t - tj)), 2, ICON_PAL)
            px = x0 + 3 + int(40 * eo(clamp(t / .6)))
            run = t < .5
            jmp = int(10 * math.sin(clamp((t - ts) / .4) * math.pi)) if t >= ts else 0
            blit(im, girl_rows(walk=(1 + int(t * 8) % 2) if run else 0, pose="cheer" if t >= ts else "idle", blink=(t % 2.6) < .12), px, gy - 44 - jmp, 2)
        if kind == "choice":
            ta = ev_time("pop", "ask"); tc = ev_time("pop", "choices"); tp = ev_time("select", "pick")
            blit(im, girl_rows(blink=(t % 2.7) < .12), x0 + 26, gy - 44, 2)
            npc = {"coral": "sky", "coral3": "blue2", "blue": "coral", "blue2": "coral3", "coral2": "skin2"}
            blit(im, girl_rows(blink=(t % 3.3) < .12, walk=0), x1 - 60, gy - 44, 2, flip=True, remap=npc)
            if ta and t >= ta:
                sc_ = back(clamp((t - ta) / .25))
                bw, bh = int(118 * sc_), int(26 * sc_)
                bx, by = x1 - 66 - bw + 30, y0 + 8
                if bw > 6:
                    box(d, bx, by, bx + bw, by + bh, "white", "dark")
                    d.polygon([(bx + bw - 22, by + bh), (bx + bw - 14, by + bh + 7), (bx + bw - 12, by + bh)], fill=rgb("white"))
                    if sc_ > .95:
                        for k, r in enumerate(b.get("ask", ["Can I borrow", "your password?"])): T(d, r, bx + 5, by + 4 + k * 10, FD, "dark", shadow=False)
            if tc and t >= tc:
                bx, by = x0 + 70, y0 + 40
                sc_ = clamp((t - tc) / .2)
                if sc_ > 0:
                    box(d, bx, by, bx + int(78 * sc_), by + 32, "dark", "white")
                    if sc_ >= 1:
                        opts = b.get("options", ["SURE", "NO WAY"])
                        sel = 1
                        for (te, n, x) in events:
                            if n == "blip" and te <= t and te >= tc: sel = 1 if x == "down" else 0
                        picked = tp and t >= tp
                        for k, o in enumerate(opts):
                            col = "gold" if (picked and k == 1) else "white"
                            if picked and k == 1 and (t * 10) % 1 < .5: col = "coral"
                            T(d, o, bx + 14, by + 6 + k * 12, F8, col)
                        cy = by + 6 + sel * 12
                        if (t * 4) % 1 < .7 or picked: d.polygon([(bx + 5, cy), (bx + 5, cy + 6), (bx + 9, cy + 3)], fill=rgb("coral"))
                        if picked and t - tp < .8:
                            T(d, "+10 XP", x0 + 40, y0 + 30 - int(16 * (t - tp)), F8, "gold")
        if kind == "feedback":
            tw = ev_time("select", "wrong", t0 - .01); th = ev_time("hurt", "wrong", t0 - .01); tr = ev_time("select", "right", t0 - .01)
            shake = 0
            if th and th <= t < th + .3: shake = int(3 * math.sin(t * 90))
            pose = "hurt" if (th and th <= t < th + .6) else ("cheer" if tr and t >= tr + .1 else "idle")
            gx = x0 + 30 + shake
            if pose != "hurt" or int(t * 16) % 2: blit(im, girl_rows(pose=pose, blink=(t % 2.5) < .12), gx, gy - 44 - (int(8 * math.sin(clamp((t - tr - .1) / .4) * math.pi)) if tr and t > tr + .1 else 0), 2)
            bx, by = x0 + 80, y0 + 10
            box(d, bx, by, x1 - 10, by + 28, "dark", "white")
            opts = b.get("options", ["SURE", "NO WAY"])
            if tw is None or t < tw: sel = 0
            elif tr and t >= tr - .35: sel = 1
            else: sel = 0
            for k, o in enumerate(opts):
                col = "white"
                if k == 0 and tw and tw <= t: col = "g3"
                if k == 1 and tr and t >= tr: col = "gold"
                T(d, o, bx + 14, by + 5 + k * 12, F8, col)
            cy = by + 5 + sel * 12
            d.polygon([(bx + 5, cy), (bx + 5, cy + 6), (bx + 9, cy + 3)], fill=rgb("coral"))
            if th and th <= t and (not tr or t < tr - .4):      # explanation card after the wrong pick
                box(d, x0 + 80, by + 34, x1 - 10, by + 64, "coral3", "dark")
                for k, r in enumerate(b.get("why", ["PHISHING! NEVER", "SHARE IT. TRY AGAIN"])): T(d, r, x0 + 85, by + 38 + k * 12, FS, "white")
                if t - th < .7: T(d, "-1", gx + 30, gy - 56 - int(14 * (t - th)), F8, "coral")
            if tr and t >= tr:
                k_ = clamp((t - tr) / .3)
                T(d, "+10 XP", x0 + 130, by + 40 - int(4 * k_), F16 if k_ >= 1 else F8, "gold")
                T(d, "CORRECT!", x0 + 140, by + 62, F8, "green")
                for j in range(5):
                    tj = tr + .3 + j * .07
                    if t >= tj and t - tj < .7:
                        blit(im, COIN, gx + 10 + j * 10, gy - 50 - int(40 * (t - tj)) + int(60 * (t - tj) ** 2), 1, ICON_PAL)
            # instant-feedback timer
            if th and t >= th - .3 and t < th + .4: T(d, "0.5s", x1 - 40, y1 - 14, FS, "white")
        if kind == "boss":
            L = b["line"]
            hits = sorted([e[0] for e in plan["ev"] if e[1] == "hit"]); ko = ev_time("explode", "ko", t0 - .01)
            tbh = ev_time("hurt", "bosshit", t0 - .01)
            nh = sum(1 for th in hits if t >= th)
            hp = max(0, 1 - nh / max(1, len(hits)))
            # boss: angry exam sheet
            bx, by = x1 - 74, y0 + 18
            if not ko or t < ko + .05:
                wob = int(2 * math.sin(t * 5))
                recoil = any(0 <= t - th < .2 for th in hits)
                if not recoil or int(t * 20) % 2:
                    px = bx + (4 if recoil else 0); py = by + wob
                    box(d, px, py, px + 44, py + 56, "white", "dark")
                    d.polygon([(px + 34, py), (px + 44, py + 10), (px + 34, py + 10)], fill=rgb("g1"), outline=rgb("dark"))
                    for k in range(4): d.line([px + 6, py + 30 + k * 6, px + 38, py + 30 + k * 6], fill=rgb("g1"))
                    d.rectangle([px + 8, py + 12, px + 15, py + 18], fill=rgb("coral")); d.rectangle([px + 25, py + 12, px + 32, py + 18], fill=rgb("coral"))
                    d.line([px + 6, py + 9, px + 16, py + 12], fill=rgb("dark")); d.line([px + 34, py + 9, px + 24, py + 12], fill=rgb("dark"))
                    d.rectangle([px + 12, py + 22, px + 28, py + 26], fill=rgb("dark"))
                    for k in range(4): d.rectangle([px + 13 + k * 4, py + 22, px + 14 + k * 4, py + 23], fill=rgb("white"))
                    T(d, "F", px + 36, py + 45, F8, "coral")
            else:
                for k in range(26):                           # pixel explosion
                    a_ = k * 2.4; r_ = (t - ko) * (60 + (k % 5) * 18)
                    if t - ko < 1.2:
                        d.rectangle([bx + 22 + r_ * math.cos(a_), by + 28 + r_ * math.sin(a_), bx + 25 + r_ * math.cos(a_), by + 31 + r_ * math.sin(a_)],
                                    fill=rgb(["white", "coral", "gold", "g1"][k % 4]))
                if t - ko > .3: T(d, b.get("ko", "K.O.!"), bx + 22, by + 20, F16, "gold", "c")
            # boss HP bar
            T(d, b.get("boss", "BOSS: FINAL EXAM"), x0 + 8, y0 + 6, FS, "coral")
            d.rectangle([x0 + 8, y0 + 15, x0 + 108, y0 + 20], fill=rgb("dark"), outline=rgb("white"))
            if hp > 0: d.rectangle([x0 + 9, y0 + 16, x0 + 9 + int(98 * hp), y0 + 19], fill=rgb("coral" if hp > .34 else "gold"))
            # intro warning flash
            if t - t0 < 1.0 and int((t - t0) * 6) % 2 == 0: T(d, "WARNING!", (x0 + x1) / 2, y0 + 50, F16, "coral", "c")
            # player
            atk = any(0 <= t - th < .25 for th in hits)
            hurt = tbh and 0 <= t - tbh < .5
            pose = "attack" if atk else ("hurt" if hurt else ("cheer" if ko and t > ko + .2 else "idle"))
            if not hurt or int(t * 16) % 2: blit(im, girl_rows(pose=pose, blink=(t % 2.6) < .12), x0 + 34 + (10 if atk else 0), gy - 44, 2)
            for th in hits:                                    # projectile: a check mark
                if 0 <= t - th + .18 < .18:
                    k_ = (t - th + .18) / .18
                    sx = x0 + 70 + k_ * (bx - x0 - 60); sy = gy - 26 - 8 * math.sin(k_ * math.pi)
                    d.line([sx, sy, sx + 3, sy + 3], fill=rgb("green"), width=2); d.line([sx + 3, sy + 3, sx + 9, sy - 4], fill=rgb("green"), width=2)
                if 0 <= t - th < .45: T(d, "HIT!" if th != hits[-1] else "CRIT!", bx + 10, by - 6 - int(14 * (t - th)), F8, "gold")
            if tbh and 0 <= t - tbh + .35 < .35:              # boss throws a red X at the player
                k_ = (t - tbh + .35) / .35; sx = bx - k_ * (bx - x0 - 50); sy = by + 30
                d.line([sx, sy, sx + 6, sy + 6], fill=rgb("coral"), width=2); d.line([sx + 6, sy, sx, sy + 6], fill=rgb("coral"), width=2)
            if hurt and t - tbh < .6: T(d, "MISS -1", x0 + 30, gy - 58 - int(10 * (t - tbh)), F8, "coral")
            q = b.get("question")
            if q and (not ko or t < ko): T(d, q, x0 + 8, y1 - 14, FS, "white")

    def vs(im, d, t, y=217):
        cx = W // 2; pulse = int(2 * math.sin(t * 6) > 0)
        box(d, cx - 13 - pulse, y - 6 - pulse, cx + 13 + pulse, y + 6 + pulse, "coral", "dark", hi="coral2")
        T(d, "VS", cx, y - 3, F8, "white", "c")

    def merge(im, d, t, sc, t0, t1, plan):
        k = clamp((t - t0) / .45)
        # panel A switches off like an old TV
        if k < 1:
            x0, y0, x1, y1 = PA; cy = (y0 + y1) // 2
            hh = int((y1 - y0) / 2 * (1 - eo(k)))
            d.rectangle([x0, cy - max(1, hh), x1, cy + max(1, hh)], fill=rgb("g1"))
            d.line([x0 + int((x1 - x0) * k / 2), cy, x1 - int((x1 - x0) * k / 2), cy], fill=rgb("white"))
            if k > .6: T(d, sc.get("over", "GAME OVER"), W / 2, cy - 4, F8, "g3", "c")
        else:
            if (t * 2) % 1 < .6 and t - t0 < .7: T(d, sc.get("over", "GAME OVER"), W / 2, 160, F8, "g3", "c")
        # panel B grows to the whole stage
        e = eo(clamp((t - t0 - .2) / .5))
        P = (14, int(224 + (118 - 224) * e), 256, 316)
        x0, y0, x1, y1 = P
        gy = floor(d, P)
        panel_frame(d, P, "GAME", "coral")
        if e > .9: T(d, sc.get("inv", "INVENTORY"), x0 + 10, y0 + 6, FS, "gold")
        items = sc.get("items", [])
        tj_list = [e_[0] for e_ in plan["ev"] if e_[1] == "power"]
        icons = [QBOX, BOLT, SWORD]
        for j, it in enumerate(items):
            if j >= len(tj_list) or t < tj_list[j]: continue
            kk = back(clamp((t - tj_list[j]) / .3))
            ix = x0 + 16 + j * 74; iy = y0 + 18
            box(d, ix, iy, ix + 64, iy + 52, "navy", "dark", hi="navy2")
            d.rectangle([ix + 1, iy + 1, ix + 63, iy + 51], outline=rgb("gold"))
            s_ = 2 if kk > .9 else 1
            ic = icons[j % 3]
            blit(im, ic, ix + 32 - len(ic[0]) * s_ / 2, iy + 8 - (1 - kk) * 10, s_, ICON_PAL)
            if j == 0 and kk > .9: T(d, "?", ix + 32, iy + 13, F8, "white", "c")
            for r_i, r in enumerate(it if isinstance(it, list) else [it]): T(d, r, ix + 32, iy + 34 + r_i * 9, FS, "white", "c")
        tc = ev_time("jump", None, t0 - .01)
        jy = int(14 * math.sin(clamp((t - tc) / .45) * math.pi)) if tc and t >= tc else 0
        pose = "cheer" if tc and t >= tc else "idle"
        gx = (x0 + x1) // 2 - 16
        blit(im, girl_rows(pose=pose, blink=(t % 2.4) < .12), gx, gy - 44 - jy, 2)
        if tc and t >= tc:
            for j in range(10):
                a_ = j * .63; r_ = (t - tc) * 50
                if t - tc < 1: blit(im, STAR, gx + 16 + r_ * math.cos(a_), gy - 30 - jy + r_ * math.sin(a_) * .6, 1, ICON_PAL)

    def end(im, d, t, sc, t0, t1, plan):
        d.rectangle([14, 118, 256, 316], fill=rgb("bg2")); d.rectangle([14, 118, 256, 316], outline=rgb("coral"))
        for j in range(40):                                   # confetti
            cx = (j * 47) % 240 + 16; ph = (t - t0) * (40 + j % 7 * 9) + j * 13
            cy = 120 + ph % 194
            d.rectangle([cx + 4 * math.sin(ph / 9), cy, cx + 4 * math.sin(ph / 9) + 2, cy + 2], fill=rgb(["coral", "gold", "sky", "white", "coral2"][j % 5]))
        title = sc.get("title", "LEVEL COMPLETE!")
        words = title.split(" ")
        for wi, wd in enumerate(words):
            y = 126 + wi * 22
            x = W / 2 - d.textlength(wd, font=F16) / 2
            for ci, ch in enumerate(wd):
                kk = clamp((t - t0 - .1 - (wi * 6 + ci) * .04) / .3)
                if kk <= 0: continue
                yy = y + int(6 * math.sin(t * 6 + ci * .7)) - int((1 - back(kk)) * 30)
                T(d, ch, x, yy, F16, "gold" if wi else "coral")
                x += d.textlength(ch, font=F16)
        gx, gy = 18, 222
        blit(im, girl_rows(pose="wave" if int(t * 2.5) % 2 else "idle", blink=(t % 2.3) < .12), gx, gy, 4)
        ts = ev_time("save", None, t0 - .01) or t0 + 1
        if t >= ts:
            kk = back(clamp((t - ts) / .35)); s_ = 3 if kk > .9 else 2
            fx, fy = 150, 170 - int((1 - kk) * 20) + int(3 * math.sin(t * 5))
            blit(im, FLOPPY, fx, fy, s_, ICON_PAL)
            for r_i, r in enumerate(sc.get("save", ["SAVE THIS", "FOR YOUR NEXT", "COURSE REDESIGN"])):
                T(d, r, 168, 212 + r_i * 11, F8 if r_i == 0 else FS, "white" if r_i else "coral", "c")
            if (t * 2) % 1 < .55: T(d, sc.get("press", "PRESS  SAVE"), 168, 252, F8, "gold", "c")
        T(d, sc.get("tagline", "GAMIFICATION FOR TEAMS"), 168, 284, FS, "muted", "c", shadow=False)
        T(d, "ludogic.dev", 168, 296, FS, "coral", "c", shadow=False)

    def frame(t):
        im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im); d.fontmode = "1"
        background(im, d, t); hud(im, d, t)
        cur = [p for p in plans if p["t0"] - .001 <= t < p["t1"]]
        for p in cur:
            sc = p["sc"]; t0, t1 = p["t0"], p["t1"]
            hd = sc.get("head"); th = sc.get("then")
            if th and t >= reel_S[th["line"]]: headline(im, d, t, th["head"], reel_S[th["line"]])
            elif hd: headline(im, d, t, hd, t0 if t0 > 0 else -2)
            if sc["type"] == "split":
                sleep = clamp((t - t0) / max(.1, t1 - t0))
                A_draw(im, d, PA, sc["a"], t, t0, t1, sleep); panel_frame(d, PA, sc.get("a_label", "SLIDES"), "g3")
                B_draw(im, d, PB, sc["b"], t, t0, t1, p); panel_frame(d, PB, sc.get("b_label", "GAME"), "coral")
                vs(im, d, t)
            elif sc["type"] == "merge": merge(im, d, t, sc, t0, t1, p)
            elif sc["type"] == "end": end(im, d, t, sc, t0, t1, p)
            if t0 > 0 and t - t0 < .12: d.rectangle([0, 0, W, H], outline=None, fill=None)
        dialog(im, d, t)
        # transition: pixel wipe between scenes
        for p in plans[1:]:
            k = (t - p["t0"]) / .18
            if -1 < k < 0:
                for y in range(0, H, 8): d.rectangle([0, y, int(W * (1 + k)), y + 3], fill=rgb("dark"))
            if 0 <= k < 1:
                for y in range(4, H, 8): d.rectangle([int(W * k), y, W, y + 3], fill=rgb("dark"))
        return im.resize((WD, HT), Image.NEAREST)
    reel_S = {l["i"]: l["start"] for l in tl["lines"]}
    return frame

# ---------------------------------------------------------------- build
def build(spec_path, out, preview=False):
    t_start = time.time(); ensure_fonts()
    spec = json.load(open(spec_path)); os.makedirs(out, exist_ok=True)
    shutil.copy(spec_path, f"{out}/spec.json")
    t = time.time(); meta = reel.make_voice(spec, out); t_voice = time.time() - t
    tl = reel.make_timeline(spec, meta, out)
    plans = plan_scenes(spec, tl)
    t = time.time(); am = make_audio(spec, tl, plans, out); t_audio = time.time() - t
    frame = make_renderer(spec, tl, plans, out)
    pts = sorted(set([0.0, .6] + [round(l["start"] + .75 * (l["end"] - l["start"]), 2) for l in tl["lines"]]
                     + [round(e[0] + .25, 2) for p in plans for e in p["ev"] if e[1] in ("hurt", "hit", "power", "explode")][:8]
                     + [round(tl["total"] - .3, 2)]))
    shutil.rmtree(f"{out}/prev", ignore_errors=True); os.makedirs(f"{out}/prev")
    for p in pts: frame(p).save(f"{out}/prev/{p:06.2f}.png")
    cols = 7
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", f"{out}/prev/*.png",
                    "-vf", f"scale=216:384:flags=neighbor,tile={cols}x{math.ceil(len(pts) / cols)}", "-frames:v", "1", "-q:v", "3", f"{out}/sheet.jpg"], check=True)
    g = reel.gates(spec, out)
    metrics = {"id": spec["id"], "engine_version": ENGINE_VERSION, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "duration_s": tl["total"], "lines": len(tl["lines"]), "scenes": len(spec["scenes"]),
               "scene_types": [s["type"] + (":" + s["a"]["kind"] + "/" + s["b"]["kind"] if s["type"] == "split" else "") for s in spec["scenes"]],
               "avg_scene_s": round(tl["total"] / len(spec["scenes"]), 2),
               "words": sum(len(l["cap"].split()) for l in tl["lines"]),
               "speech_s": round(sum(l["end"] - l["start"] for l in tl["lines"]), 2),
               "voice": spec.get("voice", {}).get("name", "af_heart"), "voice_speed": spec.get("voice", {}).get("speed", 1.08),
               "palette": "#FF5A4E/#070B1A + #3D6BFF/#FFC24D", "font": "Press Start 2P + Pixelify Sans + Silkscreen (OFL)",
               "art_direction": spec.get("style", {}).get("art", "retro pixel art, split screen slides vs game, pixel guide"),
               **am, "gates": g, "render": {"voice_s": round(t_voice, 1), "audio_s": round(t_audio, 1)}, "cost": {"elevenlabs_credits": 0, "eur": 0}}
    if not preview:
        t = time.time(); nfr = int(math.ceil(tl["total"] * FPS))
        ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{WD}x{HT}", "-r", str(FPS), "-i", "-", "-i", f"{out}/mix.wav", "-map", "0:v", "-map", "1:a",
                               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
                               "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", f"{out}/video.mp4"], stdin=subprocess.PIPE)
        for n in range(nfr): ff.stdin.write(frame(n / FPS).tobytes())
        ff.stdin.close(); ff.wait()
        frame(spec.get("cover_t", 0.6)).convert("RGB").save(f"{out}/cover.jpg", quality=90)
        metrics["render"]["video_s"] = round(time.time() - t, 1)
        metrics["file_mb"] = round(os.path.getsize(f"{out}/video.mp4") / 1e6, 2)
    metrics["render"]["total_s"] = round(time.time() - t_start, 1)
    json.dump(metrics, open(f"{out}/metrics.json", "w"), indent=1)
    hsv = g["hookscore"].get("score") if isinstance(g["hookscore"], dict) else None
    print(json.dumps({"id": spec["id"], "duration_s": tl["total"], "hookscore": hsv, "lufs": am["lufs"],
                      "voice_minus_bed_db": am["voice_minus_bed_db"], "render_s": metrics["render"]["total_s"]}))

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3], preview="--preview" in sys.argv)
    else:
        print(__doc__); sys.exit(1)
