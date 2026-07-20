# Owner Home editable-package generator — Windows fix and dependency record

Package: PS-OWNER-HOME-VIEWER-GATE-001 (known refinement 4)
Recorded: 2026-07-19 by the Claude/Fable architecture writer.

## What this directory contains

Patched copies of the two generator entry scripts from the accepted authority
package `PeerSlate-Owner-Home-Editable-Authority-Candidate-31864e4.zip`
(SHA-256 `31daf8f3d92110aed7fd540a9a20969d6084eefd59e4b94dd173db51b97575be`):

- `generate_all.mjs` — composes all 23 editable SVG review screens.
- `render_exports.mjs` — converts the SVG masters into PNG review exports.

The verbatim accepted originals remain untouched in
`../authority-candidate-31864e4/source/`. That directory is the accepted
artifact; this directory is the documented correction. `design_system.mjs`
needs no patch (it contains no filesystem or URL path handling) and is not
duplicated here; run the patched scripts from a copy of the package `source/`
directory, or apply the same two-line patch in place.

## The Windows defect and the exact fix

Both original scripts derive their location with:

```js
const here = path.dirname(new URL(import.meta.url).pathname);
```

On Windows, `new URL(import.meta.url).pathname` returns a POSIX-style path with
a leading slash before the drive letter (`/C:/Users/...`) and percent-encodes
spaces and non-ASCII characters. Feeding that into `path.dirname`/`path.join`
produces invalid Windows paths, so `fs.mkdirSync`/`fs.readFileSync` fail. The
patch applied here is the standard correction named by the refinement register:

```js
import {fileURLToPath} from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
```

No other behavior was changed. The rest of each file is byte-identical to the
accepted original.

## Dependencies and versions

- **Node.js ≥ 18 LTS** for both scripts. Required language/runtime features:
  `node:` protocol imports, ES modules (`.mjs`), top-level `await`
  (render script), and `String.prototype.replaceAll` (Node 15+).
- **`generate_all.mjs`: no third-party dependency.** It uses only `node:fs`,
  `node:path`, `node:url`, and the package's own `design_system.mjs`.
- **`render_exports.mjs`: requires `sharp`** (loaded via
  `createRequire(import.meta.url)('sharp')`). The accepted package's README
  describes it as "the locally available Sharp dependency" and does not pin a
  version; the current maintained line at the time of this record is
  `sharp@^0.33`. Install with `npm install sharp` in the directory the script
  runs from (or a parent with a resolvable `node_modules`).
- Export 20 regeneration (`authorityComparison()` inside `generate_all.mjs`)
  needs either the originally supplied binding-authority PNG at
  `../upload/01_owner_home_interface_mockup(1).png` relative to the package
  root, or the existing `exports/20-owner-home-authority-comparison.svg` from
  which it re-extracts the embedded authority image. The preserved package
  includes that export, so regeneration works from the archive alone.

## Verification status

- Static verification: the patch is the exact `fileURLToPath(import.meta.url)`
  correction required by the package refinement register; no other lines
  differ from the accepted originals.
- Runtime verification: **not executed on this machine** — Node.js is not
  installed on the Windows workstation used for this architecture branch
  (`node` is absent from both Git Bash and PowerShell PATH). The first
  implementation package that regenerates exports must run
  `node generate_all.mjs` followed by `node render_exports.mjs` from a package
  copy and record the output as evidence.
