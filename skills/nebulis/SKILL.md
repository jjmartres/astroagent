---
name: nebulis
description: >-
  Read and update the user's Nebulis astrophotography library from the terminal: list objects and
  nights, read Frame Analysis grades of the subs and record keep/reject decisions, build the
  stacking plan (lights kept plus matched darks, flats, flat-darks, bias), download a WBPP-ready
  export, and store processing results with the object. Use for "what's in Nebulis for Sh2-105",
  "which subs were bad last night", "fetch NGC 6888 for stacking", "add the final image to
  Nebulis", "push the project archive", and as the data source of the astro-processing skill.
license: MIT
metadata:
  author: jjmartres
  version: "0.5.1"
---

# Nebulis

Nebulis is the user's self-hosted library of imaging sessions and calibration frames. Talk to it only through `scripts/nebulis.py` next to this file (Python 3.9+, standard library only). Run it as `python3 <this skill's folder>/scripts/nebulis.py <command>`; add `--json` before the command for the raw payload.

## Configuration

The script reads `ASTROAGENT_NEBULIS_URL` and `ASTROAGENT_NEBULIS_API_KEY` from the environment, or from `~/.config/astroagent/env` (`KEY=value` lines, `chmod 600`); environment variables win. Never print, echo or paste the key, never put it on a command line, never write it into a file other than that one. If the configuration is missing, tell the user how to set it (see the repository README) and stop.

Some commands need an **admin** key: `review`, `push` and `image`. A 403 means the key is not admin.

## Commands

| Command | Use |
|---|---|
| `status` | Server version and an authenticated test. Run it first in a session. |
| `objects [--search TEXT]` | Find an object id. The server's search knows designations and aliases: `NGC 2264`, `ngc2264` and `Christmas Tree` all find `NGC2264`. Every other command takes the object the same way (id, designation or alias) and calls the API with its id. |
| `object OBJECT` | One object: type, constellation, catalogue position, magnitude, distance, size, names. |
| `sessions OBJECT` | Nights with filters, exposures and sub counts. |
| `analysis OBJECT DATE [--bad-only]` | Frame Analysis of one night: grade (good / fair / bad), flags (`clouds`, `faint`, `trails`, `soft`, `streak`, `spots`, `noStars`, `noisy`), FWHM, star count, kept or dropped, and the frame's library path. Unmeasured frames count as kept. |
| `review --keep\|--reject\|--reset PATH...` | Record the user's call on frames (paths from `analysis`). `--reset` returns a frame to its grade. Only after the user approved the list. |
| `plan OBJECT --dates D... \| --all [--precalibrated]` | The stacking plan: per night × filter × exposure, the lights kept and the dark, flat, flat-dark and bias Nebulis picked (`attached` or `matched`), with issues. Exit code 2 when the plan has errors. `--precalibrated` is for lights that are already calibrated (Telescope.live `*_cal.fits`, for example). It sends `"precalibrated": true` to the server, which then attaches no calibration frame and raises no calibration issue; lights whose FITS header says they are calibrated (`PROC = 'True'`) are detected by the server without it, and their groups show `already calibrated`. The plan also names each group's camera and telescope: lights of another rig form their own group. On a server without that option, the missing or imperfect calibration issues (`no_dark`, `dark_temp_far`, `dark_expired`, `no_flat`, `flat_other_night`, `no_flat_calibration`, `bias_expired`) are then shown as ignored and do not count; `unknown_settings` still does. |
| `fetch OBJECT --dates D... --dest DIR [--precalibrated] [--allow-warnings] [--force]` | Builds the export on the server (WBPP layout by default), downloads it and unpacks it under `DIR/<export folder>/`. Refuses a plan with errors; refuses warnings unless `--allow-warnings` (pass it only after the user accepted each warning). `--precalibrated` as for `plan`: pass it only when the lights really are calibrated, never to get round a missing dark or flat. The export then holds lights only. The server builds the ZIP in one go: above a few GB, fetch **one night per call** (`--dates 2026-10-14`, then the next); a 7 GB multi-night export once stopped the server mid-build. Each night's export repeats the shared darks, bias and flats: compare them by checksum and keep one copy. |
| `archives OBJECT` | Project archives already stored with the object. |
| `telescopes` | Telescope profiles: model, optical configurations (focal length, pixel size, sensor size), sensor type, filters. Connection details are never printed. |
| `site` | The active observing site: name, coordinates, Bortle class. |
| `push OBJECT --bundle DIR \| --file FILE` | Stores a **project archive** (`.zip`, `.xpsm` or `.pxiproject`) with the object, under Projects (`--bundle` zips a folder). Refuses to overwrite a same-named archive unless `--force`. **One archive per processing run**, named `<OBJECT>_<PALETTE>_<YYYY-MM-DD>_processing.zip` and built by `astro_project.py bundle` (astro-project skill) so every archive has the same layout; not the raw data or scratch. Never zip a JPEG to push it: it would show as a second project, not as an image. |
| `images OBJECT` | Finished images stored with the object (processed images), object-level or per session. |
| `image OBJECT --file FILE [--title T] [--notes N] [--force]` | Adds a finished image (JPG, PNG, TIFF, XISF, FITS) to the **object** (not to a session): it shows in the object's Processed images and in the gallery, dated by its upload day. Use it for the final JPEG at Stage 12. Refuses a same-named image unless `--force`. |

Exit codes: 0 ok, 1 usage or configuration, 2 plan errors (or unaccepted warnings), 3 API or network error.

## The WBPP export layout

`fetch` unpacks one folder, `<OBJECT>_<nights>_wbpp/`:

```
Lights/NIGHT_<date>/FILTER_<filter>/*.fits     lights kept, per night and filter
Darks/<bundle>/*.fits                          shared darks, once
Bias/<bundle>/*.fits                           shared bias, once
Flats/NIGHT_<date>/FILTER_<filter>/*.fits      flats per night and filter
FlatDarks/NIGHT_<date>/FILTER_<filter>/*.fits
manifest.json                                  the plan, exactly as Nebulis built it
not-kept.txt                                   lights left out (when any)
README.txt
```

WBPP reads IMAGETYP, FILTER and EXPTIME from the headers. With several nights, add `NIGHT` as a pre-processing grouping keyword so each night is calibrated with its own flats folder.

## Rules

- Read-only by default: only `review`, `push` and `image` change anything on the server, and only after the user approved the exact list or file.
- The script cannot delete an archive or an image (no delete command, on purpose). If one went to the wrong place, tell the user to delete it in the Nebulis UI, then upload again.
- Never delete anything in Nebulis; the script has no delete command on purpose.
- `reference/api.md` documents the endpoints, for questions the script does not answer. Use `curl` only for read-only `GET` calls, and only when the key is in the environment (`-H "X-API-Key: $ASTROAGENT_NEBULIS_API_KEY"`), never typed; otherwise use the script.
