"""A minimal mock of the Nebulis endpoints nebulis.py uses, with the server's response envelope.

Shapes follow nebulis-app/nebulis: server/middleware/apiEnvelope.ts ({ok, data, error}),
tests/backend/pixinsightContract.test.ts and server/lib/library/stackingExport.ts.
"""
import hashlib
import io
import json
import os
import tempfile
import threading
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEY = "neb-test-key"
OBJ = "Sh2-105"
PLAN = {
    "objectId": OBJ, "nights": ["2026-09-05", "2026-09-06"], "includeNotKept": False,
    "groups": [
        {"id": "g1", "night": "2026-09-05", "filter": "D1", "exposureSec": 180, "gain": 200, "binning": 1,
         "sensorTempC": -8.0, "frames": 3, "kept": 2, "bytes": 100,
         "dark": {"type": "dark", "name": "Dark_180s_G200_-8C", "scope": None, "folderName": "Darks", "key": "k1",
                  "source": "matched", "fileCount": 2, "bytes": 10, "exposureSec": 180, "gain": 200, "binning": 1,
                  "sensorTempC": -8.1, "filter": None, "capturedAt": None, "isExpired": False, "deltaTempC": 0.1},
         "flat": {"type": "flat", "name": "Flat_D1", "scope": None, "folderName": "Flats", "key": "k2",
                  "source": "attached", "fileCount": 2, "bytes": 10, "exposureSec": 0.5, "gain": 200, "binning": 1,
                  "sensorTempC": -8.0, "filter": "D1", "capturedAt": None, "isExpired": False},
         "flatDark": None,
         "bias": {"type": "bias", "name": "Bias_G200", "scope": None, "folderName": "Bias", "key": "k3",
                  "source": "matched", "fileCount": 2, "bytes": 10, "exposureSec": 0.001, "gain": 200, "binning": 1,
                  "sensorTempC": -8.0, "filter": None, "capturedAt": None, "isExpired": False},
         "issues": []},
        {"id": "g2", "night": "2026-09-06", "filter": "D2", "exposureSec": 180, "gain": 200, "binning": 1,
         "sensorTempC": -8.0, "frames": 2, "kept": 2, "bytes": 100,
         "dark": None, "flat": None, "flatDark": None, "bias": None,
         "issues": [{"code": "flat_other_night", "severity": "warning", "params": {"bundle": "Flat_D2", "days": 3}}]},
    ],
    "unmeasuredByNight": {},
    "totals": {"lights": 4, "excluded": 1, "calibrationFrames": 6, "bytes": 330, "errors": 0, "warnings": 1},
}


def make_zip() -> bytes:
    buf = io.BytesIO()
    root = f"{OBJ}_2-nights_wbpp"
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(2):
            zf.writestr(f"{root}/Lights/NIGHT_2026-09-05/FILTER_D1/L_{i}.fits", b"SIMPLE")
            zf.writestr(f"{root}/Lights/NIGHT_2026-09-06/FILTER_D2/L_{i}.fits", b"SIMPLE")
            zf.writestr(f"{root}/Darks/Dark_180s_G200_-8C/D_{i}.fits", b"SIMPLE")
        zf.writestr(f"{root}/manifest.json", json.dumps(PLAN))
        zf.writestr(f"{root}/README.txt", "readme")
    return buf.getvalue()


ZIP = make_zip()

# A Telescope.live object: calibrated lights (`*_cal.fits`), so Nebulis finds no dark or flat for them.
OBJ2 = "NGC4438"
PLAN2 = {
    "objectId": OBJ2, "nights": ["2021-12-05"], "includeNotKept": False,
    "groups": [
        {"id": "g1", "night": "2021-12-05", "filter": "Ha", "exposureSec": 600, "gain": None, "binning": 2,
         "sensorTempC": -25.0, "frames": 2, "kept": 2, "bytes": 100,
         "dark": None, "flat": None, "flatDark": None, "bias": None,
         "issues": [{"code": "no_dark", "severity": "error"},
                    {"code": "no_flat", "severity": "error", "params": {"filter": "Ha"}},
                    {"code": "unknown_settings", "severity": "warning"}]},
    ],
    "unmeasuredByNight": {},
    "totals": {"lights": 2, "excluded": 0, "calibrationFrames": 0, "bytes": 100, "errors": 2, "warnings": 1},
}


def make_zip2() -> bytes:
    buf = io.BytesIO()
    root = f"{OBJ2}_1-night_wbpp"
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(2):
            zf.writestr(f"{root}/Lights/NIGHT_2021-12-05/FILTER_Ha/L_{i}_cal.fits", b"SIMPLE")
        zf.writestr(f"{root}/manifest.json", json.dumps(PLAN2))
    return buf.getvalue()


ZIP2 = make_zip2()
OBJECTS = [
    {"id": OBJ, "catalogId": OBJ, "name": "Sh2-105", "folderName": OBJ, "sessionCount": 2,
     "type": "Emission nebula", "constellation": "Cygnus", "ra": "20h 12m 06s",
     "dec": "+38° 21' 00\"", "magnitude": 7.4, "distanceLy": 5000, "sizeArcmin": "18 × 12",
     "description": "A Wolf-Rayet shell.", "wikiUrl": None, "aliases": ["NGC 6888"],
     "nicknames": ["Crescent Nebula"]},
    {"id": OBJ2, "catalogId": OBJ2, "name": "Eyes", "folderName": OBJ2, "sessionCount": 1,
     "type": "Galaxy", "constellation": "Virgo", "ra": "12h 27m 45.6s", "dec": "+13° 00' 32\"",
     "magnitude": 10.9, "distanceLy": None, "sizeArcmin": None, "description": None, "wikiUrl": None,
     "aliases": ["UGC7574"], "nicknames": []},
]


def search_objects(term: str) -> list:
    """Like the server: designations match whatever their spacing or case ("NGC 4438" finds NGC4438)."""
    t = "".join(term.split()).lower()
    return [o for o in OBJECTS
            if any(t in "".join(str(v).split()).lower() for v in [o["id"], o["catalogId"], o["name"], *o["aliases"]])]


STATE = {"polls": 0, "reviews": [], "uploads": [], "images": [], "zip": ZIP, "bodies": [],
         # Stored files, by original name: {"path", "size", "sha256", "fields", "via": "post" | "chunked"}.
         "files": {},
         # Chunked uploads (POST /uploads...): off answers 404 like Nebulis 2.2.
         "chunked": True, "chunk_size": 8 << 20, "drop_chunks": set(), "sessions": {}, "puts": []}
SPOOL = tempfile.mkdtemp(prefix="mock-nebulis-")


def store(name, path, size, sha, fields, via, target):
    STATE["files"][name] = {"path": path, "size": size, "sha256": sha, "fields": fields, "via": via}
    if target == "project-archive":
        STATE["uploads"].append(name)
        return {"originalName": name, "size": size, "uploadedAt": "2026-11-06T12:00:00Z", **fields}
    STATE["images"].append(name)
    return {"id": "proc_1", "originalName": name, "size": size, "date": None,
            "uploadedAt": "2026-11-06T12:00:00Z", "source": "user", **fields}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, status, data=None, err=None):
        body = json.dumps({"ok": err is None, "data": data, **({"error": {"code": err[0], "message": err[1]}} if err else {})}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authed(self):
        if self.headers.get("X-API-Key") != KEY:
            self.send(401, err=("UNAUTHORIZED", "Authentication required"))
            return False
        return True

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n)

    def multipart(self):
        """Stream a multipart body to disk: never held in memory, hashed on the way.
        Returns (fields, field name, filename, path, size, sha256)."""
        ctype = self.headers.get("Content-Type", "")
        assert ctype.startswith("multipart/form-data"), ctype
        boundary = ctype.split("boundary=")[1].encode()
        tail = b"\r\n--" + boundary + b"--\r\n"
        left = int(self.headers["Content-Length"])
        head = b""
        while b'filename="' not in head or b"\r\n\r\n" not in head.split(b'filename="', 1)[1]:
            block = self.rfile.read(min(65536, left))
            assert block, "body ended inside the multipart head"
            left -= len(block)
            head += block
        before, after = head.split(b'filename="', 1)
        filename = after.split(b'"', 1)[0].decode()
        field = before.rsplit(b'name="', 1)[1].split(b'"', 1)[0].decode()
        rest = after.split(b"\r\n\r\n", 1)[1]
        fields = {}
        for part in before.split(b"--" + boundary)[1:-1]:
            hdr, _, val = part.partition(b"\r\n\r\n")
            fields[hdr.split(b'name="')[1].split(b'"')[0].decode()] = val[:-2].decode()
        fd, path = tempfile.mkstemp(dir=SPOOL)
        h, size, pending = hashlib.sha256(), 0, rest
        with os.fdopen(fd, "wb") as fh:
            while True:
                if len(pending) > len(tail):
                    out = pending[:-len(tail)]
                    fh.write(out)
                    h.update(out)
                    size += len(out)
                    pending = pending[-len(tail):]
                if not left:
                    break
                block = self.rfile.read(min(8 << 20, left))
                assert block, "body shorter than its Content-Length"
                left -= len(block)
                pending += block
        assert pending == tail, pending
        return fields, field, filename, path, size, h.hexdigest()

    def chunk_put(self, uid, index):
        sess = STATE["sessions"].get(uid)
        if sess is None:
            return self.send(404, err=("NOT_FOUND", "no such upload"))
        n = int(self.headers["Content-Length"])
        data = self.rfile.read(n)
        STATE["puts"].append(index)
        if index in STATE["drop_chunks"]:
            return self.send(500, err=("CHUNK_LOST", "chunk dropped by the stub"))
        rng = self.headers["Content-Range"]  # bytes start-end/total
        start, end = (int(x) for x in rng.split()[1].split("/")[0].split("-"))
        assert int(rng.split("/")[1]) == sess["size"], rng
        assert start == index * sess["chunkSize"] and end - start + 1 == len(data), (rng, index, len(data))
        with open(sess["path"], "r+b") as fh:
            fh.seek(start)
            fh.write(data)
        sess["received"].append([start, end])
        return self.send(200, {"index": index, "received": len(data)})

    def do_DELETE(self):
        if not self.authed():
            return
        uid = self.path.split("/uploads/")[1]
        STATE["sessions"].pop(uid, None)
        return self.send(200, {"deleted": uid})

    def do_GET(self):
        p = self.path.split("?")[0]
        if p.startswith("/api/v1/uploads/") and STATE["chunked"]:
            if not self.authed():
                return
            sess = STATE["sessions"].get(p.rsplit("/", 1)[1])
            if sess is None:
                return self.send(404, err=("NOT_FOUND", "no such upload"))
            return self.send(200, {"received": sess["received"], "size": sess["size"], "status": sess["status"]})
        if p == "/api/v1/meta/version":
            return self.send(200, {"version": "2.2.0"})
        if p.startswith("/api/v1/library/download/tmp/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(STATE["zip"])))
            self.end_headers()
            self.wfile.write(STATE["zip"])
            return
        if not self.authed():
            return
        if p == "/api/v1/library/objects":
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            term = (query.get("search") or [""])[0]
            return self.send(200, search_objects(term) if term else OBJECTS)
        if p == "/api/v1/telescopes":
            return self.send(200, [{"id": "t1", "name": "Elendil", "model": "Askar 91F", "password": "********",
                                    "hostname": "nas", "transports": [{"password": "********"}],
                                    "activeOpticalConfigId": "oc1", "usedFilters": ["D1", "D2"],
                                    "opticalConfigs": [{"id": "oc1", "name": "native", "focalLengthMm": 609,
                                                        "sensorWidthMm": 11.14, "sensorHeightMm": 6.26, "pixelSizeUm": 2.9}],
                                    "rig": {"sensorType": "color", "filters": ["D1", "D2"]}}])
        if p == "/api/v1/sites/active":
            return self.send(200, {"id": "s1", "name": "Home", "latitude": 45.5, "longitude": 6.3, "timezone": "Europe/Paris",
                                   "bortleClass": 4, "darkness": "rural", "minAlt": 20})
        if p == f"/api/v1/library/objects/{OBJ2}/sessions":
            return self.send(200, [{"date": "2021-12-05", "filters": ["Ha"], "exposures": [600], "subFrameCount": 2}])
        if p == f"/api/v1/library/objects/{OBJ}/sessions":
            return self.send(200, [{"date": "2026-09-06", "filters": ["D2"], "exposures": [180], "subFrameCount": 2},
                                   {"date": "2026-09-05", "filters": ["D1"], "exposures": [180], "subFrameCount": 3}])
        if p == f"/api/v1/library/objects/{OBJ}/sessions/2026-09-05/frame-analysis":
            return self.send(200, {"objectId": OBJ, "date": "2026-09-05", "measured": 3, "total": 3,
                                   "reference": {"stars": 800, "fwhm": 2.1, "elongation": 1.1, "noise": 0.01, "background": 0.05, "signal": 1},
                                   "frames": [
                                       {"path": f"{OBJ}/a.fits", "kept": True, "review": None, "metrics": {"fwhm": 2.0, "starCount": 810},
                                        "verdict": {"score": 0.9, "grade": "good", "flags": [], "reasons": []}},
                                       {"path": f"{OBJ}/b.fits", "kept": True, "review": None, "metrics": {"fwhm": 2.6, "starCount": 700},
                                        "verdict": {"score": 0.6, "grade": "fair", "flags": ["soft"], "reasons": []}},
                                       {"path": f"{OBJ}/c.fits", "kept": False, "review": None, "metrics": {"fwhm": 2.2, "starCount": 200},
                                        "verdict": {"score": 0.1, "grade": "bad", "flags": ["clouds"], "reasons": []}}]})
        if p.startswith("/api/v1/library/download/status/"):
            STATE["polls"] += 1
            if STATE["polls"] < 2:
                return self.send(200, {"status": "running", "filesTotal": 9, "filesDone": 4, "elapsedMs": 10})
            return self.send(200, {"status": "done", "token": "tok123", "filename": "export.zip",
                                   "size": len(STATE["zip"]), "filesTotal": 9, "filesDone": 9})
        if p == f"/api/v1/library/objects/{OBJ}/project-archives":
            return self.send(200, [{"originalName": u, "size": 1, "uploadedAt": "2026-11-06T12:00:00Z"} for u in STATE["uploads"]])
        if p == f"/api/v1/library/objects/{OBJ}/processed-images":
            return self.send(200, [{"originalName": u, "size": 1, "date": None, "uploadedAt": "2026-11-06T12:00:00Z"}
                                   for u in STATE["images"]])
        return self.send(404, err=("NOT_FOUND", "no route"))

    def do_POST(self):
        p = self.path
        if not self.authed():
            return
        if p == f"/api/v1/library/objects/{OBJ}/project-archives":
            fields, field, name, path, size, sha = self.multipart()
            if field != "archive" or not name.endswith((".zip", ".xpsm", ".pxiproject")):
                return self.send(400, err=("NO_ARCHIVE", "bad type"))
            return self.send(200, store(name, path, size, sha, fields, "post", "project-archive"))
        if p == f"/api/v1/library/objects/{OBJ}/processed-images":
            fields, field, name, path, size, sha = self.multipart()
            if field != "image":
                return self.send(400, err=("NO_IMAGE", "No image file provided"))
            if size > 2 << 30:
                return self.send(413, err=("LIMIT_FILE_SIZE", "File is too large for this upload endpoint."))
            return self.send(200, store(name, path, size, sha, fields, "post", "processed-image"))
        if p.startswith("/api/v1/uploads"):
            if not STATE["chunked"]:
                self.body()
                return self.send(404, err=("NOT_FOUND", "no route"))
            if p == "/api/v1/uploads":
                req = json.loads(self.body())
                assert req["target"] in ("project-archive", "processed-image"), req
                assert req["objectId"] == OBJ, req
                uid = f"up_{len(STATE['sessions']) + 1}_{os.urandom(3).hex()}"
                fd, path = tempfile.mkstemp(dir=SPOOL)
                os.close(fd)
                STATE["sessions"][uid] = {**req, "path": path, "received": [], "status": "open",
                                          "chunkSize": STATE["chunk_size"]}
                return self.send(200, {"uploadId": uid, "chunkSize": STATE["chunk_size"], "maxSize": 20 << 30,
                                       "expiresAt": "2026-11-23T12:00:00Z"})
            if p.endswith("/complete"):
                self.body()
                uid = p.split("/")[-2]
                sess = STATE["sessions"][uid]
                h, size = hashlib.sha256(), 0
                with open(sess["path"], "rb") as fh:
                    for block in iter(lambda: fh.read(8 << 20), b""):
                        h.update(block)
                        size += len(block)
                if size != sess["size"] or h.hexdigest() != sess["sha256"]:
                    return self.send(409, err=("CHECKSUM_MISMATCH", f"got {size} bytes, sha256 {h.hexdigest()}"))
                sess["status"] = "complete"
                fields = {k: sess[k] for k in ("title", "notes", "software") if k in sess}
                return self.send(200, store(sess["filename"], sess["path"], size, h.hexdigest(), fields,
                                            "chunked", sess["target"]))
        raw = self.body()
        if p == f"/api/v1/library/objects/{OBJ}/stacking-export/plan":
            req = json.loads(raw)
            assert req["dates"], req
            return self.send(200, PLAN)
        if p == f"/api/v1/library/objects/{OBJ}/stacking-export":
            STATE["zip"] = ZIP
            return self.send(200, {"jobId": "job1"})
        if p == f"/api/v1/library/objects/{OBJ2}/stacking-export/plan":
            req = json.loads(raw)
            assert req["dates"] == ["2021-12-05"]
            STATE["bodies"].append(("plan", req))
            return self.send(200, PLAN2)
        if p == f"/api/v1/library/objects/{OBJ2}/stacking-export":
            STATE["bodies"].append(("export", json.loads(raw)))
            STATE["zip"] = ZIP2
            return self.send(200, {"jobId": "job2"})
        return self.send(404, err=("NOT_FOUND", "no route"))

    def do_PUT(self):
        if not self.authed():
            return
        if self.path.startswith("/api/v1/uploads/") and "/chunks/" in self.path and STATE["chunked"]:
            uid, index = self.path.split("/uploads/")[1].split("/chunks/")
            return self.chunk_put(uid, int(index))
        req = json.loads(self.body())
        if self.path == "/api/v1/library/frame-analysis/review":
            STATE["reviews"].append(req)
            return self.send(200, req)
        return self.send(404, err=("NOT_FOUND", "no route"))


def start():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
