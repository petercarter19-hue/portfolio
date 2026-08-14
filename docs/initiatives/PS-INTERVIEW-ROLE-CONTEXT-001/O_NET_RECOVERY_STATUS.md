# O*NET recovery status

Date: 2026-08-14
Status: researched and planned; never implemented or connected.

## What happened

The O*NET database was not deleted or removed from PeerSlate. It never crossed
from an accepted architecture discussion into an activated repository package.

1. On 2026-08-04, O*NET 30.3 was inventoried for Opportunity Slate. The accepted
   working direction was a complete, versioned offline snapshot with only a
   small subset evaluated initially.
2. The same session attempted to activate a Protected Opportunity Slate V2
   package, but repository writer capacity was full. No O*NET branch, package,
   download, importer, migration, service, or test was created.
3. The 2026-08-11 Opportunity Slate replacement architecture and R1 package
   moved forward with paste/upload/public-link intake and captured-source review.
   O*NET was not adopted into that package's scope. R1 explicitly excluded AI
   interpretation and later requirement/alignment work.
4. The 2026-08-14 audit of current Azure `origin/main`, Git object names, local
   Downloads/iCloud filenames, and text handoffs found no O*NET snapshot,
   archive, checksum manifest, importer, schema object, service, configuration,
   or test.

The gap is therefore **planning-to-activation**, not a missing production
database or a cleanup loss.

## Current official source

The current production release is **O*NET 30.3, May 2026**. The official O*NET
Resource Center offers downloadable tabular, SQL, and RDF forms. The database
content is generally CC BY 4.0 and requires version-specific USDOL/ETA
attribution, a license link, and disclosure of modifications.

Official references:

- https://www.onetcenter.org/database.html
- https://www.onetcenter.org/db_releases.html
- https://www.onetcenter.org/license_db.html

O*NET Web Services also exists, but PeerSlate's accepted boundary is an offline
snapshot. A member request must not depend on an external taxonomy API, its
availability, or its latest mutable response.

## Accepted recovery disposition

- Do not download or vendor the full archive during this direction-only package.
- O*NET is not required to tailor Interview questions from a confirmed employer
  posting. Employer wording remains the primary source.
- A later implementation begins with an acquisition manifest: official release,
  source URL, download timestamp, archive SHA-256, format, license/attribution,
  and storage location.
- Preserve the unmodified archive outside the application deploy artifact.
- Build a repeatable selective import/evaluation step for occupation records,
  titles, related occupations, and selected task cues.
- Run blinded role-resolution and question-coverage tests before adopting any
  O*NET-informed mapping.
- Keep the feature fully functional when O*NET is absent or an occupation cannot
  be resolved.

## Truth statement

As of this record, PeerSlate uses no O*NET database content in its runtime,
Opportunity Slate, Interview Studio, search, model prompts, or member-facing UI.
This file restores the decision and next gate; it does not claim O*NET
acquisition, implementation, enablement, or live use. The surrounding
documentation/governance artifact was included in Azure pipeline 1047's
successful production deployment, but that did not deploy an O*NET archive,
service, schema, configuration, or product behavior.
