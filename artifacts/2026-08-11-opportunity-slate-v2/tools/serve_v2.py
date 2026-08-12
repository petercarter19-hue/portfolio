"""Throwaway visual-verification server for Opportunity Slate v2 R1.

Reuses the lane's own test factory; the fake database cycles the exact row
pattern each GET consumes, so repeated page loads stay stable. Local only.
"""
import os
import sys

sys.path.insert(0, r"C:\Users\peter\Documents\portfolio-opportunity-slate-v2-20260811")
os.environ.setdefault("ANTHROPIC_API_KEY", "placeholder-not-a-real-key")

from tests.test_opportunity_slate_v2 import make_app, _working_row, _identity_row  # noqa: E402

mode = sys.argv[1] if len(sys.argv) > 1 else "stage1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

app, database, _patcher = make_app(rows=[])

# Round-2 parity fixture: mockup 05's own Meridian Aerospace document, so
# the captured-wording plane is verifiable against the mockup instead of
# the one-line stub round 1 served (recorded evidence gap in F6).
MERIDIAN_DOC = """Senior Systems Engineering Manager

Meridian Aerospace is seeking a Senior Systems Engineering Manager to lead multidisciplinary systems engineering activities across the program lifecycle.

Required qualifications

• Experience leading Agile delivery in a SAFe environment, including direct ownership of PI planning and ART-level coordination within the last five years.
• Systems engineering lifecycle leadership across complex programs.
• Model-based systems engineering (MBSE) experience.
• Cross-functional team leadership.
• Risk management and mitigation.
• DoD program or acquisition experience.
• Budgeting and cost management.
• Active Secret security clearance.

Responsibilities

• Lead technical planning, integration, verification, and validation activities.
• Partner with program management and functional leads to manage execution.
• Guide team development, priorities, and delivery quality.

Location
Charlotte, North Carolina. Occasional travel may be required."""

if mode == "stage1":
    def pattern():
        return [None, None]
else:
    def pattern():
        return [None, _working_row(original_text=MERIDIAN_DOC), _identity_row()]


@app.before_request
def _reset_fake_rows():
    database.rows = list(pattern())
app.config["TESTING"] = False
print(f"serving mode={mode} on http://127.0.0.1:{port}/opportunity-slate", flush=True)
app.run(port=port, use_reloader=False)
