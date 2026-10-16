"""Self-check for registry.py: python3 engine/test_registry.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import registry as R

d = tempfile.mkdtemp(); reg, gd = os.path.join(d, "r.csv"), os.path.join(d, "g.md")
rows = []
for i in range(6):
    r = {c: "x" for c in R.COLS[:45]}
    r.update(id=f"2026-W40-R0{i}", published_at=f"2026-10-0{i + 1}", duration_s="30", wpm="180", animated_scene_pct="60",
             persona="L&D" if i % 2 else "SaaS", reach="1000", plays="1200", avg_watch_s=str(10 + i * 3),
             link_clicks=str(i), follows=str(i * 2), likes="10", comments="1", shares="1", saves="2")
    for k in ("score", "reinforcement", "interaction_rate", "retention_pct", "click_rate", "follow_rate"): r[k] = ""
    rows.append(r)
R.save(reg, rows)
for r in rows: R.outcomes(reg, r["id"], {})
R.score(reg)
out = {r["id"]: r for r in R.load(reg)}
assert out["2026-W40-R05"]["retention_pct"] == "0.8333", out["2026-W40-R05"]["retention_pct"]
assert abs(sum(R.WEIGHTS.values()) - 1) < 1e-9
assert out["2026-W40-R05"]["reinforcement"] == "+1"   # beats the median on clicks, follows and retention
open(gd, "w", encoding="utf-8").write("# Guía\n\n## Reglas del usuario\n1. regla\n\n| Atributo | Valor |\n|---|---|\n| a | b |\n\n## Notas del domingo\nnota\n")
R.guide(reg, gd); R.guide(reg, gd)          # twice: the generated block is replaced, not duplicated
g = open(gd, encoding="utf-8").read()
assert g.count(R.AUTO_A) == 1 and "## Reglas del usuario" in g and "nota" in g and "| a | b |" not in g
assert "Baremos" in g and "clics / alcance" in g
R.check(reg, "2026-W40-R01")
print("registry ok")
