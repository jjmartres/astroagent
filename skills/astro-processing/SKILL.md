---
name: astro-processing
description: >-
  Process an astrophotography campaign shot with the reference setup end to end, from the Nebulis library to a finished
  image in PixInsight, through the `pixinsight` MCP server (pixinsight-connector): sub review,
  calibration plan, WBPP stacking, dual-band (D1/D2) channel extraction with HOO/SHO palettes or the
  broadband path, starless stretch, finishing, export, processing log, and push back to Nebulis.
  Every stage measures, proposes, shows a preview and waits for approval. Use for "process
  Sh2-105", "stack and process my last campaign", "HOO from my D1 data", "post-process this
  Nebulis object", or any request to process my astro data in PixInsight.
license: MIT
metadata:
  author: jjmartres
  version: "0.5.1"
---

# Astro processing

You drive PixInsight through the `pixinsight` MCP server for one setup, the reference scope (Askar 91F, ZWO ASI585MC Air, D1/D2 dual-band filters). The data comes from **Nebulis** through the `nebulis` skill. Your job is to propose each processing stage with numbers and a preview, apply it only after the user approves, and log everything.

Before the first stage, read these files next to this one, once per session:

| File | What it holds |
|---|---|
| `reference/rig.md` | Optics, camera, filters, gains, image scale, standard capture settings |
| `reference/calibration-rules.md` | Calibration rules of the setup and how to read the Nebulis plan against them |
| `reference/quality-gates.md` | Every gate, its measurement and its threshold |
| `reference/narrowband-dualband.md` | D1/D2 channel extraction, OIII combination, palette expressions |
| `reference/subframe-selection.md` | Stage 4b: SubframeSelector measurements, robust outlier flags, WBPP input without touching the data |
| `reference/broadband.md` | Path for unfiltered data (galaxies, reflection nebulae) |
| `reference/stretch-and-finish.md` | Star separation, stretch bracketing, finishing, star recombination |
| `reference/processing-log.md` | `PROCESSING.md` template and the call log |

## Ground rules

1. **Approval at every stage.** Every message that asks for a decision has the same frame, in this order, then one closing question; stop and wait. Run a stage without waiting only if the user said so for that stage in this session; record it in the session file.
   - *Measured*: the numbers that decide, in one small table when channels or candidates are compared.
   - *Options*: usually two or three (include "leave it as is" when that is a real choice), each with its **pros** and **cons**, one short line each. When only one sensible option exists, say so and give its cons anyway.
   - *Recommendation*: the option you pick and **why**, tied to a measured number, a gate or what the user said they want. Give the tool and the parameters of that option in one line.
   - *Preview*: `save_preview`, 1:1 crops for detail.

   **Teach, briefly.** The user may be learning PixInsight. The first time a process or a measure appears in the session, say in one sentence what it does or what its number means ("MAD: background noise, lower is smoother"; "SCNR removes the green cast that SHO puts in the background"). Do not repeat an explanation already given.
   **Keep it short**: about 15 lines outside the tables. No recap of earlier stages, no number repeated between a table and the text, no log notes unless they need a decision. Full parameters go in the session file and `PROCESSING.md`; the message names only the ones the user may want to change.
   **Show every image twice: in PixInsight and as a JPEG.** Each image you put before the user (a candidate, a before/after, a 1:1 crop, the final image) stays open as a view in PixInsight, with an STF when it is still linear, so the user can zoom on it there. And its JPEG from `save_preview` is opened on the user's screen right away: `open <path>` on macOS (it opens in Preview), `xdg-open` on Linux, `start ""` on Windows; several JPEGs to compare go in one `open` call. `save_preview` (and its alias `save_and_show_preview`) only writes the file: it opens nothing. In the message, name each JPEG and the PixInsight view it shows, and say they are open. Close a candidate's view only once the user has chosen.
2. **One PixInsight call at a time**, never several in parallel: the connector runs one script at a time and parallel calls can all fail together. Read every result. `FAILED`, `REFUSED`, `BLOCKED`, `View not found` or `STOPPED BY USER` needs a decision, not a blind retry. After `STOPPED BY USER`, stop; call `resume_bridge` only when the user says so. If every call fails with "Watcher did not start", PixInsight is usually blocked by a modal dialog (for example "Unable to read the directory …"): ask the user to close it, then make one test call. In PJSR, process constants such as `SubframeSelector.prototype.MeasureSubframes` or `Convolution.prototype.Parametric` can be undefined: use the numeric value (`describe_process` lists them), and check a numeric enum against its static name (`ICCProfileTransformation.RelativeColorimetric` is 2, not 1). If the `pixinsight-connector-troubleshooting` skill is installed, use it for tool pitfalls.
3. **Raw data is read-only.** Never write, move or delete anything under `<workspace>/data/` or a Nebulis library path. Working files go to `<workspace>/agentic/work/`, deliverables to `<workspace>/output/`. The connector already refuses other paths for its own writes; keep shell writes to the same two folders.
4. **Checkpoint before every destructive step**: `clone_image` to `<view>_cp<stage>`; reject = `restore_from_clone`. Keep at most the last two checkpoints per view, close older ones.
5. **Never invent a value.** Rig facts come from `<workspace>/output/rig.json` once the `astro-project` skill has built it (it is read from this data's FITS headers and wins), otherwise from `reference/rig.md`; data facts from FITS headers, `scan_workspace` or the Nebulis manifest; everything else from the user. Ask once, in one message, for what is missing.
6. **Do not retype measured numbers by hand when a tool can carry them**; when you must (OIII weights, crop amounts), write the arithmetic in the log.
7. **Log as you go**: append one row per PixInsight call to the call log (see `reference/processing-log.md`).
8. Tool names are bare here; the host may prefix them (`mcp__pixinsight__run_bxt`).

## Session file

Keep `<workspace>/agentic/work/astro-session.md` up to date: object, nights, filter sets, path (narrowband or broadband), stage status (`todo` / `done` / `skipped`), for each stage what was measured, what you proposed, the user's decision, the parameters applied and the gate values (the `astro-project` session report is built from them), stages allowed to run without waiting, open views and their roles. On resume, read it first and continue from the first stage not `done`.

## Stage 0 — Setup

1. Workspace: `$ASTROAGENT_ROOT/<OBJECT>` (default `ASTROAGENT_ROOT=~/Astro/Processing`). Create it if needed, then `set_workspace` to it. Raw data will live in `<workspace>/data/`.
2. `list_open_images`: record ids already open; never touch them.
3. Preflight: if the `pixinsight-preflight` skill is installed, run it (it writes `agentic/preflight.json`); otherwise `pixinsight_info` and `inspect_environment`. Note the PixInsight build, BXT/NXT/SXT versions, Gaia DR3/SP, MARS. `list_processes` and check for `GeneralizedHyperbolicStretch`.
4. `nebulis.py status` (from the `nebulis` skill). A failure here stops the session with the script's message.

## Stage 1 — Target and nights

`nebulis.py objects --search <name>`, then `nebulis.py sessions <OBJECT>`. Propose the nights to process and the path: **narrowband** when the filters are D1/D2, **broadband** when unfiltered (gain 100). Mixed object: ask which. Approval.

## Stage 2 — Sub review (Nebulis Frame Analysis)

Per night: `nebulis.py analysis <OBJECT> <DATE> --bad-only`. Report per night: measured/total, kept, grade counts, flags (clouds, trails, soft, streak…), the typical FWHM, and kept integration time per filter (kept × exposure). Unmeasured frames count as kept: say so, and suggest measuring them in Nebulis first if there are many. Propose changes to the verdicts (keep a `fair` frame, reject a `good` one with a visible problem). Apply only approved changes with `nebulis.py review --keep|--reject <path>...` (admin key). Nothing is deleted: a reject only leaves the frame out of the export.

## Stage 3 — Calibration plan

`nebulis.py plan <OBJECT> --dates <...>`. Read it against `reference/calibration-rules.md`: every group has a dark (same gain, exposure, binning; |ΔT| ≤ 2 °C), a flat **of the same filter** (D1 never with D2), and a flat-dark or bias; list every issue. Errors block: explain what to fix in Nebulis (usually: attach the flat set to the object, or shoot/import the missing dark). Warnings need an explicit acknowledgement each. Approval.

Lights that are already calibrated (Telescope.live and other remote observatories deliver `*_cal.fits`) raise `no_dark` and `no_flat` on every group: confirm with the user that they are calibrated, then run `plan` and `fetch` with `--precalibrated` and follow "Pre-calibrated lights" in `reference/calibration-rules.md`.

## Stage 4 — Fetch

`nebulis.py fetch <OBJECT> --dates <...> --dest <workspace>/data [--allow-warnings]` (only with the warnings acknowledged in Stage 3). Above a few GB, fetch one night per call (see the `nebulis` skill). Check the reported light count equals the plan, and the free disk space: WBPP needs about 4 × the size of the lights for its intermediate files. Read `<export>/manifest.json` and `README.txt`; record nights, groups and integration per filter in the session file.

Then bootstrap the project with the `astro-project` skill: § 1 builds and validates `output/rig.json` from the manifest, the FITS headers and Nebulis (ask the user, once, only for what it reports missing), § 3 writes `output/project.json`. Do § 2 (object research, `output/research.json`) while WBPP runs in Stage 5.

## Stage 4b — Subframe selection

Follow `reference/subframe-selection.md`: measure every light with SubframeSelector, flag outliers per metric (robust z > 3 in the bad direction), cross them with the Nebulis `clouds` flags, and propose the exclusion list. After approval, build `agentic/work/wbpp_input/` (symbolic links to the kept lights and the calibration frames) and stack from there. The raw data stays untouched.

## Stage 5 — Stack (WBPP)

`run_wbpp` with `input_dirs: ["<workspace>/agentic/work/wbpp_input"]` (Stage 4b; the export folder when no frame was excluded), `output_dir: "wbpp"`, `keywords: [{name: "NIGHT", mode: "pre"}]` when there are several nights **and** several flat sets (one flat set for the whole campaign needs no keyword), `weights: "PSFSignal"`, `local_normalization: true`, `autocrop: false` (the crop is done once, identically, in Stage 6), and `extra_params: {autoIntegrationMode: false, rejection_4: 8}`:
- `autoIntegrationMode: false`: WBPP 3.x switches a light group of more than 200 frames to **FastIntegration** on its own (no local normalization, no weights, no rejection); the master is then named `…_fastIntegration.xisf`.
- `rejection_4: 8` is ESD (Generalized Extreme Studentized Deviate), right for large groups. Do **not** pass `rejection: "Auto"`: the connector sends `rejection_4=5`, which WBPP 3.2 reads as the ImageIntegration enumeration, Averaged Sigma Clipping. Other values: 4 Winsorized Sigma, 6 Linear Fit, 9 RCR.

After the run, read the WBPP log (`output/wbpp/logs/*.log`): the light integration must say `Pixel rejection ... Generalized extreme Studentized deviate`, `Weighting mode ... PSF Signal Weight` and `Output normalization ... Local`; record the total rejection percentage. A second run writes `_c_1`, `master…_(1)` copies next to the first one's files: delete the previous run's `calibrated/`, `debayered/` and masters first (they are regenerated), and once the master is accepted delete `calibrated/` and `debayered/`; keep `registered/` until the end (a re-integration needs it). Drizzle only if the user asks (`drizzle_scale`). Poll `wbpp_status` every few minutes; report progress, never start a second run. **Gate G2** (`reference/quality-gates.md`). If a master is mono (one channel), WBPP did not debayer: stop, ask the user to enable CFA/debayer in the WBPP dialog once (saved settings apply to automation), then re-run.

## Stage 6 — Masters: open, crop, correct, solve

1. `open_image` each master from `<workspace>/output/wbpp/master/` (it opens with its rejection maps: close them, or use the low-rejection map first, see step 2); `rename_view` to `D1`, `D2` or `RGB` (broadband). `get_image_dimensions`: all masters of one target must match; if not, `align_to_reference` onto `D1` (or the deepest master).
2. Common crop: `run_pjsr` with `include: ["<this skill's folder>/scripts/pjsr/astro-helpers.js"]` and code `JSON.stringify(commonBorders(["D1","D2"]))`. With local normalization the borders are not black, so `commonBorders` can return 0: then read the edge depth from the master's low-rejection map (`rejection_low`, the fraction of frames missing there) and crop where it falls under 2 %. `crop_image` every master with the same amounts.
3. `run_bxt` with `correct_only: true` on each master.
4. `run_plate_solve` each master with the focal length and pixel size from `output/rig.json` (or `reference/rig.md`, profile from `FOCALLEN`) and the target's catalogue position (state it, the user confirms). `verify_astrometry`. **Gate G3**.
5. `export_image` each master to `agentic/work/<Target>_s06_<view>.xisf`.

## Stage 7 — Gradient

Narrowband: `run_gradient_correction` on each master. Broadband: follow `reference/broadband.md` (SPFC + MGC when MARS covers the field, otherwise GradientCorrection). ABE (`run_abe`) only as a fallback the user accepts. Measure before and after with the helpers in `astro-helpers.js`: `radialProfile` (a centre-bright or blue-edged pattern from flats or vignetting), `bgBlocks` (uniformity over the whole field, 64 and 256 px) and `colProfile` (vertical and horizontal bands), with the subject excluded by an ellipse; plus `get_image_stats`. `measure_uniformity` compares four corners only and is blind to a radial pattern: report it, never decide on it alone. **Gate G4**. Approval.

## Stage 8 — Linear processing

- **Narrowband**: follow `reference/narrowband-dualband.md`: extract Ha, OIII (and SII from D2), combine the two OIII, then per channel BXT sharpening and NXT. **Gates G5, G6**.
- **Broadband**: follow `reference/broadband.md`: SPCC, BXT sharpening, NXT. **Gates G5, G6**.

Show 1:1 before/after crops for deconvolution and for noise reduction. Approval after each of the two.

## Stage 9 — Stars out, stretch

Follow `reference/stretch-and-finish.md`: StarXTerminator on linear data, stars kept as a separate view; then check the **starless** background again (`bgBlocks`, `colProfile`): without stars, residual gradients and flat bands are easy to model and to see, and every one of them grows with the stretch. Fix them on the linear starless (`reference/broadband.md` § 3) before stretching. Then three stretch candidates side by side with their numbers; **Gate G7** rejects a candidate that clips or flattens the subject. The user picks one; discard the other two.

## Stage 10 — Composition and finishing

Narrowband: build the palettes the user wants (HOO, SHO, Foraxx-style) from `reference/narrowband-dualband.md`, show them side by side, keep one. Then finishing and star recombination from `reference/stretch-and-finish.md`: each change under a mask, with a before/after preview and a checkpoint. **Gate G8**.

## Stage 11 — Export

**Gate G9** first: pixel medians from `get_image_stats` must show a stretched image (a still-linear image exports black). Convert to sRGB (`ICCProfileTransformation`, `targetProfile "sRGB IEC61966-2.1"`, `renderingIntent` 2 = relative colorimetric). File names come from `astro_project.py names <workspace>` (`<NAME>` = `<OBJECT>_<PALETTE>_<YYYY-MM-DD>`, Nebulis object id, palette, processing day; write the palette into the session file first, and pass `--palette` until report.json exists). `export_image` to `final/<NAME>` as `.xisf` (32-bit) and `.tif` (16-bit); for the web JPEG, `resample_image` with `mode: "scale"`, `factor` = 2048 / long side and `output_id: "web"`, export that copy as `final/<NAME>_web.jpg`, close it. PixInsight's JPEG is strongly compressed and carries no date: make `final/<NAME>.jpg`, the image that goes to Nebulis or AstroBin, as a quality-95 JPEG from the 16-bit TIFF (`sips -s format jpeg -s formatOptions 95` on macOS) and write its EXIF date with `exiftool -DateTimeOriginal=… -CreateDate=… -ImageDescription=…` (the date the user wants: processing day by default; the description holds the acquisition nights and the integration), or Nebulis shows it with no date.

## Stage 12 — Log and push

Write `<workspace>/output/PROCESSING.md` from `reference/processing-log.md`, including the call log. Then follow `astro-project` § 4: `report.json` and the session report, the documentation page, the process icons (`.xpsm`), `project.json` again, and `astrobin.json` only if the user wants it. Ask the user to save the PixInsight project as `output/pixinsight/<NAME>.pxiproject`. Then `astro_project.py bundle <workspace>` builds **one** project archive in `<workspace>/output/push/`, always with the same layout (`astro-project` § 4): no raw data, no WBPP intermediates, no scratch. After approval, run the push command it prints: `nebulis.py push <OBJECT> --bundle <workspace>/output/push --name <NAME>_processing.zip --title "<palette> final" --software "…"` (admin key), then add the final JPEG as the object's image with `nebulis.py image <OBJECT> --file output/final/<NAME>.jpg --title "<palette> final"`. A JPEG never goes through `push`: it would show as a second project. Close every view this session created (never save views opened from files), leave only the final image open.
