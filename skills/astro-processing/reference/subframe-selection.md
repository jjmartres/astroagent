# Subframe selection (Stage 4b)

A second check of the lights after the Nebulis Frame Analysis grades and before WBPP. Nebulis keeps `fair` frames, and some of them still carry a `clouds` flag; a slow sky-brightness rise at the end of a night (target sinking into the light dome, moon, dawn) is graded `good` frame by frame. Both add gradients and noise to the stack.

## 1. Measure

SubframeSelector in measure-only mode on the raw lights (nothing is written next to them). The values are relative: the lights are not calibrated, so compare them with each other, not with other projects.

`run_pjsr` (async: about 1 minute per 300 frames on an Apple-silicon Mac), with the enumerations as **numbers**: the `SubframeSelector.prototype.*` constants are undefined in PJSR and the call fails at once with "signed integer value expected".

```js
var files = searchDirectory("<lights folder>/*.fit", true).sort();
var P = new SubframeSelector;
P.routine = 0;                 // MeasureSubframes
P.nonInteractive = true;
P.subframes = files.map(function (f) { return [true, f, "", ""]; });
P.fileCache = false;
P.subframeScale = <arcsec/px from rig.json>; P.scaleUnit = 0;      // ArcSeconds
P.cameraResolution = 4; P.cameraGain = 1; P.dataUnit = 2;           // Bits16, Normalized
P.psfFit = 4;                  // Moffat4
P.executeGlobal();
// P.measurements: one row per frame. Columns: 3 filePath, 4 weight, 5 FWHM, 6 eccentricity,
// 7 PSF signal weight, 9 SNR weight, 10 median, 12 noise, 14 stars, 15 star residual, 28 PSF SNR.
```

Write the rows to `agentic/work/subframeselector.csv` (night, file, FWHM, eccentricity, PSF signal weight, SNR weight, median, noise, stars, PSF SNR) from the PJSR and return only a count. Check the job with `job_status` until it is `done` or `failed`: a job that fails at once leaves no file, and waiting for the file alone hides the failure.

## 2. Flag

Per metric, a robust z-score over all frames: `z = (x − median) / (1.4826 × MAD)`. A frame is flagged when it is beyond **3** in the bad direction:

| Metric | Bad direction | What it catches |
|---|---|---|
| FWHM | high | seeing, focus drift, wind |
| Eccentricity | high | tracking, wind |
| Stars | low | clouds, haze, dew |
| PSF signal weight, PSF SNR | low | clouds, haze, bright sky |
| Median (sky level) | high | moon, light dome, dawn, haze |

Cross the list with the Nebulis grades: frames flagged `clouds` (even `fair`) and frames flagged here. Report per night: medians of each metric, flagged frames with their z-scores, and runs of consecutive flagged frames (a rising sky at the end of a night shows as a run). Propose the exclusion list; the user approves.

## 3. Exclude without touching the data

Never move or delete files under the raw data folder. Build the WBPP input as a folder of symbolic links:

```
agentic/work/wbpp_input/light/NIGHT_<date>/<kept lights>   -> links to the raw lights
agentic/work/wbpp_input/dark/<set>/…, flat/…               -> links to the calibration frames
```

Check with a `searchDirectory` in PJSR that PixInsight follows the links (count the files, read one header), then pass `agentic/work/wbpp_input` to `run_wbpp`. Write the excluded file names to `agentic/work/ss_flagged.txt` and the counts to the session file; `PROCESSING.md` lists them with their reason.

Record the review in Nebulis too (`nebulis.py review --reject`) only if the user asks: it changes the library for every later export.
