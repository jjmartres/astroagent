# Changelog

## 0.1.0 (2026-11-06)

First version, not yet run end to end on real data.

- `astro-processing` skill: 12-stage workflow with an approval at every stage; rig, calibration rules, quality gates, dual-band D1/D2 extraction and palettes, broadband path, stretch and finishing references; PJSR border helper.
- `nebulis` skill: `nebulis.py` client for objects, sessions, Frame Analysis and review, stacking plan, WBPP export download, project archive upload; tests against a mock API.
- Claude Code plugin manifest, `install.sh` for Claude Code and OpenCode, CI.
- Workflow skill renamed `astro-processing`; the setup is described generically.
- Usage section on the site and in the README: an example Claude Code session and tips.
- Nebulis settings read from `ASTROAGENT_NEBULIS_URL` and `ASTROAGENT_NEBULIS_API_KEY`, or from `~/.config/astroagent/env`.
- Logo (“Stretch to light”), brand kit in `brand/`, website in English, French, Spanish and Italian on GitHub Pages.
