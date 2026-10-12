#!/usr/bin/env python3
"""Learning registry for Ludogic reels (one row per video).

    registry.py add      REG.csv OUTDIR [--status produced|scheduled|reserve] [--set key=value ...]
    registry.py set      REG.csv ID key=value [key=value ...]
    registry.py outcomes REG.csv ID reach=.. plays=.. likes=.. comments=.. shares=.. saves=.. follows=.. link_clicks=.. profile_visits=.. conversions=.. avg_watch_s=..
    registry.py score    REG.csv                 # recompute scores for rows with outcomes
    registry.py guide    REG.csv GUIDE.md        # reinforcement / punishment table per attribute
    registry.py pick     REG.csv ID1 ID2 ...     # rank candidates for publishing (predicted score)

Score (computed 7 days after publishing), each ratio vs the median of the last 8 published reels, capped at 3:
    score = 0.4 * interaction_rate_ratio + 0.4 * conversion_rate_ratio + 0.2 * follows_ratio
Reinforcement: score >= 1.2 -> +1 to every attribute value used; score <= 0.8 -> -1.
Winner: mean >= 1.2 with >= 3 uses. Punished: mean < 0.8 with >= 4 uses (rest 1 month, only as experiment).
Cold start: first 4 weeks only record and explore.
"""
import csv, sys, os, json, statistics, datetime

COLS = [
 # identity / lifecycle
 "id", "week", "status", "title", "pillar", "persona", "topic", "format", "networks",
 "created_at", "scheduled_for_madrid", "weekday", "hour_madrid", "published_at", "metricool_post_id", "planner_url",
 "media_url", "drive_folder_url",
 # creative (pre-publication)
 "hook_text", "hook_formula", "hookscore", "hook_weakest", "humor", "beats_flags", "caption_verdict", "caption_first_line_chars",
 "human_score", "cta_type", "hashtags", "keywords", "sources",
 "duration_s", "words", "speech_s", "wpm", "lines", "scenes", "avg_scene_s", "scene_types",
 "voice", "voice_speed", "music_bpm", "music_mood", "palette", "font", "art_direction", "cover_t",
 # production / automation
 "engine_version", "lufs", "voice_minus_bed_db", "render_s", "file_mb", "qa_fixes",
 "claude_model", "claude_session_min", "claude_tool_calls", "claude_tokens_est",
 "elevenlabs_credits", "other_cost_eur", "human_min",
 # outcomes (Metricool, 7 days after publishing)
 "reach", "plays", "avg_watch_s", "completion_rate", "likes", "comments", "shares", "saves",
 "profile_visits", "follows", "link_clicks", "conversions", "interactions", "interaction_rate", "conversion_rate",
 "score", "reinforcement", "experiment", "user_feedback", "notes"]

ATTRS = ["pillar", "persona", "hook_formula", "humor", "cta_type", "voice", "music_mood", "palette",
         "art_direction", "weekday", "hour_madrid", "dur_bucket", "scenes_bucket", "first_scene"]

def load(p):
    if not os.path.exists(p): return []
    with open(p, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
def save(p, rows):
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore"); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in COLS})
def num(x):
    try: return float(x)
    except Exception: return None
def kv(args): return dict(a.split("=", 1) for a in args)

def add(reg, outdir, extra):
    rows = load(reg)
    spec = json.load(open(f"{outdir}/spec.json")); m = json.load(open(f"{outdir}/metrics.json"))
    g = m.get("gates", {}); hs = g.get("hookscore", {}); bt = g.get("beats", {}); cl = g.get("caption_lint", {}); hu = g.get("human", {})
    cap = spec.get("caption", "")
    r = {"id": spec["id"], "week": spec["id"][:8], "status": "produced", "title": spec.get("title", ""),
         "pillar": spec.get("pillar", ""), "persona": spec.get("persona", ""), "topic": spec.get("topic", ""),
         "format": "reel", "networks": "instagram+facebook", "created_at": m.get("built_at", ""),
         "hook_text": spec.get("hook", ""), "hook_formula": spec.get("hook_formula", ""), "hookscore": hs.get("score", ""),
         "hook_weakest": hs.get("weakest", ""), "humor": spec.get("humor", ""),
         "beats_flags": len([n for n in bt.get("notes", []) if not str(n).lower().startswith(("loops", "length is on"))]) if isinstance(bt, dict) else "",
         "caption_verdict": cl.get("verdict", ""), "caption_first_line_chars": cl.get("first_line_chars", ""),
         "human_score": hu.get("human_score", ""), "cta_type": spec.get("cta_type", "follow"),
         "hashtags": " ".join(w for w in cap.split() if w.startswith("#")), "keywords": "|".join(spec.get("keywords", [])),
         "sources": "|".join(spec.get("sources", [])),
         "duration_s": m.get("duration_s"), "words": m.get("words"), "speech_s": m.get("speech_s"),
         "wpm": round(m.get("words", 0) / max(1e-6, m.get("speech_s", 1)) * 60, 1), "lines": m.get("lines"),
         "scenes": m.get("scenes"), "avg_scene_s": m.get("avg_scene_s"), "scene_types": "|".join(m.get("scene_types", [])),
         "voice": m.get("voice"), "voice_speed": m.get("voice_speed"), "music_bpm": m.get("music_bpm"),
         "music_mood": spec.get("music", {}).get("mood", ""), "palette": m.get("palette"), "font": m.get("font"),
         "art_direction": m.get("art_direction"), "cover_t": spec.get("cover_t", 0),
         "engine_version": m.get("engine_version"), "lufs": m.get("lufs"), "voice_minus_bed_db": m.get("voice_minus_bed_db"),
         "render_s": m.get("render", {}).get("total_s"), "file_mb": m.get("file_mb", ""),
         "elevenlabs_credits": 0, "other_cost_eur": 0}
    r.update(extra)
    rows = [x for x in rows if x["id"] != r["id"]] + [r]
    save(reg, rows); print("added", r["id"])

def setv(reg, rid, extra):
    rows = load(reg); hit = False
    for r in rows:
        if r["id"] == rid: r.update(extra); hit = True
    if not hit: sys.exit(f"id {rid} not found")
    save(reg, rows); print("updated", rid)

def outcomes(reg, rid, extra):
    rows = load(reg)
    for r in rows:
        if r["id"] != rid: continue
        r.update(extra)
        inter = sum(num(r.get(k)) or 0 for k in ("likes", "comments", "shares", "saves"))
        conv = num(r.get("conversions"))
        if conv is None: conv = (num(r.get("link_clicks")) or 0) + (num(r.get("profile_visits")) or 0) * 0.25
        reach = num(r.get("reach")) or num(r.get("plays")) or 0
        r["interactions"] = int(inter); r["conversions"] = round(conv, 2)
        r["interaction_rate"] = round(inter / reach, 4) if reach else ""
        r["conversion_rate"] = round(conv / reach, 4) if reach else ""
        if r.get("status") in ("scheduled", "produced", "reserve"): r["status"] = "published"
    save(reg, rows); print("outcomes", rid)

def score(reg):
    rows = load(reg)
    pub = [r for r in rows if r.get("interaction_rate") not in ("", None)]
    pub.sort(key=lambda r: r.get("published_at") or r.get("scheduled_for_madrid") or r["id"])
    for i, r in enumerate(pub):
        prev = pub[max(0, i - 8):i] or pub[:max(1, i)]
        def ratio(k):
            vals = [num(x.get(k)) for x in prev if num(x.get(k)) is not None]
            med = statistics.median(vals) if vals else None
            v = num(r.get(k))
            if v is None: return 1.0
            if not med: return 1.0 if not v else 3.0
            return min(3.0, v / med)
        s = 0.4 * ratio("interaction_rate") + 0.4 * ratio("conversion_rate") + 0.2 * ratio("follows")
        r["score"] = round(s, 3)
        r["reinforcement"] = "+1" if s >= 1.2 else ("-1" if s <= 0.8 else "0")
    save(reg, rows); print("scored", len(pub))

def attrs(r):
    d = num(r.get("duration_s")) or 0; n = num(r.get("scenes")) or 0
    a = {k: r.get(k, "") for k in ATTRS if k in r}
    a["dur_bucket"] = "<25s" if d < 25 else ("25-35s" if d <= 35 else ">35s")
    a["scenes_bucket"] = "<=7" if n <= 7 else ("8-10" if n <= 10 else "11+")
    a["first_scene"] = (r.get("scene_types", "").split("|") or [""])[0]
    return a

def guide(reg, out):
    rows = [r for r in load(reg) if r.get("score") not in ("", None)]
    stats = {}
    for r in rows:
        for k, v in attrs(r).items():
            if v in ("", None): continue
            s = stats.setdefault((k, str(v)), {"n": 0, "sum": 0., "rf": 0})
            s["n"] += 1; s["sum"] += float(r["score"]); s["rf"] += int(r.get("reinforcement") or 0)
    lines = ["# Guía vigente: refuerzo y castigo (Reels Ludogic)", "",
             f"Actualizada: {datetime.date.today().isoformat()} · reels con puntuación: {len(rows)}", "",
             "Puntuación = 0,4·interacción + 0,4·conversión + 0,2·seguidores (1,0 = normal). Ganador: media ≥ 1,2 con ≥ 3 usos. Castigado: media < 0,8 con ≥ 4 usos.", "",
             "| Atributo | Valor | Usos | Media | Refuerzo neto | Estado |", "|---|---|---|---|---|---|"]
    for (k, v), s in sorted(stats.items(), key=lambda kv: (kv[0][0], -kv[1]["sum"] / kv[1]["n"])):
        m = s["sum"] / s["n"]
        st = "GANADOR" if (m >= 1.2 and s["n"] >= 3) else ("CASTIGADO" if (m < 0.8 and s["n"] >= 4) else "explorando")
        lines.append(f"| {k} | {v} | {s['n']} | {m:.2f} | {s['rf']:+d} | {st} |")
    if not rows: lines.append("| — | sin datos aún (arranque en frío: solo registrar y explorar) | 0 | — | — | — |")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n"); print("guide", out, len(stats))

def pick(reg, ids):
    rows = load(reg); scored = [r for r in rows if r.get("score") not in ("", None)]
    def pred(r):
        if not scored:
            fb = (r.get("user_feedback") or "").lower()
            return round((num(r.get("hookscore")) or 0) / 100 - (0.5 if fb.startswith("dislike") else 0) + (0.2 if fb.startswith("like") else 0), 3)
        a = attrs(r); vals = []
        for k, v in a.items():
            m = [float(x["score"]) for x in scored if attrs(x).get(k) == v]
            if m: vals.append(sum(m) / len(m))
        base = sum(vals) / len(vals) if vals else 1.0
        p = 0.8 * base + 0.2 * (num(r.get("hookscore")) or 0) / 100
        fb = (r.get("user_feedback") or "").lower()
        if fb.startswith("dislike"): p -= 0.5      # the user's taste outranks the model
        elif fb.startswith("like"): p += 0.2
        return round(p, 3)
    cand = [r for r in rows if r["id"] in ids]
    for r in sorted(cand, key=pred, reverse=True): print(r["id"], pred(r), r.get("pillar"), r.get("hook_text"))

if __name__ == "__main__":
    a = sys.argv
    if len(a) < 3: print(__doc__); sys.exit(1)
    cmd, reg = a[1], a[2]
    if cmd == "add":
        st = a[a.index("--status") + 1] if "--status" in a else "produced"
        ex = kv(a[a.index("--set") + 1:]) if "--set" in a else {}
        ex.setdefault("status", st); add(reg, a[3], ex)
    elif cmd == "set": setv(reg, a[3], kv(a[4:]))
    elif cmd == "outcomes": outcomes(reg, a[3], kv(a[4:]))
    elif cmd == "score": score(reg)
    elif cmd == "guide": guide(reg, a[3])
    elif cmd == "pick": pick(reg, a[3:])
    else: print(__doc__)
