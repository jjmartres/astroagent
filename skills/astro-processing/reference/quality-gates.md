# Quality gates

Each gate is measured in PixInsight (or read from Nebulis) and reported with its number. A failed gate stops the stage: retry with new parameters, or ask. Thresholds are starting values for data from the reference setup; when the user changes one, record it in the session file.

| Gate | Stage | Measure | Pass | Notes |
|---|---|---|---|---|
| G1 Plan | 3 | `nebulis.py plan` totals | `errors` = 0; every warning accepted by the user | See `calibration-rules.md` |
| G2 Stacking | 5 | `wbpp_status`, then `get_image_dimensions` on each master | One master per filter set; each master has 3 channels; WBPP exit code 0 | Compare the integration time (kept lights × exposure) with the plan |
| G3 Astrometry | 6 | `verify_astrometry` median deviation (px) | ≤ 0.15 PASS; ≤ 0.30 WARN (report, continue); > 0.30 FAIL | On FAIL, solve again with `recursive_splines: true`; still failing, ask. Thresholds from pixinsight-connector-skills |
| G4 Gradient | 7 | `measure_uniformity` score before/after; `get_image_stats` median and MAD | Uniformity score lower after; median changed by less than 5%; MAD not higher | A median that drops a lot means real signal was removed: reject and try a larger scale or another tool |
| G5 Deconvolution | 8 | `measure_stars` (median FWHM, elongation) and `measure_ringing` before/after | FWHM lower or equal; elongation not higher; ringing count not higher | Plus a 1:1 crop on the brightest star field |
| G6 Noise reduction | 8 | `get_image_stats` MAD of the background before/after; 1:1 crop | MAD lower; no visible worm or blotch texture in the crop | Lower `denoise` before raising `detail` |
| G7 Stretch | 9 | `get_image_stats` `clampFractions` per channel on each candidate | Fraction at 1 ≤ 0.1%; fraction at 0 ≤ 1.5% | Starless image, so stars do not count against the white clip |
| G8 Finishing | 10 | `measure_clipped_blocks` (level 0.98, block_fraction 0.5) and `measure_saturation` after each change | No new clipped blocks compared with before the change | Informational for saturation: the user judges colour |
| G9 Export | 11 | `get_image_stats` per-channel median of the pixel data | Median ≥ 0.05 on every channel | A linear image looks fine with an STF but exports black |
