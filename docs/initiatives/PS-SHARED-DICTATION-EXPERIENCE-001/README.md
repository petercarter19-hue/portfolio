# PS-SHARED-DICTATION-EXPERIENCE-001 - Shared in-field dictation

**Status:** Planned - not active.
**Risk path:** Protected where audio leaves the browser or protected text is
processed.
**Runtime status:** No transcription provider, endpoint, storage, prompt,
retention, or UI change is authorized.

## Owner outcome

Dictation behaves like writing with your voice: press the mic, speak, review and
edit the text in the same field, then continue. It is a reusable property of
authored-prose fields, not a separate panel or public audio attachment.

## First gate: reliability diagnosis

Community currently reaches an actual `transcription unavailable` state. A UI
redesign cannot conceal that reliability problem. Before visual implementation,
trace permission, capture, upload, endpoint, provider, timeout, error mapping,
and fallback behavior and record the real cause. Do not claim the shared module
fixed transcription until the affected path is exercised end to end.

## Shared interaction contract

- The mic lives inside or directly attached to the text field.
- While recording, a circular **X** cancels only the current dictated segment;
  text that existed before dictation remains intact.
- Transcribed text appears in the same editable field at the intended caret.
- Manual stop is available. Ten seconds of detected silence is the proposed
  PeerSlate default for automatic stop.
- Stopping preserves usable text. Restarting is immediate.
- Do not open a recording tray, second transcript panel, Retry/Discard
  workspace, or separate review screen.
- Use a short inline/status or toast error such as `Couldn't hear that. Try
  again.` without expanding the page.
- Voice is an input method. The recording is not a public attachment and there
  is no `Public audio` option.

Apply this shared contract to authored prose such as Community posts/comments,
Interview answers/custom questions, Opportunity descriptions, Sparks, and
private captures. Do not force it onto every search, title, selector, or small
structured input without a field-specific reason.

## Research and accessibility boundary

OpenAI's published dictation contract supports speech becoming editable text
before sending. It does not establish PeerSlate's 10-second cutoff, live partial
words, caret behavior, or X placement; those are PeerSlate decisions. A fixed
silence cutoff can disadvantage members with longer speech or cognitive pauses.
If retained, it must never discard text, must announce the stopped state without
announcing every partial word, and must be tested with speech-disabled users.

## Privacy and truth decisions

Before activation, record where audio is processed, whether it is transmitted,
what is retained and for how long, provider use/training controls, maximum
duration, file limits, and browser support. Different engines may sit behind a
consistent interaction only if disclosure and error behavior remain truthful.

## Acceptance gate

A shared component contract, reliability root-cause record, privacy decision,
keyboard/screen-reader states, long-pause cases, cancellation preservation, and
end-to-end browser evidence are required before feature-by-feature adoption.
