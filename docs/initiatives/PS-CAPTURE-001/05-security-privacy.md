# Security and privacy

- Ownership comes from trusted server identity, never a form field, URL value,
  browser state, email address, or caller-supplied profile ID.
- Both procedures resolve `app_users.user_key` to the active member profile and
  scope every capture read/write to that profile.
- Create forces `private` and `captured`; the client cannot select another
  audience or publication state.
- Capture bodies are not written to application logs, audit metadata, redirect
  parameters, or client-side persistent state.
- SQL calls are procedure-allowlisted and parameter bound.
- Form writes reject mismatched `Origin` values and cross-site
  `Sec-Fetch-Site` requests before identity or storage calls.
- The audit event records actor, capture key, type, visibility, outcome, and
  time, but not the private text.
- The two-owner database verification uses unique synthetic identities inside
  one transaction and rolls back all synthetic rows and audit events.
- Generic 503 responses avoid leaking database details.

## Deferred member controls

Archive/delete, correction history, export, explicit audience review, and
publication are not falsely exposed in this slice. They require separate data
and UX contracts before implementation.
