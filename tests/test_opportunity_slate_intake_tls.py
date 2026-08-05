"""Real-TLS-server integration tests for the guarded public-link import —
PS-OPPSLATE-001 slice OS-6, independent review finding F5.

Why this module exists, separate from tests/test_opportunity_slate_intake.py:
every SSRF/fetch test in that file replaces
``services.opportunity_source_intake_service._PinnedHTTPSConnection`` with a
fake, so ``connect()`` (the DNS-then-pin mechanism that is the whole point
of that class) and the TLS handshake are never actually executed by that
suite — a mutation test that removed the IP pin, or one that disabled
certificate verification, would still leave that suite fully green. This
module closes that hole: it runs a real self-signed-certificate TLS server
on ``127.0.0.1`` in a background thread and drives the REAL
``_PinnedHTTPSConnection`` class and the REAL ``guarded_fetch_html``
orchestration against it — the only things replaced are ``_resolve_public_ip``
(so a loopback address, otherwise correctly refused by the SSRF guard
tested exhaustively elsewhere, can stand in for a "resolved public IP" in
this narrowly-scoped connection-mechanics test) and the port this build's
import guard accepts (``IMPORT_ALLOWED_PORT``, patched to the test server's
ephemeral port so this suite never needs to bind the privileged port 443).

The only production-code seam this module relies on is
``_PinnedHTTPSConnection(..., ssl_context=...)`` /
``guarded_fetch_html(url, ssl_context=...)`` — documented at its definition
as a test-only parameter that defaults to ``None`` (real
``ssl.create_default_context()``, full verification) everywhere production
code calls it. This module supplies a context that adds ONE throwaway,
freshly-generated, in-memory self-signed CA as an additional trusted root —
it never disables hostname checking or certificate verification.
"""

import datetime
import ipaddress
import socket
import ssl
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

import services.opportunity_source_intake_service as intake
from services.opportunity_source_intake_service import OpportunitySourceIntakeError


TEST_HOSTNAME = "os6-test.local"
TEST_HOSTNAME_HOP2 = "os6-test-hop2.local"


def _generate_self_signed_cert(hostnames):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostnames[0])])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(h) for h in hostnames]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return cert_pem, key_pem


class _TLSTestServer:
    """A one-shot-per-connection TLS server on 127.0.0.1, driven by a
    per-test handler function ``handler(tls_socket) -> None`` that writes
    whatever raw HTTP response bytes the test wants, with full control over
    timing, framing, and connection-closing behaviour."""

    def __init__(self, handler, cert_pem, key_pem):
        self._handler = handler
        self._raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._raw.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._raw.bind(("127.0.0.1", 0))
        self._raw.listen(5)
        self.port = self._raw.getsockname()[1]

        import os
        import tempfile

        certdir = tempfile.mkdtemp()
        self._certfile = os.path.join(certdir, "cert.pem")
        self._keyfile = os.path.join(certdir, "key.pem")
        with open(self._certfile, "wb") as f:
            f.write(cert_pem)
        with open(self._keyfile, "wb") as f:
            f.write(key_pem)

        self._context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self._context.load_cert_chain(self._certfile, self._keyfile)
        self._threads = []
        self._stop = False
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        self._raw.settimeout(0.2)
        while not self._stop:
            try:
                conn, _addr = self._raw.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            t = threading.Thread(target=self._serve_one, args=(conn,), daemon=True)
            t.start()
            self._threads.append(t)

    def _serve_one(self, conn):
        try:
            tls_conn = self._context.wrap_socket(conn, server_side=True)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return
        try:
            self._handler(tls_conn)
        except Exception:
            pass
        finally:
            try:
                tls_conn.close()
            except Exception:
                pass

    def close(self):
        self._stop = True
        try:
            self._raw.close()
        except Exception:
            pass


def _client_ssl_context(cert_pem):
    context = ssl.create_default_context(cadata=cert_pem.decode("ascii"))
    return context


def _read_request(tls_conn):
    """Drain one HTTP request off the wire (headers only; this module's
    requests carry no body) so the server behaves like a real HTTP peer."""
    buf = b""
    tls_conn.settimeout(5)
    while b"\r\n\r\n" not in buf:
        chunk = tls_conn.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf


class RealConnectMechanicsTests(unittest.TestCase):
    """The two unit tests independent review F5 asks for directly: proof
    that the real connect() dials the PINNED numeric IP (never the
    hostname) and presents the ORIGINAL hostname as TLS SNI — with no real
    socket or server involved, just a mocked socket.create_connection."""

    def test_connect_dials_the_pinned_ip_not_the_hostname(self):
        with patch.object(intake.socket, "create_connection") as create_connection:
            fake_sock = object()
            create_connection.return_value = fake_sock
            # A MagicMock, not a bare object(): connect() also arms the
            # deadline onto the resulting socket (self.sock._os6_deadline =
            # ...), which a plain object() cannot accept an attribute for.
            fake_ssl_sock = MagicMock()
            fake_context = MagicMock()
            fake_context.wrap_socket.return_value = fake_ssl_sock

            connection = intake._PinnedHTTPSConnection(
                "203.0.113.9", "careers.example.com", 443, timeout=5,
                ssl_context=fake_context,
            )
            connection.connect()

        create_connection.assert_called_once_with(("203.0.113.9", 443), timeout=5)
        self.assertIsNot(create_connection.call_args[0][0][0], "careers.example.com")

    def test_connect_presents_the_original_hostname_as_sni(self):
        with patch.object(intake.socket, "create_connection") as create_connection:
            fake_sock = object()
            create_connection.return_value = fake_sock
            fake_context = MagicMock()

            connection = intake._PinnedHTTPSConnection(
                "203.0.113.9", "careers.example.com", 443, timeout=5,
                ssl_context=fake_context,
            )
            connection.connect()

        fake_context.wrap_socket.assert_called_once_with(
            fake_sock, server_hostname="careers.example.com"
        )


class RealTLSFetchTests(unittest.TestCase):
    """Drives the REAL _PinnedHTTPSConnection + guarded_fetch_html against
    a REAL local TLS server. _resolve_public_ip is mocked to hand back
    127.0.0.1 (this test's job is the connection/read mechanics, not the
    already-and-separately-tested SSRF address classification), and
    IMPORT_ALLOWED_PORT is patched to the test server's ephemeral port so
    this suite never needs the privileged port 443."""

    @classmethod
    def setUpClass(cls):
        cls.cert_pem, cls.key_pem = _generate_self_signed_cert(
            [TEST_HOSTNAME, TEST_HOSTNAME_HOP2]
        )
        cls.client_context = _client_ssl_context(cls.cert_pem)

    def _serve(self, handler):
        server = _TLSTestServer(handler, self.cert_pem, self.key_pem)
        self.addCleanup(server.close)
        return server

    def _fetch(self, server, hostname=TEST_HOSTNAME, path="/", **kwargs):
        with patch.object(
            intake, "_resolve_public_ip",
            return_value=(2, ipaddress.ip_address("127.0.0.1")),
        ), patch.object(intake, "IMPORT_ALLOWED_PORT", server.port):
            return intake.guarded_fetch_html(
                f"https://{hostname}{path}", ssl_context=self.client_context, **kwargs
            )

    # -- happy path -----------------------------------------------------

    def test_happy_path_ordinary_content_length_response(self):
        def handler(tls_conn):
            _read_request(tls_conn)
            body = b"<html><body>Senior Engineer role.</body></html>"
            resp = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"\r\n" + body
            )
            tls_conn.sendall(resp)

        server = self._serve(handler)
        page = self._fetch(server)
        self.assertIn(b"Senior Engineer", page.data)

    # -- R1: the five real-server response-framing shapes -----------------
    #
    # Independent review R1: the dominant real-server shape — nginx/Apache/
    # IIS/CDNs answering a client that asked for "Connection: close" (which
    # this module's request always does) with BOTH Content-Length AND
    # Connection: close — failed with OSError EBADF under the previous
    # fix's per-iteration raw_sock.settimeout() call: the read that
    # consumes the LAST Content-Length byte also triggers http.client's own
    # _close_conn() internally, closing the file descriptor, and the loop's
    # settimeout() call on the NEXT iteration ran before it had checked
    # whether the previous read had returned empty. The current design (a
    # deadline armed once on the socket, consulted only from inside real
    # recv/recv_into/read calls — see _DeadlineSSLSocket) has nothing left
    # to crash on: there is no separate settimeout() call in the loop for a
    # closed connection to be stale for. All five shapes below must
    # round-trip correctly.

    def _assert_shape_round_trips(self, marker, resp_bytes):
        def handler(tls_conn):
            _read_request(tls_conn)
            tls_conn.sendall(resp_bytes)

        server = self._serve(handler)
        page = self._fetch(server)
        self.assertIn(marker, page.data)

    def test_shape_cl_close_content_length_and_connection_close(self):
        """The exact R1 trigger shape, and the dominant real shape for a
        client that sends its own Connection: close, which this module
        always does."""
        body = b"<html><body>cl_close body.</body></html>"
        resp = (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + body
        )
        self._assert_shape_round_trips(b"cl_close body.", resp)

    def test_shape_close_nocl_connection_close_no_length(self):
        body = b"<html><body>close_nocl body.</body></html>"
        resp = (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
            b"Connection: close\r\n\r\n" + body
        )
        self._assert_shape_round_trips(b"close_nocl body.", resp)

    def test_shape_cl_only_content_length_no_explicit_close_header(self):
        """A server that answers with Content-Length and no Connection
        header at all — the client's own "Connection: close" request
        header is what ends the exchange, not anything the server states."""
        body = b"<html><body>cl_only body.</body></html>"
        resp = (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
        )
        self._assert_shape_round_trips(b"cl_only body.", resp)

    def test_shape_eof_no_length_no_close_header(self):
        """Pure HTTP/1.0-style EOF delimiting: no Content-Length, no
        Transfer-Encoding, no Connection header at all — the body simply
        ends when the server closes the socket."""
        body = b"<html><body>eof body.</body></html>"
        resp = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + body
        self._assert_shape_round_trips(b"eof body.", resp)

    def test_shape_chunked_close_transfer_encoding_and_connection_close(self):
        body = b"chunked_close body."
        chunk = hex(len(body))[2:].encode() + b"\r\n" + body + b"\r\n0\r\n\r\n"
        resp = (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
            b"Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n" + chunk
        )
        self._assert_shape_round_trips(b"chunked_close body.", resp)

    # -- oversize stream ---------------------------------------------------

    def test_oversize_stream_is_refused_without_buffering_it_all(self):
        def handler(tls_conn):
            _read_request(tls_conn)
            header = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
            tls_conn.sendall(header)
            chunk = b"A" * 65536
            try:
                for _ in range(200):  # ~13MB, over MAX_IMPORT_RESPONSE_BYTES
                    tls_conn.sendall(chunk)
            except Exception:
                pass

        server = self._serve(handler)
        with patch.object(intake, "MAX_IMPORT_RESPONSE_BYTES", 1024 * 1024):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                self._fetch(server)
        self.assertEqual(error.exception.code, "response_too_large")

    # -- F2: chunked slowloris, short deadline ----------------------------

    def test_chunked_slowloris_aborts_within_the_deadline(self):
        """Direct regression test for F2/R2: before the fix, a single
        response.read(n) call could loop internally forever as long as the
        server kept the connection minimally alive, because the deadline
        was only checked BETWEEN read() calls that never returned. This
        server dribbles chunked-encoded bytes slowly enough that the OLD
        code would run well past any reasonable deadline; the deadline-aware
        socket wrapper (_DeadlineSSLSocket), armed once and consulted on
        every real recv/recv_into/read, must abort close to the deadline
        instead — it is the load-bearing bound now, not a per-call
        settimeout the body loop manages itself."""

        def handler(tls_conn):
            _read_request(tls_conn)
            header = (
                b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                b"Transfer-Encoding: chunked\r\n\r\n"
            )
            tls_conn.sendall(header)
            try:
                for _ in range(200):
                    word = b"slow "
                    chunk = hex(len(word))[2:].encode() + b"\r\n" + word + b"\r\n"
                    tls_conn.sendall(chunk)
                    time.sleep(0.5)
            except Exception:
                pass

        server = self._serve(handler)
        deadline_seconds = 2.0
        start = time.monotonic()
        with patch.object(intake, "IMPORT_TOTAL_TIMEOUT_SECONDS", deadline_seconds):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                self._fetch(server)
        elapsed = time.monotonic() - start
        self.assertEqual(error.exception.code, "timeout")
        # Bounded close to the deadline, not the ~100s the slowloris
        # schedule above would take to finish on its own (200 * 0.5s).
        self.assertLess(elapsed, deadline_seconds + 3.0)

    # -- R2: a header-dribbling server ---------------------------------

    def test_header_dribbling_server_aborts_within_the_deadline(self):
        """Direct regression test for R2: getresponse() reads the status
        line and every header via repeated readline() calls, entirely
        before this module's body loop ever runs — a per-recv timeout
        cannot bound that internal loop any more than it can bound the
        body-read loop F2 fixed, because each individual recv() can keep
        succeeding on a byte or two forever. Measured directly before this
        fix: a header-dribbling server blocked getresponse() for 300+
        seconds against a supposed 10-second deadline. The deadline-aware
        socket wrapper is what closes this — armed once, right after the
        TLS handshake, it governs every real socket read from the status
        line onward, not just the body."""

        def handler(tls_conn):
            _read_request(tls_conn)
            header_bytes = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html\r\n"
                b"Content-Length: 5\r\n"
                b"\r\n"
            )
            try:
                for byte in header_bytes:
                    tls_conn.sendall(bytes([byte]))
                    time.sleep(0.2)
                # Never reached within the deadline this test sets, but
                # present so a non-deadline-bound implementation would
                # eventually complete rather than hang forever.
                tls_conn.sendall(b"hello")
            except Exception:
                pass

        server = self._serve(handler)
        deadline_seconds = 2.0
        start = time.monotonic()
        with patch.object(intake, "IMPORT_TOTAL_TIMEOUT_SECONDS", deadline_seconds):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                self._fetch(server)
        elapsed = time.monotonic() - start
        self.assertEqual(error.exception.code, "timeout")
        # The header_bytes schedule above is ~63 bytes * 0.2s =~ 12.6s to
        # finish sending headers alone (before any body); bounded well
        # under that, close to the 2s deadline, is the proof.
        self.assertLess(elapsed, deadline_seconds + 3.0)

    # -- redirect with re-pin ---------------------------------------------

    def test_redirect_is_independently_resolved_and_repinned_on_the_new_host(self):
        """One physical server, dispatching on the Host header, models two
        distinct upstream hosts without needing two ports/IPs — the
        property under test is that the SECOND hop is independently
        resolved (a fresh _resolve_public_ip call, for the NEW hostname)
        and gets its OWN _PinnedHTTPSConnection/TLS handshake, exactly as
        a real redirect across two different servers would require."""

        def handler(tls_conn):
            request = _read_request(tls_conn)
            if f"Host: {TEST_HOSTNAME}\r\n".encode() in request:
                location = f"https://{TEST_HOSTNAME_HOP2}/final"
                resp = (
                    b"HTTP/1.1 302 Found\r\n"
                    b"Location: " + location.encode() + b"\r\n"
                    b"Content-Length: 0\r\n\r\n"
                )
            else:
                body = b"<html><body>Final hop content.</body></html>"
                resp = (
                    b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
                )
            tls_conn.sendall(resp)

        server = self._serve(handler)
        with patch.object(
            intake, "_resolve_public_ip",
            return_value=(2, ipaddress.ip_address("127.0.0.1")),
        ) as resolve, patch.object(intake, "IMPORT_ALLOWED_PORT", server.port):
            page = intake.guarded_fetch_html(
                f"https://{TEST_HOSTNAME}/start", ssl_context=self.client_context
            )
        self.assertIn(b"Final hop content.", page.data)
        self.assertEqual(page.final_url, f"https://{TEST_HOSTNAME_HOP2}/final")
        resolved_hosts = [call.args[0] for call in resolve.call_args_list]
        self.assertEqual(resolved_hosts, [TEST_HOSTNAME, TEST_HOSTNAME_HOP2])

    def test_a_wrong_ca_is_still_rejected_verification_is_not_silently_off(self):
        """Sanity check that the test seam itself is not a security hole:
        a client context that does NOT trust this test's self-signed CA
        must still fail the handshake, proving _PinnedHTTPSConnection
        performs real certificate verification rather than the test seam
        having quietly disabled it.

        Independent review finding N1: the original version of this test
        could not distinguish "verification correctly rejected the cert"
        from "verification was silently disabled, and the request then
        failed for some unrelated reason" — both produced the same
        code="fetch_failed" (the handler sent nothing, so even a
        non-verifying client would have gotten an empty/failed response).
        Two independent strengthenings, either of which alone would catch
        a TLS-verification-disabled mutation: (1) the handler now serves a
        genuinely valid response, so a non-verifying client would SUCCEED
        and return real page data — the assertion below would then fail
        outright, rather than merely returning a differently-labelled
        error; (2) the raised error's cause chain is asserted to be
        specifically ssl.SSLCertVerificationError, not merely "some
        OSError happened"."""

        def handler(tls_conn):
            _read_request(tls_conn)
            body = b"<html><body>should never be read by an untrusting client.</body></html>"
            resp = (
                b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
            )
            try:
                tls_conn.sendall(resp)
            except Exception:
                pass

        server = self._serve(handler)
        untrusting_context = ssl.create_default_context()  # trusts only real public CAs
        with patch.object(
            intake, "_resolve_public_ip",
            return_value=(2, ipaddress.ip_address("127.0.0.1")),
        ), patch.object(intake, "IMPORT_ALLOWED_PORT", server.port):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                intake.guarded_fetch_html(
                    f"https://{TEST_HOSTNAME}/", ssl_context=untrusting_context
                )
        self.assertEqual(error.exception.code, "fetch_failed")
        cause = error.exception.__cause__
        self.assertIsInstance(
            cause,
            ssl.SSLCertVerificationError,
            f"expected a certificate verification failure, got {type(cause)!r}: {cause!r}",
        )


if __name__ == "__main__":
    unittest.main()
