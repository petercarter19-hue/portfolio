"""Owner-only, read-only PeerSlate Control Room routes.

Two GET endpoints, each independently guarded by ``owner_required``:

* ``GET /owner/control-room``           — the server-rendered dashboard page.
* ``GET /owner/control-room/data.json`` — the same projection as JSON, so the
  page's "Refresh" control can update in place. Read-only.

There are deliberately **no** POST/PUT/PATCH/DELETE routes, form actions, or
mutation endpoints here. The dashboard is a projection of project truth; it
cannot change project state. The page is fully rendered server-side, so no
private data is exposed during unauthorized loading, redirects, or hydration.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template

from control_room_projection import build_projection, initiative_details
from owner_authorization import owner_required, resolve_owner


control_room = Blueprint("control_room", __name__)


def _harden(response):
    """Defense-in-depth headers. The owner check is the access control; these
    keep the surface out of caches and search indexes as an extra layer."""
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@control_room.get("/owner/control-room")
@owner_required
def control_room_page():
    projection = build_projection()
    owner = resolve_owner()
    owner_label = None
    if owner is not None:
        owner_label = (
            getattr(owner, "display_name", None)
            or getattr(owner, "email", None)
            or "Owner"
        )
    response = current_app.make_response(
        render_template(
            "control_room.html",
            page_title="Control Room",
            projection=projection,
            owner_label=owner_label,
            # Per-initiative plain-language detail for the pop-out, rendered
            # once into the page (kept out of data.json to keep the poll lean).
            initiative_details=initiative_details(),
        )
    )
    return _harden(response)


@control_room.get("/owner/control-room/data.json")
@owner_required
def control_room_data():
    response = jsonify(build_projection())
    return _harden(response)
