#!/usr/bin/env python3
"""Ludogic SPLIT-QUIZ reel engine (category "Comparación y mejora", user brief 2026-10-17).

    python3 engine/splitquiz.py build specs/<ID>.json out/<ID> [--preview]

Full 1080x1920 frame split in half:
  top    = gamified quiz (Kahoot-style tiles, vector presenter who throws the question, bomb countdown that sets the
           points, lives, score, quiz % progress, light feedback on SELECT, big feedback on NEXT)
  bottom = traditional form (white, black, Arial-metric Liberation Sans, A-D radios, "Next >", no feedback at all)
A mouse cursor answers on both halves at all times. While the voice talks about one half, the other half freezes
in grey and the pixel-art guide appears on it with the subtitles (Poppins). "both" scenes animate both halves and
put the guide + subtitles on the divider. Same outputs and gates as engine/reel.py.
"""
import sys, os, json, math, time, subprocess, shutil, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import reel, retro

ENGINE_VERSION = "splitquiz-1.0.0"
W, H, FPS, SR = 1080, 1920, 30, 48000
MID = 960
FONTS = os.path.expanduser("~/.cache/ludogic-reels/fonts")
POP = {k: f"{FONTS}/Poppins-{k}.ttf" for k in ("Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black")}
LIB = "/usr/share/fonts/truetype/liberation/LiberationSans-{}.ttf"

def ensure_fonts():
    os.makedirs(FONTS, exist_ok=True)
    for k, p in POP.items():
        if not os.path.exists(p):
            subprocess.run(["curl", "-sSfL", "-o", p, f"https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-{k}.ttf"], check=True)
    retro.ensure_fonts()

C = {"bg": (7, 11, 26), "bg2": (14, 22, 51), "navy": (27, 39, 86), "navy2": (42, 58, 122), "coral": (255, 90, 78),
     "coral2": (255, 138, 122), "blue": (61, 107, 255), "gold": (255, 194, 77), "gold2": (255, 176, 32), "green": (43, 182, 115),
     "white": (244, 246, 251), "muted": (138, 147, 179), "dark": (11, 15, 36), "skin": (245, 201, 166), "red": (230, 57, 70)}
TILE = [(C["coral"], "tri"), (C["blue"], "dia"), (C["gold2"], "circ"), (C["green"], "sq")]

def clamp(x, a=0., b=1.): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def eo(x): return 1 - (1 - x) ** 3
def eio(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x, s=1.7): x -= 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, k): return a + (b - a) * k
def mix(c1, c2, k): return tuple(int(lerp(c1[i], c2[i], k)) for i in range(3))

# =====================================================================
# timeline: which half is active, local clocks, simulated quiz events
# =====================================================================
def activity(spec, tl):
    S = {l["i"]: l["start"] for l in tl["lines"]}
    sc = spec["scenes"]; spans = []
    for k, s in enumerate(sc):
        t0 = S[s["line"]] if k else 0.0
        t1 = S[sc[k + 1]["line"]] if k + 1 < len(sc) else tl["total"] + 1
        spans.append((t0, t1, s))
    return spans

def clocks(spans, total):
    n = int(math.ceil(total * FPS)) + 2
    ts = np.arange(n) / FPS
    top = np.zeros(n); bot = np.zeros(n)
    for i in range(1, n):
        s = next((s for (a, b, s) in spans if a <= ts[i - 1] < b), spans[-1][2])
        act = s["active"]
        top[i] = top[i - 1] + (1 / FPS if act in ("top", "both") else 0)
        bot[i] = bot[i - 1] + (1 / FPS if act in ("bottom", "both") else 0)
    return ts, top, bot

class TopSim:
    """Gamified quiz. One question every P local seconds."""
    def __init__(self, qs, P=6.0, total_q=5):
        self.qs, self.P, self.N = qs, P, total_q
        self.k = dict(throw=0.0, tiles=.35, bomb0=.5, sel=1.7, nxt=2.6, out=P - .55)
    def q(self, tau):
        i = int(tau // self.P); return i, tau - i * self.P, self.qs[i % len(self.qs)]
    def state(self, tau):
        """cumulative score / lives / streak / answered before local time tau."""
        score, lives, streak, answered = 0, 3, 0, 0; last_pts = 0
        i = 0
        while i * self.P + self.k["nxt"] <= tau:
            q = self.qs[i % len(self.qs)]
            if q["pick"] == q["answer"]:
                f = 1 - clamp((self.k["nxt"] - self.k["bomb0"]) / q.get("bomb_s", 6.5))
                last_pts = int(round((500 + 500 * f) / 10) * 10); score += last_pts; streak += 1
            else:
                lives -= 1; streak = 0; last_pts = 0
            answered += 1; i += 1
        return dict(score=score, lives=max(0, lives), streak=streak, answered=answered, last_pts=last_pts)
    def events(self, tau_max):
        ev = []; i = 0
        while i * self.P < tau_max:
            b = i * self.P; q = self.qs[i % len(self.qs)]; ok = q["pick"] == q["answer"]
            ev += [(b + .02, "throw"), (b + self.k["tiles"], "tiles"), (b + self.k["sel"], "select"),
                   (b + self.k["nxt"], "correct" if ok else "wrong"), (b + self.k["out"], "swoosh")]
            if ok: ev += [(b + self.k["nxt"] + .45, "coins")]
            i += 1
        return ev

class BotSim:
    """Traditional form. One page every P local seconds; nothing happens after Next except the page swap."""
    def __init__(self, qs, P=3.4, page0=7):
        self.qs, self.P, self.page0 = qs, P, page0
        self.k = dict(sel=1.25, nxt=2.55, swap=2.75)
    def q(self, tau):
        i = int((tau + self.P - self.k["swap"]) // self.P)     # page swaps at k.swap
        local = tau - (i * self.P - (self.P - self.k["swap"]))
        return i, local, self.qs[i % len(self.qs)]
    def events(self, tau_max):
        ev = []; i = 0
        while i * self.P < tau_max:
            b = i * self.P - (self.P - self.k["swap"])
            for k_ in ("sel", "nxt"):
                if b + self.k[k_] >= 0: ev.append((b + self.k[k_], "click" if k_ == "sel" else "next"))
            i += 1
        return ev

def to_global(local_events, clk, ts):
    out = []
    for (tau, name) in local_events:
        j = int(np.searchsorted(clk, tau - 1e-6, side="left"))
        if j < len(ts) and clk[j] >= tau - 1e-6: out.append((float(ts[j]), name))
    return out

# =====================================================================
# audio
# =====================================================================
def make_audio(spec, tl, spans, gtop, gbot, out):
    import soundfile as sf
    from scipy.signal import resample_poly, butter, sosfilt
    rng = np.random.default_rng(5)
    TOTAL = tl["total"]; N = int(TOTAL * SR)
    def buf(): return np.zeros(N)
    def add(dst, sig, t, g=1.):
        i = int(t * SR)
        if i >= N or i < 0: return
        j = min(N, i + len(sig)); dst[i:j] += g * sig[: j - i]
    def env(n, a=.004, d=.15, c=3.):
        tt = np.arange(n) / SR; return np.minimum(1, tt / max(a, 1e-4)) * np.exp(-c * tt / max(d, 1e-4))
    def filt(x, kind, fc, o=2): return sosfilt(butter(o, fc, kind, fs=SR, output="sos"), x)
    def sine(f, dur):
        tt = np.arange(int(dur * SR)) / SR
        return np.sin(2 * np.pi * (np.cumsum(f(tt)) / SR if callable(f) else f * tt))
    def saw(f, dur): tt = np.arange(int(dur * SR)) / SR; return 2 * ((f * tt) % 1) - 1
    def noise(dur): return rng.standard_normal(int(dur * SR))
    mtof = lambda m: 440 * 2 ** ((m - 69) / 12)
    mu = spec.get("music", {}); BPM = mu.get("bpm", 118); beat = 60 / BPM
    prog_ = [[48, [60, 64, 67, 71]], [45, [57, 60, 64, 67]], [41, [57, 60, 65, 69]], [43, [59, 62, 67, 71]]]
    music = buf()
    for b in range(int(TOTAL / (4 * beat)) + 2):
        t0 = b * 4 * beat; root, ch = prog_[b % 4]
        for k in range(4):
            tb = t0 + k * beat
            add(music, sine(lambda tt: 45 + 110 * np.exp(-tt * 28), .3) * env(int(.3 * SR), .001, .12, 3), tb, .5)
            add(music, filt(noise(.04), "high", 7000) * env(int(.04 * SR), .0005, .02, 3), tb + beat / 2, .06)
            if k in (1, 3): add(music, filt(noise(.15), "band", [1000, 4000]) * env(int(.15 * SR), .001, .05, 3), tb, .12)
            for h in (0, .5): add(music, filt(saw(mtof(root - 12), .2), "low", 500) * env(int(.2 * SR), .002, .12, 3), tb + h * beat, .16)
        for s16 in range(16):
            n = ch[(s16 * 3) % 4] + (12 if s16 % 8 >= 4 else 0)
            add(music, filt(saw(mtof(n), .16), "low", 2600) * env(int(.16 * SR), .001, .07, 3), t0 + s16 * beat / 4, .035)
    # music only while the gamified half is alive; the form gets a dull office hum + clock tick
    gate = np.zeros(N); hum = np.zeros(N)
    for (a, b_, s) in spans:
        i0, i1 = int(a * SR), min(N, int(b_ * SR))
        if s["active"] in ("top", "both"): gate[i0:i1] = 1
        else: hum[i0:i1] = 1
    k_ = int(.25 * SR); gate = np.convolve(gate, np.ones(k_) / k_, mode="same"); hum = np.convolve(hum, np.ones(k_) / k_, mode="same")
    tt = np.arange(N) / SR
    hum_sig = (np.sin(2 * np.pi * 100 * tt) * .5 + np.sin(2 * np.pi * 200 * tt) * .2) * .02 * hum
    for k in range(int(TOTAL) + 1):
        add(hum_sig, filt(noise(.01), "high", 2500) * env(int(.01 * SR), .0005, .004, 3) * hum[min(N - 1, int(k * SR))], k, .18)
    music = music * (.12 + .88 * gate)

    sfx = buf()
    def arp(t, notes, step=.06, dur=.12, g=.10):
        for i, n in enumerate(notes): add(sfx, (sine(mtof(n), dur) + .4 * sine(mtof(n) * 2, dur)) * env(int(dur * SR), .002, dur * .6, 2.5), t + i * step, g)
    def whoosh(t, dur=.35, g=.25):
        n = filt(noise(dur), "band", [800, 5000]); add(sfx, n * np.sin(np.linspace(0, np.pi, len(n))) ** 2, t, g * .25)
    SF = {"throw": lambda t: whoosh(t, .3, .9), "tiles": lambda t: [arp(t + i * .08, [72 + 3 * i], dur=.07, g=.06) for i in range(4)],
          "select": lambda t: (arp(t, [84], dur=.06, g=.08), add(sfx, filt(noise(.02), "band", [1500, 5000]) * env(int(.02 * SR), .0005, .008, 3), t, .2)),
          "correct": lambda t: (arp(t, [72, 76, 79, 84], .07, .25, .12), arp(t + .3, [84, 88, 91, 96], .05, .2, .07),
                                add(sfx, filt(noise(.6), "high", 5000) * env(int(.6 * SR), .001, .35, 2), t + .1, .05)),
          "wrong": lambda t: (add(sfx, filt(np.sign(sine(lambda x: 160 - 60 * x, .5)), "low", 1800) * env(int(.5 * SR), .005, .45, 1.2), t, .12),
                              add(sfx, sine(lambda x: 90 * np.exp(-x * 4) + 40, .4) * env(int(.4 * SR), .001, .3, 2), t + .05, .3)),
          "coins": lambda t: [arp(t + i * .06, [88 + (i % 3) * 2], dur=.08, g=.05) for i in range(8)],
          "swoosh": lambda t: whoosh(t, .3, .6),
          "upgrade": lambda t: (arp(t, [67, 72, 76, 79, 84, 88], .035, .1, .11), add(sfx, sine(lambda x: 90 * np.exp(-x * 10) + 50, .3) * env(int(.3 * SR), .001, .15, 2), t, .45),
                                add(sfx, filt(noise(.5), "high", 6000) * env(int(.5 * SR), .001, .3, 2), t + .05, .08)),
          "next": lambda t: SF["click"](t),
          "click": lambda t: add(sfx, filt(noise(.012), "band", [1200, 3500]) * env(int(.012 * SR), .0005, .005, 3), t, .35)}
    for (t, n) in gtop + gbot: SF[n](t)
    # end sting
    te = tl["lines"][-1]["start"]
    arp(te, [72, 76, 79, 84, 88], .08, .3, .09)

    vo = buf()
    for l in tl["lines"]:
        a, sr = sf.read(f"{out}/vo/l{l['i']:02d}.wav")
        a = filt(resample_poly(a, SR, sr), "high", 80); add(vo, a / (np.max(np.abs(a)) + 1e-9), l["start"], .75)
    venv = np.convolve(np.abs(vo), np.ones(int(.08 * SR)) / int(.08 * SR), mode="same")
    duck = 1 - .6 * np.clip(venv / (venv.max() * .25), 0, 1); duck = np.convolve(duck, np.ones(int(.15 * SR)) / int(.15 * SR), mode="same")
    md = music * duck * mu.get("level", .6); sx = .8 * sfx * (1 - .4 * (1 - duck)) + hum_sig
    d = int(.01 * SR); L = vo + md + sx; R = vo + np.concatenate([np.zeros(d), md[:-d]]) + sx
    st = np.stack([L, R], 1); st /= np.max(np.abs(st)) / .89
    sf.write(f"{out}/mix_raw.wav", st.astype(np.float32), SR)
    sp = np.zeros(N, bool)
    for l in tl["lines"]: sp[int(l["start"] * SR):int(l["end"] * SR)] = True
    def rms(x): return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", f"{out}/mix_raw.wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                        "-ar", str(SR), f"{out}/mix.wav"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"output_i\"[^{}]*\}", r.stderr, re.S); ln = json.loads(m.group(0)) if m else {}
    fr = int(SR / FPS); mouth = [float(np.sqrt(np.mean(vo[k * fr:(k + 1) * fr] ** 2))) for k in range(N // fr)]
    mx = max(mouth) or 1; json.dump([round(v / mx, 3) for v in mouth], open(f"{out}/mouth.json", "w"))
    return {"voice_minus_bed_db": round(rms(vo[sp]) - rms((md + sx)[sp]), 1), "lufs": float(ln.get("output_i", "nan")),
            "true_peak_db": float(ln.get("output_tp", "nan")), "music_bpm": BPM, "music_drop_line": 0}

# =====================================================================
# visuals
# =====================================================================
def make_renderer(spec, tl, spans, ts, ctop, cbot, top, bot, out):
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
    FCACHE = {}
    def P(k, s):
        key = ("p", k, s)
        if key not in FCACHE: FCACHE[key] = ImageFont.truetype(POP[k], s)
        return FCACHE[key]
    def A(s, bold=False):
        key = ("a", bold, s)
        if key not in FCACHE: FCACHE[key] = ImageFont.truetype(LIB.format("Bold" if bold else "Regular"), s)
        return FCACHE[key]
    mouth = json.load(open(f"{out}/mouth.json"))
    lines = tl["lines"]; LAST = len(lines) - 1; TOTAL = tl["total"]
    S = {l["i"]: l["start"] for l in lines}; E = {l["i"]: l["end"] for l in lines}
    ACC = set(w.lower() for w in spec.get("accent_words", []))
    rng = np.random.default_rng(9)
    CONF = [(rng.uniform(-1, 1), rng.uniform(.6, 1.4), int(rng.integers(0, 5)), rng.uniform(0, 6.28)) for _ in range(70)]

    def wrap(d, txt, f, w):
        out_, cur = [], ""
        for wd in txt.split(" "):
            tst = (cur + " " + wd).strip()
            if d.textlength(tst, font=f) <= w or not cur: cur = tst
            else: out_.append(cur); cur = wd
        if cur: out_.append(cur)
        return out_
    def ctext(d, xy, txt, f, fill, anchor="mm", stroke=0, sfill=None):
        d.text(xy, txt, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill)

    # ---------- shapes
    def heart(d, cx, cy, r, col, broken=0.):
        if broken <= 0:
            d.ellipse([cx - r, cy - r * .8, cx, cy + r * .2], fill=col); d.ellipse([cx, cy - r * .8, cx + r, cy + r * .2], fill=col)
            d.polygon([(cx - r * .97, cy - r * .1), (cx + r * .97, cy - r * .1), (cx, cy + r)], fill=col)
        else:
            off = broken * 14; dy = broken ** 2 * 60
            d.ellipse([cx - r - off, cy - r * .8 + dy, cx - off, cy + r * .2 + dy], fill=col)
            d.polygon([(cx - r * .97 - off, cy - r * .1 + dy), (cx - off, cy - r * .1 + dy), (cx - off, cy + r + dy)], fill=col)
            d.ellipse([cx + off, cy - r * .8 + dy, cx + r + off, cy + r * .2 + dy], fill=col)
            d.polygon([(cx + off, cy - r * .1 + dy), (cx + r * .97 + off, cy - r * .1 + dy), (cx + off, cy + r + dy)], fill=col)
    def shape(d, kind, cx, cy, r, col):
        if kind == "tri": d.polygon([(cx, cy - r), (cx + r, cy + r * .8), (cx - r, cy + r * .8)], fill=col)
        elif kind == "dia": d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=col)
        elif kind == "circ": d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        else: d.rectangle([cx - r * .85, cy - r * .85, cx + r * .85, cy + r * .85], fill=col)
    def cursor(d, x, y, press=0., dark=False):
        s = 1 - .15 * press
        pts = [(0, 0), (0, 40), (10, 31), (17, 47), (24, 44), (17, 29), (30, 29)]
        pts = [(x + px * s, y + py * s) for px, py in pts]
        d.polygon([(px + 3, py + 3) for px, py in pts], fill=(0, 0, 0, 90) if not dark else (0, 0, 0))
        d.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))
        d.line(pts + [pts[0]], fill=(0, 0, 0), width=3)
    def flame(d, cx, cy, s, t):
        w = math.sin(t * 14) * s * .08
        d.polygon([(cx, cy - s + w), (cx + s * .55, cy - s * .1), (cx + s * .45, cy + s * .55), (cx, cy + s * .7),
                   (cx - s * .45, cy + s * .55), (cx - s * .55, cy - s * .1)], fill=C["coral"])
        d.polygon([(cx, cy - s * .45 - w), (cx + s * .28, cy + s * .1), (cx, cy + s * .55), (cx - s * .28, cy + s * .1)], fill=C["gold"])

    def presenter(d, x, y, throw=0., t=0.):
        """flat vector quiz host (original): navy hair bun, coral blazer, arm throws on `throw` 0..1."""
        bob = math.sin(t * 3) * 3
        d.rounded_rectangle([x + 30, y + 150 + bob, x + 190, y + 280], 50, fill=C["coral"])           # torso
        d.polygon([(x + 95, y + 155 + bob), (x + 125, y + 155 + bob), (x + 110, y + 205 + bob)], fill=C["white"])  # collar
        d.rectangle([x + 98, y + 125 + bob, x + 122, y + 160 + bob], fill=(226, 172, 138))           # neck
        d.ellipse([x + 55, y + 30 + bob, x + 165, y + 140 + bob], fill=C["skin"])                     # face
        d.ellipse([x + 80, y - 5 + bob, x + 140, y + 45 + bob], fill=C["navy"])                       # bun
        d.chord([x + 50, y + 22 + bob, x + 170, y + 120 + bob], 180, 360, fill=C["navy"])              # hair
        blink = (t % 3.4) < .12
        for ex in (x + 88, x + 132):
            if blink: d.line([ex - 7, y + 88 + bob, ex + 7, y + 88 + bob], fill=C["dark"], width=4)
            else: d.ellipse([ex - 6, y + 81 + bob, ex + 6, y + 95 + bob], fill=C["dark"])
        d.arc([x + 92, y + 92 + bob, x + 128, y + 120 + bob], 20, 160, fill=C["dark"], width=4)
        d.ellipse([x + 72, y + 100 + bob, x + 86, y + 110 + bob], fill=C["coral2"]); d.ellipse([x + 134, y + 100 + bob, x + 148, y + 110 + bob], fill=C["coral2"])
        # throwing arm: shoulder pivot
        sx, sy = x + 170, y + 175 + bob
        ang = math.radians(lerp(110, -40, eo(throw)) if throw < 1 else -40 + 150 * eo(clamp((throw - 1) / .6)))
        ex, ey = sx + 70 * math.cos(ang), sy - 70 * math.sin(ang)
        d.line([sx, sy, ex, ey], fill=C["coral"], width=34); d.ellipse([ex - 16, ey - 16, ex + 16, ey + 16], fill=C["skin"])
        d.line([x + 50, y + 180 + bob, x + 30, y + 260 + bob], fill=C["coral"], width=34)
        return ex, ey

    def bomb(d, cx, cy, frac, t, alive=True):
        d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=(24, 24, 32), outline=C["dark"], width=3)
        d.ellipse([cx - 24, cy - 26, cx - 8, cy - 12], fill=(90, 96, 120))
        d.rectangle([cx + 14, cy - 50, cx + 34, cy - 30], fill=(60, 62, 80))
        # fuse: curve that shortens with frac
        pts = [(cx + 24 + 60 * u + 10 * math.sin(u * 7), cy - 50 - 36 * math.sin(u * 2.2)) for u in np.linspace(0, frac, 24)]
        if len(pts) > 1: d.line(pts, fill=(200, 170, 120), width=6)
        if alive and frac > 0:
            px, py = pts[-1]
            r = 10 + 4 * math.sin(t * 40)
            d.ellipse([px - r, py - r, px + r, py + r], fill=C["gold"]); d.ellipse([px - r / 2, py - r / 2, px + r / 2, py + r / 2], fill=C["white"])
            for k in range(5):
                a = t * 23 + k * 1.3; d.line([px, py, px + 22 * math.cos(a), py + 22 * math.sin(a)], fill=C["gold"], width=3)
        sec = int(math.ceil(frac * 6.5))
        ctext(d, (cx, cy + 4), str(sec), P("ExtraBold", 34), C["white"])

    # ---------- TOP: gamified quiz
    TG = tuple((40, 556 + k * 80, 1040, 626 + k * 80) for k in range(4))
    NEXT = (800, 872, 1040, 940)
    def top_frame(t, tau, callouts=()):
        im = Image.new("RGB", (W, MID), C["bg"]); d = ImageDraw.Draw(im, "RGBA")
        for y in range(0, MID, 4): d.line([0, y, W, y], fill=mix(C["bg2"], C["bg"], y / MID))
        for k in range(18):                      # floating dots
            x = (k * 173 + tau * 18 * (1 + k % 3)) % W; y = 200 + (k * 97) % 740
            d.ellipse([x, y, x + 6, y + 6], fill=(42, 58, 122, 160))
        i, tq, q = top.q(tau); st = top.state(tau); K = top.k
        ok = q["pick"] == q["answer"]
        answered = tq >= K["nxt"]
        # HUD ---------------------------------------------------------------
        frac = 1 - clamp((min(tq, K["nxt"]) - K["bomb0"]) / q.get("bomb_s", 6.5))
        if tq < K["bomb0"]: frac = 1
        bomb(d, 100, 262, frac, tau, alive=not answered)
        pct_prev = (st["answered"] - (1 if answered else 0)) / top.N
        pct_now = st["answered"] / top.N
        pct = lerp(pct_prev, pct_now, eo(prog(tq, K["nxt"] + .2, .5))) if answered else pct_now
        pct = min(pct, 1.0)
        d.rounded_rectangle([170, 236, 640, 288], 26, fill=C["navy"])
        if pct > 0: d.rounded_rectangle([174, 240, 174 + max(44, int(462 * pct)), 284], 22, fill=C["coral"])
        ctext(d, (405, 262), f"QUIZ  {int(round(pct * 100))}%", P("ExtraBold", 28), C["white"])
        lives_now = st["lives"]
        for k in range(3):
            if k < lives_now: heart(d, 690 + k * 52, 258, 22, C["coral"])
            elif (not ok and answered and k == lives_now and tq - K["nxt"] < .9): heart(d, 690 + k * 52, 258, 22, C["coral"], broken=clamp((tq - K["nxt"]) / .9))
            else: heart(d, 690 + k * 52, 258, 22, (60, 66, 100))
        sc_shown = st["score"]
        if answered and ok: sc_shown = int(st["score"] - st["last_pts"] * (1 - eo(prog(tq, K["nxt"] + .45, .6))))
        d.rounded_rectangle([850, 234, 1044, 290], 28, fill=C["gold2"])
        ctext(d, (947, 262), f"{sc_shown:,}", P("ExtraBold", 32), C["dark"])
        if st["streak"] >= 2 and answered and ok:
            flame(d, 820, 330, 26, tau); ctext(d, (820, 372), f"x{st['streak']}", P("ExtraBold", 26), C["gold"])
        # presenter + question card ------------------------------------------
        hx, hy = presenter(d, 40, 300, throw=clamp(tq / .45) if tq < 1.2 else 1 + clamp((tq - 1.2) / .6), t=tau)
        kin = eo(prog(tq, .1, .45)); kout = prog(tq, K["out"], .45)
        cx0, cy0 = lerp(hx, 300, kin), lerp(hy - 40, 310, kin)
        cw, ch_ = lerp(60, 740, kin), lerp(40, 220, kin)
        cx0 += 1100 * eio(kout)
        if kin > .02:
            d.rounded_rectangle([cx0 + 6, cy0 + 8, cx0 + cw + 6, cy0 + ch_ + 8], 28, fill=(0, 0, 0, 90))
            d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch_], 28, fill=C["white"])
            if kin > .9:
                d.text((cx0 + 36, cy0 + 26), f"QUESTION {i % top.N + 1}/{top.N}", font=P("Bold", 24), fill=C["coral"])
                f = P("Bold", 40); yy = cy0 + 62
                for r in wrap(d, q["q"], f, cw - 72): d.text((cx0 + 36, yy), r, font=f, fill=C["dark"]); yy += 48
        # tiles --------------------------------------------------------------
        sel = tq >= K["sel"]
        for j, (x0, y0, x1, y1) in enumerate(TG):
            kk = back(prog(tq, K["tiles"] + j * .08, .3))
            if kk <= 0: continue
            col = C["navy"]
            sh = 0; sc = 1.0; dim = 0.
            if sel and j == q["pick"] and not answered: sc = 1 + .05 * (1 - eo(prog(tq, K["sel"], .25))) + .03
            if sel and j != q["pick"] and not answered: dim = .55
            if answered:
                if j == q["answer"]: col = C["green"]; sc = 1 + .06 * math.sin(clamp((tq - K["nxt"]) / .4) * math.pi) + (.03 * math.sin(tq * 8) if not ok else 0)
                elif j == q["pick"] and not ok: col = C["red"]; sh = 14 * math.sin((tq - K["nxt"]) * 60) * (1 - prog(tq, K["nxt"], .45))
                else: dim = .7
            xk = (1 - kk) * -1100 * (1 if j % 2 else -1) + 1100 * eio(prog(tq, K["out"] + j * .05, .4)); yk = 0
            cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
            hw, hh = (x1 - x0) / 2 * sc, (y1 - y0) / 2 * sc
            X0, Y0, X1, Y1 = cxm - hw + sh + xk, cym - hh + yk, cxm + hw + sh + xk, cym + hh + yk
            d.rounded_rectangle([X0, Y0 + 6, X1, Y1 + 6], 22, fill=mix(col, (0, 0, 0), .45))
            d.rounded_rectangle([X0, Y0, X1, Y1], 22, fill=col, outline=C["navy2"], width=3)
            bc = C["coral"] if col == C["navy"] else C["white"]
            d.ellipse([X0 + 18, (Y0 + Y1) / 2 - 24, X0 + 66, (Y0 + Y1) / 2 + 24], fill=bc)
            ctext(d, (X0 + 42, (Y0 + Y1) / 2 + 1), "ABCD"[j], P("ExtraBold", 28), C["white"] if col == C["navy"] else col)
            f = P("Bold", 32)
            d.text((X0 + 90, (Y0 + Y1) / 2), q["opts"][j], font=f, fill=C["white"], anchor="lm")
            if sel and j == q["pick"] and not answered:
                d.rounded_rectangle([X0 - 5, Y0 - 5, X1 + 5, Y1 + 5], 27, outline=C["coral"], width=6)
                d.rounded_rectangle([X0 - 11, Y0 - 11, X1 + 11, Y1 + 11], 32, outline=(255, 90, 78, 90), width=4)
                d.ellipse([X1 - 66, (Y0 + Y1) / 2 - 22, X1 - 22, (Y0 + Y1) / 2 + 22], fill=C["coral"]); d.line([(X1 - 54, (Y0 + Y1) / 2), (X1 - 46, (Y0 + Y1) / 2 + 9), (X1 - 32, (Y0 + Y1) / 2 - 8)], fill=C["white"], width=6)
            if answered and j == q["answer"] and not ok:
                d.rounded_rectangle([X0 - 6, Y0 - 6, X1 + 6, Y1 + 6], 30, outline=C["white"], width=5)
                ctext(d, (X1 - 120, (Y0 + Y1) / 2), "RIGHT ANSWER", P("ExtraBold", 24), C["white"])
            if dim: d.rounded_rectangle([X0, Y0, X1, Y1 + 6], 22, fill=(7, 11, 26, int(255 * dim * .7)))
        # NEXT button
        en = sel and not answered
        x0, y0, x1, y1 = NEXT; pr = 4 if (K["nxt"] - .05 <= tq < K["nxt"] + .1) else 0
        d.rounded_rectangle([x0, y0 + 6, x1, y1 + 6], 30, fill=mix(C["coral"], (0, 0, 0), .4) if en else (30, 36, 70))
        d.rounded_rectangle([x0, y0 + pr, x1, y1 + pr], 30, fill=C["coral"] if en else C["navy"])
        ctext(d, ((x0 + x1) / 2 - 14, (y0 + y1) / 2 + pr), "NEXT", P("ExtraBold", 32), C["white"] if en else C["muted"])
        ax, ay = x1 - 52, (y0 + y1) / 2 + pr; d.polygon([(ax, ay - 12), (ax + 18, ay), (ax, ay + 12)], fill=C["white"] if en else C["muted"])
        if not sel: ctext(d, (520, 906), "Faster answer = more points", P("SemiBold", 26), C["muted"])
        # big feedback ---------------------------------------------------------
        if answered and tq < K["out"]:
            k = back(prog(tq, K["nxt"], .35))
            if ok:
                d.rounded_rectangle([150, 640, 930, 800], 40, fill=(7, 11, 26, int(170 * clamp(k))))
                ctext(d, (540, 690), "CORRECT!", P("Black", int(110 * k) + 1), C["white"], stroke=8, sfill=C["green"])
                ctext(d, (540, 768), f"+{st['last_pts']}  speed bonus", P("ExtraBold", int(40 * k) + 1), C["gold"], stroke=5, sfill=C["dark"])
                tt = tq - K["nxt"]
                for (vx, vs, ci, ph) in CONF:                 # confetti
                    px = 540 + vx * 520 * eo(clamp(tt / .8)); py = 680 - 520 * vs * tt + 600 * tt * tt
                    if py < MID:
                        cc = [C["coral"], C["gold"], C["blue"], C["green"], C["white"]][ci]
                        a = ph + tt * 9; d.polygon([(px + 9 * math.cos(a), py + 9 * math.sin(a)), (px - 9 * math.cos(a), py - 9 * math.sin(a)),
                                                    (px - 5 * math.sin(a), py + 5 * math.cos(a))], fill=cc)
                ft = prog(tq, K["nxt"] + .45, .6)                 # points fly to the score pill
                if 0 < ft < 1:
                    ctext(d, (lerp(540, 947, eio(ft)), lerp(768, 262, eio(ft))), f"+{st['last_pts']}", P("ExtraBold", 34), C["gold"], stroke=4, sfill=C["dark"])
                if tt < .12: d.rectangle([0, 0, W, MID], fill=(255, 255, 255, int(90 * (1 - tt / .12))))
            else:
                d.rounded_rectangle([110, 630, 970, 860], 40, fill=(7, 11, 26, int(185 * clamp(k))))
                ctext(d, (540, 680), "OOPS!", P("Black", int(100 * k) + 1), C["white"], stroke=8, sfill=C["red"])
                ctext(d, (540, 752), "-1 life · see why", P("ExtraBold", int(40 * k) + 1), C["coral2"], stroke=5, sfill=C["dark"])
                if q.get("why") and tq > K["nxt"] + .5:
                    ctext(d, (540, 815), q["why"], P("SemiBold", 32), C["white"], stroke=4, sfill=C["dark"])
                if tq - K["nxt"] < .15: d.rectangle([0, 0, W, MID], fill=(230, 57, 70, int(80 * (1 - (tq - K["nxt"]) / .15))))
        # cursor ---------------------------------------------------------------
        tc = TG[q["pick"]]; tx, ty = 640, (tc[1] + tc[3]) / 2 + 6
        nx, ny = (NEXT[0] + NEXT[2]) / 2 + 30, (NEXT[1] + NEXT[3]) / 2
        if tq < 1.0: cxp, cyp = lerp(nx, 760, eio(clamp(tq / 1.0))), lerp(ny, 640, eio(clamp(tq / 1.0)))
        elif tq < K["sel"]: k = eio(prog(tq, 1.0, .6)); cxp, cyp = lerp(760, tx, k), lerp(640, ty, k)
        elif tq < 2.0: cxp, cyp = tx, ty
        elif tq < K["nxt"]: k = eio(prog(tq, 2.0, .5)); cxp, cyp = lerp(tx, nx, k), lerp(ty, ny, k)
        else: cxp, cyp = nx, ny
        press = max(1 - abs(tq - K["sel"]) / .12, 1 - abs(tq - K["nxt"]) / .12, 0)
        for tk in (K["sel"], K["nxt"]):                       # click ripple
            if 0 <= tq - tk < .35:
                r = 10 + 60 * (tq - tk); d.ellipse([cxp - r, cyp - r, cxp + r, cyp + r], outline=(255, 255, 255, int(220 * (1 - (tq - tk) / .35))), width=4)
        cursor(d, cxp, cyp, press)
        # callouts (mechanics named by the voice) -------------------------------
        for (box, label, kk) in callouts:
            if kk <= 0: continue
            x0, y0, x1, y1 = box; pulse = 4 * math.sin(t * 10)
            d.rounded_rectangle([x0 - 10 - pulse, y0 - 10 - pulse, x1 + 10 + pulse, y1 + 10 + pulse], 30, outline=C["gold"], width=6)
            ly = y1 + 36 if y1 < 420 else y0 - 30
            ctext(d, ((x0 + x1) / 2, ly), label, P("Black", int(34 * back(kk)) + 1), C["dark"], stroke=0)
            tw_ = d.textlength(label, font=P("Black", 34))
            if kk > .9:
                d.rounded_rectangle([(x0 + x1) / 2 - tw_ / 2 - 16, ly - 26, (x0 + x1) / 2 + tw_ / 2 + 16, ly + 26], 26, fill=C["gold"])
                ctext(d, ((x0 + x1) / 2, ly), label, P("Black", 34), C["dark"])
        return im

    # ---------- BOTTOM: traditional form
    BR = [(118, 1272 + k * 64) for k in range(4)]
    BN = (812, 1490, 1000, 1550)
    UPG = spec.get("upgrade", {})
    UPT = {st_["kind"]: retro.at(tl, st_.get("line", UPG.get("line")), st_["word"]) for st_ in UPG.get("steps", [])}
    UPXY = {"timer": (960, 190), "lives": (650, 44), "feedback": (540, 330)}
    UPLAB = {st_["kind"]: st_.get("label", "+ " + st_["kind"].upper()) for st_ in UPG.get("steps", [])}
    def up(kind, t): return back(prog(t, UPT[kind] - .05, .45), 3.2) if kind in UPT else 0.
    def pop_fx(d, kind, t):
        """big POP when a mechanic is added: flash, shock ring, sparks and a floating label."""
        if kind not in UPT: return
        k = t - UPT[kind] + .05
        if k < 0 or k > 1.6: return
        x, y = UPXY[kind]
        if k < .18: d.rectangle([0, 0, W, H - MID], fill=(255, 255, 255, int(150 * (1 - k / .18))))
        for r_, col, sp in ((1, C["coral"], 520), (.7, C["gold"], 380)):
            rr = sp * eo(clamp(k / .55)) * r_
            if k < .55: d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (int(255 * (1 - k / .55)),), width=int(14 * (1 - k / .55)) + 2)
        for a in range(14):
            ang = a * 2 * math.pi / 14 + .2; r1 = 60 + 260 * eo(clamp(k / .5)); r2 = r1 + 40 * (1 - clamp(k / .5))
            if k < .5: d.line([x + r1 * math.cos(ang), y + r1 * math.sin(ang), x + r2 * math.cos(ang), y + r2 * math.sin(ang)], fill=[C["gold"], C["coral"], C["blue"]][a % 3], width=8)
        for (vx, vs, ci, ph) in CONF[:24]:
            px = x + vx * 320 * eo(clamp(k / .8)); py = y - 260 * vs * k + 520 * k * k
            if k < 1.1: d.rectangle([px, py, px + 12, py + 12], fill=[C["coral"], C["gold"], C["blue"], C["green"], C["coral2"]][ci])
        kb = back(clamp(k / .3), 3.0); fade = 1 - clamp((k - 1.2) / .4)
        lx, ly = (x - 150 if x > 800 else (x + 40 if kind == "lives" else x)), (y + 120 if kind != "feedback" else y - 120) - 30 * k
        f = P("Black", max(1, int(54 * kb)))
        tw_ = d.textlength(UPLAB[kind], font=f)
        if kb > .1:
            d.rounded_rectangle([lx - tw_ / 2 - 26, ly - 42 * kb, lx + tw_ / 2 + 26, ly + 42 * kb], 40, fill=C["coral"] + (int(255 * fade),))
            ctext(d, (lx, ly), UPLAB[kind], f, C["white"] + (int(255 * fade),))
    def bot_frame(t, tau):
        im = Image.new("RGB", (W, H - MID), (255, 255, 255)); d = ImageDraw.Draw(im, "RGBA")
        o = MID
        i, lq, q = bot.q(tau)
        uT, uL, uF = up("timer", t), up("lives", t), up("feedback", t); uA = clamp(max(uT, uL, uF))
        if uA > 0:                                    # the form warms up while it is being gamified
            d.rectangle([0, 0, W, H - MID], fill=mix((255, 255, 255), (238, 241, 250), uA))
        hd = mix((232, 232, 232), C["navy"], uA)
        d.rectangle([0, 0, W, 86], fill=hd); d.line([0, 86, W, 86], fill=mix((190, 190, 190), C["coral"], uA), width=2 + int(4 * uA))
        d.text((60, 26), "Information Security Training", font=A(32, True), fill=mix((20, 20, 20), C["white"], uA))
        d.text((1020, 30), f"Page {bot.page0 + i} of 40", font=A(28), fill=mix((110, 110, 110), C["muted"], uA), anchor="ra")
        if uL > 0:                                    # lives
            for k in range(3):
                s_ = back(clamp((t - UPT["lives"] + .05) / .35 - k * .45), 3.2)
                if s_ > 0: heart(d, 600 + k * 50, 44, 20 * s_, C["coral"])
        d.text((80, 130), f"Question {bot.page0 + i}", font=A(36, True), fill=(0, 0, 0))
        f = A(38); yy = 186
        for r in wrap(d, q["q"], f, 900 - int(160 * uT)): d.text((80, yy), r, font=f, fill=(0, 0, 0)); yy += 48
        if uT > 0:                                    # timer
            kk = clamp(uT, 0, 1.4); fr_ = 1 - clamp(lq / bot.k["nxt"]) if lq < bot.k["nxt"] else 0
            if kk > .05:
                bx, by = 960, 190
                if kk < .98 or uT > 1.02: d.ellipse([bx - 52 * kk, by - 52 * kk, bx + 52 * kk, by + 52 * kk], fill=(24, 24, 32))
                else: bomb(d, bx, by, max(.05, fr_), t, alive=fr_ > 0)
        picked = lq >= bot.k["sel"]
        for j, (x, y) in enumerate(BR):
            y -= o
            if uF > 0 and picked and j == q["pick"]:   # light feedback on SELECT
                d.rounded_rectangle([x - 34, y - 28, 760, y + 28], 18, fill=(255, 90, 78, int(60 * uF)), outline=(255, 90, 78, int(255 * uF)), width=4)
            d.ellipse([x - 16, y - 16, x + 16, y + 16], outline=(0, 0, 0) if not (uF and picked and j == q["pick"]) else C["coral"], width=3)
            if picked and j == q["pick"]: d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(0, 0, 0) if not uF else C["coral"])
            d.text((x + 34, y), f"{'ABCD'[j]})  {q['opts'][j]}", font=A(36), fill=(0, 0, 0), anchor="lm")
        x0, y0, x1, y1 = BN; y0 -= o; y1 -= o
        d.rectangle([x0, y0, x1, y1], fill=mix((239, 239, 239), C["coral"], uA), outline=mix((120, 120, 120), C["coral"], uA), width=2)
        d.text(((x0 + x1) / 2, (y0 + y1) / 2), "Next >", font=A(32), fill=mix((0, 0, 0), C["white"], uA), anchor="mm")
        # big feedback after NEXT (shown on the new page): only once the "feedback" upgrade is on
        tsw = lq if lq < bot.k["swap"] else lq - bot.P
        since = (lq - bot.k["swap"]) if lq >= bot.k["swap"] else lq + (bot.P - bot.k["swap"])
        demo = t - UPT.get("feedback", 1e9)
        if 0 <= demo < 1.6: since = demo
        if uF > .5 and since < 1.6 and (demo > since - .1 or 0 <= demo < 1.6):
            kk = back(clamp(since / .3), 3.0)
            if since < .15: d.rectangle([0, 0, W, H - MID], fill=(43, 182, 115, int(110 * (1 - since / .15))))
            # last answer turns green with a check
            jy = BR[q["pick"]][1] - o
            d.rounded_rectangle([BR[0][0] - 34, jy - 28, 760, jy + 28], 18, fill=(43, 182, 115, 70), outline=C["green"], width=4)
            # confetti cannons from both sides + a burst around the banner
            for n_, (vx, vs, ci, ph) in enumerate(CONF):
                side = -1 if n_ % 2 else 1
                sx_ = 540 - side * 560; vx_ = side * (420 + 260 * abs(vx)); vy_ = -(700 + 380 * vs)
                px = sx_ + vx_ * since; py = 560 + vy_ * since + 900 * since * since
                a = ph + since * 12
                cc = [C["coral"], C["gold"], C["blue"], C["green"], C["coral2"]][ci]
                if -20 < py < H - MID: d.polygon([(px + 13 * math.cos(a), py + 13 * math.sin(a)), (px - 13 * math.cos(a), py - 13 * math.sin(a)),
                                                  (px - 7 * math.sin(a), py + 7 * math.cos(a))], fill=cc)
            for a_ in range(12):
                ang = a_ * math.pi / 6; r1 = 150 + 220 * eo(clamp(since / .5)); r2 = r1 + 50 * (1 - clamp(since / .5))
                if since < .5: d.line([540 + r1 * math.cos(ang), 330 + r1 * math.sin(ang) * .6, 540 + r2 * math.cos(ang), 330 + r2 * math.sin(ang) * .6], fill=C["gold"], width=9)
            d.rounded_rectangle([540 - 260 * kk, 330 - 70 * kk, 540 + 260 * kk, 330 + 70 * kk], 50, fill=C["green"], outline=C["white"], width=6)
            ctext(d, (540, 318), "CORRECT!", P("Black", int(70 * kk) + 1), C["white"])
            ctext(d, (540, 372), "+100", P("ExtraBold", int(34 * kk) + 1), C["gold"], stroke=4, sfill=C["dark"])
            ft = clamp((since - .5) / .6)
            if 0 < ft < 1: ctext(d, (lerp(540, 870, eio(ft)), lerp(372, 44, eio(ft))), "+100", P("ExtraBold", 34), C["gold"], stroke=4, sfill=C["dark"])
        d.line([60, 640, 1020, 640], fill=(210, 210, 210), width=2)
        d.text((60, 656), "Compliance Department  ·  Do not close this window", font=A(24), fill=(140, 140, 140))
        # cursor
        tx, ty = BR[q["pick"]][0] + 4, BR[q["pick"]][1] - o + 2
        nx, ny = (x0 + x1) / 2 + 20, (y0 + y1) / 2
        K = bot.k
        if lq < .3: cxp, cyp = nx, ny
        elif lq < K["sel"]: k = eio(prog(lq, .3, .8)); cxp, cyp = lerp(nx, tx, k), lerp(ny, ty, k)
        elif lq < 1.55: cxp, cyp = tx, ty
        elif lq < K["nxt"]: k = eio(prog(lq, 1.55, .8)); cxp, cyp = lerp(tx, nx, k), lerp(ty, ny, k)
        else: cxp, cyp = nx, ny
        press = max(1 - abs(lq - K["sel"]) / .1, 1 - abs(lq - K["nxt"]) / .1, 0)
        for kind in ("timer", "lives", "feedback"): pop_fx(d, kind, t)
        cursor(d, cxp, cyp, press, dark=True)
        return im

    # ---------- guide + subtitles
    def sprite(rows, s):
        from PIL import Image as I
        im = I.new("RGBA", (16, len(rows)), (0, 0, 0, 0))
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch != ".": im.putpixel((x, y), retro.rgb(retro.SPR_PAL.get(ch, "dark")) + (255,))
        return im.resize((16 * s, len(rows) * s), I.NEAREST)
    SCACHE = {}
    def guide(im, x, y, s, t, pose_override=None):
        fi = int(t * FPS); m = mouth[fi] if fi < len(mouth) else 0
        mo = 0 if m < .12 else (1 if m < .45 else 2)
        pose = pose_override or ("wave" if (t % 4) < .9 else "idle")
        key = (pose, (t % 3.1) < .12, mo, s)
        if key not in SCACHE: SCACHE[key] = sprite(retro.girl_rows(pose=pose, blink=key[1], mouth=mo), s)
        sp = SCACHE[key]; bob = int(2 * math.sin(t * 4)) * (s // 4)
        im.paste(sp, (int(x), int(y + bob)), sp)
    def current_line(t):
        cur = None
        for l in lines:
            nxt = lines[l["i"] + 1]["start"] - .05 if l["i"] < LAST else TOTAL
            if (l["start"] - .05 if l["i"] else -1) <= t < min(nxt, l["end"] + 1.0 if l["i"] < LAST else TOTAL): cur = l
        return cur
    def subtitle(im, d, t, box, size=50):
        cur = current_line(t)
        if not cur: return
        x0, yc, x1 = box
        f = P("SemiBold", size); words = cur["cap"].split(" ")
        rows = wrap(d, cur["cap"], f, x1 - x0 - 60)
        lh = int(size * 1.32); hgt = len(rows) * lh + 44
        y0 = yc - hgt / 2
        k = 1.0 if cur["i"] == 0 else eo(prog(t, cur["start"] - .05, .2))
        d.rounded_rectangle([x0, y0 + (1 - k) * 20, x1, y0 + hgt + (1 - k) * 20], 32, fill=(7, 11, 26, int(225 * k)))
        d.rounded_rectangle([x0, y0 + (1 - k) * 20, x1, y0 + hgt + (1 - k) * 20], 32, outline=(255, 90, 78, int(255 * k)), width=4)
        dur = max(.3, (cur["end"] - cur["start"])); nw = len(words)
        shown = nw if (t >= cur["end"] or cur["i"] == 0) else int(nw * clamp((t - cur["start"]) / (dur * .8)) + 1)
        wi = 0; yy = y0 + 22 + (1 - k) * 20
        for r in rows:
            xx = x0 + 30
            for wd in r.split(" "):
                if wi < shown:
                    col = C["coral"] if wd.lower().strip(".,:!?\"") in ACC else C["white"]
                    d.text((xx, yy), wd, font=f, fill=col)
                xx += d.textlength(wd + " ", font=f); wi += 1
            yy += lh

    def frozen(img, top_half):
        g = ImageOps.grayscale(img).convert("RGB")
        g = Image.blend(g, Image.new("RGB", g.size, (40, 44, 56)), .45)
        return g

    callspec = spec.get("callouts", [])
    CBOX = {"progress": (170, 236, 640, 288), "lives": (664, 232, 820, 284), "countdown": (56, 196, 190, 306),
            "points": (850, 234, 1044, 290), "feedback": (40, 556, 1040, 866)}
    def callouts_at(t):
        out_ = []
        for c in callspec:
            ta = retro.at(tl, c["line"], c["word"])
            if t >= ta - .05 and t < E[c["line"]] + .4:
                out_.append((CBOX[c["box"]], c["label"], prog(t, ta - .05, .25)))
        return out_

    FROZ = {}
    def frame(t):
        j = min(len(ts) - 1, int(round(t * FPS)))
        sc = next((s for (a, b, s) in spans if a <= t < b), spans[-1][2]); act = sc["active"]
        tt, tb = float(ctop[j]), float(cbot[j])
        im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im, "RGBA")
        if act in ("top", "both"): im.paste(top_frame(t, tt, callouts_at(t) if act == "top" else ()), (0, 0))
        else:
            key = ("t", round(tt, 3))
            if key not in FROZ: FROZ.clear() if len(FROZ) > 4 else None; FROZ[key] = frozen(top_frame(t, tt), True)
            im.paste(FROZ[key], (0, 0))
        if act in ("bottom", "both"): im.paste(bot_frame(t, tb), (0, MID))
        else:
            key = ("b", round(tb, 3))
            if key not in FROZ: FROZ[key] = frozen(bot_frame(t, tb), False)
            im.paste(FROZ[key], (0, MID))
        d = ImageDraw.Draw(im, "RGBA")
        # divider
        d.rectangle([0, MID - 5, W, MID + 5], fill=C["coral"])
        # labels on each half
        def tag(x, y, txt, on):
            f = P("ExtraBold", 26); w_ = d.textlength(txt, font=f)
            d.rounded_rectangle([x, y, x + w_ + 36, y + 46], 23, fill=C["coral"] if on else (90, 94, 110))
            d.text((x + 18, y + 23), txt, font=f, fill=C["white"], anchor="lm")
        if act != "both":
            tag(40, 896, "GAMIFIED", act == "top"); tag(40, MID + 690, "TRADITIONAL", act == "bottom")
        # guide + subtitles
        end_on = spec.get("end") and t >= S[spec["end"]["line"]]
        if act == "bottom":
            d.rectangle([0, 0, W, MID - 5], fill=(7, 11, 26, 70))
            guide(im, 50, 390, 9, t); subtitle(im, d, t, (230, 600, 1040), 52)
        elif act == "top":
            guide(im, 50, MID + 150, 9, t); subtitle(im, d, t, (230, MID + 360, 1040), 52)
        else:
            if not end_on:
                d.rounded_rectangle([20, MID - 115, 1060, MID + 115], 40, fill=(7, 11, 26, 120))
                guide(im, 36, MID - 112, 6, t); subtitle(im, d, t, (160, MID, 1050), 46)
        # end card: comment GAME or FORM
        if end_on:
            te = S[spec["end"]["line"]]; k = back(prog(t, te, .4)); pulse = 1 + .04 * math.sin(t * 8)
            d.rectangle([0, 0, W, H], fill=(7, 11, 26, int(225 * clamp((t - te) / .3))))
            en = spec["end"]
            ctext(d, (540, 470), en.get("pre", "COMMENT"), P("Black", int(64 * k) + 1), C["white"])
            ctext(d, (540, 600), en.get("word", "TRAINING"), P("Black", int(150 * k * pulse) + 1), C["white"], stroke=12, sfill=C["coral"])
            kg = back(prog(t, te + .5, .4))
            if kg > 0:                                   # the free guide: a document with a coral ribbon
                gx, gy = 540, 820 - (1 - kg) * 40; sw = 1 + .03 * math.sin(t * 5)
                d.rounded_rectangle([gx - 95 * sw + 10, gy - 120 + 12, gx + 95 * sw + 10, gy + 120 + 12], 18, fill=(0, 0, 0, 110))
                d.rounded_rectangle([gx - 95 * sw, gy - 120, gx + 95 * sw, gy + 120], 18, fill=C["white"])
                d.rectangle([gx - 95 * sw, gy - 120, gx + 95 * sw, gy - 60], fill=C["navy"])
                ctext(d, (gx, gy - 90), "GUIDE", P("Black", 34), C["white"])
                for r in range(5): d.rounded_rectangle([gx - 70, gy - 40 + r * 28, gx + 70 - (r % 2) * 40, gy - 28 + r * 28], 6, fill=(205, 210, 225))
                d.polygon([(gx + 50, gy - 120), (gx + 80, gy - 120), (gx + 80, gy - 40), (gx + 65, gy - 55), (gx + 50, gy - 40)], fill=C["coral"])
                ctext(d, (540, 1000), en.get("sub", "and get our free guide"), P("Bold", 46), C["gold"], stroke=5, sfill=C["dark"])
            guide(im, 50, 1080, 8, t, pose_override="cheer" if int(t * 3) % 2 else "wave")
            subtitle(im, d, t, (230, 1300, 1040), 46)
            d.text((540, H - 300), "ludogic.dev", font=P("SemiBold", 34), fill=C["muted"], anchor="mm")
        return im
    return frame

# =====================================================================
# build
# =====================================================================
def build(spec_path, out, preview=False):
    t_start = time.time(); ensure_fonts()
    spec = json.load(open(spec_path)); os.makedirs(out, exist_ok=True); shutil.copy(spec_path, f"{out}/spec.json")
    t = time.time(); meta = reel.make_voice(spec, out); t_voice = time.time() - t
    tl = reel.make_timeline(spec, meta, out)
    spans = activity(spec, tl)
    ts, ctop, cbot = clocks(spans, tl["total"])
    qs = spec["quiz"]
    ctop = ctop + spec.get("top_offset", 0.0)
    # pick the question period so the big feedback lands on the word the spec asks for (e.g. "feedback")
    P_ = spec.get("top_period", 6.0)
    sync = spec.get("feedback_sync")
    if sync:
        tw = retro.at(tl, sync["line"], sync["word"]); j = int(round(tw * FPS)); tau = float(ctop[min(j, len(ctop) - 1)])
        target = 2.6 + sync.get("after", .3)
        cands = [p for p in np.arange(5.0, 6.6, .01) if int(tau // p) % len(qs) != 0]
        P_ = float(round(min(cands, key=lambda p: abs((tau % p) - target)), 2))
        iw = int(tau // P_) % len(qs)
        wrong = next(k for k, q in enumerate(qs) if q["pick"] != q["answer"])
        qs = list(qs); qs[iw], qs[wrong] = qs[wrong], qs[iw]
    top = TopSim(qs, P=P_, total_q=spec.get("quiz_total", 5)); bot = BotSim(spec.get("form", qs), P=spec.get("bottom_period", 3.4))
    gtop = to_global(top.events(float(ctop[-1]) + 1), ctop, ts); gbot = to_global(bot.events(float(cbot[-1]) + 1), cbot, ts)
    fb_t = next((retro.at(tl, st_.get("line", spec["upgrade"].get("line")), st_["word"]) for st_ in spec.get("upgrade", {}).get("steps", []) if st_["kind"] == "feedback"), None)
    if fb_t is not None:
        gbot += [(fb_t, "correct")] + [(tt_ + .2, "correct") for (tt_, n_) in list(gbot) if n_ == "next" and tt_ > fb_t + .5]
    for st_ in spec.get("upgrade", {}).get("steps", []):
        gbot.append((retro.at(tl, st_.get("line", spec["upgrade"].get("line")), st_["word"]) - .05, "upgrade"))
    t = time.time(); am = make_audio(spec, tl, spans, gtop, gbot, out); t_audio = time.time() - t
    frame = make_renderer(spec, tl, spans, ts, ctop, cbot, top, bot, out)
    S = [l["start"] for l in tl["lines"]]
    pts = sorted(set([0.0, 1.5] + [round(l["start"] + .7 * (l["end"] - l["start"]), 2) for l in tl["lines"]]
                     + [round(e[0] + .4, 2) for e in gtop if e[1] in ("correct", "wrong", "select")][:6] + [round(tl["total"] - .3, 2)]))
    shutil.rmtree(f"{out}/prev", ignore_errors=True); os.makedirs(f"{out}/prev")
    for p in pts: frame(p).save(f"{out}/prev/{p:06.2f}.png")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", f"{out}/prev/*.png",
                    "-vf", f"scale=270:480,tile=6x{math.ceil(len(pts) / 6)}", "-frames:v", "1", "-q:v", "3", f"{out}/sheet.jpg"], check=True)
    g = reel.gates(spec, out)
    metrics = {"id": spec["id"], "engine_version": ENGINE_VERSION, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "duration_s": tl["total"], "lines": len(tl["lines"]), "scenes": len(spec["scenes"]),
               "scene_types": ["split:" + s["active"] for s in spec["scenes"]], "avg_scene_s": round(tl["total"] / len(spec["scenes"]), 2),
               "words": sum(len(l["cap"].split()) for l in tl["lines"]), "speech_s": round(sum(l["end"] - l["start"] for l in tl["lines"]), 2),
               "voice": spec.get("voice", {}).get("name", "af_heart"), "voice_speed": spec.get("voice", {}).get("speed", 1.08),
               "palette": "#FF5A4E/#070B1A + quiz tiles / B&W form", "font": "Poppins + Liberation Sans + pixel guide",
               "art_direction": spec.get("style", {}).get("art", ""), "top_period_s": P_,
               **am, "gates": g, "render": {"voice_s": round(t_voice, 1), "audio_s": round(t_audio, 1)}, "cost": {"elevenlabs_credits": 0, "eur": 0}}
    if not preview:
        t = time.time(); nfr = int(math.ceil(tl["total"] * FPS))
        ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-i", f"{out}/mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
                               "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                               "-shortest", "-movflags", "+faststart", f"{out}/video.mp4"], stdin=subprocess.PIPE)
        for n in range(nfr): ff.stdin.write(frame(n / FPS).tobytes())
        ff.stdin.close(); ff.wait()
        frame(spec.get("cover_t", 1.5)).save(f"{out}/cover.jpg", quality=90)
        metrics["render"]["video_s"] = round(time.time() - t, 1); metrics["file_mb"] = round(os.path.getsize(f"{out}/video.mp4") / 1e6, 2)
    metrics["render"]["total_s"] = round(time.time() - t_start, 1)
    json.dump(metrics, open(f"{out}/metrics.json", "w"), indent=1)
    hsv = g["hookscore"].get("score") if isinstance(g["hookscore"], dict) else None
    print(json.dumps({"id": spec["id"], "duration_s": tl["total"], "hookscore": hsv, "lufs": am["lufs"],
                      "voice_minus_bed_db": am["voice_minus_bed_db"], "top_period": P_, "render_s": metrics["render"]["total_s"]}))

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "build": build(sys.argv[2], sys.argv[3], preview="--preview" in sys.argv)
    else: print(__doc__); sys.exit(1)
