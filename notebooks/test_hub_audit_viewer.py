"""Offline tests for kalanos_hub_audit_viewer.ipynb.

The notebook's setup cell is executed as written. Downloads run against a local
HTTPS server (self-signed certificate for `localhost`), so no network is needed.
This is not a Colab test and never contacts hub.kalanos.ai.
"""

import contextlib
import importlib.util
import io
import json
import os
import re
import socket
import ssl
import struct
import subprocess
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).parent


# The notebook's helper cell imports these. Colab has them; a plain Python install may not.
REQUIRED = ("IPython", "ipywidgets", "markdown_it", "bleach")
if missing := [name for name in REQUIRED if importlib.util.find_spec(name) is None]:
    raise SystemExit(
        f"Missing Python packages: {', '.join(missing)}.\n"
        "Install them in a throwaway virtualenv, then run this file with it:\n"
        "  python3 -m venv /tmp/kalanos-nb && /tmp/kalanos-nb/bin/pip install -q -r "
        f"{HERE / 'requirements-test.txt'}\n"
        f"  /tmp/kalanos-nb/bin/python {Path(__file__).resolve()}"
    )
NB = json.loads((HERE / "kalanos_hub_audit_viewer.ipynb").read_text())
CODES = ["".join(c["source"]) for c in NB["cells"] if c["cell_type"] == "code"]
SETUP = CODES[1]  # helpers cell; CODES[0] is %pip, CODES[2] launches the viewer
FIXTURE = HERE / "tests" / "fixtures" / "utokyo_audit.md"
SLUG = "/d/@kalanos/hf/lerobot/utokyo_xarm_pick_and_place"


def load_helpers(**overrides):
    """Run the helper cell exactly as written and return its namespace."""
    ns = {"__name__": "nb"}
    exec(compile(SETUP, "<helpers>", "exec"), ns)  # noqa: S102
    ns.update(overrides)
    return ns


class UrlTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_helpers()

    def test_accepts_page_md_and_audit_forms(self):
        base = "https://hub.kalanos.ai" + SLUG
        for url in (
            base,
            base + "/",
            base + "/audit.md",
            base + ".md",
            base + "?tab=x#y",
            "https://hub.kalanos.ai/d/%40kalanos/hf/lerobot/utokyo_xarm_pick_and_place",
            "  " + base + "  ",
        ):
            report = self.ns["resolve_report_url"](url)
            self.assertEqual(report.audit_url, base + "/audit.md", url)
            self.assertEqual(report.name, "lerobot/utokyo_xarm_pick_and_place")

    def test_legacy_namespace_without_tenant(self):
        report = self.ns["resolve_report_url"](
            "https://hub.kalanos.ai/d/hf/lerobot/pusht"
        )
        self.assertEqual(
            report.audit_url, "https://hub.kalanos.ai/d/hf/lerobot/pusht/audit.md"
        )

    def test_rejects_unsafe_links(self):
        for url in (
            "",
            None,
            "http://hub.kalanos.ai" + SLUG,
            "https://evil.example" + SLUG,
            "https://hub.kalanos.ai.evil.example" + SLUG,
            "https://user:pw@hub.kalanos.ai" + SLUG,
            "https://hub.kalanos.ai:8443" + SLUG,
            "https://hub.kalanos.ai/d/@kalanos/hf/../../etc/passwd",
            "https://hub.kalanos.ai/d/@kalanos/hf/lerobot/..",
            "https://hub.kalanos.ai/d/@kalanos/hf/lerobot/a%2Fb",
            "https://hub.kalanos.ai/d/@kalanos/xx/lerobot/pusht",
            "https://hub.kalanos.ai/dashboard",
            "https://hub.kalanos.ai/d/@kalanos/hf/lerobot",
            "https://hub.kalanos.ai/d/@kalanos/hf/lerobot/pusht/extra",
            "file:///etc/passwd",
        ):
            with self.assertRaises(self.ns["AuditError"], msg=str(url)):
                self.ns["resolve_report_url"](url)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_helpers()
        self.text = FIXTURE.read_text()

    def test_real_report_keeps_every_section_and_tables(self):
        out = self.ns["render_markdown"](self.text)
        for heading in re.findall(r"(?m)^## (.+)$", self.text):
            self.assertIn(html_escape(heading), out, heading)
        self.assertNotIn("<script", out)
        self.assertIn("Kalanos score: 89.9 / 100", out)
        self.assertIn("101 pass · 1 review · 0 blocked · 0 unknown", out)

    def test_html_scripts_media_and_bad_links_are_inert(self):
        evil = (
            "<script>alert(1)</script> <img src=x onerror=alert(2)>\n\n"
            "![pixel](https://evil.example/p.png)\n\n"
            "[a](javascript:alert(3)) [b](http://hub.kalanos.ai/x) [c](https://evil.example/x)\n\n"
            "[d](/d/@kalanos/hf/a/b) <https://evil.example/auto> <iframe src=x></iframe>\n\n"
            "[ok](https://hub.kalanos.ai/d/@k/hf/a/b) [hf](https://huggingface.co/datasets/a/b)\n"
        )
        out = self.ns["render_markdown"](evil)
        # Escaped text such as "&lt;img ... onerror=" is harmless; live tags are not.
        for bad in (
            "<script",
            "<img",
            "<iframe",
            'href="javascript',
            "evil.example/x",
            "http://hub",
        ):
            self.assertNotIn(bad, out, bad)
        self.assertNotIn('href="https://evil', out)
        for good in (
            'href="https://hub.kalanos.ai/d/@k/hf/a/b"',
            'href="https://huggingface.co/datasets/a/b"',
        ):
            self.assertIn(good, out)

    def test_tables_render_and_stay_inert(self):
        out = self.ns["render_markdown"](
            "| a | b |\n|---|---|\n| <b onclick=x>1</b> | 2 |\n"
        )
        self.assertIn("<table>", out)
        self.assertNotIn("<b ", out)  # shown as escaped text, not a live tag

    def test_every_anchor_is_https_and_allowlisted(self):
        out = self.ns["render_markdown"](self.text)
        for href in re.findall(r'href="([^"]*)"', out):
            self.assertRegex(href, r"^https://(hub\.kalanos\.ai|huggingface\.co)/")

    def test_identity_is_best_effort_and_never_invented(self):
        got = self.ns["read_identity"](self.text)
        self.assertEqual(got["assessed"], "2026-10-31T00:39:20Z")
        self.assertEqual(
            got["source_revision"], "da56c23e1b6d32c101c300b85dc54288b53ea63c"
        )
        self.assertIsNone(got["report_id"])  # audit.md does not carry it
        self.assertEqual(
            self.ns["read_identity"]("# x\n"),
            {"assessed": None, "source_revision": None, "report_id": None},
        )

    def test_snapshot_zip_keeps_original_bytes(self):
        report = self.ns["resolve_report_url"]("https://hub.kalanos.ai" + SLUG)
        audit = self.ns["Fetched"](
            raw=FIXTURE.read_bytes(),
            text=self.text,
            url=report.audit_url,
            retrieved_at="2026-11-17T00:00:00Z",
            sha256="0" * 64,
        )
        with zipfile.ZipFile(io.BytesIO(self.ns["snapshot_bytes"](report, audit))) as z:
            self.assertEqual(z.read("audit.md"), FIXTURE.read_bytes())
            meta = json.loads(z.read("snapshot.json"))
        self.assertEqual(meta["retrieved_at_utc"], "2026-11-17T00:00:00Z")
        self.assertEqual(meta["report_url"], report.report_url)


def html_escape(text):
    import html

    return html.escape(text)


def make_certificate(directory):
    cert, key = directory / "c.pem", directory / "k.pem"
    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-days",
                "2",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=DNS:localhost",
            ],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return cert, key


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def handle(self):
        try:
            super().handle()
        except OSError:  # reset, broken pipe or TLS EOF
            pass  # the client stopped reading on purpose (size-limit cases)

    def reply(self, code, body=b"", kind="text/markdown; charset=utf-8", **headers):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(headers.pop("length", len(body))))
        for key, value in headers.items():
            self.send_header(key.replace("_", "-"), value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.removesuffix("/audit.md")
        if path == SLUG:
            return self.reply(200, FIXTURE.read_bytes())
        match path.rsplit("/", 1)[-1]:
            case "private":
                return self.reply(403, b"no", "text/plain")
            case "missing":
                return self.reply(404, b"no", "text/plain")
            case "limited":
                return self.reply(429, b"slow", "text/plain", Retry_After="30")
            case "broken":
                return self.reply(503, b"x", "text/plain")
            case "html":
                return self.reply(200, b"<html>", "text/html")
            case "binary":
                return self.reply(200, b"\xff\xfe\x00", "text/plain")
            case "empty":
                return self.reply(200, b"  \n", "text/plain")
            case "huge":
                return self.reply(200, b"a" * (2 * 1024 * 1024 + 10))
            case "huge-chunked":  # no Content-Length: the read cap must catch it
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(b"a" * (2 * 1024 * 1024 + 10))
                self.close_connection = True
                return None
            case "redirect":
                self.send_response(302)
                self.send_header("Location", "https://evil.example/audit.md")
                self.end_headers()
                return None
            case "reset":  # promise a body, then abort with a TCP reset
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", "5000")
                self.end_headers()
                self.wfile.write(b"partial")
                self.wfile.flush()
                self.connection.setsockopt(
                    socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
                )
                self.connection.close()
                return None
            case "short":  # fewer bytes than Content-Length, clean close
                return self.reply(200, b"partial", "text/plain", length=5000)
        return self.reply(404, b"no", "text/plain")


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        made = make_certificate(Path(cls.tmp.name))
        if made is None:
            raise unittest.SkipTest("openssl not available")
        server = HTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(*map(str, made))
        server.socket = context.wrap_socket(server.socket, server_side=True)
        cls.server = server
        threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.client_ctx = ssl.create_default_context(cafile=str(made[0]))
        cls.netloc = f"localhost:{server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def setUp(self):
        self.ns = load_helpers(HUB_NETLOCS={self.netloc})

    def get(self, path):
        return self.ns["fetch_audit"](
            f"https://{self.netloc}{path}/audit.md", ssl_context=self.client_ctx
        )

    def refuses(self, path, fragment):
        with self.assertRaises(self.ns["AuditError"]) as caught:
            self.get(path)
        self.assertIn(fragment, str(caught.exception))

    def test_success_keeps_original_bytes_and_records_time(self):
        got = self.get(SLUG)
        self.assertEqual(got.raw, FIXTURE.read_bytes())
        self.assertRegex(got.retrieved_at, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(len(got.sha256), 64)

    def test_http_failures_are_readable(self):
        self.refuses("/d/@k/hf/o/private", "sign-in")
        self.refuses("/d/@k/hf/o/missing", "No public export")
        self.refuses("/d/@k/hf/o/limited", "30")
        self.refuses("/d/@k/hf/o/broken", "HTTP 503")

    def test_bad_payloads_are_refused(self):
        self.refuses("/d/@k/hf/o/html", "text/html")
        self.refuses("/d/@k/hf/o/binary", "UTF-8")
        self.refuses("/d/@k/hf/o/empty", "empty")
        self.refuses("/d/@k/hf/o/huge", "limit")
        self.refuses("/d/@k/hf/o/huge-chunked", "limit")

    def test_redirect_off_host_is_stopped(self):
        self.refuses("/d/@k/hf/o/redirect", "redirected somewhere unexpected")

    def test_unreachable_host_is_readable(self):
        self.ns["TIMEOUT_SECONDS"] = 2
        self.ns["HUB_NETLOCS"] = {"localhost:1"}
        with self.assertRaises(self.ns["AuditError"]) as caught:
            self.ns["fetch_audit"](
                "https://localhost:1/d/@a/hf/b/c/audit.md", ssl_context=self.client_ctx
            )
        self.assertIn("Could not reach", str(caught.exception))

    def test_connection_dropped_mid_download_is_readable(self):
        # A truncated or reset body must become an AuditError, not a traceback.
        for name in ("reset", "short"):
            with self.subTest(name), self.assertRaises(self.ns["AuditError"]):
                self.get(f"/d/@k/hf/o/{name}")


class ViewerFlowTests(unittest.TestCase):
    """Drive the widget handlers the way the buttons do, with a fake fetcher."""

    def setUp(self):
        quiet = contextlib.redirect_stdout(
            io.StringIO()
        )  # the viewer prints progress lines
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)
        self.ns = load_helpers()
        self.shown = []
        self.ns["display"] = self.shown.append
        self.text = FIXTURE.read_text()
        self.cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.cwd)

    def build(self, fetcher):
        self.ns["ViewerState"].load.__defaults__ = (fetcher,)
        url = "https://hub.kalanos.ai" + SLUG
        state = self.ns["make_viewer"](url)
        box = next(x for x in self.shown if hasattr(x, "children"))
        field, buttons, output, _ = box.children
        return state, field, buttons.children[0], buttons.children[1], output

    def ok_fetcher(self, audit_url):
        raw = self.text.encode()
        return self.ns["Fetched"](
            raw, self.text, audit_url, "2026-11-17T00:00:00Z", "ab" * 32
        )

    def test_run_all_loads_but_never_downloads(self):
        state, _, _, save, _ = self.build(self.ok_fetcher)
        self.assertIsNotNone(state.audit)
        self.assertFalse(save.disabled)
        self.assertEqual(list(Path(".").iterdir()), [])

    def test_editing_url_invalidates_previous_report(self):
        state, field, _, save, _ = self.build(self.ok_fetcher)
        field.value = field.value + "x"
        self.assertIsNone(state.audit)
        self.assertTrue(save.disabled)

    def test_failed_load_clears_previous_report(self):
        calls = []

        def flaky(audit_url):
            calls.append(audit_url)
            if len(calls) > 1:
                raise self.ns["AuditError"]("boom")
            return self.ok_fetcher(audit_url)

        state, _, load, save, _ = self.build(flaky)
        load.click()
        self.assertIsNone(state.audit)
        self.assertTrue(save.disabled)
        self.assertFalse(load.disabled)

    def test_unexpected_network_error_does_not_leave_button_stuck(self):
        def exploding(audit_url):
            raise ConnectionResetError("peer reset")

        with contextlib.redirect_stdout(io.StringIO()) as printed:
            _, _, load, save, _ = self.build(exploding)
        self.assertFalse(load.disabled)
        self.assertTrue(save.disabled)
        self.assertIn("Could not load assessment", printed.getvalue())

    def test_snapshot_button_writes_original_bytes(self):
        _, _, _, save, _ = self.build(self.ok_fetcher)
        save.click()
        (zip_path,) = Path(".").glob("kalanos-audit-*.zip")
        with zipfile.ZipFile(zip_path) as z:
            self.assertEqual(z.read("audit.md"), self.text.encode())


class StructureTests(unittest.TestCase):
    def test_notebook_is_clean(self):
        for cell in NB["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell.get("outputs"), [])
                self.assertIsNone(cell.get("execution_count"))
        for code in CODES:
            self.assertLessEqual(code.count("# @title"), 1, "one title per form cell")

    def test_setup_pins_only_what_colab_lacks(self):
        pip = CODES[0]
        self.assertIn("markdown-it-py==", pip)
        self.assertIn("bleach==", pip)
        self.assertNotIn("ipywidgets", pip, "Colab ships its own ipywidgets")


if __name__ == "__main__":
    # Local sockets closed by the size-limit cases raise ResourceWarning; they are test plumbing.
    unittest.main(warnings="ignore")
