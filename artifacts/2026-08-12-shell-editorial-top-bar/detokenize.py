"""Produce the de-tokenized twin of public-navigation.css, for re-proving that
the --ps-shell-* layer is inert whenever the shell's CSS changes.

    python detokenize.py off   # swap in the de-tokenized twin, keep a backup
    python detokenize.py on    # restore the tokenized original

It reverses the substitution exactly: both token-definition blocks and the
shell's own focus rule come out, and every --ps-shell-* reference goes back to
the production variable it aliases.

WHAT A DELTA MEANS CHANGED ON 2026-08-13. Until the owner colour round the
family was a pure alias layer, so ANY difference was a defect. It now also
carries one deliberate cross-route correction: on a route without
body.slate-light — which is /experience and only /experience — six tokens are
pinned to the values every other route already resolves, so the shell stops
repainting itself per page. The twin this module produces is therefore "what
the shell would paint with no token layer at all", and the expected result is:

    zero deltas on every body.slate-light route, and
    exactly six pinned values on /experience, and nothing else anywhere.

verify_tokenization_computed.py classifies the run on exactly that basis.
"""
import shutil
import sys
from pathlib import Path

CSS = Path("static/css/public-navigation.css")
BACKUP = Path("static/css/.public-navigation.tokenized")

REVERSE = [
    ("var(--ps-shell-shadow)", "var(--shadow)"),
    ("var(--ps-shell-rail)", "var(--surface-soft)"),
    ("var(--ps-shell-surface)", "var(--surface)"),
    ("var(--ps-shell-border)", "var(--border)"),
    ("var(--ps-shell-text-muted)", "var(--text-muted)"),
    ("var(--ps-shell-text)", "var(--text)"),
    ("var(--ps-shell-accent-soft)", "var(--accent-soft)"),
    ("var(--ps-shell-accent-room)", "var(--ps-page-accent)"),
    ("var(--ps-shell-accent)", "var(--accent)"),
    ("var(--ps-shell-stage)", "var(--bg-elevated)"),
    ("var(--ps-shell-ground)", "var(--bg)"),
]


def detokenize(source: str) -> str:
    # Both declaration blocks come out in one span: the family itself, the
    # ONE SHELL ONE PALETTE comment between them, and the cross-route
    # correction. They are contiguous by design so this stays a single cut.
    start = source.index("/*\n * THE SHELL TOKEN FAMILY")
    correction = source.index(
        'body:not([data-theme="dark"]):not(.slate-light) .global-header,')
    end = source.index("\n}\n", correction) + 3
    out = source[:start] + source[end:]

    focus_start = out.index("/* The shell states its own focus ring")
    focus_end = out.index("\n}\n", focus_start) + 3
    out = out[:focus_start] + out[focus_end:]

    for token, production in REVERSE:
        out = out.replace(token, production)
    # Prose in the file header still names the tokens; what must not survive
    # is a live reference.
    assert "var(--ps-shell-" not in out, "a shell token reference survived"
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "off"
    if mode == "off":
        original = CSS.read_text(encoding="utf-8")
        assert "--ps-shell-" in original, "already de-tokenized"
        shutil.copyfile(CSS, BACKUP)
        CSS.write_text(detokenize(original), encoding="utf-8")
        print("de-tokenized; tokenized original saved to", BACKUP)
    elif mode == "on":
        assert BACKUP.exists(), "no backup to restore"
        shutil.copyfile(BACKUP, CSS)
        BACKUP.unlink()
        print("tokenized stylesheet restored")
    else:
        raise SystemExit("usage: detokenize.py [off|on]")
