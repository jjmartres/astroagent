# Process icons from the call log

Goal: a `.xpsm` file whose icons are the processes this session actually ran, with the parameters that were applied, so the user can re-run or tweak any step by hand in PixInsight.

## How

1. **`astro_project.py icons <WS>`** reads every pixinsight-connector call log under `<WS>/agentic/` (`*.jsonl`, one per server session; `--log FILE` to point at others). For each call it keeps:
   - only calls that **succeeded** (no error, no `FAILED`, `REFUSED`, `BLOCKED`, `STOPPED BY USER` in the result);
   - only **processing** tools (measurement, preview, listing and housekeeping tools are skipped);
   - in the PJSR the connector sent, each `var X = new <Process>` of a process a person would re-run (BXT, NXT, SXT, GradientCorrection, MGC, SPCC, PixelMath, Curves, GHS, HT, LHE, HDRMT, USM, SCNR, ChannelCombination, LRGBCombination...), followed by its parameter assignments and then executed (`X.executeOn(...)`, `X.executeGlobal()` or the connector's `__run(X, ...)`).
   Assignments whose value is not a literal (a variable computed in PixInsight at run time) are dropped and listed; the icon keeps the process default for them. A PixelMath whose expression is computed is skipped entirely.
   Icons are numbered in run order: `s01_BlurXTerminator_Ha`, `s02_PixelMath_HOO`...
2. **`run_pjsr`** with the code in `agentic/work/icons.js`. It rebuilds each instance in PixInsight and asks PixInsight to serialize it (`ProcessInstance.toSource("XPSM 1.0", id)`), so names, enumerations and tables are PixInsight's own. It returns a JSON array; save it to `agentic/work/icons-result.json`.
3. **`astro_project.py xpsm <WS> --pjsr-result agentic/work/icons-result.json`** wraps the instances into `output/Process Icons - <common name> - <palette> workflow.xpsm`, one column at `xpos` 2000, 40 px apart, workspace `Workspace01`.

## Limits

- An instance that fails to serialize is reported by `xpsm` (exit 2) and left out; the others are written. If every instance fails, this PixInsight build does not support `toSource("XPSM 1.0")`: tell the user and skip the file.
- Scripts (ImageSolver, WBPP) are not processes and have no icon; their parameters are in PROCESSING.md.
- The icons hold no image references beyond what the process stores (PixelMath expressions name views: they must exist when the icon is used).

Load the file in PixInsight with **Process → Process Icons → Merge Process Icons** (keeps the icons already on the workspace; Load replaces them).
