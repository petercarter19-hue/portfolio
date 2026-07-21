# PS-MESSAGING-001 — Architecture and Safety Requirements

## Normative requirements

- **PS-MSG-001:** Messaging shall be a separate domain from comments,
  responses, notifications, Connection requests, support, and public or
  permissioned Ask [Name] AI.
- **PS-MSG-002:** The first slice shall require trusted signed-in identity and a
  deterministic eligible relationship/consent state between participants.
- **PS-MSG-003:** Public profile visibility, public Journal visibility, shared
  employer, similar goal, AI match, or knowing a slug shall not authorize a DM.
- **PS-MSG-004:** The product shall define request/accept/decline/revoke or an
  equivalent consent model before a thread can receive messages.
- **PS-MSG-005:** Block shall stop new messages, requests, notifications, and
  referenced-object retrieval as defined by policy, without exposing the
  blocker's private reason.
- **PS-MSG-006:** Mute shall suppress notifications without changing sender
  authorization or falsely indicating delivery/read behavior.
- **PS-MSG-007:** Report shall preserve minimum necessary evidence under a
  disclosed moderation/retention policy and shall not silently send private
  Journal content unrelated to the report.
- **PS-MSG-008:** Exactly what delivery, sent, failed, and read indicators mean
  shall be defined; no false real-time/read claim is allowed.
- **PS-MSG-009:** Messages shall be private to authorized participants and
  approved moderation/support access under policy. End-to-end encryption shall
  not be implied unless actually implemented and independently reviewed.
- **PS-MSG-010:** AI may propose a draft when explicitly requested, clearly
  label it, preserve the member's voice, and show sources used. AI shall never
  press Send, start a thread, accept a request, or contact a person.
- **PS-MSG-011:** A Moment reference shall use an explicit scoped share/access
  grant revalidated on every retrieval; thread membership alone shall not grant
  the recipient the sender's Journal.
- **PS-MSG-012:** If the member deliberately copies an excerpt into message
  text, that excerpt becomes message content governed by message retention. The
  UI shall distinguish copied text from a live governed reference.
- **PS-MSG-013:** Revoking a referenced Moment's grant shall remove future live
  retrieval and show a neutral unavailable state; it cannot erase text the
  sender explicitly transmitted as message content.
- **PS-MSG-014:** Message text, attachments, references, participants, delivery,
  retention, deletion, moderation, and notification state shall be owner/
  participant scoped and lifecycle-defined.
- **PS-MSG-015:** Editing/deleting a message shall disclose participant-visible
  behavior and moderation/legal retention exceptions without promising
  impossible deletion from recipients' prior copies.
- **PS-MSG-016:** Account deletion, relationship removal, block, legal hold,
  abuse investigation, retention expiry, and participant deletion shall have a
  documented thread/message effect.
- **PS-MSG-017:** Export shall identify messages, participants, times, edits,
  delivery state, and live/unavailable references without exporting another
  participant's unrelated private data.
- **PS-MSG-018:** Search, unread counts, previews, badges, notifications, and
  pagination shall use the same authorization predicate and shall not leak
  blocked/deleted/private content.
- **PS-MSG-019:** Lock-screen/email/push notifications shall default to minimal
  content and respect member preview, quiet-hour, mute, and privacy settings.
- **PS-MSG-020:** Rate limits, request limits, spam controls, abuse detection,
  and account-age/risk controls shall not rely only on a model.
- **PS-MSG-021:** Members shall have accessible Block, Report, Mute, Leave/
  decline, delete/export, and safety/help paths from the relevant context.
- **PS-MSG-022:** The interface shall support keyboard, screen reader, mobile,
  touch, 200% zoom, reduced motion, long messages, slow connection, offline/
  reconnect, duplicate send, failed send, retry, and partial history.
- **PS-MSG-023:** A client message id/idempotency key shall prevent duplicate
  send during retry; ordering and clock-skew behavior shall be explicit.
- **PS-MSG-024:** Authorization shall be rechecked for send, thread retrieval,
  message retrieval, search, reference expansion, attachment token, edit,
  delete, and moderation actions.
- **PS-MSG-025:** Guessed thread/message/reference IDs shall return neutral
  unauthorized/not-found behavior and no participant/content clue.
- **PS-MSG-026:** Telemetry/logs shall not contain message text, private
  attachment content, private Moment content, or full sensitive participant
  context.
- **PS-MSG-027:** Automated content/moderation assistance shall be disclosed,
  appealable where appropriate, and unable to publish private content or take
  irreversible account action without deterministic policy/review.
- **PS-MSG-028:** The first slice shall not include public-profile cold DMs,
  recruiter blast tools, contact import, automatic introductions, or AI-sent
  outreach.
- **PS-MSG-029:** Group chat, attachments, audio/video, calls, message reactions,
  disappearing messages, and external email/SMS bridges require later scoped
  packages.
- **PS-MSG-030:** Messaging shall have an owner-visible safety/privacy
  explanation and public Terms/Privacy/Acceptable Use/support disclosures before
  availability.
- **PS-MSG-031:** Formal counsel, threat-model/security, moderation operations,
  incident response, retention/deletion, and abuse-response gates shall pass
  before a member pilot.
- **PS-MSG-032:** Two-member validation shall prove consent, send/fail/retry,
  mute, block, report, reference revoke, deletion/export, and no cross-thread
  retrieval.
- **PS-MSG-033:** AI or matching may suggest that a member consider connecting,
  but shall not create a Connection, thread, message request, or message.
- **PS-MSG-034:** Messaging availability may be feature-flagged and connection-
  limited; unavailable UI shall not imply real delivery.
- **PS-MSG-035:** Exact inbox/navigation placement remains open until the route
  map and notification architecture are approved.

## Logical records

```text
connection_or_message_consent
message_thread
thread_participant
message
message_revision_or_tombstone
message_delivery
message_reference + scoped_access_grant
mute / block / report
notification_preference + notification_delivery
retention_or_moderation_case
```

Records may share existing relationship/safety tables when contracts match,
but message content shall not be copied into Journal/Feed/notifications/logs.

## First-slice exit gate

- one-to-one text only;
- explicit consent/Connection requirement;
- server-side participant authorization for every operation;
- sent/failed/retry truth and duplicate prevention;
- mute/block/report and support operations;
- minimal notifications with preview controls;
- retention/deletion/export policy and legal readiness;
- optional live Moment reference with revoke behavior;
- no AI send and no cold DM;
- accessibility, two-member isolation, threat model, moderation, Azure release,
  and production verification evidence.
