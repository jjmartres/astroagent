# Reference setup

Facts the processing relies on. If a FITS header disagrees with this page, trust the header and tell the user.

## Optics and camera

| Item | Value |
|---|---|
| Telescope | Askar 91F flatfield APO, 91 mm aperture, 609 mm, f/6.9, integrated flattener |
| Reducer | Askar 0.75x, 456 mm, f/5 (profile `reducer`; backfocus to recalibrate when it arrives) |
| Camera | ZWO ASI585MC Air, Sony IMX585, colour (one-shot colour, Bayer), 3840 × 2160, 2.9 µm pixels, cooled |
| Controller | ASIAIR built into the camera; files are written by ASIAIR |
| Rotator | ZWO CAA electronic rotator: the camera angle is part of the flat validity |
| Filter wheel | ZWO EFW 5 positions: 1 = D1, 2 = D2, 3 = opaque (dark frames), 4 and 5 = empty |
| Mount | ZWO AM3N |

Read the Bayer pattern from the `BAYERPAT` header; do not assume it.

## Image scale (pick the profile from `FOCALLEN`)

| Profile | Focal length | Scale (arcsec/px) | Field (3840 × 2160) |
|---|---|---|---|
| `native` | 609 mm | 0.98 | about 1.05° × 0.59° |
| `reducer` | 456 mm | 1.31 | about 1.40° × 0.79° |

Scale = 206.265 × 2.9 / focal length (mm). For `run_plate_solve` pass `focal_length_mm` and `pixel_size_um: 2.9`, or `pixel_scale`. A WBPP drizzle at 2x halves the scale.

## Filters

| Filter | Type | Passbands | Channels on the OSC sensor |
|---|---|---|---|
| D1 | Askar Colour Magic dual-band, 6 nm | H-alpha 656.3 nm + OIII 500.7 nm | Ha in red; OIII in green and blue |
| D2 | Askar Colour Magic dual-band, 6 nm | SII 671.6 nm + OIII 500.7 nm | SII in red; OIII in green and blue |
| none | unfiltered (broadband) | the sensor's own RGB response | true colour |
| opaque | ASToptics dark frame filter | none | used only to shoot darks |

Never mix D1 and D2 data, or their flats. The `FILTER` header holds the wheel slot name set in ASIAIR; map it to this table and ask when it is ambiguous.

## Standard capture settings

| Target type | Filter | Gain | Exposure | Notes |
|---|---|---|---|---|
| Emission nebula (narrowband) | D1, D2 | 200 | 180 s | 120 subs a night, offset 10, dither every 3-4 frames |
| Galaxy, reflection nebula, dark nebula (broadband) | none | 100 | 120-150 s | offset 10 |

Sensor temperature: TEC set to −8 °C for all campaigns, except Sh2-131 which was shot at −10 °C. Binning 1.

## Site

Savoie, France: about 45° N, 750 m, Bortle 3-4. Nights of about 5-6 usable hours; light-pollution gradients are usually mild, so a heavy gradient on a single night points at clouds, dew or twilight.

## Software on the processing Mac

PixInsight with BlurXTerminator, NoiseXTerminator, StarXTerminator (RC Astro), GHS, SetiAstro scripts. Confirm what is installed in Stage 0; never assume.
