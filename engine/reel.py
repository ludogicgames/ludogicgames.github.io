#!/usr/bin/env python3
"""Ludogic reel engine: one spec JSON -> finished Instagram reel.

    python3 engine/reel.py build specs/2026-W42-R01.json out/2026-W42-R01 [--preview]

Outputs in the out dir:
  video.mp4      1080x1920, 30 fps, H.264 + AAC 48 kHz, -14 LUFS
  cover.jpg      frame used as Reel cover (spec.cover_t, default 0)
  sheet.jpg      contact sheet (10 frames) - LOOK AT IT before publishing
  metrics.json   every measurable parameter of the build (for the learning registry)
  timeline.json  start/end of every voice line
--preview renders only the contact sheet (fast) so layout can be checked first.

Brand style is fixed here (navy + coral, Inter Display, XP bar, particles).
Scene types: stat, stamp, bars, title, number, card(timer|path|flow|list|compare|meter|leaderboard|levels|streak|loop), box, cta, doors.
See README.md for the spec format.
"""
import sys, os, json, math, time, subprocess, shutil, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.expanduser("~/.cache/ludogic-reels")
WD, HT, FPS, SR = 1080, 1920, 30, 48000

# =====================================================================
# 0. setup helpers
# =====================================================================
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
def ensure_models():
    os.makedirs(CACHE, exist_ok=True)
    for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        p = os.path.join(CACHE, f)
        if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
            subprocess.run(["curl", "-sSL", "-o", p, MODEL_URL + f], check=True)
    return os.path.join(CACHE, "kokoro-v1.0.onnx"), os.path.join(CACHE, "voices-v1.0.bin")


# =====================================================================
# door-grid schedule (shared by audio and visuals)
# =====================================================================
def door_schedule(sc, t0, t1, S=None):
    """-> list of {i, t, reveal, golden} door openings for a `doors` scene."""
    mode = sc.get("mode", "coupon"); n = sc.get("count", 24); out = []
    if mode == "coupon":
        k = 0; t = t0 + .35
        while t < t1 - .3 and k < n:
            out.append({"i": k, "t": t, "reveal": sc.get("reveal", "10%"), "golden": False}); k += 1; t += sc.get("interval", .16)
    elif mode == "streak":
        st = sc.get("streak", 5)
        for k in range(st): out.append({"i": k, "t": t0 + .5 + k * .45, "reveal": "flame", "golden": False, "level": k + 1})
        tb = (S[sc["bonus_line"]] + .55) if (S and "bonus_line" in sc) else t0 + .5 + st * .45 + .35
        out.append({"i": st, "t": tb, "reveal": sc.get("bonus", "BONUS"), "golden": True})
    elif mode == "mystery":
        for j, (i, rv) in enumerate(sc.get("reveals", [])):
            out.append({"i": i, "t": t0 + .45 + j * .5, "reveal": rv, "golden": False})
    elif mode == "final":
        mix = sc.get("mix", ["flame", "+50 XP", "gift", "key", "2X", "?"])
        for i in range(n): out.append({"i": i, "t": t0 + .25 + i * .045, "reveal": mix[(i * 5 + i // 6) % len(mix)], "golden": i == 5})
    return out

# =====================================================================
# 1. voice
# =====================================================================
def make_voice(spec, out):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    m, v = ensure_models()
    k = Kokoro(m, v)
    voice = spec.get("voice", {}).get("name", "af_heart")
    speed = spec.get("voice", {}).get("speed", 1.08)
    meta = []
    os.makedirs(f"{out}/vo", exist_ok=True)
    for i, L in enumerate(spec["lines"]):
        a, sr = k.create(L["say"], voice=voice, speed=speed, lang="en-us")
        a = np.asarray(a, dtype=np.float32)
        thr = 0.01 * np.max(np.abs(a)); idx = np.where(np.abs(a) > thr)[0]
        a = a[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.06 * sr)]
        sf.write(f"{out}/vo/l{i:02d}.wav", a, sr)
        meta.append({"i": i, "dur": round(len(a) / sr, 3), "sr": sr})
    return meta

def make_timeline(spec, meta, out):
    t = 0.0; lines = []
    for i, (L, M) in enumerate(zip(spec["lines"], meta)):
        t += L.get("gap", 0.25 if i else 0.10)
        lines.append({"i": i, "start": round(t, 3), "end": round(t + M["dur"], 3),
                      "say": L["say"], "cap": L.get("cap", L["say"])})
        t += M["dur"]
    tl = {"total": round(t + spec.get("outro", 1.6), 3), "lines": lines}
    json.dump(tl, open(f"{out}/timeline.json", "w"), indent=1)
    return tl

# =====================================================================
# 2. audio (music + sfx + voice, ducked, loudness-normalised)
# =====================================================================
def make_audio(spec, tl, out):
    import soundfile as sf
    from scipy.signal import resample_poly, butter, sosfilt
    rng = np.random.default_rng(spec.get("seed", 7))
    TOTAL = tl["total"]; N = int(TOTAL * SR)
    S = {l["i"]: l["start"] for l in tl["lines"]}; E = {l["i"]: l["end"] for l in tl["lines"]}
    def buf(): return np.zeros(N)
    def add(dst, sig, at, g=1.0):
        i = int(at * SR)
        if i >= N or i < 0: return
        j = min(N, i + len(sig)); dst[i:j] += g * sig[: j - i]
    def env(n, a=.005, d=.2, c=4.0):
        tt = np.arange(n) / SR; return np.minimum(1, tt / max(a, 1e-4)) * np.exp(-c * tt / max(d, 1e-4))
    def filt(x, kind, fc, order=2): return sosfilt(butter(order, fc, kind, fs=SR, output="sos"), x)
    def sine(f, dur):
        tt = np.arange(int(dur * SR)) / SR
        if callable(f): return np.sin(2 * np.pi * np.cumsum(f(tt)) / SR)
        return np.sin(2 * np.pi * f * tt)
    def saw(f, dur): tt = np.arange(int(dur * SR)) / SR; return 2 * ((f * tt) % 1) - 1
    def square(f, dur, duty=.5): tt = np.arange(int(dur * SR)) / SR; return np.where(((f * tt) % 1) < duty, 1., -1.)
    def noise(dur): return rng.standard_normal(int(dur * SR))
    mtof = lambda m: 440 * 2 ** ((m - 69) / 12)

    mu = spec.get("music", {})
    BPM = mu.get("bpm", 112); beat = 60 / BPM
    prog = mu.get("progression", [[57, [57, 60, 64]], [53, [53, 57, 60]], [48, [55, 60, 64]], [55, [55, 59, 62]]])
    drop = mu.get("drop_line", max(1, len(tl["lines"]) // 2))
    t_full = S.get(drop, TOTAL / 2) - 0.05
    music = buf()
    for b in range(int(TOTAL / (4 * beat)) + 2):
        t0 = b * 4 * beat; root, chord = prog[b % len(prog)]
        pl = 4 * beat + .3
        pad = sum(saw(mtof(n) * (1 + d), pl) for n in chord for d in (-.004, .004))
        pad = filt(pad, "low", 1400) * np.minimum(1, np.arange(len(pad)) / (.35 * SR)) * np.minimum(1, (len(pad) - np.arange(len(pad))) / (.3 * SR))
        add(music, pad, t0, .018)
        for k in range(4):
            tb = t0 + k * beat; en = tb >= t_full
            add(music, sine(lambda tt: 50 + 120 * np.exp(-tt * 30), .35) * env(int(.35 * SR), .001, .12, 3), tb, .55 if en else .30)
            for h in (0, .5):
                add(music, filt(saw(mtof(root - 12), .22), "low", 600) * env(int(.22 * SR), .003, .12, 3), tb + h * beat, .16 if en else .10)
            for h in ((.25, .5, .75) if en else (.5,)):
                add(music, filt(noise(.05), "high", 7000) * env(int(.05 * SR), .001, .02, 3), tb + h * beat, .05)
            if en and k in (1, 3):
                add(music, filt(noise(.18), "band", [900, 3500]) * env(int(.18 * SR), .002, .06, 3), tb, .10)
        if t0 + 4 * beat > t_full:
            pat = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[1] + 12]
            for s in range(16):
                ts = t0 + s * beat / 4
                if ts < t_full: continue
                n = pat[s % 4] + (12 if s % 8 == 7 else 0)
                add(music, filt(square(mtof(n), .11, .25), "low", 3500) * env(int(.11 * SR), .002, .05, 3), ts, .028)
    add(music, filt(noise(1.2), "high", 1500) * np.linspace(0, 1, int(1.2 * SR)) ** 2, t_full - 1.2, .06)
    fo = int(1.2 * SR); music[-fo:] *= np.linspace(1, 0, fo)

    sfx = buf()
    def impact(at, g=1.):
        add(sfx, sine(lambda tt: 40 + 90 * np.exp(-tt * 18), .9) * env(int(.9 * SR), .001, .45, 2.5), at, .8 * g)
        add(sfx, filt(noise(.25), "low", 3000) * env(int(.25 * SR), .001, .05, 3), at, .25 * g)
    def whoosh(at, dur=.45, g=1., up=True):
        n = noise(dur); L = len(n); fc = np.linspace(400, 5000, L) if up else np.linspace(5000, 400, L)
        o = np.zeros(L)
        for i in range(0, L, 512): o[i:i + 512] = filt(n[i:i + 512], "band", [max(100, fc[i] * .6), min(20000, fc[i] * 1.4)], 1)
        add(sfx, o * np.sin(np.linspace(0, np.pi, L)) ** 1.5, at, .35 * g)
    def blip(at, f=880, dur=.09, g=1., sq=True):
        s = square(f, dur) if sq else sine(f, dur)
        add(sfx, filt(s, "low", 6000) * env(int(dur * SR), .001, dur * .5, 3), at, .12 * g)
    def clink(at, f=2400):
        s = sum(sine(f * r, .4) * a for r, a in ((1, 1), (2.76, .5), (5.4, .25)))
        add(sfx, s * env(int(.4 * SR), .001, .12, 3), at, .12)
    def fail(at):
        tt = np.arange(int(.55 * SR)) / SR; ph = 2 * np.pi * np.cumsum(330 * np.exp(-tt * 1.6)) / SR
        add(sfx, filt(np.sign(np.sin(ph)), "low", 2500) * env(len(tt), .005, .5, 1.5), at, .10)
    def stamp(at):
        add(sfx, sine(lambda tt: 70 + 60 * np.exp(-tt * 40), .3) * env(int(.3 * SR), .001, .08, 3), at, .7)
        add(sfx, filt(noise(.08), "band", [1500, 6000]) * env(int(.08 * SR), .001, .02, 3), at, .25)
    def chime(at, notes=(72, 76, 79, 84), step=.07, g=1.):
        for k, n in enumerate(notes):
            s = sine(mtof(n), .6) + .3 * sine(mtof(n) * 2, .6)
            add(sfx, s * env(int(.6 * SR), .002, .25, 3), at + k * step, .09 * g)
    def tick(at): add(sfx, filt(noise(.012), "high", 3000) * env(int(.012 * SR), .0005, .004, 3), at, .25)
    def riser(at, dur=2.2):
        add(sfx, filt(sine(lambda tt: 300 + 500 * tt / dur, dur) * np.linspace(0, 1, int(dur * SR)) ** 2, "low", 2000), at, .05)

    scenes = spec["scenes"]
    for si, sc in enumerate(scenes):
        t0 = S[sc["line"]]; ty = sc["type"]
        if si > 0 and ty not in ("stamp",): whoosh(t0 - .22, .4, .9)
        if ty == "stat":
            if si == 0: impact(0.0); whoosh(0.0, .35, .8, up=False)
            else: impact(t0)
            th = sc.get("then")
            if th:
                tt = S[th["line"]]
                if th.get("icons", "badges_fail") == "badges_fail":
                    for k in range(3): clink(tt + .05 + k * .16, 2200 + 300 * k)
                    fail(tt + .55)
        elif ty == "stamp": stamp(t0 + .02)
        elif ty == "bars":
            for k in range(len(sc["data"])): blip(t0 + .9 + k * .32, 520 + 60 * k, .07, .8, sq=False)
        elif ty == "title":
            if sc.get("counter"):
                tt = S[sc["counter"].get("line", sc["line"])]
                for k in range(sc["counter"].get("steps", 8)): blip(tt + k * .12, 988 if k % 2 else 1319, .06, .7)
            else: chime(t0 + .05, (64, 67, 71, 76), .06, .6)
        elif ty == "number": impact(t0 + .32, .8)
        elif ty == "card":
            vk = sc.get("visual", {}).get("kind")
            if vk == "timer":
                for k in range(3): tick(t0 + k * .33)
                chime(t0 + 1.05, (79, 84), .08)
            elif vk == "path": blip(t0 + .9, 1568, .12, 1.0, sq=False)
            elif vk == "flow": riser(t0 + .3)
            elif vk in ("list", "compare"):
                n = len(sc["visual"].get("items", [])) or 2
                for k in range(n): blip(t0 + .5 + k * .45, 880 + 110 * k, .08, .8, sq=False)
            elif vk == "meter":
                riser(t0 + .2, 1.4); chime(t0 + 1.6, (76, 81), .08)
            elif vk == "levels":
                vz = sc["visual"]; n = vz.get("count", 5); d0 = vz.get("start_done", 0); dn = vz.get("done", n - 1)
                for j in range(d0, dn): chime(t0 + .45 + (j - d0) * vz.get("interval", .55), (72 + 2 * j, 79 + 2 * j), .06, .8)
            elif vk == "streak":
                vz = sc["visual"]
                for j in range(vz.get("fill", 7)):
                    tj = t0 + .45 + j * vz.get("interval", .4)
                    if j == vz.get("freeze", -1): clink(tj, 3000)
                    else: blip(tj, 440 * 2 ** (j / 6), .1, .9, sq=True)
            elif vk == "loop":
                vz = sc["visual"]; ls = vz.get("lap_s", 2.4); n = len(vz["steps"]); tt = t0 + .6; k = 0
                t1c = S[scenes[si + 1]["line"]] if si + 1 < len(scenes) else TOTAL
                while tt < t1c - .2 and k < 40:
                    blip(tt, 660 * 2 ** ((k % n) / 12 + (k // n) / 12), .07, .7, sq=False); tt += ls / n; k += 1
        elif ty == "box": stamp(t0 + sc.get("switch", 1.25))
        elif ty == "doors":
            t1d = S[scenes[si + 1]["line"]] if si + 1 < len(scenes) else TOTAL
            for d in door_schedule(sc, t0, t1d, S):
                if d["golden"]: chime(d["t"], (76, 79, 84, 88), .06, 1.0)
                elif d["reveal"] == "flame": blip(d["t"], 440 * 2 ** (d.get("level", 1) / 6), .1, .9, sq=True)
                elif sc.get("mode") == "final": tick(d["t"])
                elif sc.get("mode") == "coupon": blip(d["t"], 330, .05, .5, sq=False)
                else: chime(d["t"], (79, 86), .05, .7)
            if sc.get("mode") == "coupon": fail(t0 + 2.4)
        elif ty == "cta":
            last = len(tl["lines"]) - 1
            chime(E[last] + .05, (69, 72, 76, 81, 84), .07, 1.2)

    vo = buf()
    for l in tl["lines"]:
        a, sr = sf.read(f"{out}/vo/l{l['i']:02d}.wav")
        a = filt(resample_poly(a, SR, sr), "high", 80)
        add(vo, a / (np.max(np.abs(a)) + 1e-9), l["start"], .75)
    venv = np.convolve(np.abs(vo), np.ones(int(.08 * SR)) / int(.08 * SR), mode="same")
    duck = 1 - .55 * np.clip(venv / (venv.max() * .25), 0, 1)
    duck = np.convolve(duck, np.ones(int(.15 * SR)) / int(.15 * SR), mode="same")
    md = music * duck * mu.get("level", 0.9)
    d = int(.012 * SR)
    L = vo + md + .85 * sfx
    R = vo + np.concatenate([np.zeros(d), md[:-d]]) + .85 * sfx
    st = np.stack([L, R], 1); st /= np.max(np.abs(st)) / .89
    sf.write(f"{out}/mix_raw.wav", st.astype(np.float32), SR)
    # voice / bed balance for the registry
    sp = np.zeros(N, bool)
    for l in tl["lines"]: sp[int(l["start"] * SR):int(l["end"] * SR)] = True
    def rms(x): return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12))
    bed = md + .85 * sfx
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", f"{out}/mix_raw.wav", "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-ar", str(SR), f"{out}/mix.wav"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"output_i\"[^{}]*\}", r.stderr, re.S)
    ln = json.loads(m.group(0)) if m else {}
    return {"voice_minus_bed_db": round(rms(vo[sp]) - rms(bed[sp]), 1),
            "lufs": float(ln.get("output_i", "nan")), "true_peak_db": float(ln.get("output_tp", "nan")),
            "music_bpm": BPM, "music_drop_line": drop}

# =====================================================================
# 3. visuals
# =====================================================================
def make_renderer(spec, tl):
    import skia
    TOTAL = tl["total"]
    S = {l["i"]: l["start"] for l in tl["lines"]}; E = {l["i"]: l["end"] for l in tl["lines"]}
    LAST = len(tl["lines"]) - 1
    st = spec.get("style", {})
    BG, BG2 = st.get("bg", "#070B1A"), st.get("bg2", "#101A3C")
    CORAL, WHITE, MUTED, LINE = st.get("accent", "#FF5A4E"), "#F4F6FB", "#8A93B3", "#26305A"
    def C(h, a=1.):
        h = h.lstrip("#"); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(max(0, min(1, a)) * 255))
    FD = "/usr/share/fonts/opentype/inter/"
    TF = {k: skia.Typeface.MakeFromFile(FD + v) for k, v in {
        "black": "InterDisplay-Black.otf", "bold": "InterDisplay-Bold.otf", "semi": "InterDisplay-SemiBold.otf",
        "med": "InterDisplay-Medium.otf", "thin": "InterDisplay-ExtraLight.otf"}.items()}
    TF["mono"] = skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")
    X0, X1 = 90, 850
    def clamp(x, a=0., b=1.): return max(a, min(b, x))
    def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
    def eo(x): return 1 - (1 - x) ** 3
    def eio(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
    def back(x, s=1.7): x -= 1; return x * x * ((s + 1) * x + s) + 1
    def vis(t, t0, t1, fin=.22, fout=.16): return eo(prog(t, t0, fin)) * (1 - prog(t, t1 - fout, fout))
    def paint(col, a=1., stroke=0):
        p = skia.Paint(AntiAlias=True, Color=C(col, a))
        if stroke: p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke); p.setStrokeCap(skia.Paint.kRound_Cap)
        return p
    def font(k, s): f = skia.Font(TF[k], s); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True); return f
    def tw(txt, k, s, tr=0): return font(k, s).measureText(txt) + tr * max(0, len(txt) - 1)
    def text(cv, txt, x, y, k, s, col, a=1., tr=0, align="l"):
        f = font(k, s); w = tw(txt, k, s, tr)
        if align == "c": x -= w / 2
        elif align == "r": x -= w
        if tr == 0: cv.drawString(txt, x, y, f, paint(col, a))
        else:
            for ch in txt: cv.drawString(ch, x, y, f, paint(col, a)); x += f.measureText(ch) + tr
        return w
    def fit(txt, k, mw, s, tr=0):
        while tw(txt, k, s, tr) > mw and s > 10: s -= 2
        return s
    def headline(cv, lines, t, t0, t1, y, size=104, col=None, k="black", accent=(), stagger=.07, mw=X1 - X0):
        col = col or WHITE; acc = set(accent)
        size = min([fit(l, k, mw, size) for l in lines] + [size])
        for n, ln in enumerate(lines):
            v = vis(t, t0 + n * stagger, t1)
            if v <= 0: continue
            x = X0
            for w in ln.split(" "):
                c = CORAL if (w in acc or w.strip(".,?!:") in acc) else col
                x += text(cv, w, x, y + n * size * 1.04 + (1 - v) * 40, k, size, c, v) + size * .26
        return size

    rng = np.random.default_rng(3)
    PART = [(rng.uniform(0, WD), rng.uniform(0, HT), rng.uniform(1.2, 3.4), rng.uniform(6, 22), rng.uniform(0, 6.28), rng.uniform(.15, .55)) for _ in range(70)]
    def background(cv, t):
        cv.clear(C(BG))
        cv.drawRect(skia.Rect(0, 0, WD, HT), skia.Paint(Shader=skia.GradientShader.MakeRadial((540 + 120 * math.sin(t * .25), 760), 1100, [C(BG2, .95), C(BG, 0)])))
        cv.drawRect(skia.Rect(0, 0, WD, HT), skia.Paint(Shader=skia.GradientShader.MakeRadial((900, 1700), 700, [C(CORAL, .10), C(CORAL, 0)])))
        gp = paint(LINE, .22, 1)
        for gx in range(0, WD + 1, 120): cv.drawLine(gx, 0, gx, HT, gp)
        for gy in range(0, HT + 1, 120): cv.drawLine(0, gy, WD, gy, gp)
        for (x, y, r, sp, ph, a) in PART:
            cv.drawCircle(x + 10 * math.sin(t * .6 + ph), (y - t * sp) % HT, r, paint(WHITE, a * (.6 + .4 * math.sin(t * 1.3 + ph))))
        cv.drawRect(skia.Rect(0, 0, WD, HT), skia.Paint(Shader=skia.GradientShader.MakeRadial((540, 960), 1250, [C(BG, 0), C("#000000", .55)], [.55, 1.])))
    def hud(cv, t):
        text(cv, "ludogic", X0, 300, "thin", 46, WHITE, .9, tr=1.5)
        p = clamp(t / (E[LAST] + .3))
        cv.drawRoundRect(skia.Rect(X0, 336, X1, 344), 4, 4, paint(LINE, .9))
        cv.drawRoundRect(skia.Rect(X0, 336, X0 + (X1 - X0) * p, 344), 4, 4, paint(CORAL))
        text(cv, "LEVEL COMPLETE" if p >= 1 else f"XP {int(p * 100):02d}%", X1, 300, "mono", 24, CORAL if p >= 1 else MUTED, .95, tr=2, align="r")
    def wrap(words, k, s, mw):
        out, cur = [], []
        for w in words:
            if cur and tw(" ".join(cur + [w]), k, s) > mw: out.append(cur); cur = [w]
            else: cur.append(w)
        if cur: out.append(cur)
        return out
    def captions(cv, t):
        for l in tl["lines"]:
            t0, t1 = l["start"], l["end"]
            if not (t0 - .05 <= t <= t1 + .25): continue
            words = l["cap"].split(" ")
            wts = np.array([len(w) + (3 if w[-1] in ".,?!" else 0) for w in words], float)
            cur = int(np.searchsorted(np.cumsum(wts) / wts.sum() * (t1 - t0) + t0, t))
            s = 38; lines = wrap(words, "semi", s, X1 - X0)
            a = vis(t, t0 - .05, t1 + .25, .1, .12)
            flat = [li for li, ln in enumerate(lines) for _ in ln]
            cl = flat[min(cur, len(flat) - 1)]
            start = max(0, min(cl - (cl % 2), len(lines) - 2)); show = lines[start:start + 2]
            base = 1338 - (len(show) - 1) * 50
            mw = max(tw(" ".join(ln), "semi", s) for ln in show)
            cv.drawRoundRect(skia.Rect(X0 - 22, base - 46, X0 + mw + 22, base + (len(show) - 1) * 50 + 20), 14, 14, paint("#05081A", .62 * a))
            gi = sum(len(ln) for ln in lines[:start])
            for li, ln in enumerate(show):
                x = X0
                for w in ln:
                    x += text(cv, w, x, base + li * 50, "semi", s, CORAL if gi == cur else (WHITE if gi < cur else MUTED), a) + s * .28; gi += 1
    def star(cx, cy, r1, r2, n=5):
        p = skia.Path()
        for k in range(2 * n):
            r = r1 if k % 2 == 0 else r2; a = -math.pi / 2 + k * math.pi / n
            (p.moveTo if k == 0 else p.lineTo)(cx + r * math.cos(a), cy + r * math.sin(a))
        p.close(); return p
    def badge(cv, cx, cy, r, a=1, grey=0., crack=0.):
        cv.drawCircle(cx, cy, r, paint(CORAL if grey < .5 else "#4A5378", a * (1 - .4 * grey)))
        cv.drawCircle(cx, cy, r * .82, paint(WHITE, a * .9, 4))
        cv.drawPath(star(cx, cy, r * .5, r * .22), paint(WHITE, a))
        if crack > 0:
            p = skia.Path(); p.moveTo(cx - r * .2, cy - r); p.lineTo(cx + r * .05, cy - r * .3); p.lineTo(cx - r * .15, cy + r * .1); p.lineTo(cx + r * .25, cy + r)
            cv.drawPath(p, paint(BG, a * crack, 7))

    # ---------------- scene implementations ----------------
    def sc_stat(cv, t, sc, t0, t1, first):
        th = sc.get("then"); tth = S[th["line"]] if th else None
        shake = max(0, .25 - (t - t0)) * 60 if first else 0
        ox, oy = math.sin(t * 90) * shake, math.cos(t * 70) * shake * .5
        up = eio(prog(t, tth, .4)) if th else 0
        a_in = 1 if first else eo(prog(t, t0, .2))
        cv.save(); cv.translate(X0 + ox, 820 - up * 230 + oy); cv.scale(1 - up * .38, 1 - up * .38)
        big = fit(sc["stat"], "black", X1 - X0, 300)
        if first and t - t0 < .3:
            text(cv, sc["stat"], -8, 0, "black", big, "#38E1FF", .45); text(cv, sc["stat"], 8, 0, "black", big, CORAL, .55)
        text(cv, sc["stat"], 0, 0, "black", big, CORAL, a_in * (1 - prog(t, t1 - .15, .15)))
        cv.restore()
        a = a_in * ((1 - prog(t, tth - .1, .15)) if th else (1 - prog(t, t1 - .15, .15)))
        if a > 0:
            ls = min(fit(l, "black", X1 - X0, 96) for l in sc["label"])
            for n, l in enumerate(sc["label"]): text(cv, l, X0 + ox, 930 + n * ls * 1.04, "black", ls, WHITE, a)
        if th and t >= tth:
            v = vis(t, tth + .05, t1)
            headline(cv, th["headline"], t, tth + .05, t1, 840, 104, accent=th.get("accent", []))
            if th.get("icons", "badges_fail") == "badges_fail":
                crack = prog(t, tth + .55, .15)
                for k in range(3):
                    tk = tth + .05 + k * .16; p = prog(t, tk, .35)
                    if p <= 0: continue
                    y = 1020 + 140 - 140 * (1 - abs(math.cos(p * math.pi * 1.2)) * (1 - p)) - (1 - eo(p)) * 300
                    badge(cv, X0 + 70 + k * 190, y + 60, 62, v * eo(prog(t, tk, .08)), grey=crack, crack=crack)
    def sc_stamp(cv, t, sc, t0, t1, first):
        p = prog(t, t0, .18); s = 1.7 - .7 * eo(p); a = p * (1 - prog(t, t1 - .12, .12))
        size = fit(sc["text"], "black", 700, 104)
        cv.save(); cv.translate(470, 800); cv.rotate(-6); cv.scale(s, s)
        w = tw(sc["text"], "black", size)
        cv.drawRoundRect(skia.Rect(-w / 2 - 36, -size, w / 2 + 36, 40), 10, 10, paint(CORAL, a, 8))
        text(cv, sc["text"], 0, 0, "black", size, CORAL, a, align="c"); cv.restore()
    def sc_bars(cv, t, sc, t0, t1, first):
        v = vis(t, t0, t1)
        if sc.get("kicker"): text(cv, sc["kicker"], X0, 470, "mono", 26, MUTED, v, tr=2)
        headline(cv, [sc["title"]], t, t0, t1, 560, 84)
        cx0, cy0, cw, ch = X0, 620, X1 - X0, 430
        data = sc["data"]; n = len(data); gap = 26 if n <= 6 else 14; bw = (cw - gap * (n - 1)) / n
        mx = sc.get("max", max(d[1] for d in data) * 1.15); unit = sc.get("unit", "")
        for k, (lab, val) in enumerate(data):
            bx = cx0 + k * (bw + gap)
            cv.drawRoundRect(skia.Rect(bx, cy0, bx + bw, cy0 + ch), 10, 10, paint(LINE, .55 * v))
            if sc.get("show_max", True): text(cv, f"{mx:g}{unit}", bx + bw / 2, cy0 + 40, "mono", 20, MUTED, .7 * v * eo(prog(t, t0 + .3, .3)), align="c")
            p = eo(prog(t, t0 + .9 + k * .32, .35)); h = ch * val / mx * p
            hl = sc.get("highlight") in (None, k)
            cv.drawRoundRect(skia.Rect(bx, cy0 + ch - max(h, .01), bx + bw, cy0 + ch), 6, 6, paint(CORAL if hl else MUTED, v))
            if p > 0:
                vs = f"{val:.{sc.get('decimals', 1)}f}{unit}"
                text(cv, vs, bx + bw / 2, cy0 + ch - h - 18, "bold", fit(vs, "bold", bw + 10, 36), WHITE, v * p, align="c")
            text(cv, str(lab), bx + bw / 2, cy0 + ch + 44, "mono", fit(str(lab), "mono", bw + 8, 20), MUTED, v, align="c")
        if sc.get("source"): text(cv, sc["source"], X0, 1132, "med", fit(sc["source"], "med", X1 - X0, 22), MUTED, v * .9)
        ft = sc.get("footer")
        if ft: text(cv, ft["text"], X0, 1215, "black", fit(ft["text"], "black", X1 - X0, 66), CORAL, vis(t, t0 + ft.get("delay", 3.0), t1))
    def sc_title(cv, t, sc, t0, t1, first):
        v = vis(t, t0, t1)
        th = sc.get("then"); tth = S[th["line"]] if th else t1
        a1 = 1 - prog(t, tth - .1, .15) if th else 1
        if sc.get("kicker"): text(cv, sc["kicker"], X0, 500, "mono", 30, MUTED, v * a1, tr=3)
        if sc.get("big"):
            sl = (1 - eo(prog(t, t0, .3))) * 120
            text(cv, sc["big"], X0 + sl, 760, "black", fit(sc["big"], "black", X1 - X0, 170), WHITE, v * a1)
            if sc.get("sub"): text(cv, sc["sub"], X0, 870, "black", fit(sc["sub"], "black", X1 - X0, 96), CORAL, vis(t, t0 + .55, tth) * a1)
        elif sc.get("lines"):
            if a1 > 0: headline(cv, sc["lines"], t, t0 + .05, tth, sc.get("y", 680), sc.get("size", 128), accent=sc.get("accent", []))
        if th and t >= tth - .05:
            headline(cv, th["lines"], t, tth, t1, th.get("y", 700), th.get("size", 140), accent=th.get("accent", []))
        cn = sc.get("counter")
        if cn:
            tc = S[cn.get("line", sc["line"])]
            if t >= tc - .05:
                vv = vis(t, tc, t1); k = int(clamp((t - tc) / .12, 0, cn.get("steps", 8)))
                y = 1060; cv.drawRoundRect(skia.Rect(X0, y, X0 + 420, y + 130), 16, 16, paint(LINE, .7 * vv))
                text(cv, cn.get("label", "LVL"), X0 + 30, y + 86, "mono", 34, MUTED, vv, tr=2)
                text(cv, f"{cn.get('from', 12) + k}", X0 + 120, y + 96, "black", 84, WHITE, vv)
                fr = ((t - tc) / .12) % 1 if k < cn.get("steps", 8) else 1
                cv.drawRoundRect(skia.Rect(X0 + 250, y + 55, X0 + 390, y + 75), 10, 10, paint(BG, vv))
                cv.drawRoundRect(skia.Rect(X0 + 250, y + 55, X0 + 250 + 140 * fr, y + 75), 10, 10, paint(CORAL, vv))
                if cn.get("note"): text(cv, cn["note"], X0 + 460, y + 80, "mono", 26, MUTED, vv * (.5 + .5 * math.sin(t * 9)), tr=1)
    def sc_number(cv, t, sc, t0, t1, first):
        v = vis(t, t0, t1, .15, .12)
        if sc.get("pre"): text(cv, sc["pre"], X0, 600, "black", 96, MUTED, v)
        p = prog(t, t0 + .32, .25)
        if p > 0:
            s = 1.4 - .4 * back(p); cv.save(); cv.translate(X0 + 10, 1110); cv.scale(s, s)
            text(cv, sc["number"], 0, 0, "black", fit(sc["number"], "black", 520, 520), CORAL, v * clamp(p * 3)); cv.restore()
            cv.drawCircle(X0 + 160, 930, 140 + 520 * eo(prog(t, t0 + .32, .6)), paint(CORAL, (1 - prog(t, t0 + .32, .6)) * .6, 6))
            if sc.get("word"):
                nw = tw(sc["number"], "black", fit(sc["number"], "black", 520, 520))
                xw = min(X0 + nw + 40, X1 - tw(sc["word"], "black", 110))
                text(cv, sc["word"], xw, 1090, "black", fit(sc["word"], "black", X1 - xw, 110), WHITE, v * eo(p))
    def sc_card(cv, t, sc, t0, t1, first):
        v = vis(t, t0, t1)
        if sc.get("num"):
            text(cv, sc["num"], X0, 520, "mono", 44, CORAL, v, tr=4); cv.drawLine(X0 + 90, 506, X1, 506, paint(CORAL, .6 * v, 2))
        hs = headline(cv, sc["lines"], t, t0 + .05, t1, 640, sc.get("size", 104), accent=sc.get("accent", []))
        vz = sc.get("visual", {}); k = vz.get("kind")
        if k == "timer":
            cx, cy, r = X0 + 160, 1040, 120; sec = vz.get("seconds", 2); p = clamp((t - t0) / 1.0)
            cv.drawCircle(cx, cy, r, paint(LINE, v, 14))
            cv.drawArc(skia.Rect(cx - r, cy - r, cx + r, cy + r), -90, 360 * p, False, paint(CORAL, v, 14))
            text(cv, f"{min(sec, p * sec):.1f}s", cx, cy + 22, "bold", 62, WHITE, v, align="c")
            q = prog(t, t0 + 1.05, .3)
            if q > 0 and vz.get("reward"):
                y = 1010 - 40 * eo(q)
                text(cv, vz["reward"], X0 + 340, y, "black", fit(vz["reward"], "black", 500, 96), CORAL, v * clamp(q * 3))
                if vz.get("reward_sub"): text(cv, vz["reward_sub"], X0 + 345, y + 60, "mono", 30, WHITE, v * clamp(q * 3), tr=3)
            if vz.get("strike"):
                a = vis(t, t0 + 1.6, t1); w = text(cv, vz["strike"], X0 + 340, 1150, "med", fit(vz["strike"], "med", 500, 40), MUTED, a)
                cv.drawLine(X0 + 336, 1137, X0 + 340 + w * eo(prog(t, t0 + 1.9, .3)), 1137, paint(CORAL, a, 4))
        elif k == "path":
            pts = [(X0 + 40, 1180), (X0 + 230, 1070), (X0 + 420, 1150), (X0 + 600, 1020), (X1 - 40, 940)]
            p = eo(prog(t, t0 + .2, .8)); path = skia.Path(); path.moveTo(*pts[0])
            for q in pts[1:]: path.lineTo(*q)
            meas = skia.PathMeasure(path, False); seg = skia.Path(); meas.getSegment(0, meas.getLength() * p, seg, True)
            cv.drawPath(seg, skia.Paint(AntiAlias=True, Color=C(MUTED, .8 * v), Style=skia.Paint.kStroke_Style, StrokeWidth=5, PathEffect=skia.DashPathEffect.Make([16, 14], 0)))
            for i, (x, y) in enumerate(pts[:-1]):
                cv.drawCircle(x, y, 22 if i == 0 else 14, paint(CORAL if i == 0 else LINE, v))
            x, y = pts[0]; text(cv, vz.get("start", "YOU"), x - 30, y + 64, "mono", 26, WHITE, v, tr=2)
            cv.drawCircle(x, y, 22 + 14 * (.5 + .5 * math.sin(t * 6)), paint(CORAL, .35 * v, 3))
            fx, fy = pts[-1]; fp = back(prog(t, t0 + .9, .3)) if t >= t0 + .9 else 0
            if fp > 0:
                cv.save(); cv.translate(fx, fy); cv.scale(fp, fp); cv.drawLine(0, 0, 0, -110, paint(WHITE, v, 6))
                fl = skia.Path(); fl.moveTo(0, -110); fl.lineTo(80, -85); fl.lineTo(0, -60); fl.close(); cv.drawPath(fl, paint(CORAL, v)); cv.restore()
                text(cv, vz.get("goal", "GOAL"), fx - 40, fy + 60, "mono", 26, CORAL, v * clamp(fp), tr=2)
        elif k == "flow":
            gx0, gy0, gw, gh = X0 + 30, 1170, X1 - X0 - 60, 390
            ax = paint(MUTED, .8 * v, 3); cv.drawLine(gx0, gy0, gx0 + gw, gy0, ax); cv.drawLine(gx0, gy0, gx0, gy0 - gh, ax)
            text(cv, vz.get("x", "SKILL →"), gx0 + gw, gy0 + 40, "mono", 22, MUTED, v, tr=1, align="r")
            cv.save(); cv.translate(gx0 - 22, gy0 - 10); cv.rotate(-90); text(cv, vz.get("y", "CHALLENGE →"), 0, 0, "mono", 22, MUTED, v, tr=1); cv.restore()
            pb = eo(prog(t, t0 + .2, .6)); band = skia.Path()
            band.moveTo(gx0, gy0 - 30); band.lineTo(gx0 + gw * pb, gy0 - 30 - gh * .85 * pb); band.lineTo(gx0 + gw * pb, gy0 - gh * .85 * pb + 60); band.lineTo(gx0 + 90, gy0); band.close()
            cv.drawPath(band, paint(CORAL, .22 * v))
            text(cv, vz.get("band", "FLOW"), gx0 + gw * .45, gy0 - gh * .38 + 10, "mono", 26, CORAL, v * pb, tr=3)
            q = eio(clamp((t - t0 - .4) / max(1, (t1 - t0) - .8)))
            px, py = gx0 + 40 + (gw - 80) * q, gy0 - 15 - (gh * .85 - 10) * q
            cv.drawCircle(px, py, 18, paint(WHITE, v)); cv.drawCircle(px, py, 18 + 10 * (.5 + .5 * math.sin(t * 7)), paint(WHITE, .3 * v, 3))
            for key, x, y, dflt in (("low", gx0 + gw - 200, gy0 - 60, 2.6), ("high", gx0 + 30, gy0 - gh + 40, 3.5)):
                if not vz.get(key): continue
                a = vis(t, t0 + vz.get(key + "_at", dflt), t1); w = text(cv, vz[key], x, y, "black", 44, MUTED, a)
                if a > 0: cv.drawLine(x - 5, y - 14, x - 5 + (w + 10) * eo(prog(t, t0 + vz.get(key + "_at", dflt) + .2, .2)), y - 14, paint(CORAL, a, 5))
        elif k == "list":
            items = vz["items"]; y0 = 640 + len(sc["lines"]) * hs * 1.04 + 70
            for i, it in enumerate(items):
                a = vis(t, t0 + .5 + i * .45, t1); y = y0 + i * 110
                cv.drawCircle(X0 + 22, y - 16, 22, paint(CORAL, a)); text(cv, str(i + 1), X0 + 22, y - 4, "bold", 30, WHITE, a, align="c")
                text(cv, it, X0 + 70 + (1 - a) * 30, y, "semi", fit(it, "semi", X1 - X0 - 70, 52), WHITE, a)
        elif k == "compare":
            y0 = 640 + len(sc["lines"]) * hs * 1.04 + 50; colw = (X1 - X0 - 30) / 2; bh = min(360, 1225 - y0)
            for ci, key in enumerate(("left", "right")):
                side = vz[key]; x = X0 + ci * (colw + 30); a = vis(t, t0 + .4 + ci * .5, t1)
                cv.drawRoundRect(skia.Rect(x, y0, x + colw, y0 + bh), 18, 18, paint(CORAL if ci else LINE, (.18 if ci else .6) * a))
                text(cv, side["title"], x + 24, y0 + 56, "mono", 26, CORAL if ci else MUTED, a, tr=2)
                for j, it in enumerate(side.get("items", [])):
                    text(cv, it, x + 24, y0 + 110 + j * min(64, (bh - 130) / max(1, len(side.get("items", [])) - 1 or 1)), "semi", fit(it, "semi", colw - 48, 38), WHITE if ci else MUTED, a)
        elif k == "leaderboard":
            rows_ = vz["rows"]; y0 = 640 + len(sc["lines"]) * hs * 1.04 + 40; rh = min(96, (1215 - y0) / len(rows_))
            mx = max(r[1] for r in rows_)
            if vz.get("tag"): text(cv, vz["tag"], X1, y0 - 12, "mono", 22, MUTED, v, tr=2, align="r")
            for j, (name, val) in enumerate(rows_):
                y = y0 + j * rh; p = eo(prog(t, t0 + .4 + j * .25, .9)); hl = j == vz.get("highlight", 0)
                cv.drawRoundRect(skia.Rect(X0, y, X1, y + rh - 14), 14, 14, paint(CORAL if hl else LINE, (.22 if hl else .5) * v))
                text(cv, f"{j + 1}", X0 + 22, y + rh * .5 + 6, "black", 34, CORAL if hl else MUTED, v)
                text(cv, name, X0 + 70, y + rh * .5 + 4, "semi", fit(name, "semi", 300, 34), WHITE, v)
                bw = (X1 - X0 - 500) * val / mx * p
                cv.drawRoundRect(skia.Rect(X0 + 380, y + rh * .5 - 16, X0 + 380 + bw, y + rh * .5 + 2), 9, 9, paint(CORAL if hl else MUTED, v))
                text(cv, f"{int(val * p)}", X1 - 10, y + rh * .5 + 4, "bold", 30, WHITE, v, align="r")
        elif k == "levels":
            # level map: nodes on a zig-zag path; nodes complete one by one and the next one unlocks
            n = vz.get("count", 5); d0 = vz.get("start_done", 0); dn = vz.get("done", n - 1); step = vz.get("interval", .55)
            yA, yB = vz.get("y_top", 900), vz.get("y_bottom", 1075)
            pts = [(X0 + 55 + k2 * (X1 - X0 - 110) / max(1, n - 1), yB if k2 % 2 == 0 else yA) for k2 in range(n)]
            def tdone(j): return -1 if j < d0 else (t0 + .45 + (j - d0) * step if j < dn else 1e9)
            for j in range(n - 1):
                (xa, ya), (xb, yb) = pts[j], pts[j + 1]
                cv.drawLine(xa, ya, xb, yb, paint(LINE, v, 10))
                f = eo(prog(t, tdone(j), .35)) if tdone(j) >= 0 else 1
                if f > 0: cv.drawLine(xa, ya, xa + (xb - xa) * f, ya + (yb - ya) * f, paint(CORAL, v, 10))
            labs = vz.get("labels", [])
            for j, (x, y) in enumerate(pts):
                td = tdone(j); done = t >= td if td >= 0 else True
                tu = -1 if j <= d0 else tdone(j - 1)          # unlock time = previous node done
                unlocked = t >= tu
                r = 46
                if done:
                    pp = back(prog(t, td, .3)) if td >= 0 else 1
                    cv.drawCircle(x, y, r * (0.6 + .4 * pp), paint(CORAL, v))
                    cv.drawPath(star(x, y, r * .55, r * .24), paint(WHITE, v))
                    if 0 < t - td < .5: cv.drawCircle(x, y, r + 60 * (t - td) / .5 * 1.5, paint(CORAL, v * (1 - (t - td) / .5), 4))
                elif unlocked:
                    cv.drawCircle(x, y, r, paint("#1E2A5C", v))
                    cv.drawCircle(x, y, r + 8 + 6 * math.sin(t * 6), paint(WHITE, .7 * v, 4))
                    text(cv, str(j + 1), x, y + 16, "black", 44, WHITE, v, align="c")
                    if tu >= 0 and t - tu < .45:        # lock popping off
                        q = (t - tu) / .45; cv.save(); cv.translate(x + 30 * q, y - 70 * q); cv.rotate(25 * q)
                        cv.drawRoundRect(skia.Rect(-20, -8, 20, 24), 5, 5, paint("#FFC24D", v * (1 - q)))
                        cv.drawArc(skia.Rect(-13, -28, 13, -2), 180, 180, False, paint("#FFC24D", v * (1 - q), 6)); cv.restore()
                else:
                    cv.drawCircle(x, y, r, paint("#121B3F", v)); cv.drawCircle(x, y, r, paint(LINE, v, 3))
                    cv.drawRoundRect(skia.Rect(x - 18, y - 4, x + 18, y + 24), 5, 5, paint(MUTED, v))
                    cv.drawArc(skia.Rect(x - 12, y - 24, x + 12, y + 2), 180, 180, False, paint(MUTED, v, 6))
                if j < len(labs) and labs[j]:
                    ly = y + 88 if y == yB else y - 66
                    text(cv, labs[j], x, ly, "mono", fit(labs[j], "mono", 150, 24), WHITE if done else MUTED, v, tr=1, align="c")
            if vz.get("tag"): text(cv, vz["tag"], X1, yA - 120, "mono", 22, MUTED, v, tr=2, align="r")
        elif k == "streak":
            # day cells fill with growing flames; optional freeze day keeps the streak alive
            n = vz.get("days", 7); fill = vz.get("fill", n); fz = vz.get("freeze", -1); step = vz.get("interval", .4)
            names = vz.get("names", ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][:n])
            y0 = vz.get("y", 880); gap = 12; w = (X1 - X0 - gap * (n - 1)) / n; h = 150
            cnt = 0
            for j in range(n):
                x = X0 + j * (w + gap); tj = t0 + .45 + j * step; on = j < fill and t >= tj
                q = eo(prog(t, tj, .25)) if j < fill else 0
                cv.drawRoundRect(skia.Rect(x, y0, x + w, y0 + h), 14, 14, paint("#0A1230", v))
                cv.drawRoundRect(skia.Rect(x, y0, x + w, y0 + h), 14, 14, paint(CORAL if on and j != fz else ("#38E1FF" if on else LINE), v, 3))
                text(cv, names[j] if j < len(names) else str(j + 1), x + w / 2, y0 + h + 36, "mono", fit(names[j] if j < len(names) else "", "mono", w, 22), MUTED, v, tr=1, align="c")
                if q > 0:
                    if j == fz:
                        cx, cy = x + w / 2, y0 + h / 2; sh = skia.Path(); s_ = 34 * back(q)
                        sh.moveTo(cx, cy - s_); sh.lineTo(cx + s_ * .85, cy - s_ * .55); sh.lineTo(cx + s_ * .7, cy + s_ * .45); sh.lineTo(cx, cy + s_); sh.lineTo(cx - s_ * .7, cy + s_ * .45); sh.lineTo(cx - s_ * .85, cy - s_ * .55); sh.close()
                        cv.drawPath(sh, paint("#38E1FF", v)); text(cv, "FREEZE", cx, y0 - 16, "mono", fit("FREEZE", "mono", w + 20, 20), "#38E1FF", v * q, tr=1, align="c")
                    else:
                        flame(cv, x + w / 2, y0 + h / 2 + 8, (18 + 26 * (j + 1) / n) * back(q), v, t)
                    cnt += 1 if on else 0
            yb = y0 + h + 125
            lab = vz.get("label", "STREAK"); text(cv, lab, X0, yb, "mono", 30, MUTED, v, tr=3)
            numtxt = f"{vz.get('base', 0) + cnt}"
            text(cv, numtxt, X0 + tw(lab, "mono", 30, 3) + 30, yb + 10, "black", 92, CORAL, v)
            if vz.get("note"): text(cv, vz["note"], X1, yb, "mono", 26, WHITE, vis(t, t0 + .45 + fill * step, t1), tr=1, align="r")
        elif k == "loop":
            # core game loop: 4 steps around a ring, a token runs laps and each lap gets harder
            steps_ = vz["steps"]; n = len(steps_); cx, cy, R = vz.get("cx", 470), vz.get("cy", 1040), vz.get("r", 165)
            lap_s = vz.get("lap_s", 2.4); pin = eo(prog(t, t0 + .2, .5))
            cv.drawArc(skia.Rect(cx - R, cy - R, cx + R, cy + R), -90, 360 * pin, False, paint(LINE, v, 12))
            el = max(0, t - t0 - .6); lap = int(el / lap_s); ang = (el % lap_s) / lap_s * 360 if t > t0 + .6 else 0
            if t > t0 + .6:
                cv.drawArc(skia.Rect(cx - R, cy - R, cx + R, cy + R), -90, ang, False, paint(CORAL, v, 12))
                a = math.radians(-90 + ang); tx, ty = cx + R * math.cos(a), cy + R * math.sin(a)
                cv.drawCircle(tx, ty, 20, paint(WHITE, v)); cv.drawCircle(tx, ty, 30, paint(WHITE, .3 * v, 3))
            for j, lab in enumerate(steps_):
                a = math.radians(-90 + j * 360 / n); x, y = cx + R * math.cos(a), cy + R * math.sin(a)
                act = t > t0 + .6 and (int(ang // (360 / n)) == j)
                fs = fit(lab, "bold", 230, 34); pw = tw(lab, "bold", fs) + 40
                x = min(max(x, X0 + pw / 2), X1 - pw / 2)
                ap = vis(t, t0 + .3 + j * .15, t1)
                cv.drawRoundRect(skia.Rect(x - pw / 2, y - 34, x + pw / 2, y + 30), 30, 30, paint(CORAL if act else "#1E2A5C", ap * v))
                text(cv, lab, x, y + 10, "bold", fs, WHITE, ap * v, align="c")
            if vz.get("center"):
                ct = vz["center"] if lap == 0 else vz.get("center_next", vz["center"]).replace("{n}", str(lap + 1))
                text(cv, ct, cx, cy + 14 + vz.get("center_dy", 0), "mono", fit(ct, "mono", R * 1.25, 30), MUTED if lap == 0 else CORAL, v, tr=2, align="c")
        elif k == "meter":
            p = eo(prog(t, t0 + .2, 1.4)); val = vz["from"] + (vz["to"] - vz["from"]) * p
            y = 1080; cv.drawRoundRect(skia.Rect(X0, y, X1, y + 44), 22, 22, paint(LINE, v))
            cv.drawRoundRect(skia.Rect(X0, y, X0 + (X1 - X0) * clamp(val / vz.get("max", 100)), y + 44), 22, 22, paint(CORAL, v))
            text(cv, f"{val:.0f}{vz.get('unit', '%')}", X0, y - 30, "black", 120, WHITE, v)
            if vz.get("label"): text(cv, vz["label"], X0, y + 100, "med", fit(vz["label"], "med", X1 - X0, 36), MUTED, v)
    def sc_box(cv, t, sc, t0, t1, first):
        v = vis(t, t0, t1); sw = t0 + sc.get("switch", 1.25)
        if t < sw: headline(cv, sc["a"]["lines"], t, t0, sw + .1, 600, 110, accent=sc["a"].get("accent", []))
        else: headline(cv, sc["b"]["lines"], t, sw, t1, 600, 110, accent=sc["b"].get("accent", []))
        cx, cy, s = 470, 1060, 190; glow = prog(t, sw, .3)
        front = skia.Rect(cx - s, cy - s * .55, cx + s, cy + s * .95)
        top = skia.Path(); top.moveTo(cx - s, cy - s * .55); top.lineTo(cx - s + 90, cy - s * .55 - 80); top.lineTo(cx + s + 90, cy - s * .55 - 80); top.lineTo(cx + s, cy - s * .55); top.close()
        side = skia.Path(); side.moveTo(cx + s, cy - s * .55); side.lineTo(cx + s + 90, cy - s * .55 - 80); side.lineTo(cx + s + 90, cy + s * .95 - 80); side.lineTo(cx + s, cy + s * .95); side.close()
        sc_ = 1 + .06 * eo(glow) - .06 * eo(prog(t, sw + .3, .3))
        cv.save(); cv.translate(cx, cy); cv.scale(sc_, sc_); cv.translate(-cx, -cy)
        if glow > 0: cv.drawCircle(cx, cy, 380, paint(CORAL, .10 * glow * v))
        on = glow > .5
        cv.drawPath(top, paint("#FF7A70" if on else "#2A376B", v)); cv.drawPath(side, paint("#D9473D" if on else "#121B3F", v))
        cv.drawRect(front, paint(CORAL if on else "#1A2550", v))
        for pth in (top, side): cv.drawPath(pth, paint(WHITE, .5 * v, 3))
        cv.drawRect(front, paint(WHITE, .5 * v, 3))
        if on and sc.get("label"): text(cv, sc["label"], cx, cy + 40, "black", fit(sc["label"], "black", 2 * s - 30, 64), WHITE, v * clamp((glow - .5) * 4), align="c")
        fly = eo(prog(t, sw, .45)); cv.save(); cv.translate(cx + 80 + fly * 260, cy + 90 - fly * 380); cv.rotate(-12 - fly * 120)
        badge(cv, 0, 0, 58 * (1 - .5 * fly), v * (1 - fly)); cv.restore(); cv.restore()
    def sc_cta(cv, t, sc, t0, t1, first):
        v = vis(t, t0, TOTAL + 1); end_ = E[LAST] + .1; a1 = 1 - prog(t, end_, .25)
        headline(cv, sc["lines"], t, t0 + .35, end_ + .3, 640, 128, accent=sc.get("accent", []))
        if sc.get("kicker"): text(cv, sc["kicker"], X0, 500, "mono", 30, MUTED, v * a1, tr=3)
        p = eo(prog(t, end_, .35))
        if p > 0:
            text(cv, "ludogic", 540, 900 + (1 - p) * 30, "thin", 170, WHITE, p, tr=4, align="c")
            cv.drawLine(540 - 200 * p, 950, 540 + 200 * p, 950, paint(CORAL, p, 4))
            text(cv, sc.get("tagline", "Training people actually finish."), 540, 1030, "med", 40, MUTED, p, align="c")
            b = eo(prog(t, end_ + .35, .3)); bt = sc.get("button", "FOLLOW FOR MORE")
            bw = tw(bt, "bold", 34, 2) + 120
            cv.drawRoundRect(skia.Rect(540 - bw / 2, 1110, 540 + bw / 2, 1200), 45, 45, paint(CORAL, b))
            text(cv, bt, 540, 1168, "bold", 34, WHITE, b, tr=2, align="c")
            text(cv, sc.get("url", "ludogic.dev"), 540, 1270, "mono", 30, WHITE, b * .9, tr=2, align="c")


    def flame(cv, cx, cy, s, a=1., t=0.):
        s *= 1 + .06 * math.sin(t * 14 + cx)
        def drop(sz, col, al):
            p = skia.Path(); p.moveTo(cx, cy - sz)
            p.cubicTo(cx + .95 * sz, cy - .15 * sz, cx + .75 * sz, cy + .85 * sz, cx, cy + .85 * sz)
            p.cubicTo(cx - .75 * sz, cy + .85 * sz, cx - .95 * sz, cy - .15 * sz, cx, cy - sz); p.close()
            cv.drawPath(p, paint(col, al))
        drop(s, CORAL, a); drop(s * .55, "#FFC24D", a)
    def gift(cv, cx, cy, s, a=1.):
        cv.drawRoundRect(skia.Rect(cx - s, cy - s * .55, cx + s, cy + s * .9), 6, 6, paint(CORAL, a))
        cv.drawRect(skia.Rect(cx - s * 1.1, cy - s * .75, cx + s * 1.1, cy - s * .45), paint("#FF7A70", a))
        cv.drawRect(skia.Rect(cx - s * .14, cy - s * .75, cx + s * .14, cy + s * .9), paint("#FFC24D", a))
        cv.drawCircle(cx - s * .35, cy - s * .9, s * .28, paint("#FFC24D", a, 5)); cv.drawCircle(cx + s * .35, cy - s * .9, s * .28, paint("#FFC24D", a, 5))
    def key(cv, cx, cy, s, a=1.):
        cv.drawCircle(cx - s * .45, cy, s * .38, paint("#FFC24D", a, 7))
        cv.drawLine(cx - s * .07, cy, cx + s * .9, cy, paint("#FFC24D", a, 7))
        cv.drawLine(cx + s * .55, cy, cx + s * .55, cy + s * .35, paint("#FFC24D", a, 7)); cv.drawLine(cx + s * .85, cy, cx + s * .85, cy + s * .3, paint("#FFC24D", a, 7))
    def reveal_draw(cv, rv, cx, cy, w, h, a, t, level=1, grey=0.):
        col = MUTED if grey > .5 else CORAL
        if rv == "flame": flame(cv, cx, cy + 6, min(w, h) * (.18 + .045 * level), a, t)
        elif rv == "gift": gift(cv, cx, cy + 4, min(w, h) * .26, a)
        elif rv == "key": key(cv, cx - 4, cy, min(w, h) * .32, a)
        else:
            sz = fit(rv, "black", w - 14, 38)
            text(cv, rv, cx, cy + sz * .36, "black", sz, col if rv not in ("?",) else WHITE, a, align="c")
    def door(cv, x, y, w, h, num, openp, rv, a, t, golden=False, level=1, grey=0., glow=0.):
        cv.drawRoundRect(skia.Rect(x, y, x + w, y + h), 10, 10, paint("#0A1230", a))
        if glow > 0: cv.drawRoundRect(skia.Rect(x - 6, y - 6, x + w + 6, y + h + 6), 14, 14, paint("#FFC24D", .55 * glow * a, 5))
        if openp > 0 and rv: reveal_draw(cv, rv, x + w * .55, y + h / 2, w * .86, h, a * clamp(openp * 1.6), t, level, grey)
        f = math.cos(clamp(openp) * math.pi / 2 * .92)          # panel width factor (hinge on the left)
        ext = (1 - f) * 10
        pnl = skia.Path(); pnl.moveTo(x, y); pnl.lineTo(x + w * f, y - ext); pnl.lineTo(x + w * f, y + h + ext); pnl.lineTo(x, y + h); pnl.close()
        cv.drawPath(pnl, paint("#E8A93A" if golden else "#1E2A5C", a))
        cv.drawPath(pnl, paint(WHITE, .35 * a, 2))
        if f > .35:
            text(cv, str(num), x + w * f / 2, y + h / 2 + 14, "black", 38 * f, "#2A1A00" if golden else WHITE, a * clamp((f - .35) * 2), align="c")
            cv.drawCircle(x + w * f - 14 * f, y + h / 2, 4.5, paint("#FFC24D" if not golden else "#2A1A00", a))
        cv.drawRoundRect(skia.Rect(x, y, x + w, y + h), 10, 10, paint(LINE, a, 2))
    def sc_doors(cv, t, sc, t0, t1, first):
        v = 1 if first else vis(t, t0, t1)
        if not first: v = vis(t, t0, t1)
        else: v = 1 - prog(t, t1 - .16, .16)
        th = sc.get("then"); tth = S[th["line"]] if th else t1
        if t < tth or not th: headline(cv, sc["lines"], t, t0 if not first else -1, tth + (.1 if th else 0), 575, sc.get("size", 84), accent=sc.get("accent", []))
        if th and t >= tth - .05: headline(cv, th["lines"], t, tth, t1, 575, th.get("size", 84), accent=th.get("accent", []))
        n = sc.get("count", 24); cols = sc.get("cols", 6); rows = math.ceil(n / cols)
        gx0, gy0, gx1, gy1 = X0, 715, X1, 1195
        gw, gh = 12, 12; w = (gx1 - gx0 - gw * (cols - 1)) / cols; h = (gy1 - gy0 - gh * (rows - 1)) / rows
        sched = {d["i"]: d for d in door_schedule(sc, t0, t1, S)}
        pre = sc.get("pre_open", {})          # {"0": "flame", ...} doors already open when the scene starts
        opened = 0
        for i in range(n):
            r, c = divmod(i, cols); x = gx0 + c * (w + gw); y = gy0 + r * (h + gh)
            a = v * eo(prog(t, (t0 if not first else -1) + .02 * i, .2)) if not first else v
            d = sched.get(i); rv = None; op = 0; golden = i == sc.get("golden", -1); lvl = 1; grey = 0
            if str(i) in pre: rv = pre[str(i)]; op = 1; lvl = i + 1
            if d:
                rv = d["reveal"]; op = eo(prog(t, d["t"], .28)); golden = golden or d["golden"]; lvl = d.get("level", 1)
                if sc.get("mode") == "coupon" and t > d["t"] + .6: grey = 1
            if op > .5: opened += 1
            pop = 1 + .12 * math.sin(clamp((t - d["t"]) / .3) * math.pi) if d and t > d["t"] else 1
            glow = (.5 + .5 * math.sin(t * 6)) if (golden and op < .5) else 0
            cv.save(); cv.translate(x + w / 2, y + h / 2); cv.scale(pop, pop); cv.translate(-(x + w / 2), -(y + h / 2))
            door(cv, x, y, w, h, i + 1, op, rv, a, t, golden, lvl, grey, glow); cv.restore()
        cnt = sc.get("counter")
        if cnt:
            if cnt == "opened": lab = f"OPENED {opened}/{n}"
            elif cnt == "streak": lab = f"STREAK x{min(opened, sc.get('streak', 5))}"
            else: lab = cnt
            text(cv, lab, X0, 490, "mono", 30, CORAL, v, tr=3)

    IMPL = {"doors": sc_doors, "stat": sc_stat, "stamp": sc_stamp, "bars": sc_bars, "title": sc_title, "number": sc_number,
            "card": sc_card, "box": sc_box, "cta": sc_cta}
    scenes = spec["scenes"]
    spans = []
    for i, sc in enumerate(scenes):
        t0 = S[sc["line"]]
        t1 = S[scenes[i + 1]["line"]] - (0.05 if scenes[i + 1]["type"] in ("stamp", "number") else 0.2) if i + 1 < len(scenes) else TOTAL + 1
        spans.append((t0, t1))
    flashes = [S[sc["line"]] for sc in scenes if sc["type"] in ("title", "cta") and sc.get("big")] + [S[sc["line"]] + .32 for sc in scenes if sc["type"] == "number"] + [S[scenes[-1]["line"]]]

    def frame(cv, t):
        background(cv, t); hud(cv, t)
        for i, (sc, (t0, t1)) in enumerate(zip(scenes, spans)):
            if i == 0 and sc["type"] in ("title", "box", "card"): t0 = -.25   # first frame already shows the hook (cover + scroll stop)
            if t0 - .1 <= t <= t1: IMPL[sc["type"]](cv, t, sc, t0, t1, i == 0)
        if t < E[LAST] + .1: captions(cv, t)
        for tt in flashes:
            f = 1 - prog(t, tt, .12)
            if 0 < f < 1: cv.drawRect(skia.Rect(0, 0, WD, HT), paint(WHITE, .10 * f))
    return frame, skia

# =====================================================================
# 4. quality gates (local text tools, MIT, from instagram-agent-skill)
# =====================================================================
def run_json(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout)
    except Exception as e:
        return {"error": str(e)}

def gates(spec, out):
    T = os.path.join(ROOT, "tools")
    hook = spec.get("hook") or " ".join(l.get("cap", l["say"]) for l in spec["lines"][:2])
    hs = run_json([sys.executable, "-I", f"{T}/hookscore.py", "--hook", hook, "--json"])
    script = "\n".join(l.get("cap", l["say"]) for l in spec["lines"])
    open(f"{out}/script.txt", "w").write(script + "\n")
    bt = run_json([sys.executable, "-I", f"{T}/beats.py", f"{out}/script.txt", "--target", str(spec.get("target_s", 30)), "--wpm", "170", "--json"])
    res = {"hook_text": hook, "hookscore": hs, "beats": bt}
    if spec.get("caption"):
        open(f"{out}/caption.txt", "w").write(spec["caption"])
        kw = ",".join(spec.get("keywords", []))
        cmd = [sys.executable, "-I", f"{T}/caption.py", f"{out}/caption.txt", "--json"] + (["--keywords", kw] if kw else [])
        res["caption_lint"] = run_json(cmd)
        res["human"] = run_json([sys.executable, "-I", f"{T}/detect.py", f"{out}/caption.txt", "--json"])
    return res

# =====================================================================
# 5. build
# =====================================================================
def build(spec_path, out, preview=False):
    t_start = time.time()
    spec = json.load(open(spec_path)); os.makedirs(out, exist_ok=True)
    shutil.copy(spec_path, f"{out}/spec.json")
    t = time.time(); meta = make_voice(spec, out); t_voice = time.time() - t
    tl = make_timeline(spec, meta, out)
    t = time.time(); am = make_audio(spec, tl, out); t_audio = time.time() - t
    frame, skia = make_renderer(spec, tl)
    surf = skia.Surface(WD, HT); cv = surf.getCanvas()
    # contact sheet: 10 frames, at each scene midpoint + ends
    S = [l["start"] for l in tl["lines"]]
    pts = sorted(set([0.0] + [round(l["start"] + .75 * (l["end"] - l["start"]), 2) for l in tl["lines"]] + [round(tl["total"] - .2, 2)]))
    shutil.rmtree(f"{out}/prev", ignore_errors=True); os.makedirs(f"{out}/prev", exist_ok=True)   # no stale frames in the sheet
    for p in pts:
        frame(cv, p); surf.makeImageSnapshot().save(f"{out}/prev/{p:06.2f}.png", skia.kPNG)
    cols = 7
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", f"{out}/prev/*.png",
                    "-vf", f"scale=216:384,tile={cols}x{math.ceil(len(pts) / cols)}", "-frames:v", "1", "-q:v", "3", f"{out}/sheet.jpg"], check=True)
    g = gates(spec, out)
    metrics = {"id": spec["id"], "engine_version": ENGINE_VERSION, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "duration_s": tl["total"], "lines": len(tl["lines"]), "scenes": len(spec["scenes"]),
               "scene_types": [s["type"] + (":" + s.get("visual", {}).get("kind") if s.get("visual") else "") for s in spec["scenes"]],
               "avg_scene_s": round(tl["total"] / len(spec["scenes"]), 2),
               "words": sum(len(l["cap"].split()) for l in tl["lines"]),
               "speech_s": round(sum(l["end"] - l["start"] for l in tl["lines"]), 2),
               "voice": spec.get("voice", {}).get("name", "af_heart"), "voice_speed": spec.get("voice", {}).get("speed", 1.08),
               "palette": spec.get("style", {}).get("accent", "#FF5A4E") + "/" + spec.get("style", {}).get("bg", "#070B1A"),
               "font": "Inter Display + DejaVu Sans Mono", "art_direction": spec.get("style", {}).get("art", "navy-coral motion graphics, XP bar, particles"),
               **am, **{"gates": g},
               "render": {"voice_s": round(t_voice, 1), "audio_s": round(t_audio, 1)},
               "cost": {"elevenlabs_credits": 0, "eur": 0}}
    if not preview:
        t = time.time()
        nfr = int(math.ceil(tl["total"] * FPS))
        ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra",
                               "-s", f"{WD}x{HT}", "-r", str(FPS), "-i", "-", "-i", f"{out}/mix.wav", "-map", "0:v", "-map", "1:a",
                               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", f"{out}/video.mp4"], stdin=subprocess.PIPE)
        for n in range(nfr):
            frame(cv, n / FPS); ff.stdin.write(surf.makeImageSnapshot().tobytes())
        ff.stdin.close(); ff.wait()
        frame(cv, spec.get("cover_t", 0.0)); surf.makeImageSnapshot().save(f"{out}/cover.png", skia.kPNG)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f"{out}/cover.png", "-q:v", "3", f"{out}/cover.jpg"], check=True)
        os.remove(f"{out}/cover.png")
        metrics["render"]["video_s"] = round(time.time() - t, 1)
        metrics["file_mb"] = round(os.path.getsize(f"{out}/video.mp4") / 1e6, 2)
    metrics["render"]["total_s"] = round(time.time() - t_start, 1)
    json.dump(metrics, open(f"{out}/metrics.json", "w"), indent=1)
    hsv = g["hookscore"].get("score") if isinstance(g["hookscore"], dict) else None
    print(json.dumps({"id": spec["id"], "duration_s": tl["total"], "hookscore": hsv, "lufs": am["lufs"],
                      "voice_minus_bed_db": am["voice_minus_bed_db"], "render_s": metrics["render"]["total_s"]}))

ENGINE_VERSION = "1.2.0"
if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3], preview="--preview" in sys.argv)
    else:
        print(__doc__); sys.exit(1)
