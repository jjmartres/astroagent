#!/usr/bin/env python3
"""astro_project.py: describe and document one processed campaign. Standard library only (Python 3.9+).

Every file goes into the processing workspace laid out by the astro-processing skill:

  <workspace>/data/<export>/      the Nebulis WBPP export (read-only; manifest.json, Lights/, Darks/, Flats/...)
  <workspace>/output/rig.json     target, site, optics, camera, filters, sequences      (scan)
  <workspace>/output/research.json  object research written by the agent (schema: reference/research.md)
  <workspace>/output/report.json  the session report written by the agent (schema: reference/report.md)
  <workspace>/output/project.json PixInsight project description, one line            (project)
  <workspace>/output/doc/index.html            documentation page                     (doc)
  <workspace>/output/doc/session-report.html   what was done, stage by stage          (report)
  <workspace>/output/astrobin.json             AstroBin form fields, optional         (astrobin)
  <workspace>/output/Process Icons - <name> - <palette> workflow.xpsm                 (icons, then xpsm)

Commands:
  scan WS [--export DIR] [--object F] [--telescope F] [--site F] [--set KEY=VALUE ...]
        build or update output/rig.json from the export's manifest.json, the FITS headers and the
        Nebulis JSON files (nebulis.py --json object|telescopes|site); --set fills or corrects a field
        (dotted path, e.g. capture_location.elevation_m=750, filters.D1="Askar D1, Ha + OIII, 6 nm").
        Prints what is still missing. Exit 0 when rig.json is valid, 2 when fields are missing.
  validate FILE                   check a rig.json against reference/rig.schema.json
  project WS                      write output/project.json (needs rig.json; uses research.json, report.json)
  doc WS                          write output/doc/index.html
  report WS                       write output/doc/session-report.html (needs report.json)
  astrobin WS                     write output/astrobin.json
  icons WS [--log FILE ...]       read the pixinsight-connector call logs and write agentic/work/icons.json and
                                  agentic/work/icons.js, the PJSR to run with run_pjsr
  xpsm WS --pjsr-result FILE      wrap what icons.js returned into the .xpsm file

Exit codes: 0 ok, 1 usage error, 2 incomplete or invalid data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCHEMA = SKILL / "reference" / "rig.schema.json"
VERSION = "0.2.0"
FITS_EXT = (".fit", ".fits", ".fts")


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


# ─── FITS headers (primary HDU only, no pixel data read) ─────────────────────

def read_fits_header(path: Path) -> dict:
    cards: dict = {}
    with open(path, "rb") as fh:
        while True:
            block = fh.read(2880)
            if len(block) < 2880:
                break
            for i in range(0, 2880, 80):
                card = block[i:i + 80].decode("ascii", "replace")
                key = card[:8].strip()
                if key == "END":
                    return cards
                if card[8:10] != "= " or not key:
                    continue
                cards.setdefault(key, parse_fits_value(card[10:]))
    return cards


def parse_fits_value(raw: str):
    raw = raw.strip()
    if raw.startswith("'"):
        out, i = [], 1
        while i < len(raw):
            if raw[i] == "'":
                if i + 1 < len(raw) and raw[i + 1] == "'":
                    out.append("'"); i += 2; continue
                break
            out.append(raw[i]); i += 1
        return "".join(out).rstrip()
    value = raw.split("/", 1)[0].strip()
    if value in ("T", "F"):
        return value == "T"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value or None


def fnum(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except ValueError:
        return sexagesimal(str(v))


def sexagesimal(s: str):
    """'+45 30 00' or '45:30:00' -> 45.5; None when it is not a number."""
    m = re.match(r"^\s*([+-]?)(\d+)[\s:dh°]+(\d+)[\s:m']+(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    v = int(m.group(2)) + int(m.group(3)) / 60 + float(m.group(4)) / 3600
    return -v if m.group(1) == "-" else v


def fmt_ra(deg: float) -> str:
    h = (deg / 15) % 24
    hh, rem = int(h), (h - int(h)) * 60
    mm, ss = int(rem), (rem - int(rem)) * 60
    return f"{hh:02d}h {mm:02d}m {ss:04.1f}s"


def fmt_dec(deg: float) -> str:
    sign = "-" if deg < 0 else "+"
    d = abs(deg)
    dd, rem = int(d), (d - int(d)) * 60
    mm, ss = int(rem), (rem - int(rem)) * 60
    return f"{sign}{dd:02d}° {mm:02d}′ {ss:02.0f}″"


# ─── workspace ──────────────────────────────────────────────────────────────

class Workspace:
    def __init__(self, root: str):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            die(f"workspace {self.root} does not exist")
        self.output = self.root / "output"
        self.work = self.root / "agentic" / "work"

    def out(self, name: str) -> Path:
        return self.output / name

    def load(self, name: str, required: bool = False):
        p = self.out(name)
        if not p.is_file():
            if required:
                die(f"{p} not found", 2)
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            die(f"{p} is not valid JSON: {e}", 2)

    def save(self, name: str, data, minified: bool = False) -> Path:
        p = self.out(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) if minified else json.dumps(data, ensure_ascii=False, indent=2)
        p.write_text(text + "\n", encoding="utf-8")
        return p

    def exports(self) -> list[Path]:
        data = self.root / "data"
        return sorted((m.parent for m in data.glob("*/manifest.json")), key=lambda p: p.stat().st_mtime) if data.is_dir() else []


# ─── scan ───────────────────────────────────────────────────────────────────

def files_under(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in FITS_EXT and p.is_file()) if folder.is_dir() else []


def most_common(values):
    vals = [v for v in values if v is not None]
    return Counter(vals).most_common(1)[0][0] if vals else None


def as_int(v):
    return int(round(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def scan_export(export: Path) -> tuple[dict, dict]:
    """Returns (sequences+nights, header facts) from manifest.json and the FITS headers of the lights."""
    manifest = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    groups = manifest.get("groups") or []
    lights = files_under(export / "Lights")
    headers = []
    for p in lights:
        try:
            headers.append(read_fits_header(p))
        except OSError:
            continue

    # nights: one row per manifest group, counts checked against the files on disk
    on_disk = Counter()
    for p in lights:
        parts = p.relative_to(export / "Lights").parts
        if len(parts) >= 3:
            on_disk[(parts[0].removeprefix("NIGHT_"), parts[1].removeprefix("FILTER_"))] += 1
    nights, warnings = [], []
    for g in groups:
        filt = g.get("filter") or "none"
        kept = int(g.get("kept") or 0)
        found = on_disk.get((g.get("night"), re.sub(r"[^\w.-]", "_", filt)), None)
        if found is not None and found != kept and not manifest.get("includeNotKept"):
            warnings.append(f"{g.get('night')} {filt}: manifest says {kept} kept, {found} files in Lights/")
        nights.append({
            "date": g.get("night"), "filter": filt, "exposure_s": g.get("exposureSec"), "gain": as_int(g.get("gain")),
            "bin": as_int(g.get("binning")), "temp_c": g.get("sensorTempC"), "subs": kept, "subs_total": int(g.get("frames") or kept),
            "darks": (g.get("dark") or {}).get("fileCount"), "flats": (g.get("flat") or {}).get("fileCount"),
            "biases": (g.get("bias") or {}).get("fileCount"), "flat_darks": (g.get("flatDark") or {}).get("fileCount"),
        })

    agg: dict = {}
    for n in nights:
        k = (n["filter"], n["exposure_s"], n["gain"], n["bin"])
        a = agg.setdefault(k, {"filter": n["filter"], "exposure_s": n["exposure_s"], "gain": n["gain"], "bin": n["bin"] or 1,
                               "subs": 0, "subs_total": 0, "temps": [], "dates": set()})
        a["subs"] += n["subs"]; a["subs_total"] += n["subs_total"]
        a["temps"].append(n["temp_c"]); a["dates"].add(n["date"])
    seq_lights = [{"filter": a["filter"], "exposure_s": a["exposure_s"], "gain": a["gain"], "bin": a["bin"], "subs": a["subs"],
                   "subs_total": a["subs_total"], "temp_c": most_common(a["temps"]), "dates": sorted(a["dates"])}
                  for a in sorted(agg.values(), key=lambda a: (a["filter"], a["exposure_s"] or 0))]

    def calib(kind: str, with_filter: bool):
        seen: dict = {}
        for g in groups:
            c = g.get(kind)
            if not c:
                continue
            key = (c.get("name"), g.get("night") if with_filter else None)
            if key in seen:
                continue
            date = (c.get("capturedAt") or "")[:10] or (g.get("night") if with_filter else None)
            seen[key] = {"name": c.get("name"), "filter": c.get("filter"), "exposure_s": c.get("exposureSec"),
                         "gain": as_int(c.get("gain")), "bin": as_int(c.get("binning")), "temp_c": c.get("sensorTempC"),
                         "subs": int(c.get("fileCount") or 0), "source": c.get("source") or "matched",
                         "dates": [date] if date else []}
        # flats of one set used on several nights: merge the dates
        merged: dict = {}
        for (name, _), v in seen.items():
            if name in merged:
                merged[name]["dates"] = sorted(set(merged[name]["dates"]) | set(v["dates"]))
            else:
                merged[name] = v
        return list(merged.values())

    seqs = {"lights": seq_lights, "darks": calib("dark", False), "flats": calib("flat", True),
            "biases": calib("bias", False), "flat_darks": calib("flatDark", True)}

    h0 = headers[0] if headers else {}
    facts = {
        "object": h0.get("OBJECT"),
        "telescope": h0.get("TELESCOP"),
        "camera": h0.get("INSTRUME"),
        "focal_length": most_common(fnum(h.get("FOCALLEN")) for h in headers),
        "pixel_size": most_common(fnum(h.get("XPIXSZ")) for h in headers),
        "width": h0.get("NAXIS1"), "height": h0.get("NAXIS2"),
        "bayer": h0.get("BAYERPAT"),
        "ra": header_ra(h0),
        "dec": header_dec(h0),
        "site_lat": fnum(h0.get("SITELAT")), "site_long": fnum(h0.get("SITELONG")),
        "site_elev": fnum(h0.get("SITEELEV")),
        "set_temp": most_common(fnum(h.get("SET-TEMP")) for h in headers) if any("SET-TEMP" in h for h in headers)
        else most_common(round(fnum(h.get("CCD-TEMP")), 0) for h in headers if fnum(h.get("CCD-TEMP")) is not None),
        "binning": most_common(as_int(h.get("XBINNING")) for h in headers),
        "lights_read": len(headers),
    }
    return {"sequences": seqs, "nights": nights, "warnings": warnings, "nights_list": manifest.get("nights") or []}, facts


def header_ra(h: dict):
    """RA in degrees: numeric RA (degrees, as ASIAIR and NINA write it) or OBJCTRA in hours."""
    if isinstance(h.get("RA"), (int, float)) and not isinstance(h.get("RA"), bool):
        return float(h["RA"])
    v = sexagesimal(str(h.get("OBJCTRA") or ""))
    return v * 15 if v is not None else None


def header_dec(h: dict):
    if isinstance(h.get("DEC"), (int, float)) and not isinstance(h.get("DEC"), bool):
        return float(h["DEC"])
    return sexagesimal(str(h.get("OBJCTDEC") or ""))


def set_path(d: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def get_path(d: dict, dotted: str):
    for k in dotted.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def coerce(text: str):
    t = text.strip()
    if t.lower() in ("null", "none", ""):
        return None
    if t.lower() in ("true", "false"):
        return t.lower() == "true"
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        return t


def load_json_arg(path: str | None):
    if not path:
        return None
    try:
        return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die(f"cannot read {path}: {e}")


def cmd_scan(args) -> int:
    ws = Workspace(args.workspace)
    exports = [Path(args.export).expanduser().resolve()] if args.export else ws.exports()
    if not exports:
        die(f"no Nebulis export with a manifest.json under {ws.root / 'data'}; run nebulis.py fetch first", 2)
    export = exports[-1]
    if len(exports) > 1 and not args.export:
        print(f"note: {len(exports)} exports in data/, using the newest: {export.name} (choose with --export)")
    scanned, f = scan_export(export)
    obj = load_json_arg(args.object) or {}
    tels = load_json_arg(args.telescope)
    site = load_json_arg(args.site) or {}
    tel = None
    if isinstance(tels, list) and tels:
        tel = next((t for t in tels if t.get("model") and f.get("telescope") and t["model"].lower() in str(f["telescope"]).lower()), None)
        tel = tel or next((t for t in tels if obj.get("primaryTelescopeId") == t.get("id")), None) or (tels[0] if len(tels) == 1 else None)
        if tel is None:
            print("note: several Nebulis telescope profiles and none matches the headers; pass the right one with --set telescope.model=...")
    elif isinstance(tels, dict):
        tel = tels
    oc = None
    if tel:
        ocs = tel.get("opticalConfigs") or []
        oc = next((o for o in ocs if o.get("id") == tel.get("activeOpticalConfigId")), None) or (ocs[0] if ocs else None)
        if f.get("focal_length") and ocs:
            oc = min(ocs, key=lambda o: abs((o.get("focalLengthMm") or 0) - f["focal_length"]))

    rig = ws.load("rig.json") or {}
    prov = rig.get("provenance", {})

    def put(path: str, value, source: str):
        if value in (None, "", []):
            return
        if get_path(rig, path) not in (None, "", []) and prov.get(path) == "user":
            return  # never override what the user set
        set_path(rig, path, value)
        prov[path] = source

    # target
    put("target.name", obj.get("id") or f.get("object") or ws.root.name, "nebulis-object" if obj.get("id") else "fits")
    nick = (obj.get("nicknames") or [None])[0]
    put("target.common_name", nick, "nebulis-object")
    put("target.aliases", [a for a in (obj.get("aliases") or []) if a], "nebulis-object")
    put("target.object_type", obj.get("type"), "nebulis-object")
    put("target.constellation", obj.get("constellation"), "nebulis-object")
    if obj.get("ra") and obj.get("dec"):
        put("target.coordinates_j2000", {"ra": obj["ra"], "dec": obj["dec"]}, "nebulis-object")
    elif f.get("ra") is not None and f.get("dec") is not None:
        put("target.coordinates_j2000", {"ra": fmt_ra(f["ra"]), "dec": fmt_dec(f["dec"])}, "fits")
    # site: headers for where it was shot, Nebulis for its name and sky
    put("capture_location.site", site.get("name"), "nebulis-site")
    put("capture_location.latitude", round(f["site_lat"], 4) if f.get("site_lat") is not None else None, "fits")
    put("capture_location.longitude", round(f["site_long"], 4) if f.get("site_long") is not None else None, "fits")
    if get_path(rig, "capture_location.latitude") is None:
        put("capture_location.latitude", site.get("latitude"), "nebulis-site")
        put("capture_location.longitude", site.get("longitude"), "nebulis-site")
    put("capture_location.elevation_m", f.get("site_elev"), "fits")
    put("capture_location.bortle", site.get("bortleClass"), "nebulis-site")
    # optics and camera
    put("telescope.model", (tel or {}).get("model") or f.get("telescope"), "nebulis-telescope" if tel else "fits")
    put("telescope.focal_length_mm", f.get("focal_length") or (oc or {}).get("focalLengthMm"), "fits" if f.get("focal_length") else "nebulis-telescope")
    put("camera.model", f.get("camera"), "fits")
    put("camera.pixel_size_um", f.get("pixel_size") or (oc or {}).get("pixelSizeUm"), "fits" if f.get("pixel_size") else "nebulis-telescope")
    if f.get("width") and f.get("height"):
        put("camera.resolution_px", f"{f['width']}x{f['height']}", "fits")
    put("camera.bayer_pattern", f.get("bayer"), "fits")
    sensor_type = (tel or {}).get("rig", {}).get("sensorType") or ("color" if f.get("bayer") else None)
    put("camera.sensor_type", sensor_type, "nebulis-telescope" if (tel or {}).get("rig", {}).get("sensorType") else "fits")
    put("tec_setpoint_c", f.get("set_temp"), "fits")
    put("binning", f.get("binning") or 1, "fits")
    # filters: keep descriptions already given
    filters = dict(rig.get("filters") or {})
    for s in scanned["sequences"]["lights"]:
        filters.setdefault(s["filter"], "")
    rig["filters"] = filters
    rig["sequences"] = scanned["sequences"]
    rig["nights"] = scanned["nights"]
    prov["sequences"] = prov["nights"] = "manifest"

    for item in args.set or []:
        if "=" not in item:
            die(f"--set expects KEY=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        set_path(rig, k.strip(), coerce(v))
        prov[k.strip()] = "user"

    # computed
    fl, ap, px = get_path(rig, "telescope.focal_length_mm"), get_path(rig, "telescope.aperture_mm"), get_path(rig, "camera.pixel_size_um")
    if fl and ap and not get_path(rig, "telescope.focal_ratio"):
        set_path(rig, "telescope.focal_ratio", round(fl / ap, 2)); prov["telescope.focal_ratio"] = "computed"
    if fl and px:
        set_path(rig, "telescope.image_scale_arcsec_px", round(206.265 * px / fl, 3)); prov["telescope.image_scale_arcsec_px"] = "computed"
    rig["provenance"] = dict(sorted(prov.items()))
    order = ["target", "capture_location", "telescope", "camera", "mount", "filters", "tec_setpoint_c", "binning",
             "sequences", "nights", "provenance"]
    rig = {k: rig[k] for k in order if k in rig} | {k: v for k, v in rig.items() if k not in order}
    path = ws.save("rig.json", rig)

    total = sum(s["subs"] * (s["exposure_s"] or 0) for s in rig["sequences"]["lights"])
    print(f"rig.json: {path}")
    print(f"export {export.name} · {f['lights_read']} light headers read · {len(rig['nights'])} night/filter groups · "
          f"{sum(s['subs'] for s in rig['sequences']['lights'])} subs kept · {total / 3600:.1f} h")
    for s in rig["sequences"]["lights"]:
        print(f"  {s['filter']:<8} {s['subs']:>4} × {s['exposure_s']} s  gain {s['gain']}  bin {s['bin']}  "
              f"{len(s['dates'])} night(s)  {s['subs'] * (s['exposure_s'] or 0) / 3600:.1f} h")
    for w in scanned["warnings"]:
        print(f"warning: {w}")
    missing = schema_errors(rig)
    empty_filters = [k for k, v in rig["filters"].items() if not v]
    advisory = [p for p in ("target.common_name", "telescope.aperture_mm", "camera.sensor", "capture_location.elevation_m")
                if get_path(rig, p) in (None, "")]
    if empty_filters:
        advisory.append("filters." + ", filters.".join(empty_filters) + " (vendor, model, passbands)")
    if missing:
        print("missing (required):")
        for m in missing:
            print(f"  - {m}")
    if advisory:
        print("missing (recommended): " + "; ".join(advisory))
    if missing:
        print("fill with: astro_project.py scan WS --set KEY=VALUE ...")
        return 2
    print("rig.json OK")
    return 0


# ─── a small JSON Schema validator (the draft-07 subset rig.schema.json uses) ─

def schema_errors(data, schema: dict | None = None, root: dict | None = None, path: str = "") -> list[str]:
    if schema is None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    root = root or schema
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[1:]
        target = root
        for k in ref:
            target = target[k]
        return schema_errors(data, target, root, path)
    errs: list[str] = []
    where = path or "(root)"
    types = schema.get("type")
    if types:
        tl = types if isinstance(types, list) else [types]
        ok = any(_is_type(data, t) for t in tl)
        if not ok:
            return [f"{where}: expected {'/'.join(tl)}, got {json.dumps(data, ensure_ascii=False)[:60] if data is not None else 'nothing'}"]
    if data is None:
        return errs
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{where}: must be one of {schema['enum']}")
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errs.append(f"{where}: must be ≥ {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errs.append(f"{where}: must be ≤ {schema['maximum']}")
        if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
            errs.append(f"{where}: must be > {schema['exclusiveMinimum']}")
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errs.append(f"{where}: must not be empty")
        if "pattern" in schema and not re.search(schema["pattern"], data):
            errs.append(f"{where}: {data!r} does not match {schema['pattern']}")
    if isinstance(data, dict):
        for k in schema.get("required", []):
            if data.get(k) is None:
                errs.append(f"{(path + '.' if path else '')}{k}: required")
        if "minProperties" in schema and len(data) < schema["minProperties"]:
            errs.append(f"{where}: needs at least {schema['minProperties']} entr{'y' if schema['minProperties'] == 1 else 'ies'}")
        props = schema.get("properties", {})
        for k, v in data.items():
            sub = props.get(k, schema.get("additionalProperties") if isinstance(schema.get("additionalProperties"), dict) else None)
            if sub is not None:
                errs += schema_errors(v, sub, root, f"{path}.{k}" if path else k)
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errs.append(f"{where}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for i, v in enumerate(data):
                errs += schema_errors(v, schema["items"], root, f"{path}[{i}]")
    return errs


def _is_type(v, t: str) -> bool:
    return {"object": isinstance(v, dict), "array": isinstance(v, list), "string": isinstance(v, str),
            "integer": isinstance(v, int) and not isinstance(v, bool),
            "number": isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": isinstance(v, bool), "null": v is None}.get(t, True)


def cmd_validate(args) -> int:
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die(f"cannot read {args.file}: {e}", 2)
    errs = schema_errors(data)
    for e in errs:
        print(f"  - {e}")
    print("rig.json OK" if not errs else f"{len(errs)} problem(s)")
    return 0 if not errs else 2


# ─── shared derived values ──────────────────────────────────────────────────

def hours(seconds: float) -> str:
    h, m = int(seconds // 3600), int(round(seconds % 3600 / 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h} h {m:02d} min" if h else f"{m} min"


def campaign(rig: dict, research: dict | None, report: dict | None) -> dict:
    """Everything the project, doc, report and astrobin outputs share."""
    research = research or {}
    report = report or {}
    t = rig["target"]
    lights = rig["sequences"]["lights"]
    total_s = sum(s["subs"] * (s["exposure_s"] or 0) for s in lights)
    dates = sorted({d for s in lights for d in s.get("dates", [])})
    filters_desc = [f"{k}: {v}" if v else k for k, v in rig["filters"].items()]
    scope = rig["telescope"]
    tel = scope["model"] + (f" ({scope['aperture_mm']:g} mm, {scope['focal_length_mm']:g} mm"
                            + (f" f/{scope['focal_ratio']:g}" if scope.get("focal_ratio") else "") + ")"
                            if scope.get("aperture_mm") else f" ({scope['focal_length_mm']:g} mm)")
    cam = rig["camera"]["model"] + (f" ({rig['camera']['sensor']})" if rig["camera"].get("sensor") else "")
    loc = rig["capture_location"]
    lat, lon = loc["latitude"], loc["longitude"]
    coords = f"{abs(lat):.2f}°{'N' if lat >= 0 else 'S'} {abs(lon):.2f}°{'E' if lon >= 0 else 'W'}"
    if loc.get("elevation_m") is not None:
        coords += f" · {loc['elevation_m']:g} m"
    coords += f" · Bortle {loc['bortle']}"
    calib = rig["sequences"]
    calib_parts = [label for key, label in (("darks", "darks"), ("flats", "flats"), ("flat_darks", "flat-darks"), ("biases", "bias"))
                   if calib.get(key)]
    return {
        "id": t["name"], "common_name": research.get("common_name") or t.get("common_name") or "",
        "constellation": research.get("constellation") or t.get("constellation") or "",
        "object_type": research.get("object_type") or t.get("object_type") or "",
        "ra": t["coordinates_j2000"]["ra"], "dec": t["coordinates_j2000"]["dec"],
        "telescope": tel, "camera": cam, "filters": filters_desc, "site": loc["site"], "site_coords": coords,
        "total_s": total_s, "total": hours(total_s), "dates": dates, "nights": len(dates),
        "subs_kept": sum(s["subs"] for s in lights), "subs_total": sum(s.get("subs_total", s["subs"]) for s in lights),
        "calibration": " / ".join(calib_parts).capitalize() if calib_parts else "none",
        "palette": report.get("palette") or "", "path": report.get("path") or "",
        "date": report.get("date") or dt.date.today().isoformat(),
    }


def per_filter_lines(rig: dict) -> list[str]:
    return [f"{s['filter']}: {s['subs']} × {s['exposure_s']:g} s, gain {s['gain']}, bin {s['bin']} = {hours(s['subs'] * s['exposure_s'])}"
            f" ({len(s.get('dates', []))} night{'s' if len(s.get('dates', [])) != 1 else ''})" for s in rig["sequences"]["lights"]]


# ─── project.json ───────────────────────────────────────────────────────────

def cmd_project(args) -> int:
    ws = Workspace(args.workspace)
    rig = ws.load("rig.json", required=True)
    errs = schema_errors(rig)
    if errs:
        die("rig.json is incomplete; run scan first:\n  " + "\n  ".join(errs), 2)
    research, report = ws.load("research.json"), ws.load("report.json")
    c = campaign(rig, research, report)
    title = f"{c['id']}" + (f" · {c['common_name']}" if c["common_name"] else "")
    lines = [title]
    if c["object_type"] or c["constellation"]:
        lines.append(" · ".join(x for x in (c["object_type"], c["constellation"]) if x))
    lines += [f"RA {c['ra']} · Dec {c['dec']}", "",
              f"Telescope: {c['telescope']}", f"Camera: {c['camera']}", f"Filters: {'; '.join(c['filters'])}",
              f"Site: {c['site']} ({c['site_coords']})", "",
              f"Integration: {c['total']} from {c['subs_kept']} subs kept of {c['subs_total']}, {c['nights']} night(s), "
              f"{c['dates'][0]} to {c['dates'][-1]}" if c["dates"] else f"Integration: {c['total']}"]
    lines += [f"  {x}" for x in per_filter_lines(rig)]
    lines += [f"Calibration: {c['calibration']}", "Stacking: WBPP (PixInsight), one master per filter set"]
    if c["palette"]:
        lines.append(f"Palette: {c['palette']}")
    if (research or {}).get("summary"):
        lines += ["", research["summary"]]
    lines += ["", f"Documentation: doc/index.html · Processing log: PROCESSING.md · astroagent {VERSION}"]
    project = {
        "target": c["id"], "common_name": c["common_name"], "constellation": c["constellation"],
        "ra": c["ra"], "dec": c["dec"], "object_type": c["object_type"], "telescope": c["telescope"], "camera": c["camera"],
        "filter": "; ".join(c["filters"]), "site": c["site"], "site_coords": c["site_coords"],
        "session_count": c["nights"], "sessions": per_filter_lines(rig), "stacking": "WBPP (PixInsight)",
        "calibration": c["calibration"], "subs_integrated": f"{c['subs_kept']} / {c['subs_total']}",
        "total_exposure": c["total"], "palette": c["palette"], "ref_alignment": "", "ref_integration": "",
        "notes": (report or {}).get("notes", ""), "description": "\n".join(lines),
    }
    p = ws.save("project.json", project, minified=True)
    print(f"project.json: {p}")
    print("PixInsight project: paste the `description` value into the Description field,"
          " and set the Documentation field to output/doc/index.html")
    return 0


# ─── astrobin.json ──────────────────────────────────────────────────────────

BAND_RE = [("Ha", r"h\s*-?\s*(?:alpha|α|a)\b|hα"), ("OIII", r"o\s*-?\s*iii|o3\b"), ("SII", r"s\s*-?\s*ii\b|s2\b"),
           ("L", r"\blum(?:inance)?\b|^l$"), ("R", r"\bred\b|^r$"), ("G", r"\bgreen\b|^g$"), ("B", r"\bblue\b|^b$")]


def bands(name: str, desc: str) -> list[str]:
    text = f"{name} {desc}".lower()
    found = [b for b, rx in BAND_RE if re.search(rx, text)]
    return found


def subject_type(object_type: str) -> str:
    t = object_type.lower()
    for keys, value in ((("planetary",), "PLANETARY_NEBULA"), (("supernova", "snr"), "SUPERNOVA_REMNANT"),
                        (("globular",), "GLOBULAR_CLUSTER"), (("cluster",), "OPEN_CLUSTER"), (("galax",), "GALAXY"),
                        (("nebula", "hii", "h ii", "emission", "reflection", "dark"), "NEBULA")):
        if any(k in t for k in keys):
            return value
    return "OTHER"


def cmd_astrobin(args) -> int:
    ws = Workspace(args.workspace)
    rig = ws.load("rig.json", required=True)
    research, report = ws.load("research.json") or {}, ws.load("report.json") or {}
    c = campaign(rig, research, report)
    scope = rig["telescope"]
    filters = []
    for name, desc in rig["filters"].items():
        bw = re.search(r"(\d+(?:\.\d+)?)\s*nm", desc or "")
        b = bands(name, desc or "")
        filters.append({"name": name, "description": desc, "bands": b or ["broadband"],
                        "type": b[0] if len(b) == 1 else ("DUAL_BAND" if len(b) == 2 else ("TRI_BAND" if len(b) == 3 else "OTHER")),
                        "bandwidth_nm": float(bw.group(1)) if bw else None})
    software = [{"name": "PixInsight", "version": (report.get("environment") or {}).get("PixInsight", "")},
                {"name": "Nebulis", "version": (report.get("environment") or {}).get("Nebulis", "")},
                {"name": "astroagent", "version": VERSION}]
    details = [{"date": n["date"], "filter": n["filter"], "number": n["subs"], "duration": n["exposure_s"],
                "binning": n.get("bin") or 1, "gain": n.get("gain"), "sensor_cooling": n.get("temp_c"),
                "darks": n.get("darks"), "flats": n.get("flats"), "flat_darks": n.get("flat_darks"), "bias": n.get("biases"),
                "bortle": rig["capture_location"]["bortle"], "mean_sqm": None, "mean_fwhm": None, "temperature": None}
               for n in rig.get("nights", []) if n["subs"]]
    title = f"{c['common_name']} ({c['id']})" if c["common_name"] else c["id"]
    desc = research.get("summary") or ""
    acq = (f"{c['total']} in {c['nights']} night(s) with {scope['model']} and {rig['camera']['model']}"
           f" through {', '.join(rig['filters'])}" + (f"; {c['palette']} palette" if c["palette"] else "") + ".")
    out = {
        "title": title, "description": (desc + "\n\n" + acq).strip(), "link": "", "image_file": "",
        "subject_type": subject_type(c["object_type"]), "data_source": "BACKYARD", "remote_source": "",
        "imaging_telescopes": [{"name": scope["model"], "aperture": scope.get("aperture_mm"), "focal_length": scope["focal_length_mm"],
                                "type": "REFRACTOR" if re.search(r"apo|refractor|askar|\bed\b|triplet|doublet", scope["model"], re.I) else "OTHER"}],
        "imaging_cameras": [{"name": rig["camera"]["model"], "type": "CMOS", "color": rig["camera"].get("sensor_type") == "color",
                             "cooled": rig.get("tec_setpoint_c") is not None}],
        "mounts": [{"name": rig["mount"]}] if rig.get("mount") else [],
        "filters": filters, "software": software,
        "location": {"name": rig["capture_location"]["site"], "latitude": rig["capture_location"]["latitude"],
                     "longitude": rig["capture_location"]["longitude"], "altitude": rig["capture_location"].get("elevation_m")},
        "first_acquisition_date": c["dates"][0] if c["dates"] else None,
        "last_acquisition_date": c["dates"][-1] if c["dates"] else None,
        "acquisition_details": details,
        "keywords": [k for k in [c["id"], c["common_name"], *(research.get("catalog_ids") or []), c["constellation"],
                                 c["palette"], "narrowband" if c["path"] == "narrowband" else ""] if k],
    }
    p = ws.save("astrobin.json", out)
    print(f"astrobin.json: {p} · {len(details)} acquisition row(s), one per night and filter")
    return 0


# ─── process icons from the pixinsight-connector call logs ───────────────────

# Processes worth an icon: what a person would re-run by hand. Helper instances the connector creates for
# measuring, masks or plumbing (Gaia, ChannelExtraction for a preview, Convolution for a mask...) are left out.
ICON_PROCESSES = {
    "BlurXTerminator", "NoiseXTerminator", "StarXTerminator", "GradientCorrection", "MultiscaleGradientCorrection",
    "SpectrophotometricColorCalibration", "SpectrophotometricFluxCalibration", "AutomaticBackgroundExtractor",
    "DynamicBackgroundExtraction", "BackgroundNeutralization", "ColorCalibration", "PixelMath", "CurvesTransformation",
    "HistogramTransformation", "GeneralizedHyperbolicStretch", "LocalHistogramEqualization", "HDRMultiscaleTransform",
    "UnsharpMask", "SCNR", "ColorSaturation", "ChannelCombination", "LRGBCombination", "LinearFit", "MorphologicalTransformation",
    "MultiscaleLinearTransform", "MultiscaleMedianTransform", "ICCProfileTransformation", "Resample", "Crop", "DynamicCrop",
    "ArcsinhStretch", "ExponentialTransformation", "StarAlignment",
}
SKIP_TOOLS = re.compile(r"^(get_|list_|measure|preview|save_preview|scan_|inspect|describe|find_|verify|workspace|pixinsight_info|"
                        r"wbpp_status|compare|set_workspace|resume_bridge|close|open_image|rename|clone_image|restore)")
LITERAL = re.compile(r"""^(?:-?\d+(?:\.\d+)?(?:e-?\d+)?|true|false|null|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|
                     [A-Z][A-Za-z0-9]*\.[A-Za-z_][A-Za-z0-9_]*|\[[\s\S]*\])$""", re.X)


def split_statements(code: str) -> list[str]:
    """Split PJSR into top-level statements on ; outside strings, brackets and parentheses."""
    out, buf, depth, quote, i = [], [], 0, None, 0
    while i < len(code):
        ch = code[i]
        buf.append(ch)
        if quote:
            if ch == "\\":
                buf.append(code[i + 1] if i + 1 < len(code) else ""); i += 2; continue
            if ch == quote:
                quote = None
        elif ch in "\"'`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch in ";\n" and depth <= 0:
            s = "".join(buf).strip().rstrip(";").strip()
            if s:
                out.append(s)
            buf, depth = [], max(depth, 0)
        i += 1
    s = "".join(buf).strip().rstrip(";").strip()
    if s:
        out.append(s)
    return out


def instances_in(code: str) -> list[dict]:
    found = []
    stmts = split_statements(code)
    for idx, st in enumerate(stmts):
        m = re.match(r"^(?:var|let|const)\s+([A-Za-z_]\w*)\s*=\s*new\s+([A-Z]\w*)\s*(?:\(\s*\))?$", st)
        if not m or m.group(2) not in ICON_PROCESSES:
            continue
        var, cls = m.groups()
        params, dropped, executed, target = [], [], False, None
        for st2 in stmts[idx + 1:]:
            if re.match(rf"^(?:var|let|const)\s+{var}\s*=", st2):
                break
            a = re.match(rf"^{var}\.([A-Za-z_]\w*)\s*=\s*([\s\S]+)$", st2)
            if a:
                (params if LITERAL.match(a.group(2).strip()) else dropped).append((a.group(1), a.group(2).strip()))
                continue
            e = re.search(rf"\b{var}\.execute(?:On|Global)\s*\(\s*([^)]*)\)|\b__run\s*\(\s*{var}\s*(?:,\s*([^)]*))?\)", st2)
            if e:
                executed, target = True, (e.group(1) or e.group(2) or "").strip()
                break
        if executed and not (cls == "PixelMath" and any(k.startswith("expression") for k, _ in dropped)):
            found.append({"class": cls, "params": params, "dropped": [k for k, _ in dropped], "target": target})
    return found


def cmd_icons(args) -> int:
    ws = Workspace(args.workspace)
    logs = [Path(p) for p in args.log] if args.log else sorted((ws.root / "agentic").rglob("*.jsonl"))
    if not logs:
        die(f"no pixinsight-connector call log (*.jsonl) under {ws.root / 'agentic'}; pass --log FILE", 2)
    calls: dict = {}
    for log in logs:
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            key = (log.name, r.get("seq"))
            if r.get("type") == "call_start":
                calls[key] = {"tool": r.get("tool"), "input": r.get("input") or {}, "codes": [], "ok": True, "ts": r.get("ts")}
            elif r.get("type") == "bridge" and key in calls and isinstance(r.get("code"), str):
                calls[key]["codes"].append(r["code"])
            elif r.get("type") == "call_end" and key in calls:
                res = r.get("result") or {}
                text = json.dumps(res)[:4000]
                calls[key]["ok"] = not (r.get("error") or res.get("isError") or re.search(r"FAILED|REFUSED|BLOCKED|STOPPED BY USER", text))
    icons, skipped = [], []
    for (logname, seq), c in sorted(calls.items(), key=lambda kv: (kv[1].get("ts") or "", kv[0][1] or 0)):
        if not c["ok"] or not c["tool"] or SKIP_TOOLS.match(c["tool"]):
            continue
        view = c["input"].get("view_id") or c["input"].get("target") or c["input"].get("id") or ""
        for code in c["codes"]:
            for inst in instances_in(code):
                base = re.sub(r"\W+", "_", f"{inst['class']}_{view}" if view else inst["class"]).strip("_")
                icons.append({"seq": seq, "tool": c["tool"], "view": view, **inst, "base": base})
                if inst["dropped"]:
                    skipped.append(f"#{seq} {inst['class']}: {', '.join(inst['dropped'])} (computed in PixInsight, defaults kept)")
    if not icons:
        die("no processing call with a process instance found in the logs", 2)
    # unique ids, numbered in order: s01_BlurXTerminator_Ha
    used = Counter()
    for i, ic in enumerate(icons, 1):
        name = f"s{i:02d}_{ic['base']}"[:60]
        used[name] += 1
        ic["id"] = name if used[name] == 1 else f"{name}_{used[name]}"
    ws.work.mkdir(parents=True, exist_ok=True)
    (ws.work / "icons.json").write_text(json.dumps(icons, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    js = ["(function(){", "var out = [];"]
    for ic in icons:
        js.append("try {")
        js.append(f"  var P = new {ic['class']};")
        js += [f"  P.{k} = {v};" for k, v in ic["params"]]
        js.append(f"  out.push({{id: {json.dumps(ic['id'])}, xml: P.toSource(\"XPSM 1.0\", {json.dumps(ic['id'] + '_instance')})}});")
        js.append(f"}} catch (e) {{ out.push({{id: {json.dumps(ic['id'])}, error: String(e && e.message ? e.message : e)}}); }}")
    js += ["return JSON.stringify(out);", "})()"]
    (ws.work / "icons.js").write_text("\n".join(js) + "\n", encoding="utf-8")
    print(f"{len(icons)} process instance(s) from {len(logs)} log file(s):")
    for ic in icons:
        print(f"  {ic['id']:<40} {ic['tool']}  {len(ic['params'])} parameter(s)")
    for s in skipped:
        print(f"  note: {s}")
    print(f"next: run_pjsr with the code of {ws.work / 'icons.js'}, save its result to {ws.work / 'icons-result.json'},"
          f" then: astro_project.py xpsm {ws.root} --pjsr-result {ws.work / 'icons-result.json'}")
    return 0


def cmd_xpsm(args) -> int:
    ws = Workspace(args.workspace)
    icons = json.loads((ws.work / "icons.json").read_text(encoding="utf-8"))
    raw = Path(args.pjsr_result).read_text(encoding="utf-8").strip()
    try:
        result = json.loads(raw)
        if isinstance(result, str):
            result = json.loads(result)
    except ValueError:
        die("the PJSR result is not the JSON array icons.js returns", 2)
    by_id = {r["id"]: r for r in result}
    rig, report, research = ws.load("rig.json") or {}, ws.load("report.json") or {}, ws.load("research.json") or {}
    errors, blocks, icon_rows = [], [], []
    y = 40
    for ic in icons:
        r = by_id.get(ic["id"], {})
        xml = r.get("xml") or ""
        m = re.search(r"<instance\b[\s\S]*?</instance>", xml)
        if not m:
            errors.append(f"{ic['id']}: {r.get('error') or 'PixInsight returned no <instance> element'}")
            continue
        inst = m.group(0)
        inst = re.sub(r'(<instance\b[^>]*\bid=")[^"]*(")', rf'\g<1>{ic["id"]}_instance\2', inst, count=1)
        if 'id="' not in inst.split(">", 1)[0]:
            inst = inst.replace("<instance ", f'<instance id="{ic["id"]}_instance" ', 1)
        blocks.append("   " + inst.strip())
        icon_rows.append(f'   <icon id="{ic["id"]}" instance="{ic["id"]}_instance" xpos="2000" ypos="{y}" workspace="Workspace01"/>')
        y += 40
    if errors:
        print("not converted:")
        for e in errors:
            print(f"  - {e}")
    if not blocks:
        die("no instance could be serialized; PixInsight's toSource(\"XPSM 1.0\") may be unavailable in this build", 2)
    name = research.get("common_name") or (rig.get("target") or {}).get("common_name") or (rig.get("target") or {}).get("name") or ws.root.name
    palette = report.get("palette") or "processing"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!--", "PixInsight XML Process Serialization Module - XPSM 1.0",
        f"Generated by astroagent {VERSION} on {now} from the pixinsight-connector call log",
        f"Target: {(rig.get('target') or {}).get('name', '')} {name} · {palette}", "-->",
        '<xpsm version="1.0" xmlns="http://www.pixinsight.com/xpsm" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.pixinsight.com/xpsm http://pixinsight.com/xpsm/xpsm-1.0.xsd">',
        *blocks, *icon_rows, "</xpsm>", ""])
    fname = re.sub(r'[\\/:*?"<>|]', "-", f"Process Icons - {name} - {palette} workflow.xpsm")
    p = ws.out(fname)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc, encoding="utf-8")
    print(f"{p.name}: {len(blocks)} icon(s) · {p}")
    print("in PixInsight: Process → Process Icons → Merge Process Icons keeps the icons already on the workspace (Load replaces them)")
    return 0 if not errors else 2


# ─── HTML pages ─────────────────────────────────────────────────────────────

def cmd_doc(args) -> int:
    from pages import render_doc
    ws = Workspace(args.workspace)
    rig = ws.load("rig.json", required=True)
    research, report = ws.load("research.json"), ws.load("report.json")
    if not research:
        print("note: no output/research.json; the page will only show acquisition and processing")
    c = campaign(rig, research, report)
    final = sorted(ws.output.glob("final/*_web.jpg")) or sorted(ws.output.glob("final/*.jpg"))
    image = os.path.relpath(final[-1], ws.output / "doc") if final else None
    html = render_doc(rig, research or {}, report or {}, c, image, (ws.output / "doc" / "session-report.html").exists() or bool(report),
                      VERSION)
    p = ws.out("doc/index.html")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    print(f"doc: {p}")
    return 0


def cmd_report(args) -> int:
    from pages import render_report
    ws = Workspace(args.workspace)
    report = ws.load("report.json", required=True)
    rig = ws.load("rig.json") or {}
    html = render_report(report, rig, VERSION)
    p = ws.out("doc/session-report.html")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    print(f"session report: {p}")
    return 0


# ─── CLI ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    sys.path.insert(0, str(HERE))
    p = argparse.ArgumentParser(prog="astro_project", description="Describe and document a processed campaign (see the module docstring)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("workspace"); s.add_argument("--export"); s.add_argument("--object")
    s.add_argument("--telescope"); s.add_argument("--site"); s.add_argument("--set", nargs="+", metavar="KEY=VALUE")
    s = sub.add_parser("validate"); s.add_argument("file")
    for name in ("project", "doc", "report", "astrobin"):
        sub.add_parser(name).add_argument("workspace")
    s = sub.add_parser("icons"); s.add_argument("workspace"); s.add_argument("--log", nargs="+")
    s = sub.add_parser("xpsm"); s.add_argument("workspace"); s.add_argument("--pjsr-result", required=True)
    args = p.parse_args(argv)
    handlers = {"scan": cmd_scan, "validate": cmd_validate, "project": cmd_project, "doc": cmd_doc, "report": cmd_report,
                "astrobin": cmd_astrobin, "icons": cmd_icons, "xpsm": cmd_xpsm}
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
