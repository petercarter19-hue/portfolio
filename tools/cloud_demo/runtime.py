"""One authenticated fictional owner per process, with durable atomic state."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import html
from http.cookies import SimpleCookie
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash
from werkzeug.wrappers import Request, Response

from tools.local_reviewer.persistence import SnapshotStore, atomic_write
from tools.local_reviewer.runtime import build_fixture, offline_html, OFFLINE_CSP

SESSION = '__Host-peerslate-demo'
LOGIN = '__Host-peerslate-demo-login'
MAX_BODY = 4_000_000
MAX_STATE = 16_000_000


def sync_directory(directory):
    """Persist a new checkpoint name before its associated state is cleared."""
    if os.name != 'posix':
        return  # The hosted cloud demo runs on Linux; Windows only runs tests.
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class Config:
    origin: str
    username: str
    password_hash: str
    signing_key: str
    owner: str
    namespace: str
    data: Path
    source_sha: str
    ttl: int = 86400

    def validate(self):
        parsed = urlsplit(self.origin)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment
                or not re.fullmatch(r'[a-z0-9.-]+(?::[0-9]+)?', parsed.netloc)):
            raise ValueError('Exact HTTPS demo origin required')
        if not re.fullmatch(r'[a-z0-9-]{3,50}', self.username):
            raise ValueError('Restricted account required')
        if not self.password_hash.startswith('scrypt:') or len(self.signing_key) < 64:
            raise ValueError('Dedicated hash and signing key required')
        if self.owner not in {'g-member-a', 'g-member-b', 'g-member-c'}:
            raise ValueError('Dedicated fictional owner required')
        if not re.fullmatch(r'[0-9a-f]{64}', self.namespace) or not re.fullmatch(r'[0-9a-f]{40}', self.source_sha):
            raise ValueError('Immutable namespace/source required')
        if self.namespace != hashlib.sha256((self.origin + '\0' + self.owner).encode()).hexdigest():
            raise ValueError('Snapshot namespace must bind this site and owner')
        if not 60 <= self.ttl <= 86400:
            raise ValueError('Bounded session expiry required')
        if not self.data.is_absolute() or any(p.is_symlink() for p in (self.data, *self.data.parents)):
            raise ValueError('Ordinary absolute persistent demo storage required')
        return self

    @classmethod
    def from_environment(cls):
        # Capture dedicated cloud settings before the fixture drops inherited
        # environment credentials. None enter product or provider configuration.
        return cls(os.environ['DEMO_ORIGIN'], os.environ['DEMO_USERNAME'],
                   os.environ['DEMO_PASSWORD_HASH'], os.environ['DEMO_SIGNING_KEY'],
                   os.environ['DEMO_OWNER'], os.environ['DEMO_NAMESPACE'],
                   Path(os.environ['DEMO_DATA']), os.environ['DEMO_SOURCE_SHA']).validate()


class ProcessLock:
    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        self.file = (directory / 'writer.lock').open('a+b')
        if self.file.tell() == 0:
            self.file.write(b'1')
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('Another process owns this demo; refuse startup') from None

    def close(self):
        self.file.close()


class Sessions:
    def __init__(self, config, clock=time.time):
        self.config, self.clock = config, clock
        self.path = config.data / 'sessions.sqlite3'
        if self.path.is_symlink():
            raise ValueError('Session storage link refused')
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, expires REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (stamp REAL NOT NULL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def begin_login(self):
        now = self.clock()
        with self.connect() as db:
            db.execute('DELETE FROM attempts WHERE stamp < ?', (now - 60,))
            if db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0] >= 12:
                return False
            db.execute('INSERT INTO attempts VALUES (?)', (now,))
        return True

    def create(self):
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires <= ?', (self.clock(),))
            db.execute('INSERT INTO sessions VALUES (?, ?)', (self.digest(token), self.clock() + self.config.ttl))
        return token

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def valid(self, token):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            return False
        with self.connect() as db:
            row = db.execute('SELECT expires FROM sessions WHERE digest = ?', (self.digest(token),)).fetchone()
        return bool(row and row[0] > self.clock())

    def revoke(self, token):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE digest = ?', (self.digest(token),))


class Boundary:
    def __init__(self, config, app, endpoints, store, *, fresh_state=None, clock=time.time):
        self.config = config.validate()
        self.app, self.endpoints, self.store = app, frozenset(endpoints), store
        self.lock = threading.RLock()
        self.sessions = Sessions(config, clock)
        self.signer = URLSafeTimedSerializer(config.signing_key, salt='cloud-demo-login')
        self.reset_signer = URLSafeTimedSerializer(config.signing_key, salt='cloud-demo-reset')
        self.fresh_state = store.state.capture() if fresh_state is None else fresh_state
        store.state.validate(self.fresh_state)

    @staticmethod
    def error(message, status):
        return Response(message, status=status, content_type='text/plain; charset=utf-8')

    def login(self, environ, cookies):
        method = environ['REQUEST_METHOD']
        if method == 'GET':
            nonce = secrets.token_urlsafe(32)
            response = Response('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PeerSlate fictional demo sign in</title><main><h1>Sign in to your fictional demo</h1><p>Separate fictional content is saved in this cloud demo. Use fictional information only. AI and speech are unavailable. Nothing is automatically published.</p><form method="post"><input type="hidden" name="csrf" value="' + nonce + '"><p><label>Demo account <input name="username" autocomplete="username" required maxlength="50"></label></p><p><label>Password <input type="password" name="password" autocomplete="current-password" required maxlength="200"></label></p><button>Sign in</button></form></main></html>', content_type='text/html; charset=utf-8')
            response.set_cookie(LOGIN, self.signer.dumps(nonce), secure=True, httponly=True, samesite='Strict', max_age=1800)
            return response
        if method != 'POST':
            return self.error('Method unavailable', 405)
        if int(environ.get('CONTENT_LENGTH') or 0) > 2000:
            return self.error('Login too large', 413)
        request = Request(environ)
        try:
            signed = self.signer.loads(cookies.get(LOGIN).value if cookies.get(LOGIN) else '', max_age=1800)
        except (BadSignature, SignatureExpired):
            return self.error('Open sign in again', 403)
        if not hmac.compare_digest(str(signed), request.form.get('csrf', '')):
            return self.error('Open sign in again', 403)
        if not self.sessions.begin_login():
            return self.error('Too many attempts. Try again in one minute.', 429)
        username, password = request.form.get('username', ''), request.form.get('password', '')
        password_valid = check_password_hash(self.config.password_hash, password)
        if not hmac.compare_digest(username.encode('utf-8'), self.config.username.encode('utf-8')) or not password_valid:
            return self.error('Demo account or password is incorrect', 403)
        response = Response(status=303, headers={'Location': '/app/resume'})
        response.set_cookie(SESSION, self.sessions.create(), secure=True, httponly=True, samesite='Strict', max_age=self.config.ttl)
        response.delete_cookie(LOGIN, secure=True, httponly=True, samesite='Strict')
        return response

    def reset_demo(self, environ, session_token):
        """Confirmed, recoverable reset of this authenticated site's fixture."""
        method = environ['REQUEST_METHOD']
        if method == 'GET':
            ticket = self.reset_signer.dumps({
                'session': self.sessions.digest(session_token),
                'namespace': self.config.namespace,
                'generation': self.store.generation,
            })
            page = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>Reset fictional demo</title><main><h1>Reset this fictional demo?</h1>'
                    '<p>This clears saved fictional content on this site after saving a recovery copy. Other sites are unaffected.</p>'
                    '<form method="post" action="/demo/reset"><input type="hidden" name="ticket" value="' + html.escape(ticket, quote=True) + '">'
                    '<button type="submit">Reset this demo</button></form><p><a href="/app/resume">Cancel</a></p></main></html>')
            return Response(page, content_type='text/html; charset=utf-8')
        if method != 'POST':
            return self.error('Method unavailable', 405)
        if int(environ.get('CONTENT_LENGTH') or 0) > 2000:
            return self.error('Reset request too large', 413)
        try:
            ticket = Request(environ).form.get('ticket', '')
            signed = self.reset_signer.loads(ticket, max_age=300)
        except (BadSignature, SignatureExpired, ValueError):
            return self.error('Open reset confirmation again', 403)
        expected = {'session': self.sessions.digest(session_token),
                    'namespace': self.config.namespace, 'generation': self.store.generation}
        if signed != expected:
            return self.error('Saved content changed. Open reset confirmation again.', 409)
        current = self.store.state.capture()
        saved = self.store.path.read_bytes()
        if self.store.unpack(saved)['state'] != current:
            raise ValueError('Saved and active demo state differ')
        directory = self.config.data / 'checkpoints'
        if directory.is_symlink():
            raise ValueError('Checkpoint directory is a link')
        directory.mkdir(exist_ok=True)
        sync_directory(self.config.data)
        name = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + secrets.token_hex(8) + '.json'
        checkpoint = directory / name
        if checkpoint.exists() or checkpoint.is_symlink():
            raise ValueError('Checkpoint name collision')
        atomic_write(checkpoint, saved)
        sync_directory(directory)
        self.store.state.restore(self.fresh_state)
        environ['peerslate.reset_save'] = True
        return Response('<!doctype html><html lang="en"><meta charset="utf-8"><title>Demo reset</title>'
                        '<main><h1>Fictional demo reset</h1><p>A recovery copy was saved. This site is ready for a fresh test.</p>'
                        '<a href="/app/resume">Open your fresh demo</a></main></html>',
                        content_type='text/html; charset=utf-8')

    def dispatch(self, environ):
        method, path = environ.get('REQUEST_METHOD', ''), environ.get('PATH_INFO', '')
        expected_host = urlsplit(self.config.origin).netloc
        if environ.get('HTTP_HOST') != expected_host:
            return self.error('Demo host refused', 403)
        if method not in {'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH'}:
            return self.error('Method unavailable', 405)
        if any(k.startswith(('HTTP_TAILSCALE_', 'HTTP_X_MS_CLIENT_PRINCIPAL', 'HTTP_X_REVIEWER_', 'HTTP_X_DEMO_OWNER')) for k in environ):
            return self.error('Client identity headers refused', 403)
        origin = environ.get('HTTP_ORIGIN')
        if origin is not None and origin != self.config.origin or environ.get('HTTP_SEC_FETCH_SITE') == 'cross-site':
            return self.error('Foreign origin refused', 403)
        if method not in {'GET', 'HEAD'} and origin != self.config.origin:
            return self.error('Same-origin mutation required', 403)
        try:
            size = int(environ.get('CONTENT_LENGTH') or 0)
            if not 0 <= size <= MAX_BODY:
                return self.error('Request too large', 413)
            cookies = SimpleCookie()
            cookies.load(environ.get('HTTP_COOKIE', ''))
        except (ValueError, TypeError):
            return self.error('Invalid request', 400)
        if any(name in cookies for name in ('mvp1-synthetic-owner', 'reviewer-fictional-owner')):
            return self.error('Client owner selector refused', 403)
        if path == '/healthz' and method == 'GET':
            return Response('{"status":"ok","release":"' + self.config.source_sha + '"}', content_type='application/json')
        if path == '/login':
            return self.login(environ, cookies)
        token = cookies.get(SESSION).value if cookies.get(SESSION) else ''
        if not self.sessions.valid(token):
            if path in {'/', '/app/resume'} and method in {'GET', 'HEAD'}:
                return Response(status=303, headers={'Location': '/login'})
            return self.error('Demo sign in required', 401)
        if any(name.lower() in {'owner', 'owner_id', 'user_key', 'workspace', 'member'} for name in parse_qs(environ.get('QUERY_STRING', ''), keep_blank_values=True)):
            return self.error('Client owner selector refused', 403)
        if path == '/logout' and method == 'POST':
            self.sessions.revoke(token)
            response = Response(status=303, headers={'Location': '/login'})
            response.delete_cookie(SESSION, secure=True, httponly=True, samesite='Strict')
            return response
        if path == '/demo/reset':
            return self.reset_demo(environ, token)
        if path == '/':
            return Response(status=303, headers={'Location': '/app/resume'})
        if path.startswith(('/__', '/auth/')):
            return self.error('Route unavailable in fictional demo', 404)
        # All product requests get identity from this authenticated site only.
        for key in list(environ):
            if key.startswith(('HTTP_X_FORWARDED_', 'HTTP_X_MS_', 'HTTP_TAILSCALE_')) or key == 'HTTP_FORWARDED':
                del environ[key]
        cookies.pop(SESSION, None)
        cookies.pop(LOGIN, None)
        environ['HTTP_COOKIE'] = '; '.join(k + '=' + v.coded_value for k, v in cookies.items())
        environ['cloud_demo.authenticated'] = True
        environ['wsgi.url_scheme'] = 'https'
        environ['HTTP_ACCEPT_ENCODING'] = 'identity'
        environ['SERVER_NAME'], environ['SERVER_PORT'] = urlsplit(self.config.origin).hostname, str(urlsplit(self.config.origin).port or 443)
        try:
            endpoint, _ = self.app.url_map.bind_to_environ(environ).match()
        except Exception:
            return self.error('Route unavailable in fictional demo', 404)
        if endpoint not in self.endpoints:
            return self.error('Route unavailable in fictional demo', 404)
        response = Response.from_app(self.app, environ, buffered=True)
        if response.mimetype == 'text/html' and not response.headers.get('Content-Encoding'):
            body = offline_html(response.get_data())
            start = body.find(b'<body')
            position = body.find(b'>', start) + 1 if start >= 0 else -1
            if position > 0:
                banner = ('<aside role="note" style="padding:10px;background:#e8f1fb;color:#17324d"><strong>FICTIONAL CLOUD DEMO.</strong> Separate fictional content saved in this cloud demo. Files up to 4 MB. AI and speech are unavailable. Review and save deliberately; publishing stays inside your authenticated demo. <a href="/demo/reset">Reset this demo</a></aside>').encode()
                response.set_data(body[:position] + banner + body[position:])
        return response

    def __call__(self, environ, start_response):
        # One complete response/atomic commit at a time. No success leaves this
        # boundary until its state is durable; errors restore in-memory state.
        with self.lock:
            previous = self.store.state.capture()
            try:
                response = self.dispatch(environ)
                current = self.store.state.capture()
                if current != previous or environ.get('peerslate.reset_save'):
                    if len(self.store.pack(current, self.store.generation + 1)) > MAX_STATE:
                        raise ValueError('Demo snapshot limit')
                    self.store.save(current)
            except Exception:
                self.store.state.restore(previous)
                response = self.error('Operation unavailable. Previous saved content is preserved.', 503)
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        response.headers.add('Content-Security-Policy', OFFLINE_CSP)
        return response(environ, start_response)


def create_application(source: Path, config: Config, stack: ExitStack):
    config.validate()
    lease = ProcessLock(config.data)
    stack.callback(lease.close)
    fixture, app, endpoints, state = build_fixture(source, stack, live_ai=False)
    from flask import request
    from identity import AuthenticationRequired, PeerSlatePrincipal

    def principal():
        if request.environ.get('cloud_demo.authenticated') is not True:
            raise AuthenticationRequired()
        return PeerSlatePrincipal('development', 'fictional-cloud-demo', config.owner,
                                  display_name='Fictional Demo Member', is_development=True)

    stack.enter_context(patch('identity.get_current_principal', side_effect=principal))
    stack.enter_context(patch('auth_routes.get_current_principal', side_effect=principal))
    app.config.update(TESTING=False, SECRET_KEY=config.signing_key,
                     TRUSTED_HOSTS=[urlsplit(config.origin).hostname],
                     SESSION_COOKIE_NAME='__Host-peerslate-demo-flask',
                     SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True,
                     SESSION_COOKIE_SAMESITE='Strict', MAX_CONTENT_LENGTH=MAX_BODY,
                     PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
                     PEERSLATE_MEMBER_VISITOR_AI_ENABLED=False,
                     MEMBER_VISITOR_AI_SERVICE=None, MEMBER_VISITOR_AI_RUNTIME=None)
    fresh_state = state.capture()
    store = SnapshotStore(config.data / 'state.json', state, namespace=config.namespace)
    if store.path.exists():
        if store.path.stat().st_size > MAX_STATE:
            raise ValueError('Existing snapshot too large; preserve it')
        store.load()
    else:
        # New dedicated empty fixture only; never load/copy/reset the PC state.
        store.save()
    return Boundary(config, app, endpoints, store, fresh_state=fresh_state)
