# Changelog

## 0.5.2 (2026-11-21)

Shorter, more educational replies during processing, each with its options and a reasoned recommendation.

- `astro-processing`: every decision message has the same frame: *Measured*, *Options* (each with its pros and cons), *Recommendation* (the choice and why, tied to a number, a gate or the user's aim), *Preview*, then one question. The tone teaches briefly (one sentence the first time a process or a measure appears) and messages stay short (about 15 lines outside tables, no recap, full parameters in the session file and `PROCESSING.md`).
- Site: the stage 9 example shows the new frame (Options with pros and cons, Recommendation with its reason), in four languages; the label column is wider so the longer labels fit.

## 0.5.1 (2026-11-20)

Every image the agent puts before the user is shown twice, as in the M20 run (SHO, Telescope.live CHI-1), where it made each choice easy.

- `astro-processing`: under ground rule 1, each candidate, before/after, 1:1 crop and the final image stays open as a PixInsight view (with an STF while linear), and its `save_preview` JPEG is opened on screen at once (`open` on macOS, `xdg-open` on Linux, `start ""` on Windows; several at once to compare). `save_preview` and `save_and_show_preview` only write the file. The message names each JPEG and its view; a candidate's view is closed once the user has chosen.

## 0.5.0 (2026-11-18)

Pre-calibrated lights are now handled by the Nebulis server as well as by the client: the M16 run (Telescope.live CHI-1, calibrated by the provider) showed that the export could carry calibration frames of another camera.

- `nebulis`: `plan` and `fetch --precalibrated` send `"precalibrated": true` in the request body, so the server attaches no calibration frame and raises no calibration issue (nebulis-app/nebulis#46). Lights whose header says they are calibrated (`PROC = 'True'`) are detected by the server without the flag. The plan shows the plan-level `precalibrated` flag, each group's camera and telescope, and an `already calibrated` line for a calibrated group, when the server returns them. Older servers ignore the field, and the client still sets their calibration issues aside.

## 0.4.0 (2026-11-16)

One name per processing run, and one layout for every project archive pushed to Nebulis. The first two archives (NGC891, SH2-112) differed: a PixInsight project in one only, named `ngc891.pxiproject`; session records in `processing/` or `work/`; the JPEG for Nebulis named `_final.jpg` or `_q95.jpg`.

- `astro-project`:
  - A run is named `<OBJECT>_<PALETTE>_<YYYY-MM-DD>` (Nebulis object id, palette, processing day). New `names` command: prints it and every name derived from it (PixInsight project, final files, icons, archive); the date comes from `output/final/` when the files exist.
  - New `bundle` command: rebuilds `output/push/` with a fixed layout (`PROCESSING.md`, the JSON files, `<NAME>.xpsm`, `doc/`, `final/`, `pixinsight/<NAME>.pxiproject/`, `session/`), notes files that do not follow the name, exits 2 on what is missing, and prints the `nebulis.py push` command with the archive name, title and software.
  - `xpsm` writes `output/<NAME>.xpsm` instead of `Process Icons - <name> - <palette> workflow.xpsm`; it needs the palette from `report.json`.
- `astro-processing`: Stage 11 exports `final/<NAME>.xisf`, `.tif`, `_web.jpg`, and `<NAME>.jpg` is the quality-95 JPEG for Nebulis and AstroBin (no more PixInsight JPEG beside it). Stage 12 asks the user to save the PixInsight project as `output/pixinsight/<NAME>.pxiproject`, then builds the archive with `bundle`.
- `nebulis`: the skill names the archive `<NAME>_processing.zip`, built by `bundle`.
- README: the dual-band path has now run end to end (SH2-112, HOO, 11.8 h).
- The archives of the first two runs (NGC891, SH2-112) were rebuilt with `bundle` and pushed again under the new names.

## 0.3.1 (2026-11-15)

From importing a Telescope.live library (calibrated lights from CHI-1, SPA-1, SPA-2 and AUS-2) into Nebulis.

- `nebulis`:
  - `objects --search` uses the server's search, which knows designations and aliases. The client matched the raw text, so `--search "NGC 2264"` found nothing for `NGC2264`.
  - Every command takes the object as an id, a designation in any spacing or case, or an alias (`sessions "M 83"`, `object "Crescent Nebula"`), and calls the API with the object's id.
  - `plan` and `fetch --precalibrated`, for lights that are already calibrated: `no_dark`, `no_flat` and the other calibration issues are shown as ignored and do not block the export. Without the flag, a plan whose only errors are calibration issues suggests it.
- `astro-processing`: Stage 3 and `reference/calibration-rules.md` describe pre-calibrated lights. Confirm them with the user, then fetch lights only and run WBPP without calibration frames.

## 0.3.0 (2026-11-15)

Fixes from the first end-to-end run on real data (NGC 891, broadband OSC, 276 × 150 s).

- `nebulis`:
  - New `image` command: adds a finished image (JPG, PNG, TIFF, XISF, FITS) to the object through `POST /library/objects/:id/processed-images`, so it shows in the object's Processed images and in the gallery. `images` lists them. `push` is for the one project archive of a run; a zipped JPEG pushed there showed as a second project.
  - `fetch`: fetch one night per call for large exports (a 7 GB multi-night export stopped the server mid-build); dedupe the calibration frames each night repeats.
  - `api.md` documents the processed-image endpoints.
- `astro-processing`:
  - New Stage 4b, subframe selection (`reference/subframe-selection.md`): SubframeSelector measurements, robust outlier flags crossed with the Nebulis `clouds` flags, and a WBPP input of symbolic links so the raw data is never touched.
  - Stage 5: `run_wbpp` with `extra_params {autoIntegrationMode: false, rejection_4: 8}`. WBPP switched a 303-frame group to FastIntegration (no local normalization, weights or rejection), and the connector's `rejection: "Auto"` is read by WBPP 3.2 as Averaged Sigma Clipping. Read the WBPP log to confirm; clean intermediates between runs.
  - Gate G4 no longer relies on a four-corner comparison, which missed a centre-bright, blue-edged flat residual: new PJSR helpers `radialProfile`, `bgBlocks`, `colProfile` and `correctBands` in `astro-helpers.js`; MGC scale and MARS files; background clean-up on the linear starless (GradientCorrection + ABE, column bands from the flats).
  - Stretch: MultiscaleAdaptiveStretch candidates for a bright compact subject; Gate G7 also checks the subject's high percentiles.
  - Finishing: background-only noise and colour-mottle treatment under an inverted mask; stars stretched with `mtf` and screen-blended (`star_protected_blend` gave hollow cores, `stretch_stars` 0.2 × 2 was too faint).
  - Export: sRGB with the right intent; a quality-95 JPEG with an EXIF date for Nebulis and AstroBin.
  - Ground rules: one PixInsight call at a time; numeric enumerations in PJSR; a modal PixInsight dialog blocks the connector.
- `astro-project`:
  - `icons` reads pixinsight-connector 2.5.2 calls, which wrap their code in a function: BXT, NXT, SXT, MGC, ABE, Curves, LHE and Crop were missed before. `--from-seq` and `--exclude-view` leave out an abandoned attempt and rejected candidates. `icons.js` writes its result file itself (run it with `run_pjsr_file`); `xpsm` reads it by default.
  - How to `scan` merged or filtered exports; session-report previews kept inside `doc/`.

## 0.2.0 (2026-11-06)

- New `astro-project` skill and `scripts/astro_project.py` (standard library only):
  - `scan` builds `output/rig.json` from the Nebulis export's `manifest.json`, the FITS headers of the lights (read without the pixels) and the Nebulis object, telescope profile and observing site; records where each value came from; asks only for what is missing; validated against `reference/rig.schema.json`.
  - `project` writes the PixInsight project description (`project.json`), `doc` a documentation page, `report` a session report of every stage (measured, proposed, decided, parameters, gates), `astrobin` the AstroBin form fields (optional).
  - `icons` and `xpsm` turn the processes the session actually ran, read from the pixinsight-connector call log, into a process icon set serialized by PixInsight.
  - Pages in the astroagent colours (Night, OIII, H-alpha) with a light/dark switch, self-contained.
- `nebulis.py`: `object`, `telescopes` (connection details stripped) and `site` commands.
- `astro-processing`: bootstraps the project after Fetch, researches the object while WBPP runs, writes the documentation at Stage 12; rig facts come from `rig.json` when present.
- Releases: a version bump in `plugin.json` on `main` creates the `vX.Y.Z` tag and the GitHub release from this file, and moves the `latest` tag; the install commands follow `latest`.
- Site redesigned: the example session replayed like a terminal recording at the top, gains, the approval loop, install with shell tabs; optional Nebulis Connector setup in PixInsight.

## 0.1.0 (2026-11-06)

First version, not yet run end to end on real data.

- `astro-processing` skill: 12-stage workflow with an approval at every stage; rig, calibration rules, quality gates, dual-band D1/D2 extraction and palettes, broadband path, stretch and finishing references; PJSR border helper.
- `nebulis` skill: `nebulis.py` client for objects, sessions, Frame Analysis and review, stacking plan, WBPP export download, project archive upload; tests against a mock API.
- Claude Code plugin manifest, `install.sh` for Claude Code and OpenCode, CI.
- Workflow skill renamed `astro-processing`; the setup is described generically.
- Usage section on the site and in the README: an example Claude Code session and tips.
- Nebulis settings read from `ASTROAGENT_NEBULIS_URL` and `ASTROAGENT_NEBULIS_API_KEY`, or from `~/.config/astroagent/env`.
- Logo (“Stretch to light”), brand kit in `brand/`, website in English, French, Spanish and Italian on GitHub Pages.
