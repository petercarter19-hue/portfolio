"""Browser-suite test servers must not stall behind an idle connection.

Chrome opens speculative preconnect sockets and keeps idle keep-alive sockets
from earlier pages. A single-threaded werkzeug server accepts such a socket and
then blocks reading a request that never arrives, so every later request,
including the next page load, waits until the browser gives the socket up
(about 20 s). That stalled the intake browser suite in CI on 2026-10-09.

The fix is ``make_server(..., threaded=True)``, as in
``tests/mvp1_acceptance_support.py``. This module needs no browser: it holds
the idle socket itself, so it also runs in the application-test job.
"""

from __future__ import annotations

import ast
import http.client
import logging
import socket
import threading
import unittest
from pathlib import Path

from flask import Flask
from werkzeug.serving import make_server


TESTS = Path(__file__).resolve().parent

# Suites still serving single-threaded, each owned by another package. Remove
# an entry when its owner switches it to ``threaded=True``.
KNOWN_SINGLE_THREADED = {
    "test_my_data_browser.py": "PS-ONBOARDING-CONVERSATION-002",
    "test_workshop_accessibility.py": "opt-in Workshop proof, not run in CI",
}


def _page_application():
    application = Flask(__name__)

    @application.get("/")
    def page():
        return "<!doctype html><title>Loaded</title><p>page loaded</p>"

    return application


def _load_page(port, timeout):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        connection.request("GET", "/")
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def _stop_server(server, thread):
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


class IdleConnectionPageLoadTests(unittest.TestCase):
    def setUp(self):
        logger = logging.getLogger("werkzeug")
        self.addCleanup(logger.setLevel, logger.level)
        logger.setLevel(logging.ERROR)

    def _serve(self, *, threaded):
        server = make_server("127.0.0.1", 0, _page_application(), threaded=threaded)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(_stop_server, server, thread)
        return server.server_port

    def _hold_idle_connection(self, port):
        # Registered after the server, so it closes first and frees a
        # single-threaded server to shut down.
        idle = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.addCleanup(idle.close)

    def test_threaded_server_loads_a_page_while_an_idle_connection_is_open(self):
        port = self._serve(threaded=True)
        self._hold_idle_connection(port)
        # A stalled server never answers while the idle socket stays open, so
        # finishing inside the client timeout is the proof.
        status, body = _load_page(port, timeout=5)
        self.assertEqual(status, 200)
        self.assertIn(b"page loaded", body)

    def test_single_threaded_server_stalls_behind_an_idle_connection(self):
        """Control: the page-load check above can see the stall it guards."""
        port = self._serve(threaded=False)
        self._hold_idle_connection(port)
        with self.assertRaises(TimeoutError):
            _load_page(port, timeout=1.0)


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


class BrowserSuiteServerGuardTests(unittest.TestCase):
    def test_every_test_server_is_threaded(self):
        single_threaded = set()
        for path in sorted(TESTS.rglob("*.py")):
            if path == Path(__file__).resolve():
                continue  # its control serves single-threaded on purpose
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and _call_name(node.func) == "make_server"):
                    continue
                threaded = next(
                    (keyword.value for keyword in node.keywords if keyword.arg == "threaded"),
                    None,
                )
                if not (isinstance(threaded, ast.Constant) and threaded.value is True):
                    single_threaded.add(path.relative_to(TESTS).as_posix())
        self.assertEqual(
            sorted(single_threaded - set(KNOWN_SINGLE_THREADED)),
            [],
            "start test servers with make_server(..., threaded=True) so an idle "
            "browser connection cannot stall page loads",
        )


if __name__ == "__main__":
    unittest.main()
