---
name: astro-project
description: >-
  Describe and document one astrophotography campaign processed with astroagent: build a schema-validated
  rig.json (target, site, optics, camera, filters, per-night sequences) from the Nebulis export's manifest,
  the FITS headers and Nebulis profiles; write the PixInsight project description (project.json), a
  documentation page (doc/index.html), a session report of what was measured, proposed and decided
  (doc/session-report.html), process icons with the parameters actually applied (.xpsm) and, on request,
  AstroBin form fields (astrobin.json). Called by astro-processing after Fetch and at the end; also on its own
  for "document Sh2-105", "bootstrap the project", "make the project description", "process icons",
  "xpsm", "astrobin post", "session report".
license: MIT
metadata:
  author: jjmartres
  version: "0.5.2"
---

# Astro project

Everything here is about one processing workspace, `$ASTROAGENT_ROOT/<OBJECT>` (default `~/Astro/Processing/<OBJECT>`), laid out by the `astro-processing` skill:

| Path | What |
|---|---|
| `data/<export>/` | The Nebulis WBPP export: `manifest.json`, `Lights/NIGHT_*/FILTER_*`, `Darks/`, `Flats/`, `Bias/`, `FlatDarks/`. **Read-only.** |
| `agentic/work/` | Scratch: Nebulis JSON, `icons.json`, `icons.js` |
| `output/rig.json` | The campaign description, validated against `reference/rig.schema.json` |
| `output/research.json` | Object research you write (`reference/research.md`) |
| `output/report.json` | Session report you write at the end (`reference/report.md`) |
| `output/project.json` | PixInsight project description, one line |
| `output/doc/index.html`, `output/doc/session-report.html` | The two pages |
| `output/<NAME>.xpsm` | Process icons |
| `output/pixinsight/<NAME>.pxiproject` | The PixInsight project, saved by the user |
| `output/push/` | The project archive's content, built by `bundle` |
| `output/astrobin.json` | Only when the user wants it |

The pixinsight-connector writes only under `agentic/` and `output/`; keep every file of this skill there too. Never write under `data/`.

**Names.** One run has one name, `<NAME>` = `<OBJECT>_<PALETTE>_<YYYY-MM-DD>`: the Nebulis object id (`rig.json` `target.name`, e.g. `SH2-112`, `NGC891`), the palette (`report.json`, e.g. `HOO`, `RGB`) and the processing day. `astro_project.py names <WS>` prints it with every name derived from it; use those names, never your own: the PixInsight project, the final files, the icons and the Nebulis archive all follow it.

When the data is not laid out as one export under `data/` (several per-night exports merged, frames excluded at Stage 4b), give `scan` an export that matches what was stacked: a folder in `agentic/work/` with a `manifest.json` (the per-night groups, `kept` set to the frames actually stacked, nights with nothing kept left out) and `Lights/NIGHT_<date>/FILTER_<filter>/` holding symbolic links to those lights; then `scan <WS> --export <that folder>`. Correct the telescope model and site name with `--set` when Nebulis gives a profile name (`ASIAIR`, `Backyard`).

The script is `scripts/astro_project.py` next to this file (standard library only). Run it with `python3`; every command prints what it did and what is missing. `NB` below is `python3 <skills>/nebulis/scripts/nebulis.py`.

## 1. Bootstrap: rig.json

Run once the export is in `data/` (Stage 4 of astro-processing, or on its own on an existing workspace).

1. Collect what Nebulis knows, into scratch files:
   ```
   NB --json object <OBJECT>  > agentic/work/object.json
   NB --json telescopes       > agentic/work/telescopes.json
   NB --json site             > agentic/work/site.json
   ```
   A failure here is not fatal: continue without that file.
2. `astro_project.py scan <WS> --object agentic/work/object.json --telescope agentic/work/telescopes.json --site agentic/work/site.json`.
   It reads `manifest.json` (nights, filters, exposures, gains, kept subs, the calibration sets Nebulis matched) and the FITS headers of every light (`TELESCOP`, `INSTRUME`, `FOCALLEN`, `XPIXSZ`, `NAXIS1/2`, `BAYERPAT`, `RA/DEC` or `OBJCTRA/OBJCTDEC`, `SITELAT/SITELONG/SITEELEV`, `SET-TEMP`, `XBINNING`), never the pixels. Headers win for optics and where the data was shot; Nebulis gives the telescope model, the site name and its Bortle class, the object's catalogue position and names. `provenance` in rig.json says where each value came from.
3. Show the user the summary it prints (one line per filter: subs, exposure, gain, nights, hours) and, **in one message**, ask only for what it lists as missing: required fields first, then the recommended ones (aperture, sensor name, elevation, a description per filter: vendor, model, passbands, bandwidth). Do not ask for anything already filled.
4. Write the answers with `scan <WS> --set KEY=VALUE ...` (dotted paths: `telescope.aperture_mm=91`, `camera.sensor="Sony IMX585"`, `filters.D1="Askar Colour Magic D1, Ha + OIII, 6 nm"`, `mount="ZWO AM3N"`). A value set this way is never overwritten by a later scan. Exit 0 means rig.json is valid; exit 2 lists what is still missing.

From now on rig.json is the source for rig facts in this workspace: image scale for plate solving, sensor type, filters. If it disagrees with the astro-processing `reference/rig.md`, rig.json wins (it comes from this data).

## 2. Research: research.json

Start from `agentic/work/object.json` (Nebulis already has type, constellation, magnitude, distance, size, description), then search the web: at least three searches (physical data and distance; nature and structure; discovery and notable observations; imaging advice for the filters in rig.json). Prefer SIMBAD, NASA/ESA, peer-reviewed papers and catalogues; note conflicting values rather than picking silently. Write `output/research.json` following `reference/research.md`, in your own words (no copied paragraphs), each claim traceable to a reference in the file. Show the user the summary line and the key facts before going on.

## 3. Project description: project.json

`astro_project.py project <WS>`. It needs a valid rig.json and uses research.json and report.json when present (run it again at the end so the palette and notes are in). Tell the user:

- **Description** field of the PixInsight project: the `description` value. On macOS, offer to copy it: `python3 -c "import json;print(json.load(open('<WS>/output/project.json'))['description'])" | pbcopy`.
- **Documentation** field: the path to `output/doc/index.html`.

## 4. At the end of processing

Called from Stage 12 of astro-processing, after `PROCESSING.md` is written.

1. **report.json.** Write `output/report.json` from the session file and the call log, following `reference/report.md`: one entry per stage with its status, what was measured, the proposal, the reason, the user's decision, the parameters applied and the gates with their values. Facts only, from the session: no stage or value that did not happen.
2. **Pages.** `astro_project.py report <WS>`, then `astro_project.py doc <WS>` (the doc page links to the session report and shows `output/final/*_web.jpg` when present). Open each in a browser or describe them; check that numbers match PROCESSING.md.
3. **Process icons.** `astro_project.py icons <WS> [--from-seq N] [--exclude-view REGEX]` reads the pixinsight-connector call logs (`agentic/**/*.jsonl`), keeps the processing calls that succeeded and the process instances they ran, and writes `agentic/work/icons.js`. Leave out an abandoned attempt (`--from-seq`) and rejected candidates or diagnostic views (`--exclude-view`), and check the printed list against PROCESSING.md. Run `agentic/work/icons.js` with `run_pjsr_file` (it writes `agentic/work/icons-result.json` itself and returns a summary); then `astro_project.py xpsm <WS>`. PixInsight itself serializes each instance (`toSource("XPSM 1.0")`), so parameter names and values are exactly what ran. Report the icons that could not be converted. Details and limits: `reference/process-icons.md`.
4. **project.json** again (step 3), so it carries the palette.
5. **astrobin.json**, only if the user asked for it or says they post on AstroBin: `astro_project.py astrobin <WS>`. One acquisition row per night and filter, with the calibration frame counts; `image_file` stays empty (the user uploads). Fields: `reference/outputs.md`.
6. **PixInsight project.** Ask the user to fill the project's Description (step 3) and Documentation fields, then save it with *File → Save Project As* as `output/pixinsight/<NAME>.pxiproject` (the path `names` prints). Optional: without it the archive has no `pixinsight/` folder.
7. **Archive.** `astro_project.py bundle <WS>` rebuilds `output/push/` in the standard layout below, lists what it placed, notes files that do not follow `<NAME>`, and prints the `nebulis.py push` command. Exit 2 lists what is missing (PROCESSING.md, rig.json, report.json, project.json, `doc/`, `final/<NAME>.xisf`). `--add FILE` puts another session record in `session/`. The session report's previews must be inside `output/doc/` (copy them to `output/doc/previews/` and use `previews/<file>` in report.json), or the links break in the archive.

```text
<NAME>_processing.zip
├── PROCESSING.md
├── rig.json  research.json  report.json  project.json  [astrobin.json]
├── <NAME>.xpsm
├── doc/            index.html, session-report.html, previews/
├── final/          <NAME>.xisf, <NAME>.tif, <NAME>.jpg, <NAME>_web.jpg
├── pixinsight/     <NAME>.pxiproject/   (when saved)
└── session/        astro-session.md, call-log.md, ss_flagged.txt, subframeselector*.csv
```

## Rules

- **Never invent** a fact about the object, the equipment or the session. Unknown stays empty and is listed as missing.
- **Ask once**, grouped, and only for what the script reports missing.
- The pages are generated: change the JSON and re-run the command rather than editing the HTML.
- Keep the Nebulis key out of every file: the JSON files hold no credentials (`nebulis.py telescopes` already strips connection details).
