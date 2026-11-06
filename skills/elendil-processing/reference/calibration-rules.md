# Calibration rules

Nebulis builds the calibration plan (`nebulis.py plan`): for each night × filter × exposure group of lights it picks a dark, a flat, a flat-dark and a bias, flats **attached** to the object first, the rest **matched** from the Calibration Library. Your job in Stage 3 is to check that plan against the Elendil rules below and to explain every issue.

## Elendil rules

| # | Rule | Why |
|---|---|---|
| R1 | A flat set is valid for a whole campaign while the optical train stays assembled (scope, filter wheel, camera) and the CAA rotation angle is unchanged. Refocusing does not invalidate it. | Flats are shot once, at the end of the campaign. |
| R2 | One flat set per filter. A D1 flat never calibrates D2 or unfiltered lights, and the reverse. | Dual-band filters vignette and pass light differently. |
| R3 | A CAA angle change during a campaign invalidates the flats and breaks alignment: such nights need their own flats, and the user must be told. | Dust shadows rotate with the camera. |
| R4 | Darks are reusable across sessions and campaigns when gain, exposure, binning and TEC setpoint match. Temperature within 2 °C. | The dark library covers 60-600 s at gains 100 and 200, at −8 °C. |
| R5 | With a matching dark, calibrate lights with dark + flat only: no bias, no dark optimisation. | The dark already holds the bias. |
| R6 | Flats are calibrated with a matching flat-dark when one exists, otherwise with the master bias. Never with the lights' dark. | At −8 °C the dark current of sub-second flats is negligible. |
| R7 | Darks shot through the opaque filter are darks whatever the `FILTER` header says. | Slot 3 of the wheel. |
| R8 | Expired darks or bias (older than the Nebulis validity setting, 180 days by default) are a warning, not an error: report the age. | Sensor drift is slow. |

## Reading the plan

For each group (night · filter · exposure · gain · binning · temperature · lights):

- `dark`: same gain, exposure and binning as the group; `deltaTempC` within ±2. Otherwise R4 is broken.
- `flat`: `filter` equal to the group's filter (R2). `source: attached` is what the Elendil workflow expects: flats are attached to the object in Nebulis. `matched` is acceptable only if the filter matches and the user confirms the CAA angle did not change (R1, R3).
- `flatDark` or `bias`: at least one (R6). When both exist, the flat-dark is used for the flats.
- `issues`: explain each one with the table below.

| Issue code | Severity | Meaning | Usual fix |
|---|---|---|---|
| `no_dark` | error | No dark in the library for this gain/exposure/binning | Shoot or import darks at those settings |
| `dark_temp_far` | error | Nearest dark more than the tolerance away in temperature | Shoot darks at this setpoint |
| `dark_expired` | warning | Dark older than the validity setting | Accept (R8) or reshoot |
| `no_flat` | error | No flat for this filter | Attach the campaign's flat set for this filter to the object in Nebulis |
| `flat_other_night` | warning | Flat from another night (`days` away) | Expected under R1 when flats were shot at the end of the campaign and the angle did not change; attach them to the object to make it explicit |
| `no_flat_calibration` | error | A flat but neither flat-dark nor bias | Import bias at the flats' gain |
| `bias_expired` | warning | Bias older than the validity setting | Accept (R8) or reshoot |
| `unknown_settings` | warning | The lights' exposure could not be read | Check the FITS headers |

## What the agent says

List errors first, each with its fix, and stop: errors are fixed in Nebulis, then the plan is rebuilt. Then list warnings and ask the user to accept each one. Record accepted warnings in the session file and in `PROCESSING.md`.
