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
  version: "0.1.0"
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
| `reference/broadband.md` | Path for unfiltered data (galaxies, reflection nebulae) |
| `reference/stretch-and-finish.md` | Star separation, stretch bracketing, finishing, star recombination |
| `reference/processing-log.md` | `PROCESSING.md` template and the call log |

## Ground rules

1. **Approval at every stage.** Present: *Measured* (numbers), *Proposal* (tools and exact parameters), *Why* (one line), *Preview* (`save_preview`, 1:1 crops for detail). Then stop and wait. Run a stage without waiting only if the user said so for that stage in this session; record it in the session file.
2. **One PixInsight call at a time.** Read every result. `FAILED`, `REFUSED`, `BLOCKED`, `View not found` or `STOPPED BY USER` needs a decision, not a blind retry. After `STOPPED BY USER`, stop; call `resume_bridge` only when the user says so. If the `pixinsight-connector-troubleshooting` skill is installed, use it for tool pitfalls.
3. **Raw data is read-only.** Never write, move or delete anything under `<workspace>/data/` or a Nebulis library path. Working files go to `<workspace>/agentic/work/`, deliverables to `<workspace>/output/`. The connector already refuses other paths for its own writes; keep shell writes to the same two folders.
4. **Checkpoint before every destructive step**: `clone_image` to `<view>_cp<stage>`; reject = `restore_from_clone`. Keep at most the last two checkpoints per view, close older ones.
5. **Never invent a value.** Rig facts come from `reference/rig.md`, data facts from FITS headers, `scan_workspace` or the Nebulis manifest, everything else from the user. Ask once, in one message, for what is missing.
6. **Do not retype measured numbers by hand when a tool can carry them**; when you must (OIII weights, crop amounts), write the arithmetic in the log.
7. **Log as you go**: append one row per PixInsight call to the call log (see `reference/processing-log.md`).
8. Tool names are bare here; the host may prefix them (`mcp__pixinsight__run_bxt`).

## Session file

Keep `<workspace>/agentic/work/astro-session.md` up to date: object, nights, filter sets, path (narrowband or broadband), stage status (`todo` / `done` / `skipped`), approved parameters, stages allowed to run without waiting, open views and their roles. On resume, read it first and continue from the first stage not `done`.

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

## Stage 4 — Fetch

`nebulis.py fetch <OBJECT> --dates <...> --dest <workspace>/data [--allow-warnings]` (only with the warnings acknowledged in Stage 3). Check the reported light count equals the plan. Read `<export>/manifest.json` and `README.txt`; record nights, groups and integration per filter in the session file.

## Stage 5 — Stack (WBPP)

`run_wbpp` with `input_dirs: ["<workspace>/data/<export folder>"]`, `output_dir: "wbpp"`, `keywords: [{name: "NIGHT", mode: "pre"}]` when there are several nights (each night calibrated with its own flats, as Nebulis laid them out), `rejection: "Auto"`, `weights: "PSFSignal"`, `local_normalization: true`, `autocrop: false` (the crop is done once, identically, in Stage 6). Drizzle only if the user asks (`drizzle_scale`). Poll `wbpp_status` every few minutes; report progress, never start a second run. **Gate G2** (`reference/quality-gates.md`). If a master is mono (one channel), WBPP did not debayer: stop, ask the user to enable CFA/debayer in the WBPP dialog once (saved settings apply to automation), then re-run.

## Stage 6 — Masters: open, crop, correct, solve

1. `open_image` each master from `<workspace>/output/wbpp/master/`; `rename_view` to `D1`, `D2` or `RGB` (broadband). `get_image_dimensions`: all masters of one target must match; if not, `align_to_reference` onto `D1` (or the deepest master).
2. Common crop: `run_pjsr` with `include: ["<this skill's folder>/scripts/pjsr/astro-helpers.js"]` and code `JSON.stringify(commonBorders(["D1","D2"]))`. `crop_image` every master with the returned `crop` amounts.
3. `run_bxt` with `correct_only: true` on each master.
4. `run_plate_solve` each master with the scale from `reference/rig.md` (pick the profile from `FOCALLEN`) and the target's catalogue position (state it, the user confirms). `verify_astrometry`. **Gate G3**.
5. `export_image` each master to `agentic/work/<Target>_s06_<view>.xisf`.

## Stage 7 — Gradient

Narrowband: `run_gradient_correction` on each master. Broadband: follow `reference/broadband.md` (SPFC + MGC when MARS covers the field, otherwise GradientCorrection). ABE (`run_abe`) only as a fallback the user accepts. Measure before/after with `measure_uniformity` and `get_image_stats`; preview both with the same STF. **Gate G4**. Approval.

## Stage 8 — Linear processing

- **Narrowband**: follow `reference/narrowband-dualband.md`: extract Ha, OIII (and SII from D2), combine the two OIII, then per channel BXT sharpening and NXT. **Gates G5, G6**.
- **Broadband**: follow `reference/broadband.md`: SPCC, BXT sharpening, NXT. **Gates G5, G6**.

Show 1:1 before/after crops for deconvolution and for noise reduction. Approval after each of the two.

## Stage 9 — Stars out, stretch

Follow `reference/stretch-and-finish.md`: StarXTerminator on linear data, stars kept as a separate view; three stretch candidates side by side with their numbers; **Gate G7** rejects a candidate that clips. The user picks one; discard the other two.

## Stage 10 — Composition and finishing

Narrowband: build the palettes the user wants (HOO, SHO, Foraxx-style) from `reference/narrowband-dualband.md`, show them side by side, keep one. Then finishing and star recombination from `reference/stretch-and-finish.md`: each change under a mask, with a before/after preview and a checkpoint. **Gate G8**.

## Stage 11 — Export

**Gate G9** first: pixel medians from `get_image_stats` must show a stretched image (a still-linear image exports black). Then `export_image` to `final/<Target>_<palette>_<YYYY-MM-DD>` as `.xisf` (32-bit), `.tif` (16-bit) and `.jpg`; for the web JPEG, `resample_image` with `mode: "scale"`, `factor` = 2048 / long side and `output_id: "<Target>_web"`, export that copy as `final/<Target>_<palette>_<YYYY-MM-DD>_web.jpg`, close it.

## Stage 12 — Log and push

Write `<workspace>/output/PROCESSING.md` from `reference/processing-log.md`, including the call log. Copy it, the JPEG and the session file into `<workspace>/output/push/`, then, after approval, `nebulis.py push <OBJECT> --bundle <workspace>/output/push --name <Target>_<YYYY-MM-DD>_processing.zip --title "<palette> final"` (admin key). Close every view this session created (never save views opened from files), leave only the final image open.
