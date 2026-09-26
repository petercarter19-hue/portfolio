# Remaining E: Resume publication integration

Package `PS-MVP1-PUBLICATION-INTEGRATION-001` implements the accepted ChatGPT
architecture for Resume publication consistency. Architecture remains ChatGPT.
This writer implements, tests, and self-reviews. Independent Grok review of the
frozen candidate and mandatory final ChatGPT/Astra High review are required
before merge. Feature enablement, F, production schema, production permissions,
identity, and deployment remain outside this package.

## Implemented boundary

- Strict policy/draft mapping: missing or unsupported versions/lifecycle refuse.
  SQL `load_owner` snapshots remain unavailable. Living Resume catalog uses
  list/get so the private editor still lists facts; publication eligibility
  requires both `access_revision` and `content_version`.
- Neutral saved review evidence supports a first explicit visitor-AI grant.
  Review still writes nothing and never constructs a PUBLIC `SourceVersion`.
- One in-memory complete publication command owns publish, correction,
  restriction, restore-private, sharing-off, catalog withdraw and media
  restrict. My Data/entry-policy writes share that boundary through
  `commit_linked_write`. SQL proposes one closed procedure with lock order
  sharing → sorted entries → draft → publication/receipts → media/catalog,
  UTF-8 length-prefixed `resume-canonical-source.v1` evidence, and both
  manifests produced from resulting rows.
- Guest HTML/JSON omit visitor-AI source material. Media delivery authorizes,
  then accesses storage, then re-authorizes immediately before bytes.
- Owner review/publish uses durable list/get adapters, not product config
  candidates. The labeled Pete example stays separately classified.

Required E browser CI is wired in `azure-pipelines.yml`. This correction does
not enable the feature, apply schema, or execute the SQL engine proof.

## SQL proof

Proof ID `ps-mvp1-ef-sql-proof-20260916-01` is prepared. `--plan` is the
default. `--execute` is implemented and gated: missing or fabricated
authorization refuses without contacting resources. The Linux x86_64/glibc
CPython 3.12 client lock in `requirements-resume-publication-sql-proof.txt`
pins mssql-python, azure-identity, and transitive published-wheel hashes.
Those digests are PyPI metadata, not independently verified downloaded bytes.
Authorized execute selects Python 3.12, downloads the hashed wheelhouse for
that Linux target, copies wheels and proof source into the isolated client,
installs offline with `--require-hashes --no-index --find-links`, and runs
oracles inside that client. The accepted resource plan named a content-ID
client image; this package reconciles that by copying reviewed source onto the
pinned `python:3.12-slim` digest and recording a `docker commit` content ID,
because a client Dockerfile is outside the claimed surfaces. Host
`job_local_connect` is not the oracle runtime. This package does not run the
authorized engine.

```text
python -B scripts/run_resume_publication_sql_proof.py --plan
python -B scripts/configure_resume_publication_sql_authority.py --plan
```

## Tests

Focused contract, service, HTTP, catalog, static SQL, engine-adapter, browser
runner, and gated proof tests live under `tests/test_resume_publication_*.py`.
Browser journeys use real application adapters. Engine live oracles skip unless
DSN and exact authorization are both present; they never SkipTest inside that
authorized method.
