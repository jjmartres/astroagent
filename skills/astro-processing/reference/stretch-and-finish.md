# Stars, stretch and finishing

## 1. Stars out (linear)

- Narrowband: `run_sxt` with `is_linear: true` on each mono channel (`Ha`, `OIII`, `SII`); close the mono star views it produces. Then `run_sxt` on the **D1 RGB master** (after BXT): keep its stars view as `Stars`.
- Broadband: `run_sxt` with `is_linear: true` on `RGB`; keep the stars view as `Stars`.
- Keep `overlap` at the tool's default (0.5).

## 2. Stretch the starless images: three candidates

Clone the starless image(s) three times (`_s1`, `_s2`, `_s3`) and stretch each candidate with one setting:

| Candidate | Narrowband (same value on every channel) | Broadband |
|---|---|---|
| s1, gentle | `robust_median_stretch` `target_median` 0.12 | 0.15 |
| s2, middle | 0.18 | 0.20 |
| s3, strong | 0.25 | 0.25 |

Use `black_point_sigma` 2.8 and `linked: true` for RGB. Narrowband: stretching each channel to the same median balances Ha and OIII before the palette. For broadband, show s1-s3 directly; for narrowband, build the chosen palette (HOO by default) from each candidate set so the user compares colour images.

GHS instead: when `GeneralizedHyperbolicStretch` is installed and the user prefers it, call `describe_process` `GeneralizedHyperbolicStretch` first, then `run_process` with three settings of its stretch factor; never guess parameter names.

For each candidate report per channel: median, MAD, `clampFractions` (from `get_image_stats`). Gate G7. Show the three previews at the same size. Apply the chosen one; close the others.

## 3. Finishing (non-linear), one change at a time

Before each change: `clone_image` checkpoint. After: before/after preview, Gate G8, approval. Masks: `create_luminance_mask` from the image (`clip_low` 0.10, `blur` 5), `apply_mask`, then `remove_mask` after the change.

| Order | Change | Tool and starting values |
|---|---|---|
| 1 | Green cast (SHO, HOO) | `run_scnr` `amount` 0.6 (SHO up to 1.0), `protection: "AverageNeutral"`; state the amount used |
| 2 | Saturation, background protected | luminance mask, `run_curves` `channel: "S"`, `points: [[0,0],[0.5,0.58],[1,1]]` |
| 3 | Contrast | luminance mask, `run_curves` `channel: "L"` gentle S-curve `[[0,0],[0.25,0.22],[0.75,0.80],[1,1]]` |
| 4 | Local contrast (optional) | luminance mask, `run_lhe` `radius` 64, `slope_limit` 1.5, `amount` 0.3; or `run_hdrmt` `layers` 6, `inverted: true` |
| 5 | Colour tweaks (optional) | `run_curves` on `R`, `G` or `B`, only on request |

## 4. Stars back

1. `stretch_stars` on `Stars`: `midtone` 0.2, `iterations` 2 (more iterations = brighter, larger stars).
2. `star_protected_blend` into the finished starless image: `strength` 1.0, `core_threshold_low` 0.6, `core_threshold_high` 0.9, `min_strength_fraction` 0.3, `max_value` 0.98.
3. Star reduction (optional): redo step 2 from the checkpoint with `strength` 0.6-0.8; show both crops.

Narrowband: the D1 stars are reddish (Ha) with teal (OIII) halos; if the user wants neutral stars, `run_scnr` or a saturation curve on `Stars` before blending, on request only.

## 5. Values are starting points

Every number on this page is a starting value. When the user changes one, keep the new value for the rest of the session and log it.
