"""Mechanical transitive closure check for the guarded app.py boundary (B2).

Starting from the guarded Interview fragments, every free name each
fragment reads must resolve to something whose behaviour is already
bound into Interview release identity:

- another app.py definition that itself lies inside a guarded fragment;
- an import of a guarded-source module (its file bytes are guarded-paths
  entries);
- an import of a hash-locked external distribution (B3 runtime lock);
- an allowlisted standard-library module;
- a Python builtin;
- one explicitly documented boundary global.

Anything else is a closure violation: an unguarded helper, global,
module, or data path that could alter authorization, refusal precedence,
provider bytes, status, headers, response serialization, evidence,
context, or call eligibility without moving Interview identity.

This module is analysis-only (no Flask import); the enforcement lives in
tests/interview_ai/test_guarded_app_closure.py, which also proves the
LIVE registered routes/hooks/error handlers execute from guarded
regions.
"""

import ast
import symtable
import sys

from services.interview_ai.fragments import (
    FRAGMENT_CLOSE,
    FRAGMENT_OPEN,
    FragmentError,
)

# Imports whose SOURCE FILES are guarded-paths entries (byte-hashed into
# runtime_core_digest). A change to any of them moves Interview identity.
GUARDED_SOURCE_MODULE_ROOTS = frozenset({
    "services",           # services/interview_ai/**, services/database_service.py
    "database_service",
    "db",
    "identity",
    "owner_authorization",
})

# Imports satisfied by hash-locked external distributions (B3). The test
# cross-checks each of these against the recorded runtime-lock closure,
# so this set cannot silently name an unlocked package.
LOCKED_DISTRIBUTION_IMPORT_ROOTS = {
    "flask": "flask",
    "flask_limiter": "Flask-Limiter",
    "werkzeug": "Werkzeug",
    "anthropic": "anthropic",
    "itsdangerous": "itsdangerous",
    "dotenv": "python-dotenv",
}

# Standard-library modules the guarded boundary may use. Closed on
# purpose: a new stdlib use inside a fragment is a reviewed change.
ALLOWED_STDLIB_ROOTS = frozenset({
    "os", "json", "re", "time", "hashlib", "ipaddress", "copy",
    "gzip", "io", "functools", "logging",
})

# The single documented boundary object: the Flask application instance.
# Its Interview-relevant registered behaviours (routing, request hooks,
# error handlers, rate limiting) are themselves fragment-guarded and
# asserted live by the closure test, and the flask distribution that
# implements it is hash-locked; the constructor/config plumbing is
# deployment surface, not Interview logic.
ALLOWED_BOUNDARY_GLOBALS = frozenset({"app"})


def fragment_line_ranges(source_bytes):
    """Return {name: (first_content_line, last_content_line)} (1-based,
    inclusive), using the same marker grammar as the byte extractor."""
    ranges = {}
    current_name = None
    current_start = None
    open_marker = FRAGMENT_OPEN.strip()
    close_marker = FRAGMENT_CLOSE.strip()
    for line_number, raw_line in enumerate(
        source_bytes.splitlines(keepends=True), start=1
    ):
        line = raw_line.decode("utf-8", errors="replace").strip()
        if line.startswith(open_marker) and line != open_marker:
            if current_name is not None:
                raise FragmentError("nested fragment markers")
            current_name = line[len(open_marker):].strip()
            current_start = line_number + 1
        elif line.startswith(close_marker) and line != close_marker:
            if current_name is None:
                raise FragmentError("closing marker without an open fragment")
            ranges[current_name] = (current_start, line_number - 1)
            current_name = None
    if current_name is not None:
        raise FragmentError("unterminated guarded fragment")
    return ranges


def _module_binding_map(tree):
    """Map every top-level app.py binding to its defining statement span.

    Imported names map to ("import", module_root); defined/assigned names
    map to ("source", first_line, last_line) where the span includes
    decorators.
    """
    bindings = {}

    def record_span(names, node):
        start = node.lineno
        for decorator in getattr(node, "decorator_list", []):
            start = min(start, decorator.lineno)
        span = ("source", start, node.end_lineno)
        for name in names:
            bindings[name] = span

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                bindings[bound] = ("import", alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            for alias in node.names:
                bindings[alias.asname or alias.name] = ("import", root)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            record_span([node.name], node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = []
            for target in targets:
                for leaf in ast.walk(target):
                    if isinstance(leaf, ast.Name):
                        names.append(leaf.id)
            record_span(names, node)
        elif isinstance(node, (ast.If, ast.Try, ast.For, ast.While, ast.With)):
            # Conditional top-level bindings (e.g. guarded config blocks):
            # bind every Name stored anywhere inside to the whole statement.
            names = []
            for leaf in ast.walk(node):
                if isinstance(leaf, ast.Name) and isinstance(leaf.ctx, ast.Store):
                    names.append(leaf.id)
                elif isinstance(leaf, (ast.FunctionDef, ast.ClassDef)):
                    names.append(leaf.name)
            for name in names:
                bindings.setdefault(name, ("source", node.lineno, node.end_lineno))
    return bindings


def _free_names(fragment_source):
    """Every identifier a fragment reads from the enclosing module scope."""
    table = symtable.symtable(fragment_source, "<fragment>", "exec")
    free = set()

    def walk(scope):
        for symbol in scope.get_symbols():
            if scope.get_type() == "module":
                if symbol.is_referenced() and not (
                    symbol.is_assigned() or symbol.is_imported()
                ):
                    free.add(symbol.get_name())
            else:
                if symbol.is_global():
                    free.add(symbol.get_name())
        for child in scope.get_children():
            walk(child)

    walk(table)
    # Names the fragment itself binds at module level are not free.
    module_bound = {
        symbol.get_name()
        for symbol in table.get_symbols()
        if symbol.is_assigned() or symbol.is_imported()
    }
    return free - module_bound


def analyze_app_closure(source_bytes):
    """Return a sorted list of closure violations (empty = closed).

    Each violation is a human-readable string naming the fragment, the
    free name, and why it is outside the guarded closure.
    """
    text = source_bytes.decode("utf-8")
    tree = ast.parse(text)
    bindings = _module_binding_map(tree)
    ranges = fragment_line_ranges(source_bytes)
    if not ranges:
        return ["app.py contains no guarded fragments"]

    lines = text.splitlines(keepends=True)

    def fragment_source(name):
        start, end = ranges[name]
        return "".join(lines[start - 1:end])

    def line_is_guarded(start, end):
        return any(
            start >= fragment_start and end <= fragment_end
            for fragment_start, fragment_end in ranges.values()
        )

    import builtins as _builtins
    builtin_names = set(dir(_builtins))

    violations = []
    for name in sorted(ranges):
        for free_name in sorted(_free_names(fragment_source(name))):
            if free_name in builtin_names:
                continue
            if free_name.startswith("__") and free_name.endswith("__"):
                # Module dunders (__file__, __name__) are interpreter-owned.
                continue
            if free_name in ALLOWED_BOUNDARY_GLOBALS:
                continue
            binding = bindings.get(free_name)
            if binding is None:
                violations.append(
                    "%s: %r has no module-level binding in app.py"
                    % (name, free_name)
                )
                continue
            if binding[0] == "import":
                root = binding[1]
                if root in GUARDED_SOURCE_MODULE_ROOTS:
                    continue
                if root in LOCKED_DISTRIBUTION_IMPORT_ROOTS:
                    continue
                if root in ALLOWED_STDLIB_ROOTS and root in sys.stdlib_module_names:
                    continue
                violations.append(
                    "%s: %r imports unguarded/unlocked module %r"
                    % (name, free_name, root)
                )
                continue
            _kind, start, end = binding
            if not line_is_guarded(start, end):
                violations.append(
                    "%s: %r is defined at app.py lines %d-%d outside every "
                    "guarded fragment" % (name, free_name, start, end)
                )
    return violations
