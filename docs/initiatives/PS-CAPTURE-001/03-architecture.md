# Architecture

```text
Browser
  -> GET/POST /app/capture
  -> owner blueprint
  -> get_current_identity()
       -> trusted Easy Auth claims
       -> usp_UpsertAppUserFromAuth
       -> opaque identity.user_key
  -> allowlisted DatabaseService call with bound parameters
       -> usp_CreateCapture or usp_ListCapturesForOwner
       -> app_users.user_key -> member_profiles.profile_id
       -> dbo.captures filtered by owner_profile_id
  -> owner_capture.html
```

The browser submits only the capture body. Identity, owner profile, visibility,
and status are resolved or enforced on the server. The create procedure commits
the capture and a metadata-only audit event in one transaction. The application
does not log the body.

The capture row is the canonical private intake/source. Future destinations
must reference it rather than copy the authoritative body into competing source
records. That placement relationship is deliberately deferred.

## Failure paths

- Missing identity: redirect to sign-in.
- Blank/overlong body: deterministic redirect with an allowlisted message key;
  no database call.
- Database or identity persistence failure: privacy-safe server log and generic
  503 response.
- Create procedure returns no row: treat as failure; never display saved state.
