# Projects Experience — Maintenance Guide

The Projects exhibition (`/petec/work`) and case studies
(`/petec/work/<slug>`) render entirely from the profile's `projects` array
in `static/data/resume_data.json`. No project facts live in templates.

## How to add a fourth project

Append an object to `projects` in the profile's resume data file:

```json
{
  "id": "my-new-project",
  "slug": "my-new-project",
  "number": "04",
  "title": "My New Project",
  "short_title": "New Project",
  "summary": "One approved sentence.",
  "status": "Live",                     // Live | Completed | Demonstration
  "status_note": "Shown when no CTA renders",
  "project_type": "Platform · Web",
  "tags": ["Platform", "Web"],
  "technologies": ["Python", "Flask"],
  "artifact_type": "digital",           // digital | academic | physical
  "artifact_alt": "Accessible description of the artifact visual",
  "is_featured": false,
  "is_demo": false,
  "details_ready": true,                // false → no detail page, 404
  "publish_detail": true,               // false → no detail page, 404
  "noindex": false,
  "live_url": "/petec/somewhere",       // "" if none
  "display_order": 4,
  "cta": "Enter the project",
  "case_study_sections": [ ... ]        // see below; [] when not ready
}
```

The exhibition automatically renders the new panel, its selector dot, its
scroll marker, and (when `details_ready` + `publish_detail` +
`case_study_sections` are truthy) its case-study route.

`artifact_type` picks the panel's artifact renderer:
- `digital` → translucent browser frame with interface fragments
- `academic` → navy blueprint notebook with abstract technical drawing
- `physical` → warm model/plan/material treatment

## Case-study sections

Six supported `section_key` values, rendered in data order:
`idea`, `problem`, `role`, `build`, `decisions`, `result`.
Each section: `{section_key, eyebrow, title, body, supporting_items[],
closing?, system_layout?}`. `supporting_items` are `{title, detail, why?}`
(`why` renders only in the decisions ledger). A project with fewer
approved sections simply lists fewer — never pad with invented content.

## How to replace the demonstration project

The Sample Home Build exists only to show that PeerSlate projects can be
physical builds. To replace it, edit its entry in `projects`:
1. Change `title`, `summary`, `tags`, `artifact_type`, etc. to the real
   project's approved content.
2. Set `"is_demo": false` and `"status"` to the real status.
3. Remove the demo language from `status_note`.
4. When a case study is approved, set `details_ready` and
   `publish_detail` to `true` and add `case_study_sections`.
To remove it entirely, delete the object — the exhibition adapts to any
project count (the wings simply rebalance).

## How to fill in the Senior Project

When Pete supplies the real description, images, tools, outcome, and role:
1. Update `summary` and add approved `technologies`/`tags`.
2. Replace `status_note` ("Case study in preparation") as appropriate.
3. Add `case_study_sections` with approved copy only.
4. Set `details_ready: true` and `publish_detail: true`.
The index panel and detail route light up automatically; the abstract
blueprint artifact can stay or move to `digital`/`physical` as fits.

## Guardrails

- The detail route 404s unless `details_ready`, `publish_detail`, AND
  `case_study_sections` are all truthy — an incomplete project can never
  render an empty or invented case study.
- The demo panel's notice renders whenever `is_demo` is true and stays
  visible even while the panel is inactive.
- Never copy text from the generated mockups: the fictional-content
  blocklist lives in `00_READ_ME_FIRST.txt`.
