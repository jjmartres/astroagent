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

1. Gradient (Stage 7): `run_spfc` with `red_filter_name`, `green_filter_name`, `blue_filter_name`, `qe_name`, then `run_mgc` (colour: no `filter`) when MARS covers the field; otherwise `run_gradient_correction`. Gate G4.
2. `run_spcc` with the same filter and QE names; `white_reference` only if the user names one (galaxies: `Average Spiral Galaxy` is a common choice, ask). SPCC includes background neutralisation: do not add another.
3. `run_bxt` with default sharpening. Gate G5.
4. `run_nxt` with `denoise` 0.5. Gate G6.

Then stars and stretch from `stretch-and-finish.md`.

## 3. Luminance

Elendil has no separate luminance filter. If the user brings a luminance master (from another dataset), fuse it on the **stretched** image with ChannelCombination in HSV mode, the luminance as V: `run_process` `name: "ChannelCombination"`, call `describe_process` first for the exact parameter names. LRGBCombination and CIE Lab fusion have destroyed chrominance on this user's data before. Check: median saturation (`measure_saturation`) not lower after the fusion.

## 4. Optional H-alpha

Galaxies with HII regions can take D1 Ha: extract `Ha` as in `narrowband-dualband.md`, register it to `RGB` (`align_to_reference`), and blend with `ha_inject_red` (read its parameters from the tool) or `dynamic_narrowband_blend`. Propose it only when D1 data of the same target exists.
