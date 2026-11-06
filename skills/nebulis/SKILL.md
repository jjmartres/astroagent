---
name: nebulis
description: >-
  Read and update the user's Nebulis astrophotography library from the terminal: list objects and
  nights, read Frame Analysis grades of the subs and record keep/reject decisions, build the
  stacking plan (lights kept plus matched darks, flats, flat-darks, bias), download a WBPP-ready
  export, and store processing results with the object. Use for "what's in Nebulis for Sh2-105",
  "which subs were bad last night", "fetch NGC 6888 for stacking", "push the final image to
  Nebulis", and as the data source of the astro-processing skill.
license: MIT
metadata:
  author: jjmartres
  version: "0.1.0"
---

# Nebulis

Nebulis is the user's self-hosted library of imaging sessions and calibration frames. Talk to it only through `scripts/nebulis.py` next to this file (Python 3.9+, standard library only). Run it as `python3 <this skill's folder>/scripts/nebulis.py <command>`; add `--json` before the command for the raw payload.

## Configuration

The script reads `NEBULIS_URL` and `NEBULIS_API_KEY` from the environment, or from `~/.config/nebulis/env` (`KEY=value` lines, `chmod 600`). Never print, echo or paste the key, never put it on a command line, never write it into a file other than that one. If the configuration is missing, tell the user how to set it (see the repository README) and stop.

Some commands need an **admin** key: `review` and `push`. A 403 means the key is not admin.

## Commands

| Command | Use |
|---|---|
| `status` | Server version and an authenticated test. Run it first in a session. |
| `objects [--search TEXT]` | Find an object id (`id` is what every other command takes). |
| `sessions OBJECT` | Nights with filters, exposures and sub counts. |
| `analysis OBJECT DATE [--bad-only]` | Frame Analysis of one night: grade (good / fair / bad), flags (`clouds`, `faint`, `trails`, `soft`, `streak`, `spots`, `noStars`, `noisy`), FWHM, star count, kept or dropped, and the frame's library path. Unmeasured frames count as kept. |
| `review --keep\|--reject\|--reset PATH...` | Record the user's call on frames (paths from `analysis`). `--reset` returns a frame to its grade. Only after the user approved the list. |
| `plan OBJECT --dates D... \| --all` | The stacking plan: per night × filter × exposure, the lights kept and the dark, flat, flat-dark and bias Nebulis picked (`attached` or `matched`), with issues. Exit code 2 when the plan has errors. |
| `fetch OBJECT --dates D... --dest DIR [--allow-warnings] [--force]` | Builds the export on the server (WBPP layout by default), downloads it and unpacks it under `DIR/<export folder>/`. Refuses a plan with errors; refuses warnings unless `--allow-warnings` (pass it only after the user accepted each warning). |
| `archives OBJECT` | Project archives already stored with the object. |
| `push OBJECT --bundle DIR \| --file FILE` | Stores a `.zip`, `.xpsm` or `.pxiproject` with the object (`--bundle` zips a folder). Refuses to overwrite a same-named archive unless `--force`. |

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

- Read-only by default: only `review` and `push` change anything on the server, and only after the user approved the exact list or file.
- Never delete anything in Nebulis; the script has no delete command on purpose.
- `reference/api.md` documents the endpoints, for questions the script does not answer. Use `curl` only for read-only `GET` calls, with the key read from the environment (`-H "X-API-Key: $NEBULIS_API_KEY"`), never typed.
