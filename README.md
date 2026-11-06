<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="brand/astroagent-horizontal-reversed.svg">
    <img src="brand/astroagent-horizontal.svg" alt="astroagent" width="420">
  </picture>
</p>

<p align="center"><a href="https://jjmartres.github.io/astroagent/">Website</a> · <a href="https://jjmartres.github.io/astroagent/fr/">Français</a> · <a href="https://jjmartres.github.io/astroagent/es/">Español</a> · <a href="https://jjmartres.github.io/astroagent/it/">Italiano</a></p>

# astroagent

Agent skills to process astrophotography campaigns shot with my setup (Askar 91F, ZWO ASI585MC Air, Askar D1/D2 dual-band filters) from the **Nebulis** library to a finished image in **PixInsight**, with an AI agent (Claude Code or OpenCode) that proposes every stage and waits for your approval.

Nothing here modifies PixInsight or the connector: PixInsight is operated through [pixinsight-connector](https://github.com/mxcoppell/pixinsight-connector), used as published on npm. This repository holds only knowledge (skills), a Nebulis client script and a PJSR helper.

| Skill | What it does |
|---|---|
| `skills/astro-processing` | The workflow: sub review, calibration plan, WBPP stacking, D1/D2 channel extraction and HOO/SHO palettes (or the broadband path), starless stretch with three candidates, finishing, export, `PROCESSING.md`, push back to Nebulis. Rig facts, calibration rules and quality gates are in its `reference/` folder. |
| `skills/nebulis` | A command-line client (`scripts/nebulis.py`) for the Nebulis API: objects, nights, Frame Analysis and keep/reject review, stacking plan, WBPP-ready export download, upload of results. Usable on its own. |

## How a session runs

```mermaid
flowchart TD
    start(["You: process Sh2-105"]) --> s1
    subgraph neb["Nebulis (nebulis.py)"]
        s1["1 · Object and nights"] --> s2["2 · Sub review<br/>Frame Analysis grades"] --> s3["3 · Calibration plan<br/>attached flats, matched darks/bias"] --> s4["4 · Fetch WBPP export"]
    end
    subgraph pi["PixInsight (pixinsight-connector)"]
        s5["5 · WBPP stacking"] --> s6["6 · Crop, BXT correct, plate solve"] --> s7["7 · Gradient"] --> s8["8 · Linear: channels, BXT, NXT"] --> s9["9 · Stars out, 3 stretch candidates"] --> s10["10 · Palette, finishing, stars back"] --> s11["11 · Export"]
    end
    s4 --> s5
    s11 --> s12["12 · PROCESSING.md, push to Nebulis"]
    gate{{"Every stage: numbers, proposal, preview → your approval"}}
```

## Requirements

- macOS (tested target), PixInsight 1.9.5 or later, with BlurXTerminator, NoiseXTerminator and StarXTerminator; GHS optional.
- Node.js 22 or later (for the connector), Python 3.9 or later (for `nebulis.py`, standard library only).
- A Nebulis server and an API key (Settings → API keys). An **admin** key is needed to record keep/reject decisions and to upload results.
- Claude Code or OpenCode.

## Install

### 1. The PixInsight connector

```sh
npm install -g pixinsight-connector@2.5.2
pixinsight-connector doctor
```

Register it as the MCP server `pixinsight`:

- Claude Code: `claude mcp add -s user pixinsight -- pixinsight-connector`
- OpenCode (`~/.config/opencode/opencode.json`):

  ```json
  { "mcp": { "pixinsight": { "type": "local", "command": ["pixinsight-connector"] } } }
  ```

Recommended: the connector's companion skills (`pixinsight-preflight`, `pixinsight-target-intake`, `pixinsight-connector-troubleshooting`), which these skills call when they are present:

```sh
npx skills add mxcoppell/pixinsight-connector-skills
```

### 2. These skills

Claude Code, as a plugin:

```sh
claude plugin marketplace add jjmartres/astroagent
claude plugin install astroagent@astroagent
```

The plugin does not register the `pixinsight` MCP server: use the one from step 1 (or from the
pixinsight-connector-skills plugin), never two, since two connectors compete for PixInsight's script slot.

OpenCode, or Claude Code without the plugin system:

```sh
git clone https://github.com/jjmartres/astroagent ~/Repositories/astroagent
~/Repositories/astroagent/install.sh
```

`install.sh` links both skills into `~/.claude/skills/`, which Claude Code and OpenCode both read. `git pull` updates them.

Any Agent Skills harness: `npx skills add jjmartres/astroagent`.

### 3. Nebulis credentials

```sh
mkdir -p ~/.config/nebulis
cp ~/Repositories/astroagent/config/nebulis.env.example ~/.config/nebulis/env
chmod 600 ~/.config/nebulis/env
$EDITOR ~/.config/nebulis/env        # NEBULIS_URL and NEBULIS_API_KEY
python3 ~/.claude/skills/nebulis/scripts/nebulis.py status   # with the plugin: the skill's folder under ~/.claude/plugins
```

### 4. WBPP, once

Open WeightedBatchPreprocessing in PixInsight and check that colour (CFA) images are debayered for your ASI585MC data; save. The connector runs WBPP headless with the parameters the skill passes, and WBPP's saved settings for the rest.

### 5. Where files go

Each object is processed in `$ASTROAGENT_ROOT/<OBJECT>/` (default `~/Astro/Processing/<OBJECT>/`):

```
data/<OBJECT>_<nights>_wbpp/   the Nebulis export (read-only for the agent)
agentic/                       connector scratch, previews, session file, call log
output/wbpp/                   WBPP output and masters
output/final/                  XISF, TIFF, JPEG
output/PROCESSING.md           the processing log
```

## Use

In Claude Code or OpenCode: *"Process Sh2-105 with the astro-processing workflow"*, *"Review last night's subs of NGC 6888 in Nebulis"*, *"Fetch Sh2-112 for stacking"*. The agent stops at every stage with numbers and a preview. To let a stage run without stopping, say so (for example *"run stacking without asking"*); it is recorded in the session file.

## Brand and website

The logo, its variants and icons are in `brand/` (usage in `brand/BRAND.md`). The website is generated from `site/` by `python3 site/build.py` into `_site/` and published to GitHub Pages by `.github/workflows/pages.yml`.

## Tests

```sh
python3 -m unittest discover -s tests
```

The tests run `nebulis.py` against a local mock of the Nebulis API. The PixInsight side cannot run in CI; `skills/astro-processing/scripts/pjsr/astro-helpers.js` is checked by hand on real data.

## Status

Version 0.1.0, not yet run end to end on real data. See `CHANGELOG.md`. Every processing value in the skills is a starting point; tune it on your data and commit the values that work.

## Credits

- [pixinsight-connector](https://github.com/mxcoppell/pixinsight-connector) and [pixinsight-connector-skills](https://github.com/mxcoppell/pixinsight-connector-skills) by Min Xie (MIT): the PixInsight tools; `scanBorders` and the astrometry gate thresholds are adapted from the companion skills.
- [Nebulis](https://github.com/nebulis-app/nebulis): the library, Frame Analysis and stacking export the workflow relies on.
- Foraxx palette idea by Paulo Tavares.

MIT License, see `LICENSE`.
