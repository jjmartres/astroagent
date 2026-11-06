"""Tests of skills/astro-project/scripts/astro_project.py on a synthetic workspace.

The workspace holds a Nebulis WBPP export (manifest.json from the mock server, FITS lights with real headers, no
pixel data), the JSON files nebulis.py --json prints, the agent's research.json and report.json, and a
pixinsight-connector call log.

Run: python3 -m unittest discover -s tests
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mock_nebulis  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "astro-project" / "scripts" / "astro_project.py"
FIX = Path(__file__).parent / "fixtures" / "astro-project"


def fits_bytes(cards: dict) -> bytes:
    lines = ["SIMPLE  =                    T", "BITPIX  =                   16", "NAXIS   =                    0"]
    for k, v in cards.items():
        if isinstance(v, bool):
            val = f"{'T' if v else 'F':>20}"
        elif isinstance(v, (int, float)):
            val = f"{v:>20}"
        else:
            val = "'" + str(v).replace("'", "''") + "'"
        lines.append(f"{k:<8}= {val}")
    lines.append("END")
    raw = "".join(line.ljust(80) for line in lines).encode("ascii")
    return raw + b" " * (-len(raw) % 2880)


def header(night: str, filt: str, i: int) -> dict:
    return {"NAXIS1": 3840, "NAXIS2": 2160, "OBJECT": "Sh2-105", "TELESCOP": "Askar 91F", "INSTRUME": "ZWO ASI585MC Air",
            "FOCALLEN": 609, "XPIXSZ": 2.9, "BAYERPAT": "RGGB", "EXPTIME": 180.0, "GAIN": 200, "XBINNING": 1,
            "SET-TEMP": -8.0, "CCD-TEMP": -8.1, "FILTER": filt, "RA": 303.025, "DEC": 38.35,
            "SITELAT": "+45 30 00", "SITELONG": "+06 18 00", "DATE-OBS": f"{night}T22:{i:02d}:00"}


def make_workspace() -> Path:
    ws = Path(tempfile.mkdtemp()) / "Sh2-105"
    exp = ws / "data" / "Sh2-105_2-nights_wbpp"
    plan = json.loads(json.dumps(mock_nebulis.PLAN))
    for night, filt, n in (("2026-09-05", "D1", 2), ("2026-09-06", "D2", 2)):
        d = exp / "Lights" / f"NIGHT_{night}" / f"FILTER_{filt}"
        d.mkdir(parents=True)
        for i in range(n):
            (d / f"Light_Sh2-105_180.0s_{filt}_{i:04d}.fit").write_bytes(fits_bytes(header(night, filt, i)))
    (exp / "manifest.json").write_text(json.dumps(plan))
    (ws / "output").mkdir()
    (ws / "agentic" / "logs").mkdir(parents=True)
    shutil.copy(FIX / "connector.jsonl", ws / "agentic" / "logs" / "20261106-100000-1.jsonl")
    neb = ws / "agentic" / "work"
    neb.mkdir(parents=True)
    # what nebulis.py --json object / telescopes / site would print (shapes from the mock server)
    (neb / "object.json").write_text(json.dumps({"id": "Sh2-105", "name": "Sh2-105", "type": "Emission nebula", "constellation": "Cygnus",
                                                 "ra": "20h 12m 06s", "dec": "+38° 21′ 00″", "aliases": ["NGC 6888"],
                                                 "nicknames": ["Crescent Nebula"], "primaryTelescopeId": "t1"}))
    (neb / "telescopes.json").write_text(json.dumps([{"id": "t1", "name": "Elendil", "model": "Askar 91F", "activeOpticalConfigId": "oc1",
                                                      "opticalConfigs": [{"id": "oc1", "name": "native", "focalLengthMm": 609, "pixelSizeUm": 2.9}],
                                                      "rig": {"sensorType": "color", "filters": ["D1", "D2"]}}]))
    (neb / "site.json").write_text(json.dumps({"name": "Home", "latitude": 45.5, "longitude": 6.3, "bortleClass": 4}))
    return ws


class AstroProjectTest(unittest.TestCase):
    def setUp(self):
        self.ws = make_workspace()
        self.work = self.ws / "agentic" / "work"

    def tearDown(self):
        shutil.rmtree(self.ws.parent, ignore_errors=True)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=60)

    def scan(self, *extra):
        return self.run_cli("scan", self.ws, "--object", self.work / "object.json", "--telescope", self.work / "telescopes.json",
                            "--site", self.work / "site.json", *extra)

    def test_scan_then_fill(self):
        r = self.scan()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)  # everything required came from headers and Nebulis
        rig = json.loads((self.ws / "output" / "rig.json").read_text())
        self.assertEqual(rig["telescope"]["focal_length_mm"], 609)
        self.assertEqual(rig["camera"]["resolution_px"], "3840x2160")
        self.assertEqual(rig["capture_location"]["latitude"], 45.5)      # from SITELAT, sexagesimal
        self.assertEqual(rig["capture_location"]["bortle"], 4)            # from the Nebulis site
        self.assertEqual(rig["target"]["common_name"], "Crescent Nebula")
        self.assertEqual(rig["provenance"]["telescope.focal_length_mm"], "fits")
        lights = {s["filter"]: s for s in rig["sequences"]["lights"]}
        self.assertEqual(lights["D1"]["subs"], 2)
        self.assertEqual(lights["D1"]["subs_total"], 3)
        self.assertEqual([d["name"] for d in rig["sequences"]["darks"]], ["Dark_180s_G200_-8C"])
        self.assertIn("filters.D1", r.stdout)                             # descriptions are recommended
        r = self.scan("--set", "telescope.aperture_mm=91", "filters.D1=Askar D1, Ha + OIII, 6 nm", "capture_location.site=Savoie")
        rig = json.loads((self.ws / "output" / "rig.json").read_text())
        self.assertEqual(rig["telescope"]["focal_ratio"], 6.69)
        self.assertEqual(rig["filters"]["D1"], "Askar D1, Ha + OIII, 6 nm")
        r = self.scan()                                                   # a re-scan keeps what the user set
        rig = json.loads((self.ws / "output" / "rig.json").read_text())
        self.assertEqual(rig["capture_location"]["site"], "Savoie")
        self.assertEqual(self.run_cli("validate", self.ws / "output" / "rig.json").returncode, 0)

    def test_missing_fields_exit_2(self):
        r = self.run_cli("scan", self.ws)                                 # no Nebulis files: no site name, no Bortle
        self.assertEqual(r.returncode, 2)
        self.assertIn("capture_location.bortle: required", r.stdout)
        r = self.run_cli("scan", self.ws, "--set", "capture_location.site=Home", "capture_location.bortle=4")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_outputs(self):
        self.scan("--set", "telescope.aperture_mm=91")
        shutil.copy(FIX / "research.json", self.ws / "output" / "research.json")
        shutil.copy(FIX / "report.json", self.ws / "output" / "report.json")
        (self.ws / "output" / "final").mkdir()
        (self.ws / "output" / "final" / "Sh2-105_Foraxx_2026-11-06_web.jpg").write_bytes(b"\xff\xd8\xff")
        for cmd in ("project", "report", "doc", "astrobin"):
            r = self.run_cli(cmd, self.ws)
            self.assertEqual(r.returncode, 0, f"{cmd}: {r.stdout}{r.stderr}")
        project = json.loads((self.ws / "output" / "project.json").read_text())
        self.assertIn("Crescent Nebula", project["description"])
        self.assertEqual(project["ref_alignment"], "")
        self.assertEqual((self.ws / "output" / "project.json").read_text().count("\n"), 1)  # one line
        doc = (self.ws / "output" / "doc" / "index.html").read_text()
        self.assertIn('src="../final/Sh2-105_Foraxx_2026-11-06_web.jpg"', doc)
        self.assertIn("session-report.html", doc)
        self.assertNotIn("http://fonts", doc)                              # self-contained
        rep = (self.ws / "output" / "doc" / "session-report.html").read_text()
        self.assertIn("1 gate failed", rep)
        ab = json.loads((self.ws / "output" / "astrobin.json").read_text())
        self.assertEqual(ab["subject_type"], "NEBULA")
        self.assertEqual(len(ab["acquisition_details"]), 2)               # one row per night and filter
        self.assertEqual(ab["acquisition_details"][0]["darks"], 2)

    def test_project_needs_valid_rig(self):
        r = self.run_cli("project", self.ws)
        self.assertEqual(r.returncode, 2)

    def test_icons_and_xpsm(self):
        r = self.run_cli("icons", self.ws)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        icons = json.loads((self.work / "icons.json").read_text())
        # get_image_stats is a measuring call and the NXT call failed: only BXT and PixelMath remain
        self.assertEqual([i["class"] for i in icons], ["BlurXTerminator", "PixelMath"])
        self.assertIn(("sharpen_nonstellar", "0.6"), [tuple(p) for p in icons[0]["params"]])
        js = (self.work / "icons.js").read_text()
        self.assertIn('P.toSource("XPSM 1.0"', js)
        fake = [{"id": icons[0]["id"], "xml": '<instance class="BlurXTerminator" version="256" id="P_instance">\n'
                                              '      <parameter id="sharpen_nonstellar" value="0.60"/>\n   </instance>'},
                {"id": icons[1]["id"], "error": "toSource failed"}]
        (self.work / "res.json").write_text(json.dumps(json.dumps(fake)))  # run_pjsr returns the string
        shutil.copy(FIX / "report.json", self.ws / "output" / "report.json")
        r = self.run_cli("xpsm", self.ws, "--pjsr-result", self.work / "res.json")
        self.assertEqual(r.returncode, 2)                                 # one icon failed: reported
        x = next((self.ws / "output").glob("Process Icons - * - Foraxx workflow.xpsm")).read_text()
        self.assertIn(f'id="{icons[0]["id"]}_instance"', x)
        self.assertIn(f'<icon id="{icons[0]["id"]}" instance="{icons[0]["id"]}_instance"', x)
        self.assertTrue(x.rstrip().endswith("</xpsm>"))


if __name__ == "__main__":
    unittest.main()
