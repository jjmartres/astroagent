# Output fields

## project.json

One line of JSON (PixInsight's Description field takes plain text: copy the `description` value).

| Field | From |
|---|---|
| `target`, `common_name`, `constellation`, `object_type`, `ra`, `dec` | rig.json `target`, research.json |
| `telescope` | `"<model> (<aperture> mm, <focal> mm f/<ratio>)"` |
| `camera` | `"<model> (<sensor>)"` |
| `filter` | every filter with its description, `; `-separated |
| `site`, `site_coords` | `capture_location` with Bortle class |
| `session_count` | distinct nights with lights |
| `sessions` | one line per filter: subs × exposure, gain, bin, time, nights |
| `stacking` | `WBPP (PixInsight)` |
| `calibration` | the frame types present: darks, flats, flat-darks, bias |
| `subs_integrated` | kept / total, from the Nebulis manifest (after the review) |
| `total_exposure`, `palette`, `notes` | computed; report.json |
| `ref_alignment`, `ref_integration` | always empty: filled by the user in PixInsight |
| `description` | the text block above, plus the research summary |

## astrobin.json (optional)

Pretty-printed, for copying into AstroBin's upload form by hand; the file is not an API payload.

| Field | From |
|---|---|
| `title` | `"<common name> (<id>)"` |
| `description` | research summary + one acquisition sentence |
| `subject_type` | from the object type: GALAXY, NEBULA, OPEN_CLUSTER, GLOBULAR_CLUSTER, PLANETARY_NEBULA, SUPERNOVA_REMNANT, OTHER |
| `data_source` | `BACKYARD` |
| `imaging_telescopes`, `imaging_cameras`, `mounts` | rig.json |
| `filters` | one per filter: description, bands found in it (Ha, OIII, SII, L, R, G, B), `DUAL_BAND`/`TRI_BAND` type, bandwidth in nm |
| `software` | PixInsight and Nebulis versions from report.json, astroagent |
| `location` | site name, latitude, longitude, altitude |
| `acquisition_details` | one row **per night and filter** from rig.json `nights`: number, duration, binning, gain, sensor cooling, darks/flats/flat-darks/bias counts, Bortle |
| `first_acquisition_date`, `last_acquisition_date` | first and last night |
| `keywords` | id, common name, catalogue ids, constellation, palette |
| `image_file`, `link` | empty: the user uploads the image |

## reddit.json (optional)

The r/astrophotography post, for pasting by hand. Built to the subreddit's rules; it holds facts only.

| Field | From |
|---|---|
| `title` | `"<common name> (<id>)"`, nothing else (rule 4: no equipment, acquisition or processing details) |
| `image_file` | `final/<NAME>.jpg`, or `final/<NAME>_web.jpg` when the first is over Reddit's 20 MB; uploaded in the post (rule 1) |
| `body` | Markdown: a placeholder line for the user's own words, **Acquisition** (telescope, camera and cooling, mount, filters, site name and Bortle class without coordinates, subs kept and total integration, one line per filter, calibration frame counts) and **Processing** (PixInsight and plug-in versions, Nebulis, astroagent, then one line per stage done in report.json: summary, processes or applied values; palette) (rule 5) |
| `checks` | what the script could not check: own words, rule 1, rule 4, the one-week wait for a reprocessing (rule 3), pre-calibrated lights (rule 3), length |

Exit 2 when the mount or report.json stages are missing: rule 5 asks for both.
