# research.json

Written by you after the research step (SKILL.md § 2), read by `project`, `doc` and `astrobin`. Every field is optional except `summary`; leave out what you could not source rather than guessing.

```json
{
  "common_name": "Crescent Nebula",
  "catalog_ids": ["NGC 6888", "Sh2-105", "LBN 203", "Caldwell 27"],
  "object_type": "Emission nebula (Wolf-Rayet wind-blown shell)",
  "constellation": "Cygnus",
  "distance_ly": 5000,
  "size_arcmin": "18 × 12",
  "magnitude": 7.4,
  "summary": "One or two sentences: what the object is and what makes it worth imaging.",
  "facts": [
    { "label": "Ionising star", "value": "WR 136" }
  ],
  "sections": [
    { "title": "What it is", "paragraphs": ["..."] },
    { "title": "Discovery", "paragraphs": ["..."] },
    { "title": "In this image", "paragraphs": ["What the filters used here show: which structures come from H-alpha, which from OIII."] }
  ],
  "imaging_notes": ["Short, practical lessons for the next campaign on this target."],
  "references": [
    { "title": "SIMBAD: NGC 6888", "url": "https://simbad.cds.unistra.fr/simbad/sim-id?Ident=NGC+6888" }
  ]
}
```

Guidelines:

- **Your own words.** Summarise sources; never paste paragraphs. Quote at most a short phrase, with its reference.
- **Numbers with their source.** When sources disagree (distances often do), give the range or the value of the most authoritative source and say so in the text.
- `distance_ly` and `magnitude` are numbers; `size_arcmin` may be a string for an elliptical size.
- `sections`: two to four, a few short paragraphs each. "In this image" ties the object to the data in rig.json and is the most useful one to the user.
- `references`: the pages you actually used, with working URLs.
