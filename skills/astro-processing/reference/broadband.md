# Broadband path (unfiltered, gain 100)

For galaxies, reflection and dark nebulae shot without a filter. The master `RGB` is a debayered colour image; colour comes from SPCC, not from a palette.

Pick the path from the light group's filter in the Nebulis plan and say which one you took. Targets whose interest is reflection nebulosity or dark lanes (IC 5146, for example) are broadband even when they hold some emission.

## 1. Curves for SPFC, MGC and SPCC

Run the `pixinsight-target-intake` skill when it is installed: it resolves the QE curve and filter curves from the headers, checks MARS coverage at the target, and writes `agentic/work/target-info.md`. Otherwise:

1. `find_filters` with `query: "IMX585"` and `channel: "Q"` for the sensor QE curve. If nothing matches, ask the user; `Ideal QE curve` only if they accept it.
2. `find_filters` for the camera's RGB filter curves (search `ZWO`, `IMX585`, `ASI585`). If none, ask; never pick a curve from another sensor silently.
3. `inspect_environment` with `sections: ["mars"]` and the target's position: MARS coverage decides between MGC and GradientCorrection.

## 2. Linear steps on `RGB`

After Stage 6 (crop, BXT correction, plate solve):

1. Gradient (Stage 7): `run_spfc` with `red_filter_name`, `green_filter_name`, `blue_filter_name`, `qe_name`, then `run_mgc` (colour: no `filter`) when MARS covers the field; otherwise `run_gradient_correction`. Pass the MARS files that cover the field with `mars_files` (`inspect_environment` with the target's position lists them; DR1 update files can hold no R data). Keep the default gradient scale (1024) for a target smaller than about a third of the frame; a smaller scale starts modelling the subject's halo. Gate G4 with the radial profile.
2. `run_spcc` with the same filter and QE names; `white_reference` only if the user names one (galaxies: `Average Spiral Galaxy` is a common choice, ask). SPCC includes background neutralisation: do not add another.
3. `run_bxt` with default sharpening. Gate G5.
4. `run_nxt` with `denoise` 0.5. Gate G6.

Then stars and stretch from `stretch-and-finish.md`.

## 3. Starless background, before the stretch

After `run_sxt` on the linear `RGB`, measure the starless background with `bgBlocks` (64 and 256 px: a spread that stays the same at 256 px is structure, not noise) and `colProfile` (columns and rows). Work on a copy, keep what improves the numbers and leaves the subject's halo level unchanged:

1. `run_gradient_correction` on the starless copy, then `run_abe` with `poly_degree` 4: without stars both model the residual background far better than on the master.
2. Bands along columns or rows (±0.3 σ or more in `colProfile`, already in the stacked master): `correctBands(id, newId, exclude)` from `astro-helpers.js` subtracts the smoothed per-column level, subject excluded. Tell the user the master flat is the likely source (flat panel uniformity).

On NGC 891 (broadband OSC, 11.5 h) this took the block spread from 1.5 σ to 0.8 σ and the column bands from ±0.3 σ to ±0.03 σ; without it the stretch showed a milky halo and cloud-like patches.

## 3. Luminance

The reference setup has no separate luminance filter. If the user brings a luminance master (from another dataset), fuse it on the **stretched** image with ChannelCombination in HSV mode, the luminance as V: `run_process` `name: "ChannelCombination"`, call `describe_process` first for the exact parameter names. LRGBCombination and CIE Lab fusion have destroyed chrominance on this user's data before. Check: median saturation (`measure_saturation`) not lower after the fusion.

## 4. Optional H-alpha

Galaxies with HII regions can take D1 Ha: extract `Ha` as in `narrowband-dualband.md`, register it to `RGB` (`align_to_reference`), and blend with `ha_inject_red` (read its parameters from the tool) or `dynamic_narrowband_blend`. Propose it only when D1 data of the same target exists.
