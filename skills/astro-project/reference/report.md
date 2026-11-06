# report.json

Written by you at Stage 12 of astro-processing, from the session file (`agentic/work/astro-session.md`) and the call log, then rendered by `astro_project.py report` into `output/doc/session-report.html`. It records what happened; it is not a plan. A stage that was not run is `"skipped"` with the reason in `decision`.

```json
{
  "target": "Sh2-105",
  "date": "2026-11-06",
  "palette": "Foraxx",
  "path": "narrowband",
  "summary": "One sentence: nights, subs kept, the result.",
  "stages": [
    {
      "n": 9,
      "name": "Stars out, stretch",
      "status": "done",
      "auto": false,
      "summary": "Short line shown under the stage name",
      "measured": "s1 median 0.12, s2 0.18, s3 0.25 (clips 0.14 %)",
      "proposal": "Three robust_median_stretch candidates at target medians 0.12, 0.18, 0.25",
      "why": "Same median per channel balances Ha and OIII before the palette",
      "decision": "s2",
      "params": { "run_stretch": { "target_median": 0.18 } },
      "gates": [
        { "id": "G7", "measure": "pixels clipped to white", "value": "0.14 %", "threshold": "≤ 0.1 %", "pass": false,
          "note": "s3 rejected, s1 and s2 kept" }
      ],
      "preview": "../../agentic/previews/s09_candidates.jpg"
    }
  ],
  "integration": [
    { "filter": "D1", "subs_kept": 768, "subs_total": 800, "exposure_s": 180 }
  ],
  "outputs": ["output/final/Sh2-105_Foraxx_2026-11-06.xisf"],
  "environment": { "PixInsight": "1.9.5", "pixinsight-connector": "2.5.2", "BlurXTerminator": "2.0", "Nebulis": "2.2.0" },
  "notes": "Anything the user asked to remember about this session."
}
```

- `status`: `done`, `skipped` or `todo` (a session stopped early).
- `auto`: true when the user let the stage run without waiting.
- `params`: an object (tool → parameters, or name → value) or a string; the values that were applied, not the ones proposed and then changed.
- `gates`: every gate measured in the stage, with the measured value; `note` explains a failed gate that only rejected a candidate.
- `preview`: optional, a path relative to `output/doc/`.
- `notes` also goes into `project.json`.
