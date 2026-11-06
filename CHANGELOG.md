# Changelog

## 0.2.0 (2026-11-06)

- New `astro-project` skill and `scripts/astro_project.py` (standard library only):
  - `scan` builds `output/rig.json` from the Nebulis export's `manifest.json`, the FITS headers of the lights (read without the pixels) and the Nebulis object, telescope profile and observing site; records where each value came from; asks only for what is missing; validated against `reference/rig.schema.json`.
  - `project` writes the PixInsight project description (`project.json`), `doc` a documentation page, `report` a session report of every stage (measured, proposed, decided, parameters, gates), `astrobin` the AstroBin form fields (optional).
  - `icons` and `xpsm` turn the processes the session actually ran, read from the pixinsight-connector call log, into a process icon set serialized by PixInsight.
  - Pages in the astroagent colours (Night, OIII, H-alpha) with a light/dark switch, self-contained.
- `nebulis.py`: `object`, `telescopes` (connection details stripped) and `site` commands.
- `astro-processing`: bootstraps the project after Fetch, researches the object while WBPP runs, writes the documentation at Stage 12; rig facts come from `rig.json` when present.
- Releases: a version bump in `plugin.json` on `main` creates the `vX.Y.Z` tag and the GitHub release from this file, and moves the `latest` tag; the install commands follow `latest`.
- Site redesigned: the example session replayed like a terminal recording at the top, gains, the approval loop, install with shell tabs; optional Nebulis Connector setup in PixInsight.

## 0.1.0 (2026-11-06)

First version, not yet run end to end on real data.

- `astro-processing` skill: 12-stage workflow with an approval at every stage; rig, calibration rules, quality gates, dual-band D1/D2 extraction and palettes, broadband path, stretch and finishing references; PJSR border helper.
- `nebulis` skill: `nebulis.py` client for objects, sessions, Frame Analysis and review, stacking plan, WBPP export download, project archive upload; tests against a mock API.
- Claude Code plugin manifest, `install.sh` for Claude Code and OpenCode, CI.
- Workflow skill renamed `astro-processing`; the setup is described generically.
- Usage section on the site and in the README: an example Claude Code session and tips.
- Nebulis settings read from `ASTROAGENT_NEBULIS_URL` and `ASTROAGENT_NEBULIS_API_KEY`, or from `~/.config/astroagent/env`.
- Logo (“Stretch to light”), brand kit in `brand/`, website in English, French, Spanish and Italian on GitHub Pages.
