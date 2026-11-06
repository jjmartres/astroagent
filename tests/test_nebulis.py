"""End-to-end tests of skills/nebulis/scripts/nebulis.py against a mock Nebulis server.

Run: python3 -m unittest discover -s tests
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mock_nebulis  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "nebulis" / "scripts" / "nebulis.py"


class NebulisCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = mock_nebulis.start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def run_cli(self, *args, key=mock_nebulis.KEY):
        env = {**os.environ, "NEBULIS_URL": self.url, "NEBULIS_API_KEY": key, "HOME": tempfile.mkdtemp()}
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=60)

    def test_status(self):
        r = self.run_cli("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Nebulis 2.2.0", r.stdout)
        self.assertNotIn(mock_nebulis.KEY, r.stdout + r.stderr)

    def test_bad_key(self):
        r = self.run_cli("objects", key="neb-wrong")
        self.assertEqual(r.returncode, 3)
        self.assertIn("401", r.stderr)
        self.assertNotIn("neb-wrong", r.stdout + r.stderr)

    def test_sessions_sorted(self):
        r = self.run_cli("sessions", "Sh2-105")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertTrue(lines[0].startswith("2026-09-05"))

    def test_analysis(self):
        r = self.run_cli("analysis", "Sh2-105", "2026-09-05")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("kept 2/3", r.stdout)
        self.assertIn("clouds 1", r.stdout)
        r = self.run_cli("analysis", "Sh2-105", "2026-09-05", "--bad-only")
        self.assertNotIn("a.fits", r.stdout)
        self.assertIn("b.fits", r.stdout)
        self.assertIn("c.fits", r.stdout)

    def test_review(self):
        r = self.run_cli("review", "--reject", "Sh2-105/b.fits")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(mock_nebulis.STATE["reviews"][-1], {"path": "Sh2-105/b.fits", "keep": False})
        self.run_cli("review", "--reset", "Sh2-105/b.fits")
        self.assertEqual(mock_nebulis.STATE["reviews"][-1], {"path": "Sh2-105/b.fits", "keep": None})

    def test_plan(self):
        r = self.run_cli("plan", "Sh2-105", "--all")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("flat_other_night", r.stdout)
        self.assertIn("Flat_D1", r.stdout)

    def test_fetch_requires_allow_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli("fetch", "Sh2-105", "--all", "--dest", d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("--allow-warnings", r.stderr)
            self.assertEqual(os.listdir(d), [])

    def test_fetch_and_refetch(self):
        mock_nebulis.STATE["polls"] = 0
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli("--json", "fetch", "Sh2-105", "--all", "--dest", d, "--allow-warnings")
            self.assertEqual(r.returncode, 0, r.stderr)
            summary = json.loads(r.stdout)
            root = Path(summary["path"])
            self.assertTrue((root / "manifest.json").is_file())
            self.assertEqual(summary["lights"], 4)
            self.assertEqual(summary["expectedLights"], 4)
            self.assertEqual(sorted(os.listdir(d)), [root.name])  # temp folder cleaned up
            mock_nebulis.STATE["polls"] = 0
            r = self.run_cli("fetch", "Sh2-105", "--all", "--dest", d, "--allow-warnings")
            self.assertEqual(r.returncode, 1)
            self.assertIn("--force", r.stderr)
            mock_nebulis.STATE["polls"] = 0
            r = self.run_cli("fetch", "Sh2-105", "--all", "--dest", d, "--allow-warnings", "--force")
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_push_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "PROCESSING.md").write_text("# log")
            (Path(d) / "final.jpg").write_bytes(b"\xff\xd8")
            r = self.run_cli("push", "Sh2-105", "--bundle", d, "--name", "Sh2-105_test.zip")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Sh2-105_test.zip", mock_nebulis.STATE["uploads"])
            r = self.run_cli("push", "Sh2-105", "--bundle", d, "--name", "Sh2-105_test.zip")
            self.assertEqual(r.returncode, 1)
            self.assertIn("already stored", r.stderr)

    def test_push_refuses_other_types(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
            r = self.run_cli("push", "Sh2-105", "--file", f.name)
            self.assertEqual(r.returncode, 1)
            self.assertIn(".zip", r.stderr)

    def test_missing_config(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("NEBULIS_")}
        env["HOME"] = tempfile.mkdtemp()
        r = subprocess.run([sys.executable, str(SCRIPT), "status"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("NEBULIS_URL", r.stderr)


if __name__ == "__main__":
    unittest.main()
