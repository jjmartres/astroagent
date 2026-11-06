"""A minimal mock of the Nebulis endpoints nebulis.py uses, with the server's response envelope.

Shapes follow nebulis-app/nebulis: server/middleware/apiEnvelope.ts ({ok, data, error}),
tests/backend/pixinsightContract.test.ts and server/lib/library/stackingExport.ts.
"""
import io
import json
import threading
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
STATE = {"polls": 0, "reviews": [], "uploads": []}


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

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/v1/meta/version":
            return self.send(200, {"version": "2.2.0"})
        if p.startswith("/api/v1/library/download/tmp/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(ZIP)))
            self.end_headers()
            self.wfile.write(ZIP)
            return
        if not self.authed():
            return
        if p == "/api/v1/library/objects":
            return self.send(200, [{"id": OBJ, "name": "Crescent Nebula", "folderName": OBJ, "sessionCount": 2}])
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
            return self.send(200, {"status": "done", "token": "tok123", "filename": f"{OBJ}_2-nights_wbpp.zip",
                                   "size": len(ZIP), "filesTotal": 9, "filesDone": 9})
        if p == f"/api/v1/library/objects/{OBJ}/project-archives":
            return self.send(200, [{"originalName": u, "size": 1, "uploadedAt": "2026-11-06T12:00:00Z"} for u in STATE["uploads"]])
        return self.send(404, err=("NOT_FOUND", "no route"))

    def do_POST(self):
        p = self.path
        if not self.authed():
            return
        raw = self.body()
        if p == f"/api/v1/library/objects/{OBJ}/stacking-export/plan":
            req = json.loads(raw)
            assert req["dates"], req
            return self.send(200, PLAN)
        if p == f"/api/v1/library/objects/{OBJ}/stacking-export":
            return self.send(200, {"jobId": "job1"})
        if p == f"/api/v1/library/objects/{OBJ}/project-archives":
            ctype = self.headers.get("Content-Type", "")
            assert ctype.startswith("multipart/form-data"), ctype
            name = raw.split(b'filename="')[1].split(b'"')[0].decode()
            if not name.endswith((".zip", ".xpsm", ".pxiproject")):
                return self.send(400, err=("NO_ARCHIVE", "bad type"))
            STATE["uploads"].append(name)
            return self.send(200, {"originalName": name, "size": len(raw), "uploadedAt": "2026-11-06T12:00:00Z"})
        return self.send(404, err=("NOT_FOUND", "no route"))

    def do_PUT(self):
        if not self.authed():
            return
        req = json.loads(self.body())
        if self.path == "/api/v1/library/frame-analysis/review":
            STATE["reviews"].append(req)
            return self.send(200, req)
        return self.send(404, err=("NOT_FOUND", "no route"))


def start():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
