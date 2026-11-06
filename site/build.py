#!/usr/bin/env python3
"""Build the astroagent site into _site/: one page per language (en at the root, fr/es/it in subfolders).

Run from the repository root: python3 site/build.py
"""
import html
import json
import re
import shutil
from pathlib import Path

from i18n import LANGS
from usage import USAGE, SESSION, resolve

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


def codify(s):
    return re.sub(r"(ASTROAGENT_[A-Z_]+|~/[\w./-]+)", r"<code>\1</code>", s)


def split_tool(call):
    """'Bash(args)' -> ('Bash', '(args)'); 'pixinsight - x (MCP)(args)' -> ('pixinsight - x (MCP)', '(args)')."""
    i = call.index("(MCP)") + 5 if "(MCP)(" in call else call.index("(")
    return call[:i], call[i:]


def render_session(u):
    out = []
    for kind, payload in SESSION:
        if kind == "user":
            out.append(f'<div class="cc-user"><span class="p">&gt;</span> {esc(resolve(payload, u))}</div>')
        elif kind == "think":
            out.append(f'<div class="cc-think"><span class="star">✻</span> Thinking…</div>'
                       f'<div class="cc-thought">{esc(resolve(payload, u))}</div>')
        elif kind == "say":
            out.append(f'<div class="cc-say"><span class="dot">⏺</span><p>{esc(resolve(payload, u))}</p></div>')
        elif kind == "note":
            out.append(f'<div class="cc-note">· · · {esc(resolve(payload, u))} · · ·</div>')
        else:
            if kind == "skill":
                name, args, lines = "Skill", f"({payload[0]})", payload[1]
            else:
                name, args = split_tool(payload[0])
                lines = payload[1]
            res = "".join(
                f'<div class="cc-out{" more" if l.startswith("…") else ""}">'
                f'<span class="el">{"⎿" if k == 0 else ""}</span><span>{esc(l)}</span></div>'
                for k, l in enumerate(lines))
            out.append(f'<div class="cc-tool"><span class="dot ok">⏺</span><span><b>{esc(name)}</b>{esc(args)}</span></div>{res}')
    return "\n".join(out)


NEBULIS_URL = "https://nebulis.app/"
SKIP = ("a", "b", "pre", "code", "script", "style", "button", "svg", "title", "textarea")


def link_nebulis(html):
    """Link every visible mention of Nebulis, except inside links, code, the terminal mock-up and the head."""
    head, sep, body = html.partition("<body")
    parts = re.split(r"(<[^>]+>)", body)
    depth, in_cc = 0, False
    for i, part in enumerate(parts):
        if part.startswith("<"):
            m = re.match(r"</?([a-zA-Z0-9]+)", part)
            tag = m.group(1).lower() if m else ""
            closing = part.startswith("</")
            if tag == "figure" and 'class="cc"' in part:
                in_cc = True
            elif tag == "figure" and closing and in_cc:
                in_cc = False
            elif tag in SKIP and not part.endswith("/>"):
                depth += -1 if closing else 1
        elif depth == 0 and not in_cc and "Nebulis" in part and i > 0:
            parts[i] = re.sub(r"\bNebulis\b(?! Connector)", f'<a class="ext" href="{NEBULIS_URL}">Nebulis</a>', part)
    return head + sep + "".join(parts)


ICONS = {  # 24 px stroke icons for the gains grid
    "g1": '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2M9 2h6"/>',
    "g2": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "g3": '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    "g4": '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    "g5": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "g6": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
}


def icon(k):
    return f'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">{ICONS[k]}</svg>'


def pi_markup(s):
    """Escape a setup step, set menu paths in bold and the repository URL as code."""
    s = esc(s)
    s = re.sub(r"(http://&lt;[^ ]+?/plugins/pixinsight/)", r"<code>\1</code>", s)
    s = re.sub(r"((?:[A-Z][\w ]*? → )+[A-Z][\w]*(?: [A-Z][\w]*)*)", r"<b>\1</b>", s)
    return s


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
INSTALL3_ENV = """export ASTROAGENT_NEBULIS_URL=http://your-server:3001
export ASTROAGENT_NEBULIS_API_KEY=neb-..."""
INSTALL3_FISH = """set -gx ASTROAGENT_NEBULIS_URL http://your-server:3001
set -gx ASTROAGENT_NEBULIS_API_KEY neb-..."""
INSTALL3 = """mkdir -p ~/.config/astroagent
printf '%s\\n' 'ASTROAGENT_NEBULIS_URL=http://your-server:3001' 'ASTROAGENT_NEBULIS_API_KEY=neb-...' > ~/.config/astroagent/env
chmod 600 ~/.config/astroagent/env"""


def page(lang):
    t = LANGS[lang]
    u = USAGE[lang]
    pre = "" if lang == "en" else "../"
    url = SITE if lang == "en" else f"{SITE}{lang}/"
    alts = "".join(
        f'<link rel="alternate" hreflang="{l}" href="{SITE if l == "en" else SITE + l + "/"}">' for l in ORDER)
    switch = "".join(
        f'<a href="{pre}{"" if l == "en" else l + "/"}" hreflang="{l}" lang="{l}"'
        f'{CURRENT if l == lang else ""}>{l.upper()}</a>' for l in ORDER)
    phases = [("ph1", [1, 2, 3, 4]), ("ph2", [5, 6]), ("ph3", [7, 8, 9, 10]), ("ph4", [11, 12])]
    stages = "".join(
        f'<li><h4>{esc(t[pk])}</h4><ol start="{steps[0]}">'
        + "".join(f'<li><span class="num">{n:02d}</span>{esc(t[f"s{n}"])}</li>' for n in steps)
        + "</ol></li>" for pk, steps in phases)
    gains = "".join(f'<article class="gain">{icon(f"g{i}")}<h3>{esc(t[f"g{i}"])}</h3><p>{esc(t[f"g{i}d"])}</p></article>'
                    for i in range(1, 7))
    know = "".join(f'<li><h4>{esc(t[f"f{i}"])}</h4><p>{esc(t[f"f{i}d"])}</p></li>' for i in range(1, 4))
    loop = "".join(f'<li><span class="step">{i}</span><h3>{esc(t[f"l{i}"])}</h3><p>{esc(t[f"l{i}d"])}</p></li>' for i in range(1, 4))
    chat = render_session(u)
    tips = "".join(f'<li><h4>{esc(h)}</h4><p>{esc(p)}</p></li>' for h, p in u["tips"])
    reqs = "".join(f"<li>{esc(r)}</li>" for r in t["rq"])
    pi_steps = "".join(f"<li>{pi_markup(s)}</li>" for s in t["in4_steps"])
    tabs = [("zsh / bash", INSTALL3_ENV), ("fish", INSTALL3_FISH), (t["tab_file"], INSTALL3)]
    tabbar = "".join(f'<button type="button" role="tab" aria-selected="{"true" if k == 0 else "false"}" data-tab="{k}">{esc(n)}</button>'
                     for k, (n, _) in enumerate(tabs))
    panes = "".join(f'<div class="pane" role="tabpanel" data-pane="{k}"{"" if k == 0 else " data-off"}>{code_block(t, c)}</div>'
                    for k, (_, c) in enumerate(tabs))
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
      <a href="#gains">{esc(t["nav_gains"])}</a>
      <a href="#how">{esc(t["nav_how"])}</a>
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
  <div class="wrap">
    <div class="hero-text">
      <p class="kicker">{esc(t["hero_kicker"])}</p>
      <h1>{esc(t["hero_h1"])}</h1>
      <p class="lead">{esc(t["hero_lead"])}</p>
      <div class="ctas">
        <a class="btn primary" href="#install">{esc(t["cta_install"])}</a>
        <a class="btn" href="{REPO}">{esc(t["cta_github"])}</a>
      </div>
    </div>
    <div class="stage">
      <figure class="cc" aria-label="{esc(u["caption"])}" data-thinking="{esc(u["thinking"])}" data-running="{esc(u["running"])}">
        <div class="cc-bar"><i></i><i></i><i></i><span>~/Astro/Processing · claude</span>
          <span class="cc-ctl"><button type="button" class="cc-replay">↻ {esc(u["replay"])}</button><button type="button" class="cc-skip">⏭ {esc(u["skip"])}</button></span></div>
        <div class="cc-body"><div class="cc-log">{chat}</div>
          <div class="cc-status" aria-hidden="true"><span class="star">✻</span> <span class="lbl"></span> <span class="sec"></span></div>
          <div class="cc-input"><span class="p">&gt;</span><span class="typed"></span><span class="cursor"></span></div>
          <div class="cc-hint"><span>? for shortcuts</span><span>astro-processing · nebulis</span></div>
        </div>
      </figure>
      <p class="caption">{esc(u["caption"])}</p>
    </div>
  </div>
</section>

<section id="gains" class="block">
  <div class="wrap">
    <p class="eyebrow">{esc(t["g_eyebrow"])}</p>
    <h2>{esc(t["g_title"])}</h2>
    <div class="gains">{gains}</div>
  </div>
</section>

<section id="how" class="block alt">
  <div class="wrap">
    <p class="eyebrow">{esc(t["how_eyebrow"])}</p>
    <h2>{esc(t["how_title"])}</h2>
    <p class="sub">{esc(t["how_lead"])}</p>
    <div class="how">
      <ol class="loop">{loop}</ol>
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
    <h3 class="minor">{esc(t["stages_title"])}</h3>
    <ol class="stages">{stages}</ol>
    <div class="duo">
      <div><h3 class="minor">{esc(t["talk_title"])}</h3><ul class="cards">{tips}</ul></div>
      <div><h3 class="minor">{esc(t["know_title"])}</h3><ul class="cards">{know}</ul></div>
    </div>
  </div>
</section>

<section id="install" class="block">
  <div class="wrap">
    <p class="eyebrow">{esc(t["in_lead"])}</p>
    <h2>{esc(t["in_title"])}</h2>
    <ol class="steps">
      <li><span class="step">1</span><div><h3>{esc(t["in1"])}</h3>{code_block(t, INSTALL1)}</div></li>
      <li><span class="step">2</span><div><h3>{esc(t["in2"])}</h3>{code_block(t, INSTALL2)}<p class="small">{esc(t["in_alt"])}</p>{code_block(t, INSTALL2B)}</div></li>
      <li><span class="step">3</span><div><h3>{esc(t["in3"])}</h3><p class="small">{codify(esc(t["in3_short"]))}</p>
        <div class="tabs"><div class="tabbar" role="tablist">{tabbar}</div>{panes}</div></div></li>
      <li class="opt"><span class="step">4</span><div><h3>{esc(t["in4"])}</h3><p class="small">{esc(t["in4_lead"])}</p>
        <ol class="sub-steps">{pi_steps}</ol></div></li>
    </ol>
    <div class="reqs">
      <h3 class="minor">{esc(t["rq_title"])} <span class="badge">{esc(t["ver"])} {esc(t["st"])}</span></h3>
      <ul>{reqs}</ul>
    </div>
  </div>
</section>
</main>

<footer class="foot">
  <div class="wrap">
    <a class="brand" href="{REPO}">{symbol_inline()}<span>astroagent</span></a>
    <p>{esc(t["ft_credits"])} {esc(t["ft_scope"])}</p>
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
        (d / "index.html").write_text(link_nebulis(page(lang)), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print("built", sorted(str(p.relative_to(OUT)) for p in OUT.rglob("index.html")))


if __name__ == "__main__":
    main()
