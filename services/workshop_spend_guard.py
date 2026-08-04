"""Workshop AI daily spend guard — PS-WORKSHOP-001 W2b (F2 correction).

**The gap this closes (independent Opus review, finding F2).** Before this
module, nothing durably bounded what a hostile visitor could spend against a
paid AI provider through the Workshop review/improve routes:

  - The per-session cap (``workshop_work_session.MAX_AI_CALLS_PER_SESSION``,
    20) lives entirely in the visitor's own signed session cookie. Clearing
    that cookie resets it for free, and two concurrent posts both read the
    same pre-increment cookie value, so it is not even reliable within one
    visit. It is a courtesy budget for an honest visitor, never a control
    against someone who does not want to be bounded.
  - flask-limiter's per-IP limit on these routes (``6 per minute``) uses the
    default in-memory storage — per worker process, lost on restart, and not
    coordinated across workers. It shapes burst rate; it does not cap a day.
  - There was no global ceiling of ANY kind. A scripted client rotating its
    cookie could bill the owner without limit.

This module adds the two missing durable ceilings: a per-UTC-day cap on
calls from one client address (``PER_IP_DAILY_AI_CALLS``) and a per-UTC-day
cap on calls from EVERYONE combined (``GLOBAL_DAILY_AI_CALLS``). The global
one is the real protection: it is the number that bounds the bill no matter
how many addresses, cookies, or workers are involved.

**Reserve before the call, never after.** ``reserve()`` performs the check
and the increment as one locked read-modify-write, and every caller invokes
it immediately BEFORE ``client.messages.create``. A call that then fails,
times out, or returns an unusable reply still counts — the thing being
bounded is provider requests ATTEMPTED, which is what actually costs money
and what an attacker actually controls. This mirrors the same
reserve-before-call discipline ``workshop_work_session.increment_ai_calls``
already documents for the per-session cap.

**Deliberate scope limit — one instance.** State is a single JSON file under
the Flask instance path, and mutual exclusion is an exclusive OS lock on
that file (``_lock_exclusive`` below). That is correct and genuinely atomic
for any number of threads, workers, or processes sharing ONE filesystem —
which is exactly today's single-App-Service-instance deployment. It is NOT
correct across scaled-out instances, which do not share an instance path:
each instance would enforce its own independent ceiling, so N instances
would permit N x the intended global cap. Revisit this with shared storage
(the Redis backend flask-limiter's own warning already points at, or a small
database table) BEFORE Workshop AI is served from more than one instance.
This limitation is disclosed rather than hidden precisely because scaling
out is the moment it silently stops holding.

**Failure posture: closed, and loud.** If the state file cannot be opened or
written, this module returns a capped outcome and logs an error rather than
letting the call through. An unwritable state file means spend cannot be
bounded at all, which is the exact condition this module exists to prevent;
allowing calls in that state would silently restore the unbounded-billing
gap while looking healthy. The visitor still gets an honest "today's limit"
state with their words intact and Save unfinished working, so the failure is
safe for the member and visible to the operator (``logger.error``) — the
same "an operator error must be loud, not silently downgraded" reasoning the
F6 signing-key correction on this branch already applies.
"""

import ipaddress
import json
import os
import time
from datetime import datetime, timezone

from flask import current_app, request

# Capability detection, done ONCE at import rather than as scattered
# ``sys.platform`` checks at the call sites: exactly one of these provides the
# exclusive file lock, and which one is decided here so the locking code below
# reads as a single contract. ``fcntl`` is POSIX-only and ``msvcrt`` is
# Windows-only; both are stdlib, so this adds no dependency. Before this,
# importing ``fcntl`` unconditionally made the whole module — and therefore
# ``app.py``, which imports it transitively — unimportable on Windows.
try:  # POSIX (Linux, macOS): production and CI
    import fcntl
except ImportError:  # pragma: no cover - depends on the running platform
    fcntl = None

try:  # Windows: local development
    import msvcrt
except ImportError:  # pragma: no cover - depends on the running platform
    msvcrt = None


# ---------------------------------------------------------------------------
# Ceilings
# ---------------------------------------------------------------------------

GLOBAL_DAILY_AI_CALLS = 400
PER_IP_DAILY_AI_CALLS = 40

# PS-WORKSHOP-001 W2d — voice transcription's OWN ceilings, deliberately
# separate counters rather than a share of the numbers above.
#
# They bill different providers. The review/improve/spark calls bounded by
# GLOBAL_DAILY_AI_CALLS go to Anthropic on ANTHROPIC_API_KEY. Workshop voice
# goes to Azure Speech fast transcription
# (services/speech_transcription_service.py, VOICE_SPEECH_ENDPOINT, Entra
# credential), which is a different vendor, a different meter, and a
# different bill. Conflating them would mean a visitor who dictated a lot
# could exhaust the budget for AI review — two unrelated costs silently
# competing — and would make either number impossible to reason about
# against its own invoice. So voice reserves against its own pair of
# counters in the same state file, under the same lock and the same UTC-day
# rollover.
#
# Sizing: Azure fast transcription is priced per audio-hour, so the ceiling
# that matters is total audio, not call count. At MAX seconds per recording
# (services/workshop_voice_service.MAX_WORKSHOP_VOICE_SECONDS, 90) the
# global cap here bounds the day at roughly 7.5 audio-hours no matter how
# many addresses, cookies, or workers are involved. The per-address number
# is generous for one honest person dictating all day and still small
# against the global one.
GLOBAL_DAILY_VOICE_TRANSCRIPTIONS = 300
PER_IP_DAILY_VOICE_TRANSCRIPTIONS = 30

STATE_FILENAME = "workshop_spend.json"

RESERVE_OK = "ok"
RESERVE_IP_CAPPED = "ip_capped"
RESERVE_GLOBAL_CAPPED = "global_capped"

# Which pair of counters a reservation touches. Adding a kind here is the
# only thing needed to bound a new provider separately; the lock, the day
# rollover, the fail-closed posture, and the atomicity are shared.
KIND_AI = "ai"
KIND_VOICE = "voice"

_KINDS = {
    KIND_AI: {
        "global_key": "global_count",
        "per_ip_key": "per_ip",
        "global_cap": lambda: GLOBAL_DAILY_AI_CALLS,
        "per_ip_cap": lambda: PER_IP_DAILY_AI_CALLS,
    },
    KIND_VOICE: {
        "global_key": "voice_global_count",
        "per_ip_key": "voice_per_ip",
        "global_cap": lambda: GLOBAL_DAILY_VOICE_TRANSCRIPTIONS,
        "per_ip_cap": lambda: PER_IP_DAILY_VOICE_TRANSCRIPTIONS,
    },
}

# One honest daily-limit message, deliberately distinct from
# workshop_work_session.AI_CALL_CAP_MESSAGE (the per-visit session cap).
# The two are different facts and must not read as the same one: the session
# cap is about THIS visit and clears when the visitor starts fresh; this one
# is about today across the whole preview and does not clear until tomorrow.
# Telling a visitor to "start fresh" here would be a false promise.
DAILY_CAP_MESSAGE = (
    "PeerSlate has reached today's limit for AI review across the whole "
    "preview — this is a daily limit, not something you did wrong, and "
    "starting fresh will not lift it. Your answer is still here, Save "
    "unfinished still works, and AI review is available again tomorrow."
)
DAILY_CAP_TITLE = "Today's preview limit reached"

# Longest client-address key stored. A real address is far shorter; this
# only bounds what a malformed value could write into the state file.
MAX_IP_KEY_CHARS = 64


# ---------------------------------------------------------------------------
# Client address — mirrors app.py's _client_rate_limit_key / _address_without_port
# ---------------------------------------------------------------------------


def _address_without_port(value):
    """The bare address from one X-Forwarded-For entry.

    Deliberate mirror of app.py's ``_address_without_port`` rather than an
    import: app.py imports workshop_work_routes (and therefore this module)
    at its line ~35, well before it defines this helper at ~217, so
    importing it here would be a circular/ordering problem — the same
    reasoning services/workshop_review_service.py's docstring records for
    ``_strip_md`` and the Anthropic client. Behavior is copied exactly, so
    this guard buckets a caller identically to the rate limiter.
    """
    if value.startswith("["):
        closing = value.find("]")
        return value[1:closing] if closing != -1 else value
    if value.count(":") == 1:
        return value.split(":", 1)[0]
    return value


def client_ip():
    """The calling client's address, derived exactly as app.py's
    ``_client_rate_limit_key`` derives it.

    Azure terminates TLS at the platform edge and APPENDS the real caller as
    the last X-Forwarded-For entry, so the rightmost entry is the only
    trustworthy one — a forged header can prepend values but never replace
    that appended one. Keying on ``request.remote_addr`` instead would put
    the entire internet in a single bucket (every request arrives from the
    edge address), which would make the per-IP ceiling here meaningless and
    let one visitor exhaust it for everyone.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    entries = [part.strip() for part in forwarded.split(",") if part.strip()]
    if entries:
        address = _address_without_port(entries[-1])
        try:
            ipaddress.ip_address(address)
        except ValueError:
            pass
        else:
            return address
    return request.remote_addr or "unknown"


# ---------------------------------------------------------------------------
# Exclusive lock — one implementation, selected at import
# ---------------------------------------------------------------------------

# The Windows lock covers this one byte at offset 0. ``msvcrt.locking`` locks a
# byte RANGE beginning at the handle's CURRENT position, not the whole file, so
# both helpers seek to 0 first and lock and unlock the identical region. Locking
# a byte of a file that may still be empty is fine — Windows permits a lock past
# end-of-file — and nothing ever reads through the lock, because every reader
# acquires it first. It is a rendezvous between openers, exactly as flock is.
_WINDOWS_LOCK_BYTES = 1

# How long a blocked Windows opener waits before trying again. msvcrt has no
# "block until acquired" mode: LK_LOCK retries on a fixed one-second cadence and
# then gives up with OSError after ten attempts. Measured here, ten simultaneous
# reservations under LK_LOCK take ~9s and come within a single attempt of that
# ceiling, which would turn ordinary contention into a spurious failure — a
# failure that fails CLOSED and would refuse legitimate AI calls. Retrying
# LK_NBLCK on a short interval instead reproduces flock(LOCK_EX)'s actual
# contract, wait as long as necessary, at a granularity matching the
# microseconds this module spends holding the lock.
_WINDOWS_LOCK_RETRY_SECONDS = 0.005


if fcntl is not None:

    def _lock_exclusive(handle):
        """Block until this handle alone may read-modify-write the state file."""
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    def _unlock(handle):
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

elif msvcrt is not None:

    def _lock_exclusive(handle):
        """Block until this handle alone may read-modify-write the state file.

        Byte-range locks are held per open handle, so two handles conflict even
        inside one process — threads are serialized here just as processes are.
        """
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, _WINDOWS_LOCK_BYTES)
            except OSError:
                time.sleep(_WINDOWS_LOCK_RETRY_SECONDS)
            else:
                return

    def _unlock(handle):
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, _WINDOWS_LOCK_BYTES)

else:  # pragma: no cover - reached only where BOTH backends are missing

    _NO_LOCK_MESSAGE = (
        "Workshop spend guard: neither fcntl nor msvcrt is available, so the "
        "daily AI spend ceilings cannot be enforced atomically on this "
        "platform. Refusing to run an unlocked counter, which would silently "
        "turn a spend ceiling into a suggestion."
    )

    def _lock_exclusive(handle):
        raise RuntimeError(_NO_LOCK_MESSAGE)

    def _unlock(handle):
        raise RuntimeError(_NO_LOCK_MESSAGE)


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------


def _utc_day():
    """Today's UTC date as ``YYYY-MM-DD``.

    UTC, not local time, so the rollover boundary is one fixed instant
    everywhere and cannot be moved by a server timezone change or by a
    daylight-saving transition (which would otherwise give a 23- or 25-hour
    "day", and in the 25-hour case a longer window than the cap intends).
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def state_path():
    """The state file's absolute path, creating the instance directory if it
    does not exist yet. Flask does not create ``instance_path`` itself, and
    a fresh checkout or a fresh container has never had it — so this must
    not assume it is there."""
    directory = current_app.instance_path
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, STATE_FILENAME)


def _fresh_state(day):
    state = {"day": day}
    for kind in _KINDS.values():
        state[kind["global_key"]] = 0
        state[kind["per_ip_key"]] = {}
    return state


def _count(value):
    """A non-negative int, or 0. ``isinstance(True, int)`` is True in
    Python, so a JSON ``true`` would otherwise be counted as 1."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _read_state(handle, today):
    """Today's counters from an already-locked handle.

    Anything that is not today's own well-formed state — an empty new file,
    yesterday's state (the automatic day rollover), or a file that cannot be
    parsed — becomes a fresh zeroed day. Resetting on an unparseable file is
    a deliberate choice: the alternative (refusing forever until an operator
    deletes the file) would take Workshop AI down permanently over one bad
    byte, and a torn write is only reachable by killing a process inside the
    microseconds between truncate and flush while it holds the exclusive
    lock. The global ceiling still bounds the day either way.
    """
    handle.seek(0)
    raw = handle.read()
    if not raw.strip():
        return _fresh_state(today)
    try:
        state = json.loads(raw)
    except (ValueError, TypeError):
        current_app.logger.warning(
            "Workshop spend guard: unreadable state file, starting today's counters fresh."
        )
        return _fresh_state(today)
    if not isinstance(state, dict) or state.get("day") != today:
        return _fresh_state(today)

    # Every kind's counters are read back, not only the one being reserved:
    # _write_state rewrites the whole file, so dropping a kind here would
    # silently zero another provider's ceiling on the next reservation.
    parsed = {"day": today}
    for kind in _KINDS.values():
        raw_per_ip = state.get(kind["per_ip_key"])
        per_ip = {}
        if isinstance(raw_per_ip, dict):
            for key, value in raw_per_ip.items():
                counted = _count(value)
                if counted:
                    per_ip[str(key)[:MAX_IP_KEY_CHARS]] = counted
        parsed[kind["global_key"]] = _count(state.get(kind["global_key"]))
        parsed[kind["per_ip_key"]] = per_ip
    return parsed


def _write_state(handle, state):
    """Rewrite the state file in place through an already-locked handle.

    In place (seek/write/truncate) rather than write-temp-and-rename,
    because the lock is held on this file's own open handle: replacing the
    path would give the next opener a DIFFERENT file whose lock does not
    conflict with a lock already held on the old one, quietly destroying the
    mutual exclusion this whole module depends on. That is true of both
    backends — flock is bound to the inode, and a Windows byte-range lock is
    bound to the handle — so the constraint is not POSIX-specific.
    """
    payload = json.dumps(state, separators=(",", ":"), sort_keys=True)
    handle.seek(0)
    handle.write(payload)
    handle.truncate()
    handle.flush()
    os.fsync(handle.fileno())


def reserve_voice(ip):
    """Reserve one Azure Speech transcription for ``ip`` against today's
    voice ceilings.

    Same contract, same lock, and the same reserve-BEFORE-the-call
    discipline as ``reserve`` — an attempted transcription is what costs
    money, so a call that then fails still counts. It touches the voice
    counters only: exhausting voice never blocks AI review, and exhausting
    AI review never blocks voice, because the two are different bills.
    """
    return _reserve(ip, KIND_VOICE)


def reserve(ip):
    """Reserve one AI call for ``ip`` against today's ceilings.

    Returns ``RESERVE_OK`` (the call may proceed and has been counted),
    ``RESERVE_IP_CAPPED`` (this address has used its own day's allowance),
    or ``RESERVE_GLOBAL_CAPPED`` (everyone together has used the day's
    allowance). Nothing is counted for a refused reservation — a refused
    request never reaches the provider, so it costs nothing and must not
    consume budget.

    The per-IP ceiling is checked first, so a single abusive address is
    named as such in the outcome rather than being masked by the global
    ceiling it is in the middle of exhausting.

    The whole check-and-increment happens inside one exclusive file lock, so
    ten simultaneous requests produce exactly ten increments and the
    (count == cap) boundary cannot be crossed twice — the precise defect the
    cookie-based session counter has.

    ``per_ip`` cannot grow without bound: an entry is only ever added by a
    successful reservation, and successful reservations are themselves
    capped at ``GLOBAL_DAILY_AI_CALLS`` per day, so the map holds at most
    that many keys before the day rolls over and it is discarded.
    """
    return _reserve(ip, KIND_AI)


def _reserve(ip, kind_name):
    """The shared reservation, parameterised only by which counters it moves."""
    kind = _KINDS[kind_name]
    global_key = kind["global_key"]
    per_ip_key = kind["per_ip_key"]
    global_cap = kind["global_cap"]()
    per_ip_cap = kind["per_ip_cap"]()

    key = str(ip or "unknown")[:MAX_IP_KEY_CHARS]
    today = _utc_day()

    try:
        path = state_path()
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError:
        current_app.logger.error(
            "Workshop spend guard: cannot open its state file; refusing AI calls "
            "rather than allowing unbounded provider spend."
        )
        return RESERVE_GLOBAL_CAPPED

    try:
        # "r+" (not "a+"): in append mode every write goes to end-of-file
        # regardless of seek, which would grow the file forever instead of
        # replacing its contents.
        with os.fdopen(descriptor, "r+", encoding="utf-8") as handle:
            _lock_exclusive(handle)
            try:
                state = _read_state(handle, today)
                if state[per_ip_key].get(key, 0) >= per_ip_cap:
                    return RESERVE_IP_CAPPED
                if state[global_key] >= global_cap:
                    return RESERVE_GLOBAL_CAPPED

                state[global_key] += 1
                state[per_ip_key][key] = state[per_ip_key].get(key, 0) + 1
                _write_state(handle, state)
                return RESERVE_OK
            finally:
                _unlock(handle)
    except OSError:
        current_app.logger.error(
            "Workshop spend guard: cannot record a reservation; refusing the AI "
            "call rather than allowing unbounded provider spend."
        )
        return RESERVE_GLOBAL_CAPPED
