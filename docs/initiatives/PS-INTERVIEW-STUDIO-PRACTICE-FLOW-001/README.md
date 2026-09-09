# PS-INTERVIEW-STUDIO-PRACTICE-FLOW-001

## Outcome

This MVP1 package gives an authenticated member a direct Interview Studio
practice loop: choose or accept the current setup, answer a question, receive
review, improve or retry, continue to another question, and return through
History. Practice has no required New Session or Finish Session ceremony and
no fixed question count.

The package succeeds the closed Operability work without rebuilding it. Its
setup launcher, cancel and Escape handling, focus return, History destination,
settings launcher, responsive controls, and browser-local truth remain the
foundation for this simpler flow.

## Product contract

- Setup is optional and dismissible. Applying it selects context for the next
  question while the existing draft and recording guards continue to prevent
  silent replacement.
- The rail describes the current practice and its tools. It does not report an
  unanswered question as completed or expose an empty completion ceremony.
- Each accepted review remains a normal browser-local History record. An
  active review workspace stores only its record and question identifiers plus
  an optional unsaved improvement draft. On refresh, the reviewed content is
  recovered through the sanitized History record rather than duplicated.
- Review and improvement remain visible when the member visits Interview AI,
  Video Practice, or History and returns. An unsaved improvement is explicitly
  labelled as absent from History and is restored after refresh.
- Edit and retry starts an editable new attempt while preserving the accepted
  review in History. Next question remains a deliberate action.
- Existing browser-local records are read through the existing sanitizer.
  This package performs no deletion, schema change, migration, or silent
  conversion.

## Preserved boundaries

The existing review, improvement, nudge, Interview AI, and Video Practice APIs
and providers are unchanged. Authenticated access, account-scoped storage
prefixes, public flag-off rendering, feature configuration, safe return,
robots and indexing behavior, and working failure and duplicate-submit guards
are preserved.

This package does not add cloud sync, cross-device recovery, private follow-up,
onboarding, schema or provider work. It does not select a broader visual
redesign, Focus mode, pop-out window, video/device expansion, or a new session
data model. Production release and live proof require separate authority.

## Acceptance

Acceptance requires focused route and browser checks for setup dismissal and
focus, the direct answer/review/improve/retry/next-question journey, continuity
through sibling modes and History, refresh restoration, one-record History
integrity, existing-record readability, public flag-off parity, and existing
video draft guards. The immutable candidate then requires the repository's
independent review, Protected CI, accepted merge, and a closed lifecycle claim.

The owner technical completion report and governance evidence distinguish
repository acceptance from deployment and live proof.
