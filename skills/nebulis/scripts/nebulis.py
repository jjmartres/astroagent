#!/usr/bin/env python3
"""nebulis.py: a small command-line client for the Nebulis HTTP API, for agents and humans.

Standard library only (Python 3.9+). Every command prints a short human-readable summary;
add --json to get the raw API payload instead.

Configuration: environment variables, which win, or the file ~/.config/astroagent/env (KEY=VALUE lines):
  ASTROAGENT_NEBULIS_URL       Nebulis server base URL, e.g. http://nas.local:3001 (no trailing /api)
  ASTROAGENT_NEBULIS_API_KEY   API key created in Nebulis, Settings -> Account -> API keys -> New key (starts with "neb-")

The key is sent in the X-API-Key header only. It is never printed, never written to disk by this
script, and never put on a command line.

Commands:
  status                                  server version and an authenticated test call
  objects [--search TEXT]                 library objects; the search knows designations and aliases
                                          ("NGC 2264", "Christmas Tree")
  object OBJECT                           one object: type, constellation, coordinates, distance, size
                                          (OBJECT, here and below: id, designation or alias)
  sessions OBJECT                         nights of one object, with filters, exposures, sub counts
  analysis OBJECT DATE [--bad-only]       Frame Analysis report of one night (grades, flags, kept)
  review --keep|--reject|--reset PATH...  record your keep / reject call on frames (admin key)
  plan OBJECT (--dates D [D ...] | --all) [--include-not-kept] [--precalibrated]
                                          stacking plan: lights kept, matched calibration, issues
  fetch OBJECT (--dates D [D ...] | --all) --dest DIR [--layout wbpp|siril] [--include-not-kept]
        [--precalibrated] [--allow-warnings] [--force]
                                          download the stacking export and unpack it under DIR
                                          (--precalibrated: lights already calibrated; sent to the
                                          server, and missing darks, flats or bias are not errors)
  archives OBJECT                         project archives stored with the object
  telescopes                              telescope profiles: model, optical configs, filters
  site                                    the active observing site: coordinates, Bortle class
  push OBJECT (--file FILE | --bundle DIR) [--title T] [--notes N] [--software S]
                                          upload a .zip/.xpsm/.pxiproject (admin key); --bundle
                                          zips a folder first. One archive per processing run.
  images OBJECT                           finished images stored with the object (processed images)
  image OBJECT --file FILE [--title T] [--notes N] [--force]
                                          add a finished image (JPG/PNG/TIFF/XISF/FITS) to the object,
                                          not to a session (admin key); it shows in the object's
                                          Processed images and in the gallery

Exit codes: 0 ok, 1 usage or configuration error, 2 the plan has errors (plan/fetch),
3 API or network error.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path

ENV_FILE = Path.home() / ".config" / "astroagent" / "env"
URL_VAR = "ASTROAGENT_NEBULIS_URL"
KEY_VAR = "ASTROAGENT_NEBULIS_API_KEY"
USER_AGENT = "nebulis-cli/1.0 (astroagent)"


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code, self.message = status, code, message


# ─── configuration ──────────────────────────────────────────────────────────

def load_config() -> tuple[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.is_file():
        mode = ENV_FILE.stat().st_mode & 0o077
        if mode:
            print(f"warning: {ENV_FILE} is readable by other users; run: chmod 600 {ENV_FILE}", file=sys.stderr)
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip().removeprefix("export ").strip()] = v.strip().strip('"').strip("'")
    url = os.environ.get(URL_VAR) or values.get(URL_VAR) or ""
    key = os.environ.get(KEY_VAR) or values.get(KEY_VAR) or ""
    if not url:
        die(f"{URL_VAR} is not set (environment or {ENV_FILE})", 1)
    if not key:
        die(f"{KEY_VAR} is not set (environment or {ENV_FILE})", 1)
    url = url.rstrip("/")
    if url.endswith("/api/v1"):
        url = url[: -len("/api/v1")]
    return url, key


def die(msg: str, code: int) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


# ─── HTTP ───────────────────────────────────────────────────────────────────

class Client:
    def __init__(self, base: str, key: str, timeout: float = 60.0):
        self.base, self.key, self.timeout = base, key, timeout

    def _request(self, method: str, path: str, body: bytes | None = None, ctype: str | None = None,
                 auth: bool = True) -> urllib.request.Request:
        url = path if path.startswith("http") else f"{self.base}{path if path.startswith('/api/') else '/api/v1' + path}"
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("User-Agent", USER_AGENT)
        req.add_header("Accept", "application/json")
        if auth:
            req.add_header("X-API-Key", self.key)
        if ctype:
            req.add_header("Content-Type", ctype)
        return req

    def call(self, method: str, path: str, payload: object | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        req = self._request(method, path, body, "application/json" if body is not None else None)
        return self._send(req)

    def _send(self, req: urllib.request.Request):
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                status = resp.status
        except urllib.error.HTTPError as e:
            raw, status = e.read(), e.code
        except urllib.error.URLError as e:
            raise ApiError(0, "NETWORK", f"cannot reach {self.base}: {e.reason}") from None
        try:
            env = json.loads(raw.decode("utf-8") or "null")
        except ValueError:
            raise ApiError(status, "BAD_RESPONSE", f"non-JSON answer (HTTP {status})") from None
        if isinstance(env, dict) and "ok" in env:
            if env.get("ok"):
                return env.get("data")
            err = env.get("error") or {}
            raise ApiError(status, err.get("code", "ERROR"), err.get("message", "request failed"))
        if status >= 400:
            raise ApiError(status, "HTTP_ERROR", f"HTTP {status}")
        return env

    def download(self, path: str, dest: Path, auth: bool = False) -> int:
        req = self._request("GET", path, auth=auth)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp, open(dest, "wb") as fh:
                total = 0
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
                    total += len(chunk)
                return total
        except urllib.error.HTTPError as e:
            raise ApiError(e.code, "DOWNLOAD_FAILED", f"download answered HTTP {e.code}") from None
        except urllib.error.URLError as e:
            raise ApiError(0, "NETWORK", f"download failed: {e.reason}") from None

    def upload(self, path: str, file_path: Path, fields: dict[str, str], field: str = "archive"):
        boundary = f"----nebulis{uuid.uuid4().hex}"
        parts: list[bytes] = []
        for k, v in fields.items():
            if v:
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        head = (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{file_path.name}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n").encode()
        body = b"".join(parts) + head + file_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = self._request("POST", path, body, f"multipart/form-data; boundary={boundary}")
        return self._send(req)


def q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


# ─── helpers ────────────────────────────────────────────────────────────────

def out(args, data, text: str) -> None:
    print(json.dumps(data, indent=2) if args.json else text)


def fmt_bytes(n: float | None) -> str:
    if not n:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def resolve_dates(c: Client, obj: str, args) -> list[str]:
    if args.dates:
        return args.dates
    sessions = c.call("GET", f"/library/objects/{q(obj)}/sessions") or []
    dates = sorted({s["date"] for s in sessions if s.get("date")})
    if not dates:
        die(f"object {obj} has no sessions", 1)
    return dates


# Plan issues about missing or imperfect calibration frames. Lights that are already calibrated
# (Telescope.live `*_cal.fits`, any service that delivers calibrated subs) raise them on every group,
# and they do not apply: --precalibrated leaves them out of the error and warning counts.
CALIBRATION_ISSUES = {"no_dark", "dark_temp_far", "dark_expired", "no_flat", "flat_other_night",
                      "no_flat_calibration", "bias_expired"}


def counted_issues(plan: dict, precalibrated: bool) -> tuple[int, int, int]:
    """Errors and warnings that still count, and how many calibration issues were set aside."""
    errors = warnings = ignored = 0
    for g in plan["groups"]:
        for i in g.get("issues", []):
            if precalibrated and i["code"] in CALIBRATION_ISSUES:
                ignored += 1
            elif i["severity"] == "error":
                errors += 1
            elif i["severity"] == "warning":
                warnings += 1
    return errors, warnings, ignored


def only_calibration_errors(plan: dict) -> bool:
    codes = [i["code"] for g in plan["groups"] for i in g.get("issues", []) if i["severity"] == "error"]
    return bool(codes) and all(code in CALIBRATION_ISSUES for code in codes)


PRECALIBRATED_HINT = ("if the lights are already calibrated (Telescope.live *_cal.fits, for example), "
                      "re-run with --precalibrated")


def request_body(args, dates: list, **extra) -> dict:
    """Body of the plan and export requests. With --precalibrated the server is told too
    ("precalibrated": true, nebulis-app/nebulis#46): it then attaches no calibration frame and
    raises no calibration issue. Lights whose header says they are calibrated (PROC = 'True')
    are detected by the server without it. Older servers ignore the field; the client-side
    filter below still sets their calibration issues aside."""
    body = {"dates": dates, "includeNotKept": bool(args.include_not_kept), **extra}
    if args.precalibrated:
        body["precalibrated"] = True
    return body


def plan_text(plan: dict, precalibrated: bool = False) -> tuple[str, int, int]:
    lines = [f"{plan['objectId']} · nights {', '.join(plan['nights'])}"
             + (" · precalibrated (no calibration frames)" if plan.get("precalibrated") else "")]
    t = plan["totals"]
    errors, warnings, ignored = counted_issues(plan, precalibrated)
    lines.append(f"lights {t['lights']} kept, {t['excluded']} not kept · calibration frames {t['calibrationFrames']}"
                 f" · {fmt_bytes(t['bytes'])} · errors {errors} · warnings {warnings}"
                 + (f" · {ignored} calibration issues ignored (lights already calibrated)" if ignored else ""))
    for g in plan["groups"]:
        n = g["frames"] if plan.get("includeNotKept") else g["kept"]
        lines.append(f"\n{g['night']} · filter {g['filter'] or 'none'} · {g['exposureSec']}s · gain {g['gain']}"
                     f" · bin {g['binning']} · {g['sensorTempC']}°C · {n} lights ({g['frames']} total)"
                     + "".join(f" · {g[k]}" for k in ("camera", "telescope") if g.get(k)))
        if g.get("precalibrated"):
            lines.append("  already calibrated: no calibration frames")
        for label in ("dark", "flat", "flatDark", "bias"):
            c = g.get(label)
            if not c:
                lines.append(f"  {label:<9} —")
                continue
            extra = [c["source"]]
            if c.get("deltaTempC") is not None:
                extra.append(f"ΔT {c['deltaTempC']}°C")
            if c.get("deltaDays"):
                extra.append(f"{c['deltaDays']} d from night")
            if c.get("isExpired"):
                extra.append("EXPIRED")
            lines.append(f"  {label:<9} {c['name']} · {c['fileCount']} files · {', '.join(extra)}")
        for i in g.get("issues", []):
            params = f" {json.dumps(i['params'])}" if i.get("params") else ""
            note = " (ignored: lights already calibrated)" if precalibrated and i["code"] in CALIBRATION_ISSUES else ""
            lines.append(f"  ! {i['severity']}: {i['code']}{params}{note}")
    unmeasured = plan.get("unmeasuredByNight") or {}
    if unmeasured:
        lines.append("\nunmeasured frames (count as kept): " + ", ".join(f"{k}: {v}" for k, v in unmeasured.items()))
    return "\n".join(lines), errors, warnings


# ─── commands ───────────────────────────────────────────────────────────────

def cmd_status(c: Client, args):
    meta = c.call("GET", "/meta/version")
    objs = c.call("GET", "/library/objects")
    data = {"version": meta.get("version") if isinstance(meta, dict) else meta, "objects": len(objs or [])}
    out(args, data, f"Nebulis {data['version']} at {c.base} · authenticated · {data['objects']} library objects")


def list_objects(c: Client, search: str = "") -> list:
    # The server's search knows catalog designations and aliases: "NGC 2264", "ngc2264" and
    # "Christmas Tree" all find NGC2264. Matching here on the raw text missed the spaced form.
    path = "/library/objects" + (f"?search={q(search)}" if search else "")
    objs = c.call("GET", path) or []
    if isinstance(objs, dict):
        objs = objs.get("items") or objs.get("objects") or []
    return objs


def cmd_objects(c: Client, args):
    objs = list_objects(c, args.search or "")
    rows = [f"{o['id']:<16} {o.get('name', ''):<32} sessions {o.get('sessionCount', '?')}" for o in objs]
    out(args, objs, "\n".join(rows) or "no objects")


def squash(s: object) -> str:
    """Case, spaces and underscores do not tell designations apart: "NGC 2264" is NGC2264."""
    return "".join(str(s or "").split()).replace("_", "").lower()


def find_object(c: Client, name: str) -> dict:
    objs = list_objects(c)
    n = squash(name)
    for o in objs:
        if n in {squash(o.get(k)) for k in ("id", "folderName", "catalogId")}:
            return o
    for o in objs:
        if n in {squash(a) for a in [o.get("name"), *(o.get("aliases") or []), *(o.get("nicknames") or [])]}:
            return o
    hits = list_objects(c, name)
    if len(hits) == 1:
        return hits[0]
    die(f"no library object {name!r}; list them with: nebulis.py objects --search {name!r}", 1)


def cmd_object(c: Client, args):
    o = find_object(c, args.object)
    keys = [("type", "type"), ("constellation", "constellation"), ("ra", "RA"), ("dec", "Dec"),
            ("magnitude", "magnitude"), ("distanceLy", "distance (ly)"), ("sizeArcmin", "size (arcmin)")]
    rows = [f"{o.get('id')}  {o.get('name', '')}"] + [f"  {label:<14} {o.get(k)}" for k, label in keys if o.get(k) not in (None, "")]
    out(args, o, "\n".join(rows))


def cmd_telescopes(c: Client, args):
    ts = c.call("GET", "/telescopes") or []
    rows = []
    for t in ts:
        rig = t.get("rig") or {}
        rows.append(f"{t.get('id')}  {t.get('name', '')} · {t.get('model', '')} · {rig.get('sensorType') or '?'} sensor · "
                    f"filters {', '.join(rig.get('filters') or t.get('usedFilters') or []) or '-'}")
        for oc in t.get("opticalConfigs") or []:
            rows.append(f"    optics {oc.get('name')}: {oc.get('focalLengthMm')} mm, pixel {oc.get('pixelSizeUm')} µm, "
                        f"sensor {oc.get('sensorWidthMm')} × {oc.get('sensorHeightMm')} mm"
                        f"{' (active)' if oc.get('id') == t.get('activeOpticalConfigId') else ''}")
    # connection details and credentials are never printed, even masked
    hidden = ("password", "transports", "username", "hostname", "shareName", "localPath")
    slim = [{k: v for k, v in t.items() if k not in hidden} for t in ts]
    out(args, slim, "\n".join(rows) or "no telescopes")


def cmd_site(c: Client, args):
    s = c.call("GET", "/sites/active")
    if not s:
        die("no active observing site; choose one in Nebulis, Settings → Sky", 1)
    slim = {k: s.get(k) for k in ("id", "name", "latitude", "longitude", "timezone", "bortleClass", "darkness")}
    out(args, slim, f"{s.get('name')} · {s.get('latitude')}, {s.get('longitude')} · Bortle {s.get('bortleClass') or '?'} · {s.get('timezone')}")


def cmd_sessions(c: Client, args):
    ss = c.call("GET", f"/library/objects/{q(args.object)}/sessions") or []
    rows = [f"{s['date']}  filters {','.join(s.get('filters') or []) or '-':<14} exposures "
            f"{','.join(str(e) for e in s.get('exposures') or []) or '-':<10} subs {s.get('subFrameCount', '?')}"
            for s in sorted(ss, key=lambda s: s.get("date", ""))]
    out(args, ss, "\n".join(rows) or "no sessions")


def cmd_analysis(c: Client, args):
    rep = c.call("GET", f"/library/objects/{q(args.object)}/sessions/{q(args.date)}/frame-analysis")
    frames = rep.get("frames", [])
    grades: dict[str, int] = {}
    flags: dict[str, int] = {}
    for f in frames:
        g = (f.get("verdict") or {}).get("grade") or "unmeasured"
        grades[g] = grades.get(g, 0) + 1
        for fl in (f.get("verdict") or {}).get("flags", []):
            flags[fl] = flags.get(fl, 0) + 1
    kept = sum(1 for f in frames if f.get("kept"))
    lines = [f"{rep.get('objectId')} {rep.get('date')} · measured {rep.get('measured')}/{rep.get('total')}"
             f" · kept {kept}/{len(frames)}",
             "grades: " + ", ".join(f"{k} {v}" for k, v in sorted(grades.items())),
             "flags: " + (", ".join(f"{k} {v}" for k, v in sorted(flags.items())) or "none")]
    ref = rep.get("reference")
    if ref:
        lines.append(f"typical frame: stars {ref.get('stars')} · FWHM {ref.get('fwhm')} px · elongation "
                     f"{ref.get('elongation')} · background {ref.get('background')}")
    lines.append("")
    for f in frames:
        v = f.get("verdict") or {}
        if args.bad_only and f.get("kept") and v.get("grade") != "fair":
            continue
        m = f.get("metrics") or {}
        review = f.get("review") or "-"
        lines.append(f"{'KEEP' if f.get('kept') else 'DROP'} {v.get('grade', 'n/a'):<5} review {review:<6} "
                     f"fwhm {m.get('fwhm', '-')} stars {m.get('starCount', '-')} flags {','.join(v.get('flags', [])) or '-'}"
                     f"  {f['path']}")
    out(args, rep, "\n".join(lines))


def cmd_review(c: Client, args):
    keep = True if args.keep else False if args.reject else None
    done = []
    for p in args.paths:
        done.append(c.call("PUT", "/library/frame-analysis/review", {"path": p, "keep": keep}))
    label = {True: "keep", False: "reject", None: "follow the grade"}[keep]
    out(args, done, f"{len(done)} frame(s) set to {label}")


def cmd_plan(c: Client, args):
    dates = resolve_dates(c, args.object, args)
    plan = c.call("POST", f"/library/objects/{q(args.object)}/stacking-export/plan",
                  request_body(args, dates))
    text, errors, _ = plan_text(plan, args.precalibrated)
    out(args, plan, text)
    if errors:
        if not args.precalibrated and only_calibration_errors(plan):
            print(f"note: {PRECALIBRATED_HINT}", file=sys.stderr)
        sys.exit(2)


def cmd_fetch(c: Client, args):
    dates = resolve_dates(c, args.object, args)
    body = request_body(args, dates, layout=args.layout)
    plan = c.call("POST", f"/library/objects/{q(args.object)}/stacking-export/plan", body)
    text, errors, warnings = plan_text(plan, args.precalibrated)
    if errors:
        print(text)
        hint = f"; {PRECALIBRATED_HINT}" if not args.precalibrated and only_calibration_errors(plan) else ""
        die(f"the stacking plan has errors; fix them in Nebulis (attach flats, add darks) before fetching{hint}", 2)
    if warnings and not args.allow_warnings:
        print(text)
        die("the stacking plan has warnings; review them, then re-run with --allow-warnings", 2)

    dest = Path(args.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    job = c.call("POST", f"/library/objects/{q(args.object)}/stacking-export", body)
    job_id = job["jobId"]
    print(f"export job {job_id} started", file=sys.stderr)
    status = None
    deadline = time.time() + args.timeout
    last = -1
    while time.time() < deadline:
        status = c.call("GET", f"/library/download/status/{q(job_id)}")
        st = status.get("status")
        if st == "done":
            break
        if st in ("error", "cancelled"):
            die(f"export job {st}: {status.get('error')}", 3)
        done = status.get("filesDone", 0)
        if done != last:
            print(f"  building zip: {done}/{status.get('filesTotal', '?')} files", file=sys.stderr)
            last = done
        time.sleep(2)
    else:
        die(f"export job did not finish within {args.timeout}s", 3)

    filename = status.get("filename") or f"{args.object}.zip"
    with tempfile.TemporaryDirectory(prefix="nebulis-", dir=dest) as tmp:
        tmpdir = Path(tmp)
        zpath = tmpdir / filename
        print(f"downloading {filename} ({fmt_bytes(status.get('size'))})", file=sys.stderr)
        size = c.download(f"/api/v1/library/download/tmp/{q(status['token'])}", zpath)
        if status.get("size") and size != status["size"]:
            die(f"download truncated: {size} of {status['size']} bytes", 3)
        unpack = tmpdir / "unpacked"
        with zipfile.ZipFile(zpath) as zf:
            for member in zf.namelist():
                target = (unpack / member).resolve()
                if not str(target).startswith(str(unpack.resolve()) + os.sep):
                    die(f"refusing zip entry outside the destination: {member}", 3)
            zf.extractall(unpack)
        roots = [p for p in unpack.iterdir()]
        if len(roots) != 1 or not roots[0].is_dir():
            die("unexpected archive layout: expected one root folder", 3)
        root = roots[0]
        final = dest / root.name
        if final.exists():
            if not args.force:
                die(f"{final} already exists; re-run with --force to replace it", 1)
            shutil.rmtree(final)
        def is_light(p: Path) -> bool:
            rel = p.relative_to(root).parts
            return p.is_file() and (rel[0] == "Lights" or "lights" in rel[:-1])
        lights = sum(1 for p in root.rglob("*") if is_light(p))
        root.rename(final)

    expected = plan["totals"]["lights"]
    summary = {"path": str(final), "lights": lights, "expectedLights": expected, "nights": plan["nights"],
               "groups": [{"night": g["night"], "filter": g["filter"], "exposureSec": g["exposureSec"],
                           "lights": g["frames"] if plan.get("includeNotKept") else g["kept"]} for g in plan["groups"]]}
    if lights != expected:
        print(f"warning: {lights} light files unpacked, the plan announced {expected}", file=sys.stderr)
    text = [f"unpacked to {final}", f"lights {lights} (plan {expected}) · layout {args.layout}"]
    for g in summary["groups"]:
        text.append(f"  {g['night']} · {g['filter'] or 'none'} · {g['exposureSec']}s · {g['lights']} lights")
    text.append(f"manifest: {final / 'manifest.json'}")
    out(args, summary, "\n".join(text))


def cmd_archives(c: Client, args):
    arcs = c.call("GET", f"/library/objects/{q(args.object)}/project-archives") or []
    rows = [f"{a.get('uploadedAt', '')[:19]}  {fmt_bytes(a.get('size')):>9}  {a.get('originalName')}  {a.get('title') or ''}"
            for a in arcs]
    out(args, arcs, "\n".join(rows) or "no project archives")


def cmd_push(c: Client, args):
    allowed = (".zip", ".xpsm", ".pxiproject")
    cleanup = None
    if args.bundle:
        src = Path(args.bundle).expanduser().resolve()
        if not src.is_dir():
            die(f"{src} is not a folder", 1)
        cleanup = tempfile.TemporaryDirectory(prefix="nebulis-push-")
        name = args.name or f"{args.object}_{time.strftime('%Y-%m-%d')}_processing.zip"
        fpath = Path(cleanup.name) / name
        with zipfile.ZipFile(fpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(src.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(src))
    else:
        fpath = Path(args.file).expanduser().resolve()
        if not fpath.is_file():
            die(f"{fpath} not found", 1)
    if fpath.suffix.lower() not in allowed:
        die(f"Nebulis accepts only {', '.join(allowed)} project archives; add a finished image with the image command", 1)
    existing = c.call("GET", f"/library/objects/{q(args.object)}/project-archives") or []
    if any(a.get("originalName") == fpath.name for a in existing) and not args.force:
        die(f"{fpath.name} is already stored with {args.object}; rename it or pass --force", 1)
    print(f"uploading {fpath.name} ({fmt_bytes(fpath.stat().st_size)})", file=sys.stderr)
    rec = c.upload(f"/library/objects/{q(args.object)}/project-archives", fpath,
                   {"title": args.title or fpath.name, "notes": args.notes or "", "software": args.software})
    if cleanup:
        cleanup.cleanup()
    out(args, rec, f"stored {rec.get('originalName')} ({fmt_bytes(rec.get('size'))}) with {args.object}")


IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".xisf", ".fits", ".fit", ".fts")


def cmd_images(c: Client, args):
    imgs = c.call("GET", f"/library/objects/{q(args.object)}/processed-images") or []
    rows = [f"{(i.get('uploadedAt') or '')[:19]}  {i.get('date') or 'object-level':<12}  {fmt_bytes(i.get('size')):>9}  "
            f"{i.get('originalName')}  {i.get('title') or ''}" for i in imgs]
    out(args, imgs, "\n".join(rows) or "no processed images")


def cmd_image(c: Client, args):
    """Add a finished image to the object (its Processed images and the gallery), not to a session."""
    fpath = Path(args.file).expanduser().resolve()
    if not fpath.is_file():
        die(f"{fpath} not found", 1)
    if fpath.suffix.lower() not in IMAGE_TYPES:
        die(f"not an image Nebulis stores as a processed image ({', '.join(IMAGE_TYPES)}); "
            "project archives go through push", 1)
    existing = c.call("GET", f"/library/objects/{q(args.object)}/processed-images") or []
    if any(i.get("originalName") == fpath.name for i in existing) and not args.force:
        die(f"{fpath.name} is already an image of {args.object}; rename it or pass --force", 1)
    print(f"uploading {fpath.name} ({fmt_bytes(fpath.stat().st_size)})", file=sys.stderr)
    rec = c.upload(f"/library/objects/{q(args.object)}/processed-images", fpath,
                   {"title": args.title or "", "notes": args.notes or ""}, field="image")
    out(args, rec, f"added image {rec.get('originalName')} ({fmt_bytes(rec.get('size'))}) to {args.object}")


# ─── CLI ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="nebulis", description="Nebulis API client (see the module docstring)")
    p.add_argument("--json", action="store_true", help="print the raw API payload")
    p.add_argument("--timeout", type=float, default=3600, help="seconds to wait for an export job (fetch)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    s = sub.add_parser("objects"); s.add_argument("--search")
    s = sub.add_parser("object"); s.add_argument("object")
    sub.add_parser("telescopes"); sub.add_parser("site")
    s = sub.add_parser("sessions"); s.add_argument("object")
    s = sub.add_parser("analysis"); s.add_argument("object"); s.add_argument("date")
    s.add_argument("--bad-only", action="store_true", help="only frames not kept or graded fair")
    s = sub.add_parser("review"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--keep", action="store_true"); g.add_argument("--reject", action="store_true")
    g.add_argument("--reset", action="store_true"); s.add_argument("paths", nargs="+")
    for name in ("plan", "fetch"):
        s = sub.add_parser(name); s.add_argument("object")
        d = s.add_mutually_exclusive_group(required=True)
        d.add_argument("--dates", nargs="+"); d.add_argument("--all", action="store_true")
        s.add_argument("--include-not-kept", action="store_true")
        s.add_argument("--precalibrated", action="store_true",
                       help="the lights are already calibrated: missing darks, flats or bias are not errors")
        if name == "fetch":
            s.add_argument("--dest", required=True)
            s.add_argument("--layout", choices=["wbpp", "siril"], default="wbpp")
            s.add_argument("--allow-warnings", action="store_true")
            s.add_argument("--force", action="store_true")
    s = sub.add_parser("archives"); s.add_argument("object")
    s = sub.add_parser("images"); s.add_argument("object")
    s = sub.add_parser("image"); s.add_argument("object"); s.add_argument("--file", required=True)
    s.add_argument("--title"); s.add_argument("--notes"); s.add_argument("--force", action="store_true")
    s = sub.add_parser("push"); s.add_argument("object")
    src = s.add_mutually_exclusive_group(required=True)
    src.add_argument("--file"); src.add_argument("--bundle")
    s.add_argument("--name", help="zip name for --bundle"); s.add_argument("--title"); s.add_argument("--notes")
    s.add_argument("--software", default="PixInsight"); s.add_argument("--force", action="store_true")

    args = p.parse_args(argv)
    base, key = load_config()
    c = Client(base, key)
    handlers = {"status": cmd_status, "objects": cmd_objects, "object": cmd_object,
                "telescopes": cmd_telescopes, "site": cmd_site, "sessions": cmd_sessions, "analysis": cmd_analysis,
                "review": cmd_review, "plan": cmd_plan, "fetch": cmd_fetch, "archives": cmd_archives,
                "push": cmd_push, "images": cmd_images, "image": cmd_image}
    try:
        if getattr(args, "object", None) and args.cmd != "object":
            # Every command takes the object as the user writes it ("NGC 2264", "m 31") and calls
            # the API with its id.
            args.object = find_object(c, args.object)["id"]
        handlers[args.cmd](c, args)
    except ApiError as e:
        hint = ""
        if e.status == 401:
            hint = f" (check {KEY_VAR}; keys are created in Nebulis, Settings -> Account -> API keys -> New key)"
        elif e.status == 403:
            hint = " (this action needs an admin key)"
        elif e.status == 404 and e.code in ("NOT_FOUND", "HTTP_ERROR"):
            hint = " (unknown object or date, or a Nebulis version without this endpoint)"
        die(f"{e.status} {e.code}: {e.message}{hint}", 3)


if __name__ == "__main__":
    main()
