# Processing log

Write `<workspace>/output/PROCESSING.md` at the end of Stage 12 from this template. Fill it from what happened, never from memory of a previous target. The call log is kept during the session in `<workspace>/agentic/work/call-log.md` and copied in as the appendix.

```markdown
# <Target> · <palette> · <YYYY-MM-DD>

## Data
| Night | Filter | Exposure | Gain | Temp | Lights kept / total | Integration kept |
|---|---|---|---|---|---|---|
(from the Nebulis manifest.json and Stage 2)

Total integration per filter: D1 <h>, D2 <h>, none <h>.
Frames rejected by review: <n> (list in the appendix).

## Calibration
(per group, from the Nebulis plan: dark, flat (attached or matched), flat-dark or bias, ΔT, issues and the user's decision on each warning)

## Stacking
WBPP <version from the console>, parameters passed to run_wbpp, masters produced (file, size, channels).

## Linear processing
| Step | View | Tool | Parameters | Gate | Result |
|---|---|---|---|---|---|

## Stretch and palette
Candidates (medians, clip fractions), the one chosen, palette expressions used.

## Finishing
| Step | Tool | Parameters | Mask | Gate |
|---|---|---|---|---|

## Outputs
Files in output/final/ with sizes.

## Environment
PixInsight build, pixinsight-connector version, BXT / NXT / SXT versions and AI models, Nebulis version, skill version.

## Appendix: call log
(every PixInsight call in order: #, tool, parameters, views in, views out, one-line outcome; retries included)
```

Call log row format, one per call:

```
| 14 | run_bxt | view_id=Ha, sharpen_stellar=0.5, sharpen_nonstellar=0.5 | Ha | Ha | FWHM 3.1 -> 2.6 px, ringing 0 -> 0 |
```
