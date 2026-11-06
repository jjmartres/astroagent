# Narrowband with the D1/D2 dual-band filters

The ASI585MC is a colour camera: each dual-band master is an RGB image in which the red channel holds one emission line and green and blue share OIII.

| Master | Red channel | Green and blue |
|---|---|---|
| D1 | H-alpha (656.3 nm) | OIII (500.7 nm) |
| D2 | SII (671.6 nm) | OIII (500.7 nm) |

Do everything below on the linear masters, after Stage 7 (crop, BXT correction, plate solve, gradient).

## 1. Extract the channels

With `pixelmath_new_image` (`color: "gray"`, `size_from` the master, `copy_astrometric_solution: true`):

| New view | Expression |
|---|---|
| `Ha` | `D1[0]` |
| `OIII_D1` | `(D1[1] + D1[2]) / 2` |
| `SII` (D2 present) | `D2[0]` |
| `OIII_D2` (D2 present) | `(D2[1] + D2[2]) / 2` |

D1 only: the palettes are HOO only. Say that SHO needs D2 data.

## 2. One OIII from D1 and D2

When both exist:

1. `linear_fit` `OIII_D2` to `OIII_D1` (default rejection).
2. `get_image_stats` on both: take each MAD (noise estimate).
3. Weights `w1 = 1/MAD1²`, `w2 = 1/MAD2²`, `k = w1 / (w1 + w2)`. Write the arithmetic in the log.
4. `pixelmath_new_image` `OIII`, gray: `k*OIII_D1 + (1-k)*OIII_D2` with `symbols: "k=<value>"`.
5. **Check**: MAD of `OIII` below the MAD of each input. Otherwise keep `OIII_D1` as `OIII` and say why.

D1 only: `rename_view` `OIII_D1` to `OIII`.

## 3. Linear processing per channel

For each of `Ha`, `OIII`, `SII`, with a checkpoint before each step:

1. `run_bxt` with default sharpening (`sharpen_stellar` 0.5, `sharpen_nonstellar` 0.5; lower `sharpen_nonstellar` to 0.3 on OIII when it is faint and noisy). Gate G5.
2. `run_nxt`: start at `denoise` 0.5 for Ha, 0.6 for OIII and SII. Gate G6.

Then follow `stretch-and-finish.md` for stars and the stretch. Stars for the final image come from the **D1 RGB master** (BXT applied), not from the mono channels.

## 4. Palettes (on the stretched starless channels)

Build each candidate with `pixelmath_new_image`, `color: "rgb"`, `size_from: "Ha"`. The connector's PixelMath has no `pow()`: `a^b` is written `exp(b*ln(a+1e-6))`; `~x` is `1-x`.

| Palette | Red | Green | Blue |
|---|---|---|---|
| HOO | `Ha` | `OIII` | `OIII` |
| HOO, warm green | `Ha` | `0.4*Ha + 0.6*OIII` | `OIII` |
| SHO (Hubble) | `SII` | `Ha` | `OIII` |
| SHO, Foraxx-style dynamic | `exp((1-OIII)*ln(OIII+1e-6))*SII + (1-exp((1-OIII)*ln(OIII+1e-6)))*Ha` | `exp((1-OIII*Ha)*ln(OIII*Ha+1e-6))*Ha + (1-exp((1-OIII*Ha)*ln(OIII*Ha+1e-6)))*OIII` | `OIII` |

The dynamic SHO follows the idea of the Foraxx palette (Paulo Tavares): the green mixes Ha and OIII according to where both are strong, which avoids the green cast of a plain SHO.

Show the candidates side by side with the same preview size; the user picks one (or two to compare after finishing). Expressions used go into `PROCESSING.md`.

## 5. Colour notes

- Plain SHO is green-dominated: the finishing stage removes most of it with SCNR (see `stretch-and-finish.md`).
- HOO OIII often needs to be brought up to Ha: balance it in the stretch (same target median per channel) rather than by multiplying OIII in PixelMath.
- SPCC narrowband mode is not used for D1/D2 data: the channel balance comes from the stretch.
