"""Explicit artifact promotion and owned local process controls. No automatic pulls."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

from .persistence import atomic_write, canonical

DEFAULT_ROOT = Path("X:/PeerSlate/local-reviewer")
PORT = 53720
ID = "PS-LOCAL-REVIEWER-INSTALLATION-001"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    atomic_write(Path(path), canonical(value))


def safe_root(root):
    root = Path(root).absolute()
    if os.name == "nt" and root.drive.lower() != "x:":
        raise ValueError("This installation belongs on X")
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve() != root or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("Installation root must be an ordinary directory")
    return root


@contextmanager
def exclusive(root, filename="control.lock"):
    # OS lock is automatically released after a crash; no stale lock deletion.
    lock = (root / filename).open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            lock.seek(0)
            if lock.read(1) == b"":
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        lock.close()


def runtime_identity():
    packages = {re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(): d.version for d in importlib.metadata.distributions()}
    return {"python": sys.version.split()[0], "packages": packages}


def require_private_runtime(root, expected=None):
    if Path(sys.prefix).resolve() != (root / "runtime").resolve() or sys.version_info[:2] != (3, 12):
        raise ValueError("Use this installation's private Python3.12 runtime")
    actual = runtime_identity()
    if expected is not None and actual != expected:
        raise ValueError("Private runtime changed; prepare and explicitly validate an update")
    return actual


def verify_release(root, manifest):
    name = manifest["release"]
    if not re.fullmatch(r"[0-9a-f]{40}-[0-9a-f]{12}", name):
        raise ValueError("Invalid release identity")
    release = root / "releases" / name
    record = read(release / "release.json")
    if record != manifest["artifact"]:
        raise ValueError("Release metadata changed")
    if digest(release / "requirements-reviewed.txt") != record["overlay_sha256"]:
        raise ValueError("Reviewed dependency overlay changed")
    files = record["files"]
    actual = {str(p.relative_to(release / "source")).replace("\\", "/"): digest(p)
              for p in (release / "source").rglob("*") if p.is_file()}
    if any(p.is_symlink() for p in release.rglob("*")) or actual != files:
        raise ValueError("Immutable application files changed")
    require_private_runtime(root, manifest["runtime"])
    if "controller" in manifest:
        if not re.fullmatch(r"[0-9a-f]{64}", manifest["controller"]):
            raise ValueError("Invalid controller identity")
        directory = root / "controllers" / manifest["controller"]
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (directory, *directory.rglob("*"))):
            raise ValueError("Installed controller contains a link")
        actual_controller = {p.relative_to(directory).as_posix(): digest(p) for p in directory.rglob("*") if p.is_file()}
        if actual_controller != manifest["controller_files"] or hashlib.sha256(canonical(actual_controller)).hexdigest() != manifest["controller"]:
            raise ValueError("Installed controller changed")
        if "workspace" in manifest and b"WORKSPACE_PROTOCOL = 1" not in (directory / "tools/local_reviewer/runtime.py").read_bytes():
            raise ValueError("Controller cannot preserve the workspace contract")
    return release


def owned_status(root, manifest=None):
    manifest = manifest or read(root / "installation.json")
    state_path = root / "process.json"
    if not state_path.exists():
        return {"running": False, "reason": "not started"}
    state = read(state_path)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        request = urllib.request.Request("http://127.0.0.1:" + str(PORT) + "/__reviewer__/status",
                                         headers={"X-Reviewer-Token": state["token"]})
        with opener.open(request, timeout=2) as response:
            observed = json.load(response)
    except (OSError, ValueError):
        return {"running": False, "reason": "owned listener unavailable", "last_instance": state["instance"]}
    if observed.get("instance") != state["instance"] or observed.get("installation") != manifest["installation"] or observed.get("release") != manifest["release"]:
        raise ValueError("Port is occupied by another instance; leave it alone")
    if "workspace" in manifest or "workspace" in state:
        from .runtime import selected_context
        binding = selected_context(root, manifest).binding
        if state.get("workspace") != binding or observed.get("workspace") != binding:
            raise ValueError("Owned process workspace binding changed")
    return observed


def control(root, action, payload=None):
    manifest = read(root / "installation.json")
    if not owned_status(root, manifest)["running"]:
        raise ValueError("Start the owned installation before using controls")
    state = read(root / "process.json")
    req = urllib.request.Request("http://127.0.0.1:" + str(PORT) + "/__reviewer__/control/" + action,
                                 data=canonical(payload or {}), method="POST",
                                 headers={"Content-Type": "application/json", "X-Reviewer-Token": state["token"]})
    # Never automatically replay an uncertain mutation or use system proxies.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=60) as response:
        return json.load(response)


def wait_stopped(root):
    # Public AI permits two phases, each with a bounded deferred credential
    # and response wait. New operations are fenced after Stop is accepted.
    deadline = time.monotonic() + 660
    while time.monotonic() < deadline:
        if not owned_status(root)["running"]:
            try:
                with exclusive(root, "server.lock"):
                    return {"running": False, "stopped": True}
            except OSError:
                pass  # Listener closed; the same child is finishing teardown.
        time.sleep(0.25)
    raise ValueError("Stop was accepted but completion is not confirmed; inspect Status before continuing")


def stop(root, *, wait=False):
    status = owned_status(root)
    if not status["running"]:
        return wait_stopped(root) if wait else status
    result = control(root, "stop")
    return wait_stopped(root) if wait else result


def start(root):
    from .runtime import require_publication_ready
    require_publication_ready(root)
    manifest = read(root / "installation.json")
    release = verify_release(root, manifest)
    if (root / "private-access.json").exists() and not manifest.get("private_profile"):
        raise ValueError("Incomplete private setup; offline fallback refused")
    if manifest.get("private_profile"):
        require_private_files(root)
    status = owned_status(root, manifest)
    if status["running"]:
        if not status.get("stopping"):
            return status
        wait_stopped(root)
    with exclusive(root, "server.lock"):
        pass  # A previous starting/hung owned process must not be duplicated.
    with socket.socket() as check:
        if os.name == "nt":
            check.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        check.bind(("127.0.0.1", PORT))
    from .runtime import selected_context
    state = {"instance": secrets.token_hex(24), "token": secrets.token_hex(32), "installation": manifest["installation"], "release": manifest["release"],
             "workspace": selected_context(root, manifest).binding}
    write(root / "process.json", state)
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    with (log_dir / "server.log").open("ab") as log:
        child = subprocess.Popen([sys.executable, "-I", "-B", str(root / "controllers" / manifest["controller"] / "scripts" / "local_reviewer.py"), "--root", str(root), "serve"],
                                 cwd=root, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
    state["pid"] = child.pid
    write(root / "process.json", state)
    for _ in range(100):
        if child.poll() is not None:
            raise ValueError("Owned server failed startup; see logs/server.log. Data was preserved")
        status = owned_status(root, manifest)
        if status["running"]:
            return status
        time.sleep(0.1)
    raise ValueError("Startup not confirmed; inspect status/logs before any retry")


def extract_artifact(artifact, destination):
    """Only regular, bounded paths; no overwrites, links, credentials or traversal."""
    files, seen = {}, set()
    with zipfile.ZipFile(artifact) as archive:
        entries = archive.infolist()
        if sum(e.file_size for e in entries) > 1_000_000_000 or len(entries) > 20000:
            raise ValueError("Artifact exceeds installer limits")
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or "\\" in entry.filename or any(p in {"", ".", ".."} or ":" in p or p.endswith((".", " ")) for p in path.parts)
                    or any(p.lower() in {".env", ".git"} or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?", p) for p in path.parts)):
                raise ValueError("Unsafe artifact path")
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))):
                raise ValueError("Artifact contains a nonregular entry")
            key = str(path).casefold()
            if key in seen:
                raise ValueError("Artifact contains colliding paths")
            seen.add(key)
            target = destination.joinpath(*path.parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            files[str(path)] = digest(target)
    if not (destination / "app.py").is_file() or not (destination / "tests" / "mvp1_acceptance_support.py").is_file():
        raise ValueError("Artifact does not contain the supported application factory")
    return files


def prepare_release(root, args):
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha) or not re.fullmatch(r"[0-9a-f]{64}", args.artifact_sha256) or not re.fullmatch(r"[0-9a-f]{64}", args.overlay_sha256):
        raise ValueError("Supply exact artifact, source and overlay identities")
    if digest(args.artifact) != args.artifact_sha256 or digest(args.overlay) != args.overlay_sha256:
        raise ValueError("Artifact or dependency overlay hash does not match")
    runtime = require_private_runtime(root)
    pins = re.findall(r"(?m)^([A-Za-z0-9_.-]+)==([^\s#]+)", Path(args.overlay).read_text(encoding="utf-8"))
    for name, version in pins:
        if runtime["packages"].get(re.sub(r"[-_.]+", "-", name).lower()) != version:
            raise ValueError("Private runtime does not match reviewed overlay: " + name)
    if runtime["packages"].get("waitress") != "3.0.2":
        raise ValueError("Install pinned waitress3.0.2 in the private runtime")
    name = args.source_sha + "-" + args.artifact_sha256[:12]
    release = root / "releases" / name
    if release.exists():
        record = read(release / "release.json")
        if record["artifact_sha256"] != args.artifact_sha256 or record["overlay_sha256"] != args.overlay_sha256:
            raise ValueError("Existing release has a different identity; preserve it")
    else:
        release.mkdir(parents=True)
        files = extract_artifact(Path(args.artifact), release / "source")
        shutil.copyfile(args.overlay, release / "requirements-reviewed.txt")
        record = {"source_sha": args.source_sha, "artifact_sha256": args.artifact_sha256,
                  "overlay_sha256": args.overlay_sha256, "candidate_state": args.candidate_state,
                  "files": files}
        write(release / "release.json", record)
    return name, record, runtime


def install(root, args):
    if getattr(args, "factory", None) is not None:
        if args.action != "update" or args.candidate_state != "accepted-main":
            raise ValueError("Factory promotion requires an explicit accepted-app update")
        # The caller also holds control.lock. No supported Start can interleave;
        # retain the worker lifetime lock until the paired manifest is committed.
        with private_operator(root) as (_, _, configuration, budget):
            scopes = [profile["scope"] for profile in configuration["profiles"].values()]
            if budget.has_active(scopes):
                raise ValueError("Resolve active provider reservations under the original binding first")
            configuration_id = prepare_factory_configuration(root, args.factory, configuration)
            return install_artifact(root, args, configuration_id=configuration_id)
    return install_artifact(root, args)


def prepare_factory_configuration(root, factory_path, configuration):
    from .providers import (bound_factory, ordinary_configuration_bytes,
                            selected_configuration)
    factory_data = ordinary_configuration_bytes(factory_path)
    interface = bound_factory(factory_data, for_promotion=True)
    _, previous_interface = selected_configuration(root)
    if (interface.get("ongoing_budget_port") != previous_interface.get("ongoing_budget_port")
            or interface["profile_contract"] != configuration["factory"]["profile_contract"]
            or interface["limits_maxima"] != configuration["factory"]["limits_maxima"]):
        raise ValueError("Factory promotion cannot change provider contracts or caps")
    candidate = {**configuration, "factory": {key: interface[key] for key in
                 ("files_sha256", "profile_contract", "limits_maxima")}}
    pair = canonical({"live_ai": candidate, "factory_utf8": factory_data.decode("utf-8")})
    configuration_id = hashlib.sha256(pair).hexdigest()
    destination = root / "data" / "provider-configurations" / (configuration_id + ".json")
    if any(p.is_symlink() or p.is_junction() for p in (destination, *destination.parents)):
        raise ValueError("Private configuration snapshot contains a link")
    if destination.exists():
        if destination.read_bytes() != pair:
            raise ValueError("Existing private configuration snapshot changed")
    else:
        atomic_write(destination, pair)
    private_permissions(root)
    return configuration_id


def install_artifact(root, args, *, configuration_id=None):
    existing = (root / "installation.json").exists()
    if args.action == "install" and existing:
        raise ValueError("Installation exists; use explicit update")
    if args.action == "update" and not existing:
        raise ValueError("Installation is absent; use install")
    name, artifact, runtime = prepare_release(root, args)
    if configuration_id is not None and artifact.get("candidate_state") != "accepted-main":
        raise ValueError("Prepared app artifact is not accepted main")
    old = read(root / "installation.json") if existing else None
    manifest = {"installation": old["installation"] if old else secrets.token_hex(24),
                "release": name, "artifact": artifact, "runtime": runtime, "port": PORT}
    if old and old.get("private_profile"):
        manifest["private_profile"] = True
        if "provider_configuration" in old:
            manifest["provider_configuration"] = old["provider_configuration"]
        if "workspace" in old:
            manifest["workspace"] = old["workspace"]
    if configuration_id is not None:
        manifest["provider_configuration"] = configuration_id
    verify_release(root, manifest)
    # Check data compatibility in a separate offline process before promotion.
    probe_command = [sys.executable, "-I", "-B", str(Path(__file__).resolve().parents[2] / "scripts" / "local_reviewer.py"),
                     "--root", str(root), "probe", "--release", name]
    if configuration_id is not None:
        probe_command.extend(["--provider-configuration", configuration_id])
    probe = subprocess.run(probe_command, capture_output=True, text=True, timeout=60)
    if probe.returncode:
        raise ValueError("Candidate is incompatible; current installation/data remain unchanged: " + probe.stderr[-1000:])
    paths = ("scripts/local_reviewer.py", "tools/local_reviewer/__init__.py", "tools/local_reviewer/persistence.py", "tools/local_reviewer/runtime.py", "tools/local_reviewer/manager.py",
             "tools/local_reviewer/private_identity.py", "tools/local_reviewer/provider_budget.py", "tools/local_reviewer/providers.py")
    source_root = Path(__file__).resolve().parents[2]
    controller_files = {relative: digest(source_root / relative) for relative in paths}
    controller_id = hashlib.sha256(canonical(controller_files)).hexdigest()
    controller = root / "controllers" / controller_id
    manifest["controller"], manifest["controller_files"] = controller_id, controller_files
    # Installer-owned code only, disjoint from the immutable application.
    for relative in paths:
        src = Path(__file__).resolve().parents[2] / relative
        dst = controller / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dst.resolve():
            atomic_write(dst, src.read_bytes())
    inputs = {
        "early-career.txt": "FICTIONAL TEST INPUT. Riley Finch was a Data Support Intern at Example Orchard Cooperative, June to August2025. Riley cleaned240 inventory rows and wrote a handoff guide. No efficiency result is established. Bachelor of Science in Information Systems at Example Lake College, May2026.",
        "mid-career.txt": "FICTIONAL TEST INPUT. Morgan Vale is a Project Coordinator at Example Cedar Works since2021. Morgan coordinates schedules and writes meeting notes. Earlier role: Service Associate at Example Trail Supply,2017 to2021. No revenue or productivity increase is established.",
        "extensive-history.txt": "FICTIONAL TEST INPUT. Casey Rowan was an Analyst at Example Alder Office,2008 to2012; Senior Analyst,2012 to2017; Operations Lead at Example Pine Company,2017 to2023; Program Coordinator at Example Meadow Cooperative since2023. Casey maintained planning documents. Team size and financial outcomes are unknown.",
        "conflicting-update.txt": "FICTIONAL TEST INPUT. Riley Finch's Data Support Internship ended in September2025. This conflicts with the earlier August2025 date. A person must decide which date is correct.",
        "empty.txt": "",
    }
    for name, value in inputs.items():
        if not (root / "inputs" / name).exists():
            atomic_write(root / "inputs" / name, (value + "\n").encode())
    guide = source_root / "docs" / "LOCAL_REVIEWER.md"
    if guide.is_file():
        atomic_write(root / "README.md", guide.read_bytes())
    launcher = '''from pathlib import Path
import hashlib, json, subprocess, sys
root = Path(__file__).resolve().parent
manifest = json.loads((root / "installation.json").read_text())
controller = manifest["controller"]
if len(controller) != 64 or any(c not in "0123456789abcdef" for c in controller):
    raise SystemExit("Invalid controller identity")
directory = root / "controllers" / controller
if any(p.is_symlink() or p.is_junction() for p in (directory, *directory.rglob("*"))):
    raise SystemExit("Installed controller contains a link")
actual = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob("*") if p.is_file()}
encoded = json.dumps(actual, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
if actual != manifest["controller_files"] or hashlib.sha256(encoded).hexdigest() != controller:
    raise SystemExit("Installed controller changed; no code was imported")
if (root / "data/fictional-workspaces/onboarding").exists() or "workspace" in manifest:
    if "workspace" not in manifest or b"WORKSPACE_PROTOCOL = 1" not in (directory / "tools/local_reviewer/runtime.py").read_bytes():
        raise SystemExit("Workspace contract requires a compatible controller; no personal fallback")
raise SystemExit(subprocess.call([str(root / "runtime" / "Scripts" / "python.exe"), "-I", "-B", str(directory / "scripts" / "local_reviewer.py"), "--root", str(root), *sys.argv[1:]]))
'''
    atomic_write(root / "reviewer.py", launcher.encode())
    for action, command in {"Start": "start", "Stop": "stop", "Status": "status", "Checkpoint": "checkpoint",
                            "Fresh Demo": "reset-fictional-workspace --open"}.items():
        content = '@echo off\r\n"' + str(root / "runtime" / "Scripts" / "python.exe") + '" -I -B "' + str(root / "reviewer.py") + '" ' + command + '\r\n'
        if command == "start":
            content += 'if not errorlevel 1 "' + str(root / "runtime" / "Scripts" / "python.exe") + '" -I -B "' + str(root / "reviewer.py") + '" open\r\n'
        content += 'pause\r\n'
        atomic_write(root / (action + ".cmd"), content.encode())
    atomic_write(root / "Run.cmd", ('@echo off\r\n"' + str(root / "runtime" / "Scripts" / "python.exe") + '" -I -B "' + str(root / "reviewer.py") + '" %*\r\npause\r\n').encode())
    verify_release(root, manifest)
    # All fallible preparation is complete before stopping or advancing the
    # authoritative pointer. A failed preparation retains the old installation.
    with ExitStack() as promotion:
        if existing:
            running = owned_status(root, old)["running"] if configuration_id is None else False
            if running:
                checkpoint = control(root, "checkpoint")["checkpoint"]
                stop(root, wait=True)
            elif configuration_id is None:
                wait_stopped(root)
            if old.get("private_profile") and manifest["release"] != old["release"] and configuration_id is None:
                _, _, configuration, budget = promotion.enter_context(private_operator(root))
                scopes = [profile["scope"] for profile in configuration["profiles"].values()]
                if budget.has_active(scopes):
                    raise ValueError("Resolve active provider reservations before updating the app binding")
            if not running:
                checkpoint = offline_checkpoint(root)
            write(root / "previous.json", {"manifest": old, "checkpoint": checkpoint, "restart": running})
        write(root / "installation.json", manifest)
    return {"installed": manifest["release"], "candidate_state": artifact["candidate_state"], "url": "http://127.0.0.1:" + str(PORT), "previous_preserved": existing}


def offline_checkpoint(root):
    from .runtime import selected_context, ordinary_path
    context = selected_context(root)
    path = ordinary_path(context.state_path)
    if not path.exists():
        return None
    from uuid import uuid4
    name = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid4().hex[:8] + ".json"
    raw = path.read_bytes()
    if context.namespace:
        body = read(path)["body"]
        if body.get("namespace") != context.namespace:
            raise ValueError("Checkpoint namespace differs from selected workspace")
    atomic_write(ordinary_path(context.checkpoints / name), raw)
    return name


def rollback(root):
    from .runtime import require_publication_ready
    require_publication_ready(root)
    previous = read(root / "previous.json")
    old = previous["manifest"]
    current = read(root / "installation.json")
    if "workspace" in current or (root / "data/fictional-workspaces/onboarding").exists():
        if old.get("workspace") != current.get("workspace") or "workspace" not in old:
            raise ValueError("Rollback must retain the exact workspace; older controllers cannot reinterpret it")
    if read(root / "installation.json").get("private_profile") and not old.get("private_profile"):
        raise ValueError("Cannot roll private personal data back to an offline shared-profile controller")
    verify_release(root, old)
    stop(root, wait=True)
    current = read(root / "installation.json")
    if current.get("private_profile") and (
        current["release"] != old["release"]
        or current.get("provider_configuration") != old.get("provider_configuration")
        or "workspace" in current
    ):
        with private_operator(root) as (_, _, configuration, budget):
            scopes = [profile["scope"] for profile in configuration["profiles"].values()]
            if budget.has_active(scopes):
                raise ValueError("Resolve active provider reservations under the current binding before rollback")
            return rollback_stopped(root, previous, old)
    return rollback_stopped(root, previous, old)


def rollback_stopped(root, previous, old):
    from .runtime import selected_context, ordinary_path, require_publication_ready
    # Stop may have drained a request that established an unresolved fence
    # after rollback's initial check. Recheck before any recovery side effect.
    require_publication_ready(root)
    context = selected_context(root)
    if old.get("private_profile"):
        # The previous pointer never authorizes restoring old content. Probe
        # its exact app/configuration in a fresh child, including both current
        # namespaces and the behavior needed by their approved content.
        command = [sys.executable, "-I", "-B", str(Path(__file__).resolve().parents[2] / "scripts/local_reviewer.py"),
                   "--root", str(root), "probe", "--release", old["release"], "--rollback-target"]
        if "provider_configuration" in old:
            command.extend(["--provider-configuration", old["provider_configuration"]])
        else:
            command.append("--original-provider-configuration")
        probe = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if probe.returncode:
            raise ValueError("Rollback target cannot preserve current approved content; retain it and use a reviewed forward correction: " + probe.stderr[-1000:])
        checkpoint = offline_checkpoint(root)
        write(root / "rollback-receipt.json", {"from": read(root / "installation.json")["release"],
              "to": old["release"], "displaced_checkpoint": checkpoint, "content_preserved": True})
        write(root / "installation.json", old)
        return {"rolled_back": old["release"], "displaced_checkpoint": checkpoint, "content_preserved": True}
    checkpoint = offline_checkpoint(root)
    if "workspace" in old:
        # The context pointer and its durable content are separate authorities.
        # Validate compatibility, then roll back only the controller/app pointer.
        # Explicit operator restore is the sole saved-state rewind operation.
        with ExitStack() as stack:
            from .runtime import build_fixture
            _, _, _, state = build_fixture(verify_release(root, old) / "source", stack)
            context.store(state).load()
    elif previous["checkpoint"]:
        name = previous["checkpoint"]
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
            raise ValueError("Invalid rollback checkpoint name")
        raw = ordinary_path(context.checkpoints / name).read_bytes()
        if context.namespace:
            with ExitStack() as stack:
                from .runtime import build_fixture
                _, _, _, state = build_fixture(verify_release(root, old) / "source", stack)
                context.store(state).unpack(raw)
        atomic_write(ordinary_path(context.state_path), raw)
    write(root / "rollback-receipt.json", {"from": read(root / "installation.json")["release"], "to": old["release"], "displaced_checkpoint": checkpoint})
    write(root / "installation.json", old)
    return {"rolled_back": old["release"], "displaced_checkpoint": checkpoint}


RECOVERY_BEHAVIOR = "contextual_exclusion_recovery"


def required_onboarding_behaviors(state):
    required = set()
    owners = state.validate(state.capture()).get("intake._owners", {})
    for owner in owners.values():
        if not isinstance(owner, dict):
            raise ValueError("Invalid saved intake owner")
        if (owner.get("draft_revision", 0) or (owner.get("drafts") or {}).get("composer")):
            required.add("monotonic_composer_lifecycle")
        for proposal in (owner.get("proposals") or {}).values():
            metadata = proposal.get("resume_conversation_v1") or {}
            if metadata.get("approved_credential_binding"):
                required.add("bound_credential_details")
            if ("recovery_review" in metadata or metadata.get("resume_exclusion")
                    or metadata.get("resume_restoration") or metadata.get("excluded_bullets")
                    or any(edit.get("action") in {"exclude", "include"}
                           for edit in metadata.get("bullet_edits") or [])):
                required.add(RECOVERY_BEHAVIOR)
        for source in (owner.get("sources") or {}).values():
            metadata = (source.get("structured_values") or {}).get("resume_conversation_v1") or {}
            if metadata.get("topic_skipped") is True:
                required.add(RECOVERY_BEHAVIOR)
    return required


def require_onboarding_behavior_coverage(required, declared, qualified=None):
    """A retained decision contract needs both reviewed and executed proof."""
    if not set(required) <= set(declared):
        raise ValueError("Target lacks reviewed behavior required by retained onboarding decisions; preserve content and use a reviewed forward correction")
    if qualified is not None and not (set(required) | set(declared)) <= set(qualified):
        raise ValueError("Target execution does not qualify the retained onboarding decision behavior")


def qualify_onboarding_behavior(fixture, app, *, behaviors=()):
    """Actual zero-provider synthetic routes/renderer, not capability labels."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch
    from uuid import uuid4
    from identity import PeerSlatePrincipal
    from services.resume_guide_service import ResumeGuideService
    from tests.test_resume_onboarding_coverage import ResumeOnboardingCoverageTests
    intake, owner, _, command = ResumeOnboardingCoverageTests().credential_proposal(
        draft_service=fixture.shared.draft)
    intake.original_files = fixture.intake.original_files
    principal = PeerSlatePrincipal("development", "private-delivery-behavior-probe", owner,
                                  display_name="Synthetic qualification owner", is_development=True)
    configuration = {"RESUME_INTAKE_SERVICE": intake, "RESUME_DRAFT_SERVICE": fixture.shared.draft,
                     "ENTRY_POLICY_SERVICE": fixture.shared.policy,
                     "RESUME_GUIDE_SERVICE": ResumeGuideService(repository=intake.repository),
                     "PEERSLATE_RESUME_INTAKE_ENABLED": True, "PEERSLATE_RESUME_EDITOR_ENABLED": True,
                     "PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED": True}
    with patch.dict(app.config, configuration), patch("identity.get_current_principal", return_value=principal), \
            patch("auth_routes.get_current_principal", return_value=principal):
        client = app.test_client()
        headers = {"X-PeerSlate-Request": "same-origin"}
        def request(path, method="POST", payload=None):
            return client.open(path, method=method, json=payload, headers=headers)
        route = "/api/resume-intake/me/proposals/decision"
        approved = request(route, payload=command)
        if approved.status_code != 200 or not request(route, payload=command).json.get("replayed"):
            raise ValueError("Target credential approval/replay behavior failed")
        rows = intake.draft_service.get_workspace(owner)["items"]
        if sorted(row["record_type"] for row in rows) != ["credential", "knowledge"]:
            raise ValueError("Target credential parent/supplement composition failed")
        reviewed = fixture.shared.publication.review_for_owner(owner, {"entries": [
            {"entry_key": row["record_key"], "resume_display": True, "visitor_ai": False} for row in rows]}).reviewed
        if reviewed is None:
            raise ValueError("Target credential preview review failed")
        reference = reviewed.candidate.profile_identity
        preview = request("/api/resume-publication/me/preview", payload={
            "candidate": fixture.shared.publication.publish_candidate(reviewed), "reviewed_digest": reviewed.digest,
            "profile_identity": reference.to_payload() if reference else None})
        data = preview.json or {}
        display = list(data.get("display", {}).values())
        credentials = re.search(r'<section\b[^>]*\bid="resume-credentials"[^>]*>(.*?)</section>',
                                data.get("html", ""), re.S)
        if (preview.status_code != 200 or len(display) != 1 or display[0].get("canonical_type") != "credential"
                or not display[0].get("credential_details") or credentials is None
                or 'class="resume-publication__credential-details"' not in credentials.group(1)
                or "not currently licensed." not in credentials.group(1)
                or "&lt;literal&gt;" not in credentials.group(1)):
            raise ValueError("Target cannot render the approved credential limitation in its bound Credentials placement")
        approved_owner = intake.repository.load_owner(owner)
        draft_route = "/api/resume-intake/me/draft"
        for action, legacy in (("direct_expiry", True), ("read_expiry", True), ("discard", True), ("discard", False)):
            # Independent synthetic legacy fixtures; actual namespace content
            # was loaded/captured separately and is never written by this probe.
            intake.repository.save_owner(owner, approved_owner)
            seed = request(draft_route, "PUT", {"request_id": str(uuid4()), "text": "Acknowledged legacy words"})
            if seed.status_code != 200:
                raise ValueError("Target cannot construct the actual composer fixture")
            snapshot = intake.repository.load_owner(owner)
            snapshot["drafts"]["composer"]["version"] = 37
            snapshot["drafts"]["composer"]["expires_at"] = (datetime.now(timezone.utc)
                + timedelta(days=1) if action == "discard" else datetime.now(timezone.utc)
                - timedelta(days=1)).isoformat()
            if legacy:
                snapshot.pop("draft_revision", None)
            else:
                snapshot["draft_revision"] = 37
            intake.repository.save_owner(owner, snapshot)
            if action == "read_expiry":
                dropped = request(draft_route, "GET")
                if dropped.status_code != 200 or dropped.json.get("draft") is not None:
                    raise ValueError("Target expired composer behavior failed")
            elif action == "discard":
                if request(draft_route, "DELETE", {"request_id": str(uuid4()), "expected_version": 37}).status_code != 200:
                    raise ValueError("Target composer discard behavior failed")
            first = request(draft_route, "PUT", {"request_id": str(uuid4()), "text": "First acknowledged recreation"})
            if first.status_code != 200 or first.json["draft"]["version"] != 38:
                raise ValueError("Target does not retain the legacy composer high-water")
            if request(draft_route, "DELETE", {"request_id": str(uuid4()), "expected_version": 38}).status_code != 200:
                raise ValueError("Target composer rediscard behavior failed")
            next_command = {"request_id": str(uuid4()), "text": "Second acknowledged recreation <literal>"}
            second = request(draft_route, "PUT", next_command)
            if second.status_code != 200 or second.json["draft"]["version"] != 39:
                raise ValueError("Target composer recreation is not monotonic")
            before = intake.repository.load_owner(owner)
            replay = request(draft_route, "PUT", next_command)
            stale = request(draft_route, "PUT", {"request_id": str(uuid4()), "expected_version": 38,
                                               "text": "Stale first-device words"})
            after = intake.repository.load_owner(owner)
            if (replay.status_code != 200 or not replay.json.get("replayed") or stale.status_code != 409
                    or not stale.json.get("input_preserved") or after != before
                    or after["drafts"]["composer"]["text"] != next_command["text"]
                    or after["proposals"] != approved_owner["proposals"]):
                raise ValueError("Target accepts stale composer input or loses acknowledged approval")
    qualified = ["bound_credential_details", "monotonic_composer_lifecycle"]
    if RECOVERY_BEHAVIOR in behaviors:
        qualify_recovery_behavior(fixture, app)
        qualified.append(RECOVERY_BEHAVIOR)
    return qualified


def qualify_recovery_behavior(fixture, app):
    """Execute the selected target's real decision routes on isolated owners.

    The fixture, services and test schema helpers come from the target source
    selected by build_fixture. No installed namespace or provider is written.
    """
    from unittest.mock import patch
    from uuid import uuid4
    from itsdangerous import URLSafeTimedSerializer
    from identity import PeerSlatePrincipal
    from services.resume_intake_repository import InMemoryIntakeUnitOfWork, ResumeIntakeStoreUnavailable
    from services.resume_intake_runtime import PrivateResumeAssistanceService
    from services.resume_guide_service import ResumeGuideService
    from tests.test_my_data_intake_ai import add_request
    from tests.test_resume_onboarding_conversation import (
        ContextPorts, DeterministicFakeExtractionAdapter, FakeUpload, extracted_pipeline, operation,
    )

    def check(condition, reason):
        if not condition:
            raise ValueError("Target recovery behavior failed: " + reason)

    check(callable(getattr(fixture.intake, "review_excluded_details", None)), "contextual target interface unavailable")

    @contextmanager
    def case():
        owner = str(uuid4())
        intake = type(fixture.intake)(repository=fixture.intake.repository, draft_service=fixture.shared.draft,
            policy=fixture.intake.policy(), original_files=fixture.intake.original_files,
            interpreter=lambda text, kind: [{"kind": "inferred_wording", "record_type": "role",
                "confidence": "certain", "values": {"role_title": "Engineer", "employer_name": "Example Labs"}}])
        ports = ContextPorts(fixture.shared.canonical)
        action, calls = [], []
        def provider(**kwargs):
            calls.append(kwargs["context"])
            return {"response": "Review these details.", "next_question": "",
                    "operations": [action[0](kwargs["context"])]}
        assistance = PrivateResumeAssistanceService(draft_service=fixture.shared.draft, catalog=ports,
            policy_repository=ports, providers={"interview": provider},
            signer=URLSafeTimedSerializer("isolated-recovery-probe-" + str(uuid4())),
            limits={"maximum_task_bytes": 20000, "maximum_input_bytes": 65536,
                    "maximum_output_bytes": 100000, "maximum_field_bytes": 8000, "proof_max_age_seconds": 900})
        principal = PeerSlatePrincipal("development", "private-recovery-behavior-probe", owner,
                                      display_name="Synthetic recovery owner", is_development=True)
        with ExitStack() as stack:
            stack.enter_context(patch.dict(app.config, {"RESUME_INTAKE_SERVICE": intake,
                "RESUME_DRAFT_SERVICE": fixture.shared.draft, "ENTRY_POLICY_SERVICE": fixture.shared.policy,
                "RESUME_GUIDE_SERVICE": ResumeGuideService(repository=intake.repository),
                "PEERSLATE_RESUME_INTAKE_ENABLED": True, "PEERSLATE_RESUME_EDITOR_ENABLED": True,
                "PEERSLATE_RESUME_INTERVIEW_ENABLED": False, "RESUME_PRIVATE_ASSISTANCE_SERVICE": None}))
            stack.enter_context(patch("identity.get_current_principal", return_value=principal))
            stack.enter_context(patch("auth_routes.get_current_principal", return_value=principal))
            client = app.test_client()
            def request(path, payload):
                return client.post("/api/resume-intake/me/" + path, json=payload,
                                   base_url="http://127.0.0.1:53720",
                                   headers={"X-PeerSlate-Request": "same-origin"})
            def turn(ref, make_operation, *, command=None, full_response=False):
                action[:] = [make_operation]
                result = intake.converse(owner, command or {"request_id": str(uuid4()),
                    "expected_draft_version": fixture.shared.draft.get_workspace(owner)["draft_version"],
                    "statement": "Synthetic review instruction.", "selected_target": ref, "source_keys": []},
                    assistance=assistance)
                return result if full_response else result["proposals"][0]
            def seed(summary="Keep my contribution.\nRetain this limitation."):
                return intake.submit(owner, add_request(items=[{"client_key": "role", "record_type": "role",
                    "values": {"role_title": "Engineer", "employer_name": "Example Labs", "location_text": "Denver",
                               "summary": summary}, "explicit_clears": []}]))["results"][0]["record_key"]
            def decide(proposal, decision="accept", **extra):
                command = {"request_id": str(uuid4()), "proposal_key": proposal["proposal_key"],
                           "decision": decision, **extra}
                response = request("proposals/decision", command)
                check(response.status_code == 200, "explicit decision " + str(response.status_code) + ": " + response.get_data(as_text=True))
                return response.json
            def review_command(row):
                return {"request_id": str(uuid4()), "recovery_key": row["recovery_key"],
                        "recovery_token": row["recovery_token"]}
            yield owner, intake, calls, request, turn, seed, decide, review_command

    # Retained stop control has the same compatibility requirement even when
    # no exclusion exists. Execute the target's validator, response and replay.
    with case() as (owner, intake, calls, request, turn, seed, decide, review_command):
        key = seed()
        pending = turn("record:" + key, lambda ctx: operation(ctx, ref="record:" + key,
                       values={"location_text": "Chicago"}))
        command = {"request_id": str(uuid4()),
            "expected_draft_version": fixture.shared.draft.get_workspace(owner)["draft_version"],
            "statement": "Don't worry about it.", "selected_target": "proposal:" + pending["proposal_key"],
            "source_keys": []}
        before_pending = intake.get_workspace(owner)["pending_proposals"]
        before_draft = fixture.shared.draft.get_workspace(owner)
        stop = lambda ctx: {**operation(ctx, op="skip_topic"), "source_refs": []}
        response = turn(command["selected_target"], stop, command=command, full_response=True)
        check(response.get("topic_skipped") is True, "validated stop control absent")
        check(response.get("next_question") == "" and response["proposals"] == [], "stop starts another exchange")
        replay = turn(command["selected_target"], stop, command=command, full_response=True)
        check(replay.get("replayed") is True and replay.get("topic_skipped") is True
              and replay.get("next_question") == "" and replay["proposals"] == [] and len(calls) == 2,
              "stop replay changes control or dispatches again")
        check(intake.get_workspace(owner)["pending_proposals"] == before_pending
              and fixture.shared.draft.get_workspace(owner) == before_draft, "stop changes retained review or facts")
        sources = intake.repository.load_owner(owner)["sources"].values()
        check(any(((source.get("structured_values") or {}).get("resume_conversation_v1") or {}).get("topic_skipped")
                  is True for source in sources), "stop control not retained")

    # Rejected imports are returned to review through the actual disabled-AI
    # HTTP route; failed publication and replay do not create a second item.
    with case() as (owner, intake, calls, request, turn, seed, decide, review_command):
        original_text = "Experience\nEngineer, Example Labs.\nCoordinated eight people; not their manager."
        intake._document_pipeline = extracted_pipeline(original_text)
        intake._extraction_adapter = DeterministicFakeExtractionAdapter([{"record_type": "role",
            "values": {"role_title": "Engineer", "employer_name": "Example Labs"},
            "quote": original_text.split("\n", 1)[1], "outcome": "new", "confidence": "certain"}])
        intake.submit(owner, add_request(attachments=[{"client_key": "doc", "kind": "document",
            "declared_content_type": "text/plain", "filename": "resume.txt"}]),
            files={"doc": FakeUpload("text/plain", original_text.encode())})
        original = intake.get_workspace(owner)["pending_proposals"][0]
        decide(original, "reject")
        command = review_command(intake.get_workspace(owner)["resume_recoverable_details"][0])
        before = intake.repository.load_owner(owner)
        forged = request("excluded-details/review", {**command, "recovery_token": "0" * 64})
        check(forged.status_code == 409 and intake.repository.load_owner(owner) == before, "forged recovery token")
        with patch.object(InMemoryIntakeUnitOfWork, "commit", side_effect=ResumeIntakeStoreUnavailable("probe failure")):
            check(request("excluded-details/review", command).status_code == 503, "failed review commit")
        check(intake.repository.load_owner(owner) == before and not fixture.shared.canonical.list_items(owner), "atomic review rollback")
        reviewed = request("excluded-details/review", command)
        check(reviewed.status_code == 200 and not fixture.shared.canonical.list_items(owner), "review without saving")
        proposal = reviewed.json["proposals"][0]
        replay = request("excluded-details/review", command)
        check(replay.status_code == 200 and replay.json["replayed"]
              and replay.json["proposals"][0]["proposal_key"] == proposal["proposal_key"], "review replay")
        check(request("excluded-details/review", {**command, "recovery_token": "0" * 64}).status_code == 409, "changed-payload replay")
        decide(proposal)
        check(len(fixture.shared.canonical.list_items(owner)) == 1 and not calls, "import confirmation without AI")

    # Both exact direct saved targets and prior pending amendments must work
    # for whole-record and literal-bullet Undo, including explicit clears.
    for pending in (False, True):
        for bullet in (False, True):
            with case() as (owner, intake, calls, request, turn, seed, decide, review_command):
                key = seed(); canonical = fixture.shared.draft.get_workspace(owner)
                ref = "record:" + key; prior = None
                summary = "Keep my contribution.\nRetain this limitation.\nI wrote a review checklist."
                if pending:
                    prior = turn(ref, lambda ctx: operation(ctx, ref=ref,
                        values={"summary": summary}, clears=["location_text"]))
                    ref = "proposal:" + prior["proposal_key"]
                edits = [{"action": "exclude", "field": "summary", "index": 1,
                          "expected_text": "Retain this limitation.", "replacement": None}] if bullet else []
                exclusion = turn(ref, lambda ctx: operation(ctx,
                    op="revise_content" if bullet else "exclude_content", ref=ref, bullets=edits))
                row = intake.get_workspace(owner)["pending_proposals"][0]
                check(bool(row.get("undo_exclusion_token")), "bound Undo token")
                command = {"request_id": str(uuid4()), "proposal_key": exclusion["proposal_key"],
                           "decision": "reject", "undo_exclusion_token": row["undo_exclusion_token"]}
                before = intake.repository.load_owner(owner)
                with patch.object(InMemoryIntakeUnitOfWork, "commit", side_effect=ResumeIntakeStoreUnavailable("probe failure")):
                    check(request("proposals/decision", command).status_code == 503, "failed Undo commit")
                check(intake.repository.load_owner(owner) == before, "atomic Undo rollback")
                undone = request("proposals/decision", command)
                check(undone.status_code == 200 and fixture.shared.draft.get_workspace(owner) == canonical, "Undo without canonical write")
                replay = request("proposals/decision", command)
                check(replay.status_code == 200 and replay.json["replayed"], "Undo replay")
                if pending:
                    restored = undone.json["restored_proposal"]
                    check(restored["target_key"] == key and restored["proposed_values"] == prior["proposed_values"]
                          and restored["explicit_clears"] == prior["explicit_clears"]
                          and restored["provided_fields"] == prior["provided_fields"]
                          and not restored["resume_conversation_v1"]["recovery_review"]["as_shown"]
                          and replay.json["restored_proposal"]["proposal_key"] == restored["proposal_key"], "exact pending lineage")
                    decide(restored)
                    item = fixture.shared.draft.get_workspace(owner)["items"][0]
                    check(item["proposed_values"]["summary"] == summary and item["proposed_values"]["location_text"] is None,
                          "explicit pending confirmation")
                else:
                    check("restored_proposal" not in undone.json and not intake.get_workspace(owner)["pending_proposals"], "saved Undo rejects only")
                check(len(calls) == 1 + int(pending), "Undo does not dispatch AI")

    # Saved restoration stays exact-as-shown. Duplicate equal text is bound
    # to retained proposal/edit identity, and other exclusions remain intact.
    for bullet in (False, True):
        with case() as (owner, intake, calls, request, turn, seed, decide, review_command):
            key = seed("Same literal detail.\nSame literal detail.\nKeep this limitation.")
            ref = "record:" + key
            edits = [{"action": "exclude", "field": "summary", "index": index,
                      "expected_text": "Same literal detail.", "replacement": None} for index in (1, 0)] if bullet else []
            exclusion = turn(ref, lambda ctx: operation(ctx,
                op="revise_content" if bullet else "exclude_content", ref=ref, bullets=edits))
            decide(exclusion)
            for ordinal in range(2 if bullet else 1):
                rows = intake.get_workspace(owner)["resume_recoverable_details"]
                command = review_command(rows[-1] if bullet else rows[0])
                before = fixture.shared.draft.get_workspace(owner)
                reviewed = request("excluded-details/review", command)
                check(reviewed.status_code == 200 and fixture.shared.draft.get_workspace(owner) == before, "saved review does not restore")
                proposal = reviewed.json["proposals"][0]
                check(proposal["resume_conversation_v1"]["recovery_review"]["as_shown"], "saved exact-as-shown marker")
                snapshot = intake.repository.load_owner(owner)
                altered = {**proposal["proposed_values"], "summary": "Forged restored wording."}
                response = request("proposals/decision", {"request_id": str(uuid4()), "proposal_key": proposal["proposal_key"],
                    "decision": "edit", "confirmed_values": altered})
                check(response.status_code == 400 and intake.repository.load_owner(owner) == snapshot, "saved restoration cannot be edited")
                if bullet:
                    meta = proposal["resume_conversation_v1"]
                    check(meta["recovery_bullet_identity"] == [exclusion["proposal_key"], 1 - ordinal]
                          and meta["bullet_edits"][0]["index"] == ordinal, "duplicate ordinal identity")
                decide(proposal)
                check(len(intake.get_workspace(owner)["resume_recoverable_details"]) == (1 - ordinal if bullet else 0), "other exclusions preserved")
            check(len(fixture.shared.canonical.list_items(owner)) == 1 and len(calls) == 1, "saved restoration without duplication or AI")

    # Revalidate the current retained state before and under the actual commit
    # lock. Changed target is an independent synthetic canonical edit.
    for change in ("history", "source", "purge", "target", "commit_lock"):
        with case() as (owner, intake, calls, request, turn, seed, decide, review_command):
            key = seed(); ref = "record:" + key
            exclusion = turn(ref, lambda ctx: operation(ctx, op="exclude_content", ref=ref))
            decide(exclusion)
            command = review_command(intake.get_workspace(owner)["resume_recoverable_details"][0])
            reviewed = request("excluded-details/review", command)
            check(reviewed.status_code == 200, "stale-case initial review")
            proposal = reviewed.json["proposals"][0]
            def changed_target():
                snapshot = fixture.shared.policy.repository.load_owner(owner)
                snapshot["entries"][key]["content_version"] += 1
                fixture.shared.policy.repository.save_owner(owner, snapshot)
            if change in {"history", "source"}:
                snapshot = intake.repository.load_owner(owner)
                if change == "history": snapshot["proposals"][exclusion["proposal_key"]]["command_digest"] = "0" * 64
                else: snapshot["sources"][exclusion["provenance"]["source_key"]]["version"] += 1
                intake.repository.save_owner(owner, snapshot)
            elif change == "purge":
                intake.purge_source(owner, {"request_id": str(uuid4()),
                    "source_key": exclusion["provenance"]["source_key"]})
            elif change == "target": changed_target()
            before = intake.repository.load_owner(owner)
            original_enter = InMemoryIntakeUnitOfWork.__enter__
            def interleave(unit):
                changed_target()
                return original_enter(unit)
            with patch.object(InMemoryIntakeUnitOfWork, "__enter__", interleave if change == "commit_lock" else original_enter):
                response = request("proposals/decision", {"request_id": str(uuid4()),
                    "proposal_key": proposal["proposal_key"], "decision": "accept"})
            check(response.status_code == 409 and (not response.json.get("proposed_values")
                  or change == "purge" and "Keep my contribution." not in json.dumps(response.json))
                  and intake.repository.load_owner(owner) == before, "stale " + change + " confirmation")


def private_permissions(root, *, apply=False):
    """Keep personal files within this Windows user, SYSTEM and Administrators."""
    if os.name != "nt":
        raise ValueError("Private personal-data mode requires the Windows installation")
    # One native PowerShell process owns the complete bounded ACL operation.
    # Paths are literal strings, never commands or cross-shell deletion targets.
    script = r'''
$ErrorActionPreference = 'Stop'
$target = [IO.Path]::GetFullPath('__ROOT__')
$apply = __APPLY__
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$allowed = @($sid, 'S-1-5-18', 'S-1-5-32-544')
$targets = [Collections.Generic.List[string]]::new()
$targets.Add($target)
foreach ($name in @('data', 'checkpoints', 'logs')) {
    $item = Join-Path $target $name
    if (Test-Path -LiteralPath $item) {
        $targets.Add($item)
        Get-ChildItem -LiteralPath $item -Force -Recurse | ForEach-Object { $targets.Add($_.FullName) }
    }
}
foreach ($name in @('private-access.json','live-ai.json','ai-allocation.json','ai-factory.json','process.json')) {
    $item = Join-Path $target $name
    if (Test-Path -LiteralPath $item) { $targets.Add($item) }
}
foreach ($item in $targets) {
    $entry = Get-Item -LiteralPath $item -Force
    if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Private storage contains a link' }
    if ($apply) {
        if ($entry.PSIsContainer) {
            $acl = [Security.AccessControl.DirectorySecurity]::new()
            $inherit = [Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
        } else {
            $acl = [Security.AccessControl.FileSecurity]::new()
            $inherit = [Security.AccessControl.InheritanceFlags]::None
        }
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($identity in $allowed) {
            $principal = [Security.Principal.SecurityIdentifier]::new($identity)
            $rule = [Security.AccessControl.FileSystemAccessRule]::new($principal, 'FullControl', $inherit, 'None', 'Allow')
            $acl.AddAccessRule($rule)
        }
        $entry.SetAccessControl($acl)
        $entry.Refresh()
    }
    $rules = $entry.GetAccessControl().GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
    foreach ($rule in $rules) {
        if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -notin $allowed) {
            throw 'Private storage is readable by another account'
        }
    }
}
Write-Output 'private-storage-verified'
'''.replace('__ROOT__', str(root).replace("'", "''")).replace('__APPLY__', '$true' if apply else '$false')
    import base64
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                             base64.b64encode(script.encode("utf-16-le")).decode()],
                            capture_output=True, text=True, timeout=60,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode or result.stdout.strip() != "private-storage-verified":
        raise ValueError("Windows private storage permissions are not verified")


def require_private_files(root):
    from .runtime import private_access
    if not read(root / "installation.json").get("private_profile"):
        raise ValueError("Private setup is incomplete; startup refused")
    if private_access(root) is None:
        raise ValueError("Private profile configuration missing; offline fallback refused")
    for name in ("live-ai.json", "ai-allocation.json", "ai-factory.json", "data/provider-budget-v1.sqlite3", "data/state.json"):
        path = root / name
        if not path.is_file() or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
            raise ValueError("Private installation file unavailable; automatic reset refused")
    from .runtime import selected_context, ordinary_path
    context = selected_context(root)
    if context.namespace and not ordinary_path(context.state_path).is_file():
        raise ValueError("Fictional saved state missing; automatic recreation refused")
    private_permissions(root)


def setup_private(root, args):
    """One installation identity and one allocation. Never reset on rerun."""
    from uuid import uuid4
    from .private_identity import PrivateIdentity
    from .provider_budget import ProviderBudget
    from .runtime import build_fixture
    manifest = read(root / "installation.json")
    release = verify_release(root, manifest)
    if manifest.get("private_profile") or any((root / name).exists() for name in (
        "private-access.json", "live-ai.json", "ai-allocation.json", "ai-factory.json", "data/provider-budget-v1.sqlite3"
    )):
        raise ValueError("Private setup already exists or is incomplete; preserve its identity and budget")
    if owned_status(root, manifest)["running"]:
        raise ValueError("Stop this installation before its one-time private setup")
    if not (root / "data/state.json").is_file():
        raise ValueError("Existing durable content state required before private setup")
    identity_config = {"origin": args.origin, "login": args.login,
                       "owner": str(uuid4()), "display_name": "Private Test Profile"}
    identity = PrivateIdentity.from_config(identity_config)
    with ExitStack() as stack:
        fixture, app, _, _ = build_fixture(release / "source", stack)
        from .providers import (ALLOCATION_SHA256, FACTORY_SHA256, bound_document,
                                load_configuration, configure_private_providers)
        allocation = bound_document(args.allocation, ALLOCATION_SHA256)
        interface = bound_document(args.factory, FACTORY_SHA256)
        if Path(allocation["ledger_path"]).resolve() != (root / "data/provider-budget-v1.sqlite3").resolve():
            raise ValueError("This allocation belongs to another installation")
        private_permissions(root, apply=True)
        write(root / "private-access.json", identity_config)
        atomic_write(root / "ai-allocation.json", args.allocation.read_bytes())
        atomic_write(root / "ai-factory.json", args.factory.read_bytes())
        write(root / "live-ai.json", {"owner": identity.owner, "allocation_sha256": ALLOCATION_SHA256,
              "profiles": allocation["profiles"], "signing_key": secrets.token_hex(32),
              "factory": {k: interface[k] for k in ("files_sha256", "profile_contract", "limits_maxima")}})
        configuration = load_configuration(root, identity, release / "source")
        ProviderBudget.initialize(root / "data/provider-budget-v1.sqlite3", owner=identity.owner,
                                  allocation_sha256=ALLOCATION_SHA256, profiles=allocation["profiles"])
        configure_private_providers(fixture, app, root, identity, configuration)
    # Startup refuses partial setup and this durable marker prohibits downgrade.
    manifest["private_profile"] = True
    write(root / "installation.json", manifest)
    require_private_files(root)
    return {"private_profile_configured": True, "url": identity.origin, "provider_calls": 0}


def operator_source_digest():
    directory = Path(__file__).parent
    return hashlib.sha256(canonical({name: digest(directory / name) for name in
        ("manager.py", "provider_budget.py", "providers.py")})).hexdigest()


def allowance_source_digest():
    directory = Path(__file__).parent
    return hashlib.sha256(canonical({name: digest(directory / name) for name in
        ("manager.py", "provider_budget.py", "providers.py", "runtime.py")})).hexdigest()


def grant_onboarding_test_allowance(root, proof_path, review_path):
    """One reviewed prospective grant; never alter the original allocation."""
    from .provider_budget import ProviderBudget
    from .runtime import selected_context
    proof, review = read(proof_path), read(review_path)
    if (type(review) is not dict or set(review) != {"schema_version", "result", "proof_sha256", "allowance_source_sha256", "reviewer_ref"}
            or type(review["schema_version"]) is not int or review["schema_version"] != 1 or review["result"] != "pass"
            or review["proof_sha256"] != digest(proof_path) or review["allowance_source_sha256"] != allowance_source_digest()
            or not isinstance(review["reviewer_ref"], str) or not 1 <= len(review["reviewer_ref"]) <= 200):
        raise ValueError("Independent exact-source and allowance proof review required")
    # A local attestation, not an authenticated review service; private OS/operator custody still applies.
    with private_operator(root) as (manifest, identity, configuration, budget):
        selection = manifest.get("workspace")
        if type(selection) is not dict:
            raise ValueError("Existing authenticated onboarding workspace required")
        context = selected_context(root, {**manifest, "workspace": {**selection, "selected": "onboarding"}})
        if (type(proof) is not dict or proof.get("installation") != manifest["installation"]
                or proof.get("owner") != identity.owner or proof.get("namespace") != context.namespace
                or proof.get("configuration_sha256") != operator_configuration_digest(root, manifest)
                or proof.get("allocation_sha256") != configuration["allocation_sha256"]):
            raise ValueError("Exact original installation and onboarding descriptor required")
        scoped = ProviderBudget(budget.path, owner=identity.owner, allocation_sha256=configuration["allocation_sha256"],
                                profiles=configuration["profiles"], onboarding_context={"installation": manifest["installation"],
                                                                                      "namespace": context.namespace})
        result = scoped.grant_onboarding_allowance(proof, evidence={"proof_sha256": digest(proof_path),
            "review_sha256": digest(review_path), "source_sha256": allowance_source_digest()})
        return {**result, "allowance": scoped.onboarding_allowance_snapshot(), "provider_dispatches": 0}


def qualify_onboarding_allowance_accounting(root, target, configuration):
    """Execute the selected controller on copied accounting before rollback effects."""
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect((root / "data/provider-budget-v1.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (2, 3, 4):
            raise ValueError("Unknown provider accounting format remains fenced")
        if version != 4:
            return None
        manifest = read(root / "installation.json")
        from .runtime import selected_context
        selection = manifest.get("workspace")
        if type(selection) is not dict:
            raise ValueError("Allowance requires its retained onboarding workspace")
        context = selected_context(root, {**manifest, "workspace": {**selection, "selected": "onboarding"}})
        path = (root / "controllers" / target["controller"] / "tools/local_reviewer/provider_budget.py"
                if target is not None else Path(__file__).parent / "provider_budget.py")
        if target is not None and target.get("controller_files", {}).get("tools/local_reviewer/provider_budget.py") != digest(path):
            raise ValueError("Selected accounting controller binding changed")
        with tempfile.TemporaryDirectory(prefix="peerslate-allowance-qualification-") as directory:
            directory = Path(directory)
            copied = directory / "actual-accounting-copy.sqlite3"
            with closing(sqlite3.connect(copied)) as destination:
                db.backup(destination)
            arguments = {"owner": configuration["owner"], "allocation_sha256": configuration["allocation_sha256"],
                         "profiles": configuration["profiles"]}
            binding = {"installation": manifest["installation"], "namespace": context.namespace}
            parameters = directory / "parameters.json"
            parameters.write_bytes(canonical({"arguments": arguments, "context": binding}))
            script = '''import importlib.util,json,sys
from pathlib import Path
from uuid import uuid4
p=Path(sys.argv[1]); spec=importlib.util.spec_from_file_location("selected_accounting",p)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
v=json.loads(Path(sys.argv[3]).read_bytes()); a=v["arguments"]; c=v["context"]
# Decode with the actual selected implementation before invoking any new interface.
m.ProviderBudget(Path(sys.argv[2]),**a)
b=m.ProviderBudget(Path(sys.argv[2]),**a,onboarding_context=c)
w=b.onboarding_allowance_snapshot()
if w is None or w["amount_micro_usd"]!=50000000 or w["namespace"]!=c["namespace"]:
    raise ValueError("Selected controller does not preserve the actual allowance")
# Behavioral fixture uses that same selected module, never current helpers substituted into it.
profiles={n:{"scope":"fixture-"+n,"maximum_calls":100,"hard_cap_micro_usd":30000000,
"reservation_micro_usd":30000000,"concurrent_requests":1,"input_tokens":1,"output_tokens":0,
"input_micro_usd_per_million":30000000000000,"output_micro_usd_per_million":1} for n in a["profiles"]}
f=Path(sys.argv[2]).with_name("synthetic-behavior.sqlite3")
m.ProviderBudget.initialize(f,owner=a["owner"],allocation_sha256=a["allocation_sha256"],profiles=profiles)
s=m.ProviderBudget(f,owner=a["owner"],allocation_sha256=a["allocation_sha256"],profiles=profiles,onboarding_context=c)
doc={"schema_version":1,"request_id":str(uuid4()),**c,"owner":a["owner"],"allocation_sha256":a["allocation_sha256"],
"configuration_sha256":"a"*64,"authority_ref":"synthetic-qualification-only","amount_micro_usd":50000000}
e={"proof_sha256":"b"*64,"review_sha256":"c"*64,"source_sha256":"d"*64}
s.grant_onboarding_allowance(doc,evidence=e)
def reserve(b,n,r):
    p=profiles[n]
    return b.reserve({"@UserKey":a["owner"],"@Scope":p["scope"],"@RequestId":r,
"@ReservationMicroUsd":p["reservation_micro_usd"],"@MaximumCalls":100,"@HardCapMicroUsd":p["hard_cap_micro_usd"],"@ConcurrentRequests":1})
r=str(uuid4())
if not reserve(s,"interview",r) or reserve(s,"extraction",str(uuid4())):
    raise ValueError("Selected controller fails aggregate full-envelope reservation")
s.settle(a["owner"],profiles["interview"]["scope"],r,[{"phase":1,"identity_sha256":"1"*64,"input_tokens":1,"output_tokens":0}])
personal=m.ProviderBudget(f,owner=a["owner"],allocation_sha256=a["allocation_sha256"],profiles=profiles)
if not reserve(personal,"interview",str(uuid4())) or reserve(s,"extraction",str(uuid4())):
    raise ValueError("Selected controller borrows or consumes unrelated base funding")
# Replenishment runs on fresh ledgers with nothing active or fenced, so no other refusal can mask it.
def fresh(name):
    q=Path(sys.argv[2]).with_name(name)
    m.ProviderBudget.initialize(q,owner=a["owner"],allocation_sha256=a["allocation_sha256"],profiles=profiles)
    return q,m.ProviderBudget(q,owner=a["owner"],allocation_sha256=a["allocation_sha256"],profiles=profiles,onboarding_context=c)
second={**doc,"request_id":str(uuid4()),"authority_ref":"another-synthetic-authority"}
fresh("synthetic-second-document.sqlite3")[1].grant_onboarding_allowance(second,evidence=e)
g,t=fresh("synthetic-replenishment.sqlite3")
t.grant_onboarding_allowance(doc,evidence=e)
try:
    t.grant_onboarding_allowance(second,evidence=e)
    refused=False
except ValueError:
    refused=True
import sqlite3
from contextlib import closing
with closing(sqlite3.connect(g)) as q:
    grants=q.execute("SELECT COUNT(*) FROM onboarding_allowances").fetchone()[0]
if not refused or grants!=1:
    raise ValueError("Selected controller permits replenishment")
print(json.dumps({"actual_ledger_decode":True,"selected_target_behavior":True,"provider_dispatches":0}))
'''
            probe = subprocess.run([sys.executable, "-I", "-B", "-c", script, str(path), str(copied), str(parameters)],
                                   capture_output=True, text=True, timeout=60)
            if probe.returncode:
                raise ValueError("Selected target cannot preserve onboarding allowance before promotion: " + probe.stderr[-1000:])
            proof = json.loads(probe.stdout)
            if proof != {"actual_ledger_decode": True, "selected_target_behavior": True, "provider_dispatches": 0}:
                raise ValueError("Selected accounting qualification incomplete")
            return proof


def operator_configuration_digest(root, manifest):
    binding = {"installation": manifest["installation"], "release": manifest["release"],
        "files": {name: digest(root / name) for name in
                  ("private-access.json", "live-ai.json", "ai-allocation.json", "ai-factory.json")}}
    if "provider_configuration" in manifest:
        from .providers import selected_configuration
        selected_configuration(root, manifest["provider_configuration"])
        binding["provider_configuration"] = manifest["provider_configuration"]
    from .runtime import selected_context
    context = selected_context(root, manifest)
    if context.namespace:
        binding["workspace"] = context.binding
    return hashlib.sha256(canonical(binding)).hexdigest()


@contextmanager
def private_operator(root):
    """Caller holds control.lock; hold server lifetime lock through the mutation.

    A closed listener alone is insufficient: executor teardown retains server.lock.
    This command refuses a live process; it never stops one or dispatches a provider.
    """
    manifest = read(root / "installation.json")
    release = verify_release(root, manifest)
    require_private_files(root)
    if owned_status(root, manifest)["running"]:
        raise ValueError("Stop the private site and confirm worker teardown first")
    with exclusive(root, "server.lock"), ExitStack() as stack:
        from .runtime import build_fixture, selected_context
        build_fixture(release / "source", stack)
        from .providers import load_configuration
        from .provider_budget import ProviderBudget
        identity = selected_context(root, manifest).identity
        configuration = load_configuration(root, identity, release / "source")
        budget = ProviderBudget(root / "data/provider-budget-v1.sqlite3", owner=identity.owner,
            allocation_sha256=configuration["allocation_sha256"], profiles=configuration["profiles"])
        yield manifest, identity, configuration, budget


def require_inactive(configuration, budget):
    scopes = [profile["scope"] for profile in configuration["profiles"].values()]
    if budget.has_active(scopes):
        raise ValueError("Resolve all active reservations under their original context before changing saved-state context")


def create_workspace(root):
    """Create one fresh fixture, never a copy of the owner's personal snapshot."""
    from .runtime import WORKSPACE_ID, build_fixture, ordinary_path
    from urllib.parse import urlsplit
    with private_operator(root) as (manifest, identity, configuration, budget):
        require_inactive(configuration, budget)
        directory = ordinary_path(root / "data/fictional-workspaces" / WORKSPACE_ID)
        if "workspace" in manifest or directory.exists():
            raise ValueError("Fictional workspace already exists or preparation is incomplete; preserve it")
        origin = "https://" + urlsplit(identity.origin).hostname + ":8444"
        identity.fictional_origin(origin)
        descriptor = {"schema": 1, "workspace": WORKSPACE_ID, "installation": manifest["installation"],
                      "owner": identity.owner, "personal_origin": identity.origin, "origin": origin,
                      "private_access_sha256": digest(root / "private-access.json")}
        data = canonical(descriptor)
        namespace = hashlib.sha256(data).hexdigest()
        with ExitStack() as stack:
            _, _, _, state = build_fixture(verify_release(root, manifest) / "source", stack)
            from .persistence import SnapshotStore
            SnapshotStore(directory / "state.json", state, namespace=namespace).save()
        atomic_write(directory / "descriptor.json", data)
        write(root / "installation.json", {**manifest, "workspace": {
            "protocol": 1, "descriptor_sha256": namespace, "selected": "personal"}})
        return {"created": WORKSPACE_ID, "selected": "personal", "url": origin, "provider_calls": 0}


def select_workspace(root, selection):
    from .runtime import WORKSPACE_ID, selected_context, build_fixture
    if selection not in {"personal", WORKSPACE_ID}:
        raise ValueError("Choose the existing personal or onboarding workspace")
    with private_operator(root) as (manifest, _, configuration, budget):
        require_inactive(configuration, budget)
        if "workspace" not in manifest:
            raise ValueError("Explicitly create the fictional workspace first")
        candidate = {**manifest, "workspace": {**manifest["workspace"], "selected": selection}}
        context = selected_context(root, candidate)
        # Fully validate the other context before its single atomic selection.
        with ExitStack() as stack:
            _, _, _, state = build_fixture(verify_release(root, manifest) / "source", stack)
            context.store(state).load()
        write(root / "installation.json", candidate)
        return {"selected": selection, "url": context.identity.origin, "provider_calls": 0}


def restore_private(root, name):
    from .runtime import selected_context, build_fixture, ordinary_path
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
        raise ValueError("Invalid checkpoint name")
    with private_operator(root) as (manifest, _, configuration, budget):
        require_inactive(configuration, budget)
        context = selected_context(root, manifest)
        raw = ordinary_path(context.checkpoints / name).read_bytes()
        with ExitStack() as stack:
            _, _, _, state = build_fixture(verify_release(root, manifest) / "source", stack)
            store = context.store(state)
            store.load()
            body = store.unpack(raw)
            previous = offline_checkpoint(root)
            store.save(body["state"])
        return {"restored": name, "previous": previous, "workspace": context.binding, "provider_calls": 0}


def reset_fictional_workspace(root):
    """Explicit local demo reset; caller holds control.lock throughout restart."""
    from .runtime import WORKSPACE_ID, selected_context, build_fixture, ordinary_path
    manifest = read(root / "installation.json")
    original = selected_context(root, manifest)
    if not manifest.get("private_profile") or original.key != WORKSPACE_ID or not original.namespace:
        raise ValueError("Select the existing fictional onboarding workspace before reset; personal reset is unavailable")
    # Refuse a missing, foreign or corrupt namespace before touching its server.
    raw = ordinary_path(original.state_path).read_bytes()
    saved = json.loads(raw)
    if (type(saved) is not dict or set(saved) != {"body", "sha256"}
            or type(saved["body"]) is not dict
            or saved["body"].get("namespace") != original.namespace
            or hashlib.sha256(canonical(saved["body"])).hexdigest() != saved["sha256"]):
        raise ValueError("Invalid fictional saved state; preserve it instead of resetting")
    stop(root, wait=True)
    with private_operator(root) as (manifest, _, configuration, budget):
        require_inactive(configuration, budget)
        context = selected_context(root, manifest)
        if context.binding != original.binding:
            raise ValueError("Selected fictional context changed; reset refused")
        with ExitStack() as stack:
            _, _, _, state = build_fixture(verify_release(root, manifest) / "source", stack)
            fresh = state.capture()
            store = context.store(state)
            store.load()  # Validate the latest post-drain typed state before checkpoint/write.
            checkpoint = offline_checkpoint(root)
            store.save(fresh)
            generation = store.generation
    try:
        status = start(root)
        if not status.get("running") or status.get("stopping"):
            raise ValueError("Owned startup was not confirmed")
    except Exception as exc:
        raise ValueError("Fictional reset committed; recovery checkpoint " + checkpoint
                         + ". Startup was not confirmed. Use Status before restarting; do not repeat reset to recover startup.") from exc
    return {"reset": WORKSPACE_ID, "checkpoint": checkpoint, "generation": generation,
            "workspace": context.binding, "url": context.identity.origin + "/app/resume",
            "running": True, "provider_calls": 0}


def resolve_failed_public(root, proof_path, review_path):
    from .provider_budget import request_id
    proof, review = read(proof_path), read(review_path)
    fields = {"schema_version", "installation", "owner", "allocation_sha256", "configuration_sha256",
              "scope", "request_id", "amount", "transport_quiescence", "original_worker_quiescence", "evidence_files"}
    if (type(proof) is not dict or set(proof) != fields or proof["schema_version"] != 1
            or proof["transport_quiescence"] != "synchronous_response_connection_closed"
            or proof["original_worker_quiescence"] != "original_server_lifetime_lock_released"
            or type(proof["evidence_files"]) is not dict or not 3 <= len(proof["evidence_files"]) <= 20):
        raise ValueError("Closed original-operation quiescence proof required")
    request_id(proof["request_id"])
    for name, expected in proof["evidence_files"].items():
        path = Path(name)
        if not path.is_absolute() or not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise ValueError("Original-operation evidence changed or missing")
    proof_sha = digest(proof_path)
    if (type(review) is not dict or set(review) != {"schema_version", "result", "proof_sha256", "recovery_source_sha256", "reviewer_ref"}
            or review["schema_version"] != 1 or review["result"] != "pass" or review["proof_sha256"] != proof_sha
            or review["recovery_source_sha256"] != operator_source_digest()
            or not isinstance(review["reviewer_ref"], str) or not 1 <= len(review["reviewer_ref"]) <= 200):
        raise ValueError("Independent exact-source and quiescence review required")
    # Review is a local operator attestation, not an authenticated review service.
    # OS private-directory access and the command boundary identify the operator.
    with private_operator(root) as (manifest, identity, configuration, budget):
        binding = operator_configuration_digest(root, manifest)
        if (proof["installation"] != manifest["installation"] or proof["owner"] != identity.owner
                or proof["configuration_sha256"] != binding
                or proof["allocation_sha256"] != configuration["allocation_sha256"]):
            raise ValueError("Original private installation/configuration required")
        return budget.resolve_failed_public(owner=identity.owner, scope=proof["scope"],
            request=proof["request_id"], amount=proof["amount"], evidence={"proof_sha256": proof_sha,
                "configuration_sha256": binding, "review_sha256": digest(review_path)})


def arm_public_diagnostic(root):
    """Explicit fictional qualification only. No ordinary content capture."""
    with private_operator(root) as (_, identity, configuration, budget):
        scope = configuration["profiles"]["public"]["scope"]
        if budget.has_active([scope]):
            raise ValueError("Active public operation cannot be diagnosed by replay")
        previous_calls = budget.snapshot(scope)["budget"]["dispatched_calls"]
        parent = root / "logs" / "public-diagnostic"
        budget._ordinary(parent)
        parent.mkdir(exist_ok=True)
        if (parent / "armed.json").exists() or any(parent.glob("operation-*/armed.json")):
            raise ValueError("Existing diagnostic permit must not be duplicated")
        directory = parent / ("operation-" + str(previous_calls + 1))
        directory.mkdir()  # One explicit permit per operation; never overwrite/rearm it.
        permit = {"owner": identity.owner, "allocation_sha256": configuration["allocation_sha256"],
                  "scope": scope, "previous_calls": previous_calls}
        with (directory / "armed.json").open("x", encoding="utf-8") as output:
            json.dump(permit, output)
        return {"armed": "next_public_operation_only", "content": "fictional_qualification_only"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Permanent offline reviewer; all durable installation files stay on X")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("install", "update"):
        command = sub.add_parser(action)
        command.add_argument("--artifact", type=Path, required=True)
        command.add_argument("--artifact-sha256", required=True)
        command.add_argument("--source-sha", required=True)
        command.add_argument("--overlay", type=Path, required=True)
        command.add_argument("--overlay-sha256", required=True)
        command.add_argument("--candidate-state", choices=("reviewed-preview", "accepted-main"), required=True)
        if action == "update":
            command.add_argument("--factory", type=Path)
    for action in ("start", "stop", "status", "checkpoint", "rollback", "serve", "open"):
        sub.add_parser(action)
    sub.add_parser("create-fictional-workspace")
    fresh = sub.add_parser("reset-fictional-workspace")
    fresh.add_argument("--open", action="store_true", help="Open the fresh demo after confirmed restart")
    workspace = sub.add_parser("select-workspace")
    workspace.add_argument("workspace", choices=("personal", "onboarding"))
    restore = sub.add_parser("restore")
    restore.add_argument("checkpoint")
    reset = sub.add_parser("reset")
    reset.add_argument("--member", choices=("g-member-a", "g-member-b", "g-member-c"), required=True)
    probe = sub.add_parser("probe")
    probe.add_argument("--release", required=True)
    probe.add_argument("--provider-configuration")
    probe.add_argument("--original-provider-configuration", action="store_true")
    probe.add_argument("--rollback-target", action="store_true")
    private = sub.add_parser("setup-private")
    private.add_argument("--origin", required=True)
    private.add_argument("--login", required=True)
    private.add_argument("--allocation", type=Path, required=True)
    private.add_argument("--factory", type=Path, required=True)
    recovery = sub.add_parser("resolve-failed-public")
    recovery.add_argument("--proof", type=Path, required=True)
    recovery.add_argument("--review", type=Path, required=True)
    allowance = sub.add_parser("grant-onboarding-test-allowance")
    allowance.add_argument("--proof", type=Path, required=True)
    allowance.add_argument("--review", type=Path, required=True)
    diagnostic = sub.add_parser("arm-public-diagnostic")
    diagnostic.add_argument("--fictional-qualification-only", action="store_true", required=True)
    args = parser.parse_args(argv)
    root = safe_root(args.root)
    require_private_runtime(root)
    if args.action == "serve":
        manifest, process = read(root / "installation.json"), read(root / "process.json")
        release = verify_release(root, manifest)
        if manifest.get("private_profile") or (root / "private-access.json").exists():
            require_private_files(root)
        if process["release"] != manifest["release"] or process["installation"] != manifest["installation"]:
            raise ValueError("Owned startup identity changed")
        from .runtime import selected_context
        if process.get("workspace") != selected_context(root, manifest).binding:
            raise ValueError("Owned startup workspace changed")
        from .runtime import serve
        with exclusive(root, "server.lock"):
            serve(root, release, {"installation": manifest["installation"], "instance": process["instance"], "release": manifest["release"], "port": PORT,
                                  "source_sha": manifest["artifact"]["source_sha"], "candidate_state": manifest["artifact"]["candidate_state"], "provider": "offline_synthetic_or_unavailable"}, process["token"])
        return
    if args.action == "probe":
        if not re.fullmatch(r"[0-9a-f]{40}-[0-9a-f]{12}", args.release):
            raise ValueError("Invalid release identity")
        from .runtime import build_fixture, selected_context, ordinary_path
        from .persistence import SnapshotStore
        with ExitStack() as stack:
            current = read(root / "installation.json") if (root / "installation.json").exists() else {}
            target = read(root / "previous.json")["manifest"] if args.rollback_target else None
            if target is not None:
                if (target["release"] != args.release or target.get("provider_configuration") != args.provider_configuration
                        or args.original_provider_configuration != ("provider_configuration" not in target)):
                    raise ValueError("Explicit rollback app/configuration pair differs from the preserved target")
                verify_release(root, target)
            source = root / "releases" / args.release / "source"
            interface = ocr_configuration = None
            if (root / "private-access.json").exists() or current.get("private_profile"):
                require_private_files(root)
                sys.path.insert(0, str(source))
                from .providers import (load_configuration, selected_configuration,
                                        selected_ocr_configuration, onboarding_qualification)
                identity = selected_context(root, current).identity
                configuration = load_configuration(root, identity, source, configuration_id=args.provider_configuration,
                                   original=args.original_provider_configuration)
                qualify_onboarding_allowance_accounting(root, target, configuration)
                _, interface = selected_configuration(root, args.provider_configuration,
                                                      original=args.original_provider_configuration)
                ocr_configuration = selected_ocr_configuration(root, configuration_id=args.provider_configuration,
                                                              original=args.original_provider_configuration)
            selected_proof = onboarding_qualification(interface) if interface is not None else None
            expected_ocr = selected_proof["resume_ocr"]["manifest_sha256"] if selected_proof else None
            fixture, app, _, state = build_fixture(source, stack, ocr_configuration=ocr_configuration,
                                                ocr_manifest_sha256=expected_ocr)
            if interface is not None and (len(state.bindings) != 29
                    or state.contract != "9b0391909811ad0caf0a2056b857d6319f0161026a46dfca0b00c3239954ae86"):
                raise ValueError("Private snapshot bindings or approved record constructors changed")
            fresh = state.capture()
            selections = [current]
            if "workspace" in current:
                selections = [{**current, "workspace": {**current["workspace"], "selected": name}}
                              for name in ("personal", "onboarding")]
            required = set()
            namespaces = []
            for selection in selections:
                state.restore(fresh)
                context = selected_context(root, selection)
                store = context.store(state)
                if context.namespace and not ordinary_path(store.path).is_file():
                    raise ValueError("Fictional saved state missing; probe cannot recreate it")
                if ordinary_path(store.path).exists():
                    raw = store.path.read_bytes()
                    store.load()
                    encoded = state.capture()
                    required.update(required_onboarding_behaviors(state))
                    # Capture/resave proof runs on an external temporary copy;
                    # the actual snapshot and its generation are never changed.
                    with tempfile.TemporaryDirectory(prefix="peerslate-private-qualification-") as directory:
                        copy = SnapshotStore(Path(directory) / "state.json", state, namespace=context.namespace)
                        copy.path.write_bytes(raw)
                        copy.load()
                        copy.save(encoded)
                        copy.load()
                        if state.capture() != encoded:
                            raise ValueError("Target loses typed snapshot content through capture/resave")
                    if store.path.read_bytes() != raw:
                        raise ValueError("Saved content changed during qualification; stop and qualify a fresh copy")
                namespaces.append(context.key)
            proof = onboarding_qualification(interface) if interface is not None else None
            if required and proof is None:
                raise ValueError("Target lacks exact reviewed factory/source proof for current approved credential/composer behavior")
            declared = proof["behaviors"] if proof is not None else []
            require_onboarding_behavior_coverage(required, declared)
            if required and target is not None:
                for relative in ("tools/local_reviewer/runtime.py", "tools/local_reviewer/manager.py"):
                    if target.get("controller_files", {}).get(relative) != digest(Path(__file__).resolve().parents[2] / relative):
                        raise ValueError("Target controller lacks the qualified save and semantic rollback boundary; preserve content and use a reviewed forward correction")
            behaviors = []
            if proof is not None:
                state.restore(fresh)
                behaviors = qualify_onboarding_behavior(fixture, app, behaviors=declared)
            require_onboarding_behavior_coverage(required, declared, behaviors)
            print(json.dumps({"compatible": True, "contract": state.contract, "bindings": len(state.bindings),
                              "record_constructors": len(state.codec.classes),
                              "namespaces": namespaces, "required_behaviors": sorted(required),
                              "qualified_behaviors": behaviors, "provider_dispatches": 0,
                              "ocr_manifest_verified": ocr_configuration is not None}))
        return
    with exclusive(root):
        if args.action in {"install", "update"}:
            result = install(root, args)
        elif args.action == "start":
            result = start(root)
        elif args.action == "stop":
            result = stop(root)
        elif args.action == "status":
            result = owned_status(root)
        elif args.action == "checkpoint":
            result = control(root, "checkpoint") if owned_status(root)["running"] else {"checkpoint": offline_checkpoint(root)}
        elif args.action == "restore":
            result = (restore_private(root, args.checkpoint) if read(root / "installation.json").get("private_profile")
                      else control(root, "restore", {"checkpoint": args.checkpoint}))
        elif args.action == "create-fictional-workspace":
            result = create_workspace(root)
        elif args.action == "select-workspace":
            result = select_workspace(root, args.workspace)
        elif args.action == "reset-fictional-workspace":
            result = reset_fictional_workspace(root)
            if args.open:
                import webbrowser
                result["browser_open_requested"] = bool(webbrowser.open(result["url"]))
        elif args.action == "reset":
            result = control(root, "reset", {"member": args.member})
        elif args.action == "rollback":
            result = rollback(root)
        elif args.action == "setup-private":
            result = setup_private(root, args)
        elif args.action == "resolve-failed-public":
            result = resolve_failed_public(root, args.proof, args.review)
        elif args.action == "grant-onboarding-test-allowance":
            result = grant_onboarding_test_allowance(root, args.proof, args.review)
        elif args.action == "arm-public-diagnostic":
            result = arm_public_diagnostic(root)
        elif args.action == "open":
            from .runtime import selected_context
            import webbrowser
            identity = selected_context(root).identity
            if read(root / "installation.json").get("private_profile") and identity is None:
                raise ValueError("Private profile configuration missing")
            url = identity.origin if identity else "http://127.0.0.1:" + str(PORT)
            webbrowser.open(url)
            result = {"opened": url}
        print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        raise SystemExit(1)
