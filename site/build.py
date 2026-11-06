#!/usr/bin/env python3
"""Build the astroagent site into _site/: one page per language (en at the root, fr/es/it in subfolders).

Run from the repository root: python3 site/build.py
"""
import html
import json
import math
import re
import shutil
from pathlib import Path

from i18n import LANGS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
REPO = "https://github.com/jjmartres/astroagent"
SITE = "https://jjmartres.github.io/astroagent/"
ORDER = ["en", "fr", "es", "it"]
CURRENT = ' aria-current="true"'


def esc(s):
    return html.escape(s, quote=True)


def symbol_inline(cls="mark"):
    """The symbol with the frame in currentColor and the star in the OIII token."""
    svg = (ROOT / "brand" / "astroagent-symbol.svg").read_text()
    paths = re.findall(r'<path fill="([^"]+)"((?: fill-rule="evenodd")?) d="([^"]+)"/>', svg)
    out = []
    for i, (_, rule, d) in enumerate(paths):
        fill = "var(--oiii)" if i == len(paths) - 1 else "currentColor"
        out.append(f'<path fill="{fill}"{rule} d="{d}"/>')
    return f'<svg class="{cls}" viewBox="0 0 256 256" aria-hidden="true">{"".join(out)}</svg>'


def hero_art():
    """A histogram of faint linear data, the midtones transfer curve that stretches it, and the star at its end."""
    w, h, pad = 520, 360, 36
    bars = []
    n = 48
    for i in range(n):
        x = i / (n - 1)
        v = math.exp(-((x - 0.06) ** 2) / 0.0018) + 0.18 * math.exp(-((x - 0.2) ** 2) / 0.02)
        bh = (h - 2 * pad) * min(v, 1) * 0.92
        bx = pad + i * (w - 2 * pad) / n
        bars.append(f'<rect x="{bx:.1f}" y="{h - pad - bh:.1f}" width="{(w - 2 * pad) / n - 2:.1f}" height="{bh:.1f}" rx="1.5"/>')
    m = 0.08  # midtones balance: MTF(m, x) = (m-1)x / ((2m-1)x - m)
    pts = []
    for i in range(0, 101):
        x = i / 100
        y = ((m - 1) * x) / ((2 * m - 1) * x - m)
        pts.append(f"{pad + x * (w - 2 * pad):.1f},{h - pad - y * (h - 2 * pad):.1f}")
    grid = "".join(
        f'<line x1="{pad}" y1="{pad + k * (h - 2 * pad) / 4:.1f}" x2="{w - pad}" y2="{pad + k * (h - 2 * pad) / 4:.1f}"/>'
        for k in range(5)) + "".join(
        f'<line x1="{pad + k * (w - 2 * pad) / 4:.1f}" y1="{pad}" x2="{pad + k * (w - 2 * pad) / 4:.1f}" y2="{h - pad}"/>'
        for k in range(5))
    sx, sy, R, o = w - pad, pad, 22, 22 * 0.16
    star = (f"M{sx},{sy - R} Q{sx + o},{sy - o} {sx + R},{sy} Q{sx + o},{sy + o} {sx},{sy + R} "
            f"Q{sx - o},{sy + o} {sx - R},{sy} Q{sx - o},{sy - o} {sx},{sy - R}Z")
    return (f'<svg class="hero-art" viewBox="-10 -10 {w + 20} {h + 20}" role="img" aria-label="Histogram and stretch curve">'
            f'<g class="grid">{grid}</g><g class="bars">{"".join(bars)}</g>'
            f'<polyline class="curve" points="{" ".join(pts)}"/>'
            f'<path class="star" d="{star}"/></svg>')


def code_block(t, text):
    return (f'<div class="code"><pre><code>{esc(text)}</code></pre>'
            f'<button type="button" class="copy" data-copied="{esc(t["copied"])}">{esc(t["copy"])}</button></div>')


INSTALL1 = """npm install -g pixinsight-connector@2.5.2
claude mcp add -s user pixinsight -- pixinsight-connector
pixinsight-connector doctor"""
INSTALL2 = """claude plugin marketplace add jjmartres/astroagent
claude plugin install astroagent@astroagent"""
INSTALL2B = """git clone https://github.com/jjmartres/astroagent ~/Repositories/astroagent
~/Repositories/astroagent/install.sh"""
INSTALL3 = """mkdir -p ~/.config/astroagent
printf '%s\\n' 'ASTROAGENT_NEBULIS_URL=http://your-server:3001' 'ASTROAGENT_NEBULIS_API_KEY=neb-...' > ~/.config/astroagent/env
chmod 600 ~/.config/astroagent/env"""


def page(lang):
    t = LANGS[lang]
    pre = "" if lang == "en" else "../"
    url = SITE if lang == "en" else f"{SITE}{lang}/"
    alts = "".join(
        f'<link rel="alternate" hreflang="{l}" href="{SITE if l == "en" else SITE + l + "/"}">' for l in ORDER)
    switch = "".join(
        f'<a href="{pre}{"" if l == "en" else l + "/"}" hreflang="{l}" lang="{l}"'
        f'{CURRENT if l == lang else ""}>{l.upper()}</a>' for l in ORDER)
    phases = [
        ("ph1", "ph1_sub", [1, 2, 3, 4]), ("ph2", "ph2_sub", [5, 6]),
        ("ph3", "ph3_sub", [7, 8, 9, 10]), ("ph4", "ph4_sub", [11, 12]),
    ]
    flow = ""
    for pk, ps, steps in phases:
        items = "".join(
            f'<li><span class="num">{n:02d}</span><div><h4>{esc(t[f"s{n}"])}</h4><p>{esc(t[f"s{n}d"])}</p></div></li>'
            for n in steps)
        flow += f'<section class="phase"><header><h3>{esc(t[pk])}</h3><span>{esc(t[ps])}</span></header><ol>{items}</ol></section>'
    feats = "".join(f'<article class="feat"><h3>{esc(t[f"f{i}"])}</h3><p>{esc(t[f"f{i}d"])}</p></article>' for i in range(1, 7))
    reqs = "".join(f"<li>{esc(r)}</li>" for r in t["rq"])
    return f"""<!DOCTYPE html>
<html lang="{lang}" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(t["title"])}</title>
<meta name="description" content="{esc(t["meta"])}">
<link rel="canonical" href="{url}">
{alts}<link rel="alternate" hreflang="x-default" href="{SITE}">
<meta property="og:title" content="astroagent">
<meta property="og:description" content="{esc(t["meta"])}">
<meta property="og:image" content="{SITE}og.png">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{pre}favicon.ico" sizes="48x48">
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{pre}apple-touch-icon.png">
<link rel="manifest" href="{pre}site.webmanifest">
<meta name="theme-color" content="#0B1220">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Sora:wght@600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{pre}style.css">
<script>try{{var s=localStorage.getItem('aa-theme');if(s)document.documentElement.dataset.theme=s;}}catch(e){{}}</script>
</head>
<body>
<header class="top">
  <div class="wrap bar">
    <a class="brand" href="{pre}{"" if lang == "en" else lang + "/"}">{symbol_inline()}<span>astroagent</span></a>
    <nav aria-label="Main">
      <a href="#workflow">{esc(t["nav_workflow"])}</a>
      <a href="#features">{esc(t["nav_features"])}</a>
      <a href="#install">{esc(t["nav_install"])}</a>
    </nav>
    <div class="tools">
      <div class="langs" role="group" aria-label="{esc(t["lang_switch"])}">{switch}</div>
      <button type="button" class="theme" aria-label="{esc(t["theme"])}" title="{esc(t["theme"])}">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z"/></svg>
      </button>
      <a class="gh" href="{REPO}" aria-label="GitHub"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.07-2.7-1.07-.36-.92-.89-1.17-.89-1.17-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.71 1.22 1.87.87 2.33.66.07-.52.28-.87.5-1.07-1.78-.2-3.65-.89-3.65-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.66 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0z"/></svg></a>
    </div>
  </div>
</header>

<main>
<section class="hero">
  <div class="wrap hero-grid">
    <div>
      <p class="kicker">{esc(t["hero_kicker"])}</p>
      <h1>{esc(t["hero_h1"])}</h1>
      <p class="lead">{esc(t["hero_lead"])}</p>
      <div class="ctas">
        <a class="btn primary" href="{REPO}">{esc(t["cta_github"])}</a>
        <a class="btn" href="#install">{esc(t["cta_install"])}</a>
      </div>
    </div>
    <figure class="art">{hero_art()}<figcaption>{esc(t["hero_caption"])}</figcaption></figure>
  </div>
</section>

<section id="workflow" class="block">
  <div class="wrap">
    <h2>{esc(t["wf_title"])}</h2>
    <p class="sub">{esc(t["wf_lead"])}</p>
    <div class="flow">{flow}</div>
  </div>
</section>

<section class="block alt">
  <div class="wrap approval">
    <div>
      <h2>{esc(t["ap_title"])}</h2>
      <p class="sub">{esc(t["ap_lead"])}</p>
      <ul class="four">
        <li><b>{esc(t["ap_measured"])}</b></li><li><b>{esc(t["ap_proposal"])}</b></li>
        <li><b>{esc(t["ap_why"])}</b></li><li><b>{esc(t["ap_preview"])}</b></li>
      </ul>
    </div>
    <div class="term" aria-label="{esc(t["ap_example"])}">
      <div class="term-bar"><i></i><i></i><i></i><span>{esc(t["ap_example"])}</span></div>
      <div class="term-body">
        <p><span class="tag">{esc(t["ap_measured"])}</span>{esc(t["ap_ex_measured"])}</p>
        <p><span class="tag">{esc(t["ap_proposal"])}</span>{esc(t["ap_ex_proposal"])}</p>
        <p><span class="tag">{esc(t["ap_why"])}</span>{esc(t["ap_ex_why"])}</p>
        <div class="thumbs"><span class="t1">s1</span><span class="t2">s2</span><span class="t3">s3</span></div>
        <p class="gate">{esc(t["ap_ex_gate"])}</p>
        <p class="ask">&gt; {esc(t["ap_ex_ask"])}<span class="cursor"></span></p>
      </div>
      <p class="note">{esc(t["ap_note"])}</p>
    </div>
  </div>
</section>

<section id="features" class="block">
  <div class="wrap">
    <h2>{esc(t["ft_title"])}</h2>
    <div class="feats">{feats}</div>
  </div>
</section>

<section id="install" class="block alt">
  <div class="wrap">
    <h2>{esc(t["in_title"])}</h2>
    <p class="sub">{esc(t["in_lead"])}</p>
    <ol class="steps">
      <li><h3>{esc(t["in1"])}</h3>{code_block(t, INSTALL1)}</li>
      <li><h3>{esc(t["in2"])}</h3>{code_block(t, INSTALL2)}<p class="small">{esc(t["in_alt"])}</p>{code_block(t, INSTALL2B)}</li>
      <li><h3>{esc(t["in3"])}</h3>{code_block(t, INSTALL3)}</li>
    </ol>
    <div class="cols">
      <div><h3>{esc(t["rq_title"])}</h3><ul class="req">{reqs}</ul></div>
      <div><h3>{esc(t["st_title"])}</h3><p>{esc(t["st"])}</p></div>
    </div>
  </div>
</section>
</main>

<footer class="foot">
  <div class="wrap">
    <a class="brand" href="{REPO}">{symbol_inline()}<span>astroagent</span></a>
    <p>{esc(t["ft_credits"])}</p>
  </div>
</footer>
<script src="{pre}site.js"></script>
</body>
</html>
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    src = Path(__file__).resolve().parent
    for f in ("style.css", "site.js"):
        shutil.copy(src / f, OUT / f)
    for f in (ROOT / "brand" / "icons").iterdir():
        shutil.copy(f, OUT / f.name)
    shutil.copytree(ROOT / "brand", OUT / "brand", ignore=shutil.ignore_patterns("icons"))
    og = src / "og.png"
    if og.exists():
        shutil.copy(og, OUT / "og.png")
    (OUT / "site.webmanifest").write_text(json.dumps({
        "name": "astroagent", "short_name": "astroagent", "start_url": "./", "display": "standalone",
        "theme_color": "#0B1220", "background_color": "#0B1220",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ]}, indent=2))
    for lang in ORDER:
        d = OUT if lang == "en" else OUT / lang
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(page(lang), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print("built", sorted(str(p.relative_to(OUT)) for p in OUT.rglob("index.html")))


if __name__ == "__main__":
    main()
