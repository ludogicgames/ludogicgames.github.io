# Ludogic social engine (branch `social-engine`)

Automated Instagram/Facebook reel production for Ludogic. This branch is **not** part of the website.
It is used by the Community Manager scheduled tasks (Friday / Sunday / day 1).

- `engine/reel.py` - spec JSON -> finished reel (voice, music, SFX, motion graphics, captions, cover, contact sheet, metrics)
- `engine/registry.py` - learning registry (one row per reel; scoring, reinforcement/punishment guide, publish picker)
- `tools/` - local text gates (MIT, from Jake Schincariol's instagram-agent-skill): `hookscore.py`, `beats.py`, `caption.py`, `detect.py`
- `specs/` - every reel's spec (the spec + engine version regenerate the exact video)
- `setup.sh` - installs deps and downloads the Kokoro TTS model (GitHub releases)

Media for Metricool lives on the orphan branch `reels-media` and is served from
`https://raw.githubusercontent.com/ludogicgames/ludogicgames.github.io/reels-media/<ID>.mp4` (and `<ID>-cover.jpg`).
Metricool copies the media to its own storage when a post is scheduled, so files can be pruned after scheduling
(keep the reserve reels until they are used). The private recovery archive and the master registry live in
Google Drive: `Ludogic · Social Media/` (`00_Sistema`, `01_Registro`, `02_Reels/<ID>/`).

## Quick start (fresh session)

```bash
git clone --depth 1 -b social-engine https://github.com/ludogicgames/ludogicgames.github.io social-engine
cd social-engine && bash setup.sh
python3 engine/reel.py build specs/<ID>.json out/<ID> --preview   # contact sheet only (~40 s) -> LOOK at out/<ID>/sheet.jpg
python3 engine/reel.py build specs/<ID>.json out/<ID>             # full render (~3 min)
```

## Spec format

```json
{
 "id": "2026-W43-R01", "title": "...", "pillar": "Enseña|Demuestra|Opina|Vende", "persona": "L&D|MKT|SaaS|All",
 "topic": "...", "mechanics": ["levels", "unlocks"], "language": "en", "hook": "first spoken line(s) as text", "hook_formula": "Stat + Stakes", "humor": 0,
 "cta_type": "follow|comment-keyword|comment-number|save|dm|visit",
 "target_s": 30, "voice": {"name": "af_heart", "speed": 1.08},
 "music": {"bpm": 112, "drop_line": 6, "mood": "driving minimal electronic", "progression": [[57,[57,60,64]], ...]},
 "style": {"accent": "#FF5A4E", "bg": "#070B1A", "art": "navy-coral motion graphics, XP bar, particles"},
 "keywords": ["3 search terms that appear in the caption"], "sources": ["every fact used"],
 "lines": [{"say": "TTS text (numbers spelled out, M.I.T., Ludo-jick)", "cap": "on-screen caption text", "gap": 0.25}],
 "scenes": [{"type": "...", "line": <index of the line where the scene starts>, ...}],
 "caption": "post text (first line = hook + single ask; source; max 5 hashtags)",
 "cover_t": 0.0
}
```

Scene types (a scene lasts until the next scene's line starts):

| type | params |
|---|---|
| `stat` | `stat`, `label[]`, optional `then{line, headline[], accent[], icons: badges_fail|none}` (best opening scene: hook card at frame 1) |
| `stamp` | `text` (short verdict, e.g. NOT A GUESS.) |
| `bars` | `kicker`, `title`, `data[[label,value]]`, `max`, `unit`, `decimals`, `source`, `footer{text, delay}`, `highlight` |
| `title` | `kicker`, `big`+`sub` **or** `lines[]`+`accent[]`, optional `then{line, lines[], accent[]}`, `counter{line,label,from,steps,note}` |
| `number` | `pre`, `number`, `word` |
| `card` | `num`, `lines[]`, `accent[]`, `visual{kind: timer|path|flow|list|compare|meter, ...}` |
| `box` | `a{lines,accent}`, `b{lines,accent}`, `switch` (s), `label` |
| `cta` | `kicker`, `lines[]`, `accent[]`, `tagline`, `button`, `url` (always last) |

Visual kinds: `timer{seconds,reward,reward_sub,strike}`, `path{start,goal}`, `flow{x,y,band,low,high,low_at,high_at}`,
`list{items[]}` (max 4), `compare{left{title,items[]},right{title,items[]}}` (max 3 items each), `meter{from,to,max,unit,label}`.

Editorial rules from the user (2026-10-12):
- **Do not say "At Ludogic..." in the voiceover or captions**, and no brand kicker on the CTA scene. The logo/end card is enough. Close on the idea (e.g. a punchline about gamification), not on the company name.
- **Talk more about gamification**: every reel must name and explain at least one concrete gamification mechanic (streaks, levels, XP, feedback loops, quests, badges done right, leaderboards, unlocks, progress bars, boss fights...). Data-only reels (e.g. the forgetting-curve one) are not enough on their own.

Rules: headlines <= 6 words per card; every number/fact must be sourced; safe zone x 90-850, y 260-1420 is enforced by the layouts.

## Quality gates (must pass before a reel can be published)

1. `hookscore` >= 90 (`tools/hookscore.py --hook "..."`)
2. `beats.py` (170 wpm): hook <= 3 s; long beats only if the visual animates inside them
3. Caption: `caption.py --keywords ...` = READY
4. Contact sheet looked at: no overlaps, nothing outside safe zone, colours correct
5. Audio: LUFS -14 +/- 1, voice clearly over the bed (voice_minus_bed_db >= 5)

## A/B tests

A/B pair = same topic and hook, one deliberate change set (spec fields `ab_group`, `variant` A|B).
Publish both in the **same weekday and hour on consecutive weeks** (or as Instagram TRIAL_REEL on the same day when available).
After both have 7-day scores, compare: the winner's distinguishing attributes get +1 in the guide, and the result is written
in `guia_vigente.md` under "Resultados A/B". Note the order effect (later week = bigger account) when concluding.

## Registry

```bash
python3 engine/registry.py add registry/reels_registry.csv out/<ID> --set status=scheduled scheduled_for_madrid=... weekday=Wed hour_madrid=18
python3 engine/registry.py outcomes registry/reels_registry.csv <ID> reach=.. plays=.. likes=.. comments=.. shares=.. saves=.. follows=.. link_clicks=.. profile_visits=..
python3 engine/registry.py score registry/reels_registry.csv
python3 engine/registry.py guide registry/reels_registry.csv out/guia_vigente.md
python3 engine/registry.py pick registry/reels_registry.csv <ID1> <ID2> <ID3> <ID4>
python3 engine/registry.py check registry/reels_registry.csv <ID>   # must pass (>= 40 stats) before uploading the registry
python3 engine/test_registry.py                                      # self-check after editing registry.py
```

Baremos (user, 2026-10-16): the goal is more clicks, followers, views and retention. 7-day score =
clicks/reach 0.30 + follows/reach 0.25 + retention (avg watch / duration) 0.25 + plays 0.10 + interactions/reach 0.10,
each vs the median of the previous 8 reels. `registry.py guide` writes these weights, the targets to beat, the winning
combination and the punished values between `<!-- auto:start -->` / `<!-- auto:end -->` in `guia_vigente.md`;
everything outside those markers (user rules, feedback, A/B results, Sunday notes) is kept.

Weekly cadence (user, 2026-10-16): produce 4, schedule 3 (Mon, Wed, Fri 18:00 Madrid unless the guide says otherwise),
keep 1 in reserve. Every reel is fully rendered once; it is pushed to `reels-media` right after its build.

The master copy of the registry is the Google Sheet in Drive `01_Registro` (exported as CSV, edited here, re-uploaded).
The CSV in this branch is a structural template only.
