"""Uploads of nebulis.py: streamed single POST, chunked upload, resume, fallback, bundle zip.

Against the local stub in mock_nebulis.py (old multipart endpoints and the /uploads API).
The test over 2.1 GiB is opt-in: ASTROAGENT_TEST_LARGE=1 python3 -m unittest tests.test_nebulis_upload
"""
import contextlib
import hashlib
import io
import os
import re
import resource
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import mock_nebulis  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "nebulis" / "scripts" / "nebulis.py"
sys.path.insert(0, str(SCRIPT.parent))
import nebulis  # noqa: E402

MiB = 1 << 20


def make_file(path: Path, mib: int) -> str:
    """mib MiB where every MiB differs (its index in front), so a misplaced chunk changes the hash."""
    h = hashlib.sha256()
    base = os.urandom(MiB)
    with open(path, "wb") as fh:
        for i in range(mib):
            block = i.to_bytes(8, "big") + base[8:]
            fh.write(block)
            h.update(block)
    return h.hexdigest()


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 * MiB), b""):
            h.update(block)
    return h.hexdigest()


class UploadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = mock_nebulis.start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def setUp(self):
        st = mock_nebulis.STATE
        st.update(chunked=True, chunk_size=8 * MiB, drop_chunks=set(), puts=[])
        st["uploads"].clear()
        st["images"].clear()
        st["files"].clear()

    def env(self):
        return {**os.environ, "ASTROAGENT_NEBULIS_URL": self.url, "ASTROAGENT_NEBULIS_API_KEY": mock_nebulis.KEY,
                "HOME": tempfile.mkdtemp(), "ASTROAGENT_NEBULIS_RETRY_BASE": "0.01"}

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                              env=self.env(), timeout=600)

    def run_inproc(self, *args):
        """main() in this process, so library calls can be patched. Returns (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.dict(os.environ, self.env()), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                nebulis.main(list(args))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def stored(self, name):
        return mock_nebulis.STATE["files"][name]

    # ── chunked ──

    def test_chunked_few_hundred_mb(self):
        f = self.dir / "Sh2-105_big_processing.zip"
        digest = make_file(f, 300)
        r = self.run_cli("push", "Sh2-105", "--file", str(f), "--chunked", "--title", "big")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = self.stored(f.name)
        self.assertEqual(rec["via"], "chunked")
        self.assertEqual(rec["size"], f.stat().st_size)
        self.assertEqual(rec["sha256"], digest)
        self.assertEqual(sha256(rec["path"]), digest)  # the bytes themselves, not only the claim
        self.assertEqual(rec["fields"]["title"], "big")
        self.assertIn("stored Sh2-105_big_processing.zip (300.0 MB)", r.stdout)
        progress = [ln for ln in r.stderr.splitlines() if re.search(r" / 300\.0 MB$", ln)]
        self.assertTrue(1 <= len(progress) <= 21, r.stderr)
        self.assertFalse(nebulis.resume_path(self.upload_ids()[-1]).exists())

    def upload_ids(self):
        return list(mock_nebulis.STATE["sessions"])

    def test_resume_after_dropped_chunk(self):
        f = self.dir / "Sh2-105_resume_processing.zip"
        digest = make_file(f, 40)  # 5 chunks of 8 MiB
        mock_nebulis.STATE["drop_chunks"] = {2}
        r = self.run_cli("push", "Sh2-105", "--file", str(f), "--chunked")
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertEqual(mock_nebulis.STATE["puts"].count(2), 1 + nebulis.CHUNK_RETRIES)
        uid = re.search(r"--resume (\S+)", r.stderr).group(1)
        self.assertIn(f"nebulis.py push Sh2-105 --resume {uid}", r.stderr)
        self.assertTrue(nebulis.resume_path(uid).is_file())
        self.assertNotIn(f.name, mock_nebulis.STATE["files"])
        mock_nebulis.STATE["drop_chunks"] = set()
        mock_nebulis.STATE["puts"] = []
        r = self.run_cli("push", "Sh2-105", "--resume", uid)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(mock_nebulis.STATE["puts"], [2, 3, 4])  # only what the server is missing
        self.assertEqual(self.stored(f.name)["sha256"], digest)
        self.assertEqual(sha256(self.stored(f.name)["path"]), digest)
        self.assertFalse(nebulis.resume_path(uid).exists())

    def test_ctrl_c_leaves_upload_resumable(self):
        f = self.dir / "Sh2-105_ctrlc_processing.zip"
        digest = make_file(f, 24)
        real = nebulis.Client.put_bytes
        calls = []

        def put(self_, path, data, headers):
            calls.append(path)
            if len(calls) == 2:
                raise KeyboardInterrupt
            return real(self_, path, data, headers)

        with mock.patch.object(nebulis.Client, "put_bytes", put):
            code, _, err = self.run_inproc("push", "Sh2-105", "--file", str(f), "--chunked")
        self.assertEqual(code, 4, err)
        uid = re.search(r"--resume (\S+)", err).group(1)
        self.assertIn(uid, mock_nebulis.STATE["sessions"])  # not deleted
        r = self.run_cli("push", "Sh2-105", "--resume", uid)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.stored(f.name)["sha256"], digest)

    def test_resume_of_bundle_does_not_rezip(self):
        d = self.dir / "bundle-resume"
        (d / "final").mkdir(parents=True)
        make_file(d / "final" / "x.xisf", 20)
        mock_nebulis.STATE["drop_chunks"] = {1}
        r = self.run_cli("push", "Sh2-105", "--bundle", str(d), "--name", "Sh2-105_b_processing.zip", "--chunked")
        self.assertEqual(r.returncode, 4, r.stderr)
        uid = re.search(r"--resume (\S+)", r.stderr).group(1)
        state = nebulis.read_resume(uid)
        zpath = Path(state["path"])
        self.assertTrue(zpath.is_file())  # the zip is kept for --resume
        mock_nebulis.STATE["drop_chunks"] = set()
        r = self.run_cli("push", "Sh2-105", "--resume", uid)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("zipping", r.stderr)
        self.assertFalse(zpath.parent.exists())  # temporary zip removed once stored

    # ── fallback and limits ──

    def test_fallback_to_single_post(self):
        mock_nebulis.STATE["chunked"] = False
        f = self.dir / "Sh2-105_old_processing.zip"
        digest = make_file(f, 12)
        r = self.run_cli("push", "Sh2-105", "--file", str(f), "--chunked")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no chunked upload API", r.stderr)
        self.assertEqual(self.stored(f.name)["via"], "post")
        self.assertEqual(self.stored(f.name)["sha256"], digest)

    def test_refuses_over_2_gib_without_chunked_api(self):
        mock_nebulis.STATE["chunked"] = False
        f = self.dir / "Sh2-105_huge.tif"
        with open(f, "wb") as fh:
            fh.truncate((2 << 30) + 1)  # sparse: no disk used
        try:
            r = self.run_cli("image", "Sh2-105", "--file", str(f))
        finally:
            f.unlink()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("Nebulis 2.2.0 has no chunked upload; files over 2.0 GB need Nebulis ≥", r.stderr)
        self.assertNotIn(f.name, mock_nebulis.STATE["files"])

    def test_oserror_during_send_is_not_cannot_reach(self):
        # The macOS failure: send() of the body raises EINVAL. The server was reached.
        mock_nebulis.STATE["chunked"] = False
        f = self.dir / "Sh2-105_einval_processing.zip"
        make_file(f, 20)
        real = nebulis.http.client.HTTPConnection.send
        sent = []

        def send(self_, data):
            if len(data) == nebulis.STREAM_BLOCK:
                sent.append(len(data))
            if len(sent) == 2:  # fail on the second 8 MiB block of the file
                raise OSError(22, "Invalid argument")
            return real(self_, data)

        with mock.patch.object(nebulis.http.client.HTTPConnection, "send", send):
            code, _, err = self.run_inproc("push", "Sh2-105", "--file", str(f))
        self.assertEqual(code, 3, err)
        self.assertIn("upload failed after 8.0 MB of 20.0 MB: [Errno 22] Invalid argument", err)
        self.assertNotIn("cannot reach", err)

    def test_cannot_reach_only_without_connection(self):
        f = self.dir / "Sh2-105_x.jpg"
        f.write_bytes(b"\xff\xd8\xff\xd9")
        env = {**self.env(), "ASTROAGENT_NEBULIS_URL": "http://127.0.0.1:9"}
        r = subprocess.run([sys.executable, str(SCRIPT), "status"], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 3)
        self.assertIn("cannot reach", r.stderr)

    # ── image unchanged ──

    def test_image_27_mb_as_before(self):
        f = self.dir / "Sh2-105_final.jpg"
        digest = make_file(f, 27)
        r = self.run_cli("image", "Sh2-105", "--file", str(f), "--title", "SHO final")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "added image Sh2-105_final.jpg (27.0 MB) to Sh2-105\n")
        self.assertEqual(r.stderr, "uploading Sh2-105_final.jpg (27.0 MB)\n")
        self.assertEqual(self.stored(f.name)["via"], "post")
        self.assertEqual(self.stored(f.name)["sha256"], digest)
        self.assertEqual(self.stored(f.name)["fields"], {"title": "SHO final"})

    # ── bundle ──

    def test_bundle_zip_members(self):
        d = self.dir / "bundle"
        proj = d / "pixinsight" / "M52.pxiproject"
        (proj / "M52.data").mkdir(parents=True)
        (d / "final").mkdir()
        (d / "doc").mkdir()
        (d / "PROCESSING.md").write_text("# log\n" * 100)
        (d / "rig.json").write_text('{"a": 1}')
        (d / "doc" / "index.html").write_text("<p>x</p>")
        (d / "final" / "M52.xisf").write_bytes(b"\0" * 4096)
        (d / "final" / "M52.jpg").write_bytes(b"\xff\xd8" * 100)
        (proj / "M52.xosm").write_text("<xml/>" * 100)
        (proj / "M52.data" / "view.xisf").write_bytes(b"\0" * 4096)
        r = self.run_cli("push", "Sh2-105", "--bundle", str(d), "--name", "Sh2-105_zip_processing.zip",
                         "--tmp", str(self.dir))
        self.assertEqual(r.returncode, 0, r.stderr)
        with zipfile.ZipFile(self.stored("Sh2-105_zip_processing.zip")["path"]) as zf:
            kinds = {i.filename: i.compress_type for i in zf.infolist()}
        S, D = zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED
        self.assertEqual(kinds, {
            "PROCESSING.md": D, "rig.json": D, "doc/index.html": D, "final/M52.xisf": S, "final/M52.jpg": S,
            "pixinsight/M52.pxiproject/M52.xosm": S, "pixinsight/M52.pxiproject/M52.data/view.xisf": S})
        self.assertEqual([p for p in self.dir.iterdir() if p.name.startswith("nebulis-push-")], [])

    def test_bundle_duplicate_checked_before_zipping(self):
        d = self.dir / "bundle-dup"
        d.mkdir()
        (d / "PROCESSING.md").write_text("# log")
        mock_nebulis.STATE["uploads"].append("Sh2-105_dup_processing.zip")
        r = self.run_cli("push", "Sh2-105", "--bundle", str(d), "--name", "Sh2-105_dup_processing.zip")
        self.assertEqual(r.returncode, 1)
        self.assertIn("already stored", r.stderr)
        self.assertNotIn("zipping", r.stderr)

    def test_bundle_checks_free_space(self):
        d = self.dir / "bundle-space"
        d.mkdir()
        (d / "PROCESSING.md").write_text("# log")
        usage = nebulis.shutil.disk_usage(self.dir)._replace(free=1024)
        with mock.patch.object(nebulis.shutil, "disk_usage", return_value=usage):
            code, _, err = self.run_inproc("push", "Sh2-105", "--bundle", str(d), "--name", "Sh2-105_s_processing.zip")
        self.assertEqual(code, 1)
        self.assertIn("not enough space", err)
        self.assertIn("--tmp DIR", err)

    # ── memory ──

    def test_no_read_bytes_of_the_file(self):
        f = self.dir / "Sh2-105_mem_processing.zip"
        make_file(f, 16)
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("read_bytes on an upload")):
            for extra in ([], ["--chunked", "--force"]):
                code, _, err = self.run_inproc("push", "Sh2-105", "--file", str(f), *extra)
                self.assertEqual(code, 0, err)

    def test_memory_stays_flat(self):
        f = self.dir / "Sh2-105_rss_processing.zip"
        make_file(f, 300)
        for extra in ([], ["--chunked", "--force"]):
            r = self.run_cli("push", "Sh2-105", "--file", str(f), *extra)
            self.assertEqual(r.returncode, 0, r.stderr)
        peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        peak_mb = peak / MiB if sys.platform == "darwin" else peak / 1024  # bytes on macOS, KiB on Linux
        self.assertLess(peak_mb, 120, f"a child process peaked at {peak_mb:.0f} MB for a 300 MB file")

    # ── opt-in: over 2.1 GiB ──

    @unittest.skipUnless(os.environ.get("ASTROAGENT_TEST_LARGE"), "set ASTROAGENT_TEST_LARGE=1 (writes 2.1 GiB)")
    def test_over_2_gib(self):
        f = self.dir / "Sh2-105_large_processing.zip"
        digest = make_file(f, 2150)
        try:
            for extra, via in (([], "post"), (["--chunked", "--force"], "chunked")):
                # Without --chunked the file goes chunked anyway (over 1 GiB): turn the API off
                # to force the streamed single POST, the path that failed on macOS.
                mock_nebulis.STATE["chunked"] = via == "chunked"
                r = self.run_cli("push", "Sh2-105", "--file", str(f), *extra)
                self.assertEqual(r.returncode, 0, r.stderr)
                rec = self.stored(f.name)
                self.assertEqual((rec["via"], rec["size"], rec["sha256"]), (via, f.stat().st_size, digest))
                os.unlink(rec["path"])
        finally:
            f.unlink()


if __name__ == "__main__":
    unittest.main()
