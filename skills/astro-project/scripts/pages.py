"""HTML pages of astro_project.py: the documentation page and the session report.

Self-contained (no external font, script or image besides the final JPEG next to them), so they open offline in a
browser or in PixInsight's documentation viewer. Colours follow the astroagent brand: Night, OIII, H-alpha.
"""
from __future__ import annotations

import html
import json
import re

E = lambda s: html.escape("" if s is None else str(s), quote=True)  # noqa: E731

MARK = ('<svg class="mark" viewBox="0 0 256 256" aria-hidden="true">'
        '<path fill="currentColor" fill-rule="evenodd" d="M72,20H184A52,52 0 0 1 236,72V184A52,52 0 0 1 184,236H72A52,52 0 0 1 20,184V72A52,52 0 0 1 72,20ZM72,40H184A32,32 0 0 1 216,72V184A32,32 0 0 1 184,216H72A32,32 0 0 1 40,184V72A32,32 0 0 1 72,40Z"/>'
        '<path fill="currentColor" d="M80.96,190.83C85.79,138.64 98.05,115.76 126.18,108.73A9.0,9.0 0 0 0 121.82,91.27C85.95,100.24 68.21,133.36 63.04,189.17A9.0,9.0 0 0 0 80.96,190.83Z"/>'
        '<path fill="var(--oiii)" d="M170.00,58.00 Q175.12,84.88 202.00,90.00 Q175.12,95.12 170.00,122.00 Q164.88,95.12 138.00,90.00 Q164.88,84.88 170.00,58.00Z"/></svg>')

CSS = """
:root { --sky:#0B1220; --night:#0E1A2B; --surface:#111B2C; --surface2:#16233A; --line:#24344D; --text:#E9EEF4; --muted:#93A3B6;
  --oiii:#14A3A0; --oiii-text:#3CC6C2; --ha:#E5484D; --ha-text:#F08A8D; --ok:#3FB950; --warn:#D9A441;
  --sans: "IBM Plex Sans", "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --display: "Sora", "Avenir Next", "IBM Plex Sans", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; color-scheme: dark; }
:root[data-theme="light"] { --sky:#F4F6F9; --night:#0E1A2B; --surface:#FFFFFF; --surface2:#EEF2F6; --line:#D8E0EA; --text:#0E1A2B;
  --muted:#536173; --oiii-text:#0B7C79; --ha:#C9363B; --ha-text:#B42B30; --ok:#1F883D; --warn:#9A6700; color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--sky); color: var(--text); font: 400 16px/1.6 var(--sans); }
a { color: var(--oiii-text); }
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 24px; }
header.top { position: sticky; top: 0; z-index: 5; background: color-mix(in srgb, var(--sky) 90%, transparent); backdrop-filter: blur(8px); border-bottom: 1px solid var(--line); }
.bar { display: flex; align-items: center; gap: 14px; height: 56px; }
.brand { display: inline-flex; align-items: center; gap: 8px; font: 600 15px var(--display); color: var(--text); text-decoration: none; }
.mark { width: 22px; height: 22px; }
.bar nav { display: flex; gap: 18px; margin-left: 10px; }
.bar nav a { color: var(--muted); text-decoration: none; font-size: 14px; }
.bar nav a:hover { color: var(--text); }
.tools { margin-left: auto; display: flex; gap: 8px; }
.btn { font: 500 12.5px var(--mono); color: var(--muted); background: transparent; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; cursor: pointer; text-decoration: none; }
.btn:hover { color: var(--text); border-color: var(--oiii); }
h1, h2, h3 { font-family: var(--display); font-weight: 600; letter-spacing: -0.01em; margin: 0; text-wrap: balance; }
h1 { font-size: clamp(34px, 5vw, 54px); line-height: 1.05; }
h2 { font-size: 26px; margin-bottom: 18px; }
h3 { font-size: 17px; }
.eyebrow { font: 500 12.5px var(--mono); color: var(--oiii-text); text-transform: uppercase; letter-spacing: .08em; margin: 0 0 10px; }
.hero { padding: 56px 0 40px; position: relative; overflow: hidden; }
.hero::before { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .6;
  background: radial-gradient(1px 1px at 14% 22%, var(--muted) 50%, transparent 51%), radial-gradient(1px 1px at 80% 14%, var(--muted) 50%, transparent 51%),
  radial-gradient(1.5px 1.5px at 90% 52%, var(--oiii-text) 50%, transparent 51%), radial-gradient(1.5px 1.5px at 6% 66%, var(--ha) 50%, transparent 51%),
  radial-gradient(60% 60% at 70% 20%, color-mix(in srgb, var(--oiii) 14%, transparent), transparent 70%); }
.hero .wrap { position: relative; }
.sub { color: var(--muted); font-size: 19px; margin: 12px 0 0; max-width: 62ch; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 22px; }
.chip { font: 500 13px var(--mono); padding: 5px 11px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: var(--muted); }
.chip b { color: var(--text); font-weight: 500; }
.chip.oiii { border-color: color-mix(in srgb, var(--oiii) 50%, transparent); color: var(--oiii-text); }
.chip.ha { border-color: color-mix(in srgb, var(--ha) 50%, transparent); color: var(--ha-text); }
figure.final { margin: 34px 0 0; border: 1px solid var(--line); border-radius: 16px; overflow: hidden; background: #000; }
figure.final img { display: block; width: 100%; height: auto; }
figure.final figcaption { font-size: 13px; color: var(--muted); padding: 10px 14px; background: var(--surface); border-top: 1px solid var(--line); }
section.block { padding: 40px 0; border-top: 1px solid var(--line); }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.fact { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.fact span { display: block; font: 500 12px var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.fact b { display: block; margin-top: 4px; font: 600 18px var(--display); }
.prose p { margin: 0 0 14px; max-width: 72ch; }
.prose h3 { margin: 24px 0 8px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
table { width: 100%; border-collapse: collapse; font-size: 14.5px; }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font: 500 12px var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 4px 6px; overflow-x: auto; }
.kv { display: grid; grid-template-columns: 150px 1fr; gap: 6px 16px; margin: 0; }
.kv dt { color: var(--muted); font-size: 14px; } .kv dd { margin: 0; }
ul.plain { margin: 0; padding-left: 18px; } ul.plain li { margin: 4px 0; }
.bar-int { height: 8px; border-radius: 4px; background: var(--surface2); overflow: hidden; min-width: 80px; }
.bar-int i { display: block; height: 100%; background: var(--oiii); }
.bar-int.ha i { background: var(--ha); }
.bar-int.dual i { background: linear-gradient(90deg, var(--ha), var(--oiii)); }
footer { padding: 28px 0 44px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13.5px; }
/* session report */
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 26px; }
.stat { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.stat b { display: block; font: 600 26px var(--display); } .stat span { color: var(--muted); font-size: 13.5px; }
.timeline { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.stage { border: 1px solid var(--line); border-radius: 14px; background: var(--surface); }
.stage summary { list-style: none; cursor: pointer; display: grid; grid-template-columns: 44px 1fr auto; align-items: center; gap: 12px; padding: 14px 16px; }
.stage summary::-webkit-details-marker { display: none; }
.stage .n { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; font: 600 13px var(--mono); background: var(--oiii); color: #06201F; }
.stage.skipped .n, .stage.todo .n { background: var(--surface2); color: var(--muted); }
.stage .t { font: 600 16px var(--display); } .stage .t small { display: block; font: 400 13.5px var(--sans); color: var(--muted); margin-top: 2px; }
.pill { font: 500 12px var(--mono); padding: 3px 9px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); white-space: nowrap; }
.pill.done { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 45%, transparent); }
.pill.auto { color: var(--oiii-text); border-color: color-mix(in srgb, var(--oiii) 45%, transparent); }
.pill.fail { color: var(--ha-text); border-color: color-mix(in srgb, var(--ha) 45%, transparent); }
.stage .body { padding: 0 16px 16px 72px; display: grid; gap: 12px; }
.stage .body h4 { margin: 0 0 4px; font: 500 12px var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.stage .body p { margin: 0; }
.stage .body code, td code { font: 13px var(--mono); background: var(--surface2); border-radius: 6px; padding: 1px 6px; }
.gates td:first-child { font-family: var(--mono); }
.ok { color: var(--ok); } .bad { color: var(--ha-text); }
.toolbar { display: flex; gap: 8px; margin: 0 0 14px; }
@media (max-width: 760px) { .grid2 { grid-template-columns: 1fr; } .bar nav { display: none; } .stage .body { padding-left: 16px; } .kv { grid-template-columns: 1fr; } }
@media print { header.top, .toolbar, .tools { display: none; } body { background: #fff; color: #000; } .stage { break-inside: avoid; } details { display: block; } }
"""

THEME_JS = """<script>
(function(){var r=document.documentElement;try{var s=localStorage.getItem('aa-doc-theme');if(s)r.dataset.theme=s;}catch(e){}
document.addEventListener('click',function(ev){var b=ev.target.closest('[data-action]');if(!b)return;var a=b.dataset.action;
if(a==='theme'){var n=r.dataset.theme==='light'?'dark':'light';r.dataset.theme=n;try{localStorage.setItem('aa-doc-theme',n);}catch(e){}}
if(a==='expand'||a==='collapse'){document.querySelectorAll('details.stage').forEach(function(d){d.open=a==='expand';});}
if(a==='print'){window.print();}});})();
</script>"""


def page(title: str, nav: list[tuple[str, str]], body: str, extra_tools: str = "") -> str:
    links = "".join(f'<a href="{E(h)}">{E(t)}</a>' for t, h in nav)
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="astroagent">
<title>{E(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap bar">
  <span class="brand">{MARK}<span>astroagent</span></span>
  <nav>{links}</nav>
  <div class="tools">{extra_tools}<button class="btn" type="button" data-action="theme" title="Light or dark">◐ Theme</button></div>
</div></header>
{body}
{THEME_JS}
</body>
</html>
"""


def band_class(name: str, desc: str = "") -> str:
    """Bar colour: dual-band H-alpha + OIII gradient, H-alpha/SII red, OIII and broadband teal."""
    t = f"{name} {desc}".lower()
    red = re.search(r"\bh\s*-?\s*(?:a|alpha|α)\b|hα|\bs\s*-?\s*ii\b|\bsii\b|\bred\b", t)
    oiii = re.search(r"o\s*-?\s*iii|\bo3\b", t)
    return "dual" if red and oiii else ("ha" if red else "")


def render_doc(rig: dict, research: dict, report: dict, c: dict, image: str | None, has_report: bool, version: str) -> str:
    t = rig["target"]
    title = f"{c['id']}" + (f" · {c['common_name']}" if c["common_name"] else "")
    kicker = " · ".join(x for x in (c["object_type"], c["constellation"]) if x)
    aliases = research.get("catalog_ids") or t.get("aliases") or []
    chips = [f'<span class="chip oiii"><b>{E(c["total"])}</b> integration</span>',
             f'<span class="chip"><b>{c["subs_kept"]}</b> subs · {c["nights"]} night{"s" if c["nights"] != 1 else ""}</span>']
    if c["palette"]:
        chips.append(f'<span class="chip ha">{E(c["palette"])} palette</span>')
    chips += [f'<span class="chip">{E(a)}</span>' for a in aliases if a != c["id"]][:6]
    hero_img = (f'<figure class="final"><img src="{E(image)}" alt="{E(title)}, final image">'
                f'<figcaption>{E(title)} · {E(c["palette"] or "final")} · {E(c["date"])}</figcaption></figure>') if image else ""
    hero = f"""<section class="hero"><div class="wrap">
  <p class="eyebrow">{E(kicker or "Deep-sky object")}</p>
  <h1>{E(title)}</h1>
  {f'<p class="sub">{E(research["summary"])}</p>' if research.get("summary") else ""}
  <div class="chips">{"".join(chips)}</div>
  {hero_img}
</div></section>"""

    facts = [("RA (J2000)", c["ra"]), ("Dec (J2000)", c["dec"])]
    for key, label, fmt in (("distance_ly", "Distance", lambda v: f"{v:,.0f} ly" if isinstance(v, (int, float)) else v),
                            ("size_arcmin", "Apparent size", lambda v: f"{v}′" if isinstance(v, (int, float)) else v),
                            ("magnitude", "Magnitude", lambda v: v), ("constellation", "Constellation", lambda v: v)):
        if research.get(key) not in (None, ""):
            facts.append((label, fmt(research[key])))
    facts += [(f["label"], f["value"]) for f in research.get("facts") or []]
    facts_html = "".join(f'<div class="fact"><span>{E(k)}</span><b>{E(v)}</b></div>' for k, v in facts)

    about = ""
    if research.get("sections"):
        parts = []
        for s in research["sections"]:
            parts.append(f"<h3>{E(s.get('title'))}</h3>" + "".join(f"<p>{E(p)}</p>" for p in s.get("paragraphs") or []))
        about = f'<section class="block" id="about"><div class="wrap"><p class="eyebrow">The object</p><h2>About {E(c["common_name"] or c["id"])}</h2><div class="prose">{"".join(parts)}</div></div></section>'

    lights = rig["sequences"]["lights"]
    max_s = max((s["subs"] * s["exposure_s"] for s in lights), default=1) or 1
    rows = ""
    for s in lights:
        kept = f'{s["subs"]}' + (f' / {s["subs_total"]}' if s.get("subs_total") not in (None, s["subs"]) else "")
        width = 100 * s["subs"] * s["exposure_s"] / max_s
        rows += (f'<tr><td>{E(s["filter"])}</td><td class="num">{kept}</td><td class="num">{s["exposure_s"]:g} s</td>'
                 f'<td class="num">{E(s.get("gain"))}</td><td class="num">{len(s.get("dates", []))}</td>'
                 f'<td class="num">{s["subs"] * s["exposure_s"] / 3600:.1f} h</td>'
                 f'<td><div class="bar-int {band_class(s["filter"], rig["filters"].get(s["filter"], ""))}"><i style="width:{width:.0f}%"></i></div></td></tr>')
    loc = rig["capture_location"]
    scope, cam = rig["telescope"], rig["camera"]
    kv = [("Telescope", c["telescope"]), ("Image scale", f'{scope["image_scale_arcsec_px"]:g}″/px' if scope.get("image_scale_arcsec_px") else None),
          ("Camera", c["camera"] + (f' · {cam["resolution_px"].replace("x", " × ")} px' if cam.get("resolution_px") else "")
           + (f' · {cam["pixel_size_um"]:g} µm' if cam.get("pixel_size_um") else "")),
          ("Cooling", f'{rig["tec_setpoint_c"]:g} °C' if rig.get("tec_setpoint_c") is not None else None),
          ("Mount", rig.get("mount")), ("Site", f'{loc["site"]} · {c["site_coords"]}')]
    kv_html = "".join(f"<dt>{E(k)}</dt><dd>{E(v)}</dd>" for k, v in kv if v)
    filt_html = "".join(f"<li><b>{E(k)}</b>{(' · ' + E(v)) if v else ''}</li>" for k, v in rig["filters"].items())
    cal = rig["sequences"]
    cal_rows = "".join(f'<tr><td>{label}</td><td>{E(x["name"])}</td><td class="num">{x["subs"]}</td>'
                       f'<td>{E(x.get("filter") or "")}</td><td>{E(", ".join(x.get("dates") or []))}</td></tr>'
                       for key, label in (("darks", "Dark"), ("flats", "Flat"), ("flat_darks", "Flat-dark"), ("biases", "Bias"))
                       for x in cal.get(key) or [])
    nights = "".join(f'<tr><td>{E(n["date"])}</td><td>{E(n["filter"])}</td><td class="num">{n["subs"]} / {n.get("subs_total", n["subs"])}</td>'
                     f'<td class="num">{n["exposure_s"]:g} s</td><td class="num">{E(n.get("temp_c"))}</td></tr>' for n in rig.get("nights") or [])
    acquisition = f"""<section class="block" id="acquisition"><div class="wrap">
  <p class="eyebrow">Acquisition</p><h2>{E(c["total"])} over {c["nights"]} night{"s" if c["nights"] != 1 else ""}</h2>
  <div class="card"><table><thead><tr><th>Filter</th><th class="num">Subs kept</th><th class="num">Exposure</th><th class="num">Gain</th><th class="num">Nights</th><th class="num">Time</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>
  <div class="grid2" style="margin-top:24px">
    <div><h3 style="margin-bottom:10px">Equipment and site</h3><dl class="kv">{kv_html}</dl></div>
    <div><h3 style="margin-bottom:10px">Filters</h3><ul class="plain">{filt_html}</ul></div>
  </div>
  <details style="margin-top:24px"><summary class="btn" style="display:inline-block">Nights and calibration frames</summary>
    <div class="grid2" style="margin-top:14px">
      <div class="card"><table><thead><tr><th>Night</th><th>Filter</th><th class="num">Kept</th><th class="num">Exp.</th><th class="num">°C</th></tr></thead><tbody>{nights}</tbody></table></div>
      <div class="card"><table><thead><tr><th>Type</th><th>Set</th><th class="num">Frames</th><th>Filter</th><th>Dates</th></tr></thead><tbody>{cal_rows}</tbody></table></div>
    </div>
  </details>
</div></section>"""

    processing = ""
    if report:
        st = report.get("stages") or []
        done = sum(1 for s in st if s.get("status") == "done")
        gates = [g for s in st for g in s.get("gates") or []]
        steps = "".join(f'<li><b>{E(s.get("name"))}</b>{(" · " + E(s.get("decision"))) if s.get("decision") else ""}</li>'
                        for s in st if s.get("status") == "done")
        processing = f"""<section class="block" id="processing"><div class="wrap">
  <p class="eyebrow">Processing</p><h2>{E(report.get("palette") or "Processing")} · {done} stages, {sum(1 for g in gates if g.get("pass"))} of {len(gates)} gates passed</h2>
  <ul class="plain">{steps}</ul>
  {'<p style="margin-top:18px"><a class="btn" href="session-report.html">Open the session report →</a></p>' if has_report else ""}
</div></section>"""

    notes = ""
    if research.get("imaging_notes"):
        notes = (f'<section class="block"><div class="wrap"><p class="eyebrow">Imaging notes</p><h2>What to know for next time</h2>'
                 f'<ul class="plain">{"".join(f"<li>{E(n)}</li>" for n in research["imaging_notes"])}</ul></div></section>')
    refs = ""
    if research.get("references"):
        refs = (f'<section class="block" id="references"><div class="wrap"><p class="eyebrow">Sources</p><h2>References</h2><ul class="plain">'
                + "".join(f'<li><a href="{E(r.get("url"))}">{E(r.get("title") or r.get("url"))}</a></li>' for r in research["references"])
                + "</ul></div></section>")
    body = (hero + f'<section class="block" id="facts"><div class="wrap"><p class="eyebrow">At a glance</p><div class="facts">{facts_html}</div></div></section>'
            + about + acquisition + processing + notes + refs
            + f'<footer><div class="wrap">Generated by astroagent {E(version)} on {E(c["date"])} from rig.json'
            + (", research.json" if research else "") + (" and report.json" if report else "") + ".</div></footer>")
    nav = [("Object", "#about" if about else "#facts"), ("Acquisition", "#acquisition")]
    if processing:
        nav.append(("Processing", "#processing"))
    if refs:
        nav.append(("References", "#references"))
    tools = '<a class="btn" href="session-report.html">Session report</a>' if has_report else ""
    return page(f"{title} · astroagent", nav, body, tools)


def fmt_params(p) -> str:
    if not p:
        return ""
    if isinstance(p, str):
        return f"<p><code>{E(p)}</code></p>"
    if isinstance(p, dict):
        return "<table><tbody>" + "".join(f"<tr><td><code>{E(k)}</code></td><td>{E(json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)}</td></tr>"
                                         for k, v in p.items()) + "</tbody></table>"
    if isinstance(p, list):
        return "".join(fmt_params(x) for x in p)
    return f"<p>{E(p)}</p>"


def render_report(report: dict, rig: dict, version: str) -> str:
    target = report.get("target") or (rig.get("target") or {}).get("name", "")
    name = (rig.get("target") or {}).get("common_name") or ""
    st = report.get("stages") or []
    gates = [g for s in st for g in s.get("gates") or []]
    passed = sum(1 for g in gates if g.get("pass"))
    done = sum(1 for s in st if s.get("status") == "done")
    integ = report.get("integration") or []
    total_s = sum((i.get("subs_kept") or 0) * (i.get("exposure_s") or 0) for i in integ)
    hours_txt = f"{total_s / 3600:.1f} h" if total_s else "—"
    items = []
    for s in st:
        status = s.get("status") or "todo"
        pills = [f'<span class="pill {"done" if status == "done" else ""}">{E(status)}</span>']
        if s.get("auto"):
            pills.append('<span class="pill auto">ran without waiting</span>')
        failed = [g for g in s.get("gates") or [] if g.get("pass") is False]
        if failed:
            pills.append(f'<span class="pill fail">{len(failed)} gate{"s" if len(failed) > 1 else ""} failed</span>')
        body = []
        for key, label in (("measured", "Measured"), ("proposal", "Proposal"), ("why", "Why"), ("decision", "Your decision")):
            if s.get(key):
                body.append(f"<div><h4>{label}</h4><p>{E(s[key])}</p></div>")
        if s.get("params"):
            body.append(f"<div><h4>Parameters applied</h4>{fmt_params(s['params'])}</div>")
        if s.get("gates"):
            rows = "".join(f'<tr><td>{E(g.get("id"))}</td><td>{E(g.get("measure"))}</td><td class="num">{E(g.get("value"))}</td>'
                           f'<td class="num">{E(g.get("threshold"))}</td><td class="{"ok" if g.get("pass") else "bad"}">{"pass" if g.get("pass") else "fail"}'
                           f'{("<br><small>" + E(g["note"]) + "</small>") if g.get("note") else ""}</td></tr>'
                           for g in s["gates"])
            body.append(f'<div><h4>Quality gates</h4><div class="card gates"><table><thead><tr><th>Gate</th><th>Measure</th>'
                        f'<th class="num">Value</th><th class="num">Threshold</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table></div></div>')
        if s.get("preview"):
            body.append(f'<div><h4>Preview</h4><img src="{E(s["preview"])}" alt="" style="max-width:100%;border-radius:10px;border:1px solid var(--line)"></div>')
        items.append(f"""<li><details class="stage {E(status)}"{" open" if failed else ""}>
  <summary><span class="n">{E(s.get("n", ""))}</span><span class="t">{E(s.get("name"))}<small>{E(s.get("summary") or s.get("decision") or "")}</small></span><span>{" ".join(pills)}</span></summary>
  <div class="body">{"".join(body) or "<p>No details recorded.</p>"}</div>
</details></li>""")
    integ_rows = "".join(f'<tr><td>{E(i.get("filter"))}</td><td class="num">{E(i.get("subs_kept"))} / {E(i.get("subs_total"))}</td>'
                         f'<td class="num">{E(i.get("exposure_s"))} s</td><td class="num">{(i.get("subs_kept") or 0) * (i.get("exposure_s") or 0) / 3600:.1f} h</td></tr>'
                         for i in integ)
    outputs = "".join(f"<li><code>{E(o)}</code></li>" for o in report.get("outputs") or [])
    env = "".join(f"<dt>{E(k)}</dt><dd>{E(v)}</dd>" for k, v in (report.get("environment") or {}).items())
    title = f"{target}{' · ' + name if name else ''}"
    body = f"""<section class="hero"><div class="wrap">
  <p class="eyebrow">Session report · {E(report.get("date"))}</p>
  <h1>{E(title)}</h1>
  <p class="sub">{E(report.get("summary") or "")}</p>
  <div class="stats">
    <div class="stat"><b>{done}/{len(st)}</b><span>stages done</span></div>
    <div class="stat"><b>{passed}/{len(gates)}</b><span>quality gates passed</span></div>
    <div class="stat"><b>{E(hours_txt)}</b><span>integration kept</span></div>
    <div class="stat"><b>{E(report.get("palette") or "—")}</b><span>{E(report.get("path") or "")} palette</span></div>
  </div>
</div></section>
<section class="block" id="stages"><div class="wrap">
  <p class="eyebrow">Stage by stage</p><h2>What was measured, proposed and decided</h2>
  <div class="toolbar"><button class="btn" type="button" data-action="expand">Expand all</button><button class="btn" type="button" data-action="collapse">Collapse all</button><button class="btn" type="button" data-action="print">Print</button></div>
  <ol class="timeline">{"".join(items)}</ol>
</div></section>
<section class="block" id="data"><div class="wrap"><div class="grid2">
  <div><p class="eyebrow">Integration</p><div class="card"><table><thead><tr><th>Filter</th><th class="num">Kept / total</th><th class="num">Exposure</th><th class="num">Time</th></tr></thead><tbody>{integ_rows}</tbody></table></div></div>
  <div><p class="eyebrow">Outputs</p><ul class="plain">{outputs}</ul><p class="eyebrow" style="margin-top:22px">Environment</p><dl class="kv">{env}</dl></div>
</div></div></section>
<footer><div class="wrap">Generated by astroagent {E(version)} from report.json. The full call log is in PROCESSING.md.</div></footer>"""
    return page(f"{title} · session report · astroagent", [("Stages", "#stages"), ("Data", "#data")], body,
                '<a class="btn" href="index.html">Documentation</a>')
