/*
 * Dependency-free behavioural harness for the device-local draft expiry.
 *
 * Approved retention decision, 2026-08-03: "Automatically expire after 30 days
 * without an edit." A draft never reaches PeerSlate, so this is the only place
 * that rule can be enforced — there is no server-side sweep that can reach it.
 *
 * Run: node tests/community_draft_expiry.test.js
 */

'use strict';

const fs = require('fs');
const path = require('path');

const source = fs.readFileSync(
  path.join(__dirname, '..', 'static', 'js', 'community-v1.js'),
  'utf8'
);

let checks = 0;
function check(label, actual, expected) {
  checks += 1;
  if (actual !== expected) {
    console.error(`FAIL: ${label}\n  expected ${expected}\n  actual   ${actual}`);
    process.exit(1);
  }
}

/* Lift the two pure helpers out of the IIFE and evaluate them in isolation.
 * This exercises the real shipped source rather than a copy that could drift. */
const limitMatch = source.match(/var DRAFT_IDLE_LIMIT_MS = ([^;]+);/);
const expiryMatch = source.match(
  /function draftHasExpired\(value\) \{[\s\S]*?\n  \}/
);
if (!limitMatch || !expiryMatch) {
  console.error('FAIL: could not locate the draft expiry helpers in community-v1.js');
  process.exit(1);
}

const harness = new Function(
  `var DRAFT_IDLE_LIMIT_MS = ${limitMatch[1]};
   ${expiryMatch[0]}
   return { DRAFT_IDLE_LIMIT_MS: DRAFT_IDLE_LIMIT_MS, draftHasExpired: draftHasExpired };`
);
const { DRAFT_IDLE_LIMIT_MS, draftHasExpired } = harness();

const DAY = 24 * 60 * 60 * 1000;

check('the window is exactly 30 days', DRAFT_IDLE_LIMIT_MS, 30 * DAY);

check(
  'a draft saved just now survives',
  draftHasExpired({ body: 'x', saved_at: Date.now() }),
  false
);

check(
  'a draft edited 29 days ago survives',
  draftHasExpired({ body: 'x', saved_at: Date.now() - 29 * DAY }),
  false
);

check(
  'a draft untouched for 31 days expires',
  draftHasExpired({ body: 'x', saved_at: Date.now() - 31 * DAY }),
  true
);

/* The boundary must not expire a draft a moment early: the decision says
 * "after 30 days", so exactly 30 days is still inside the window. */
check(
  'a draft at exactly 30 days is still inside the window',
  draftHasExpired({ body: 'x', saved_at: Date.now() - 30 * DAY }),
  false
);

/* A draft written before this envelope existed has no timestamp. Discarding
 * it on upgrade would throw away someone's unsent words for no reason. */
check(
  'an undated legacy draft is kept rather than discarded on upgrade',
  draftHasExpired({ body: 'written before the envelope existed' }),
  false
);

check('a missing value is not treated as expired', draftHasExpired(null), false);

check(
  'a corrupted timestamp is not treated as expired',
  draftHasExpired({ body: 'x', saved_at: 'not-a-number' }),
  false
);

/* A clock that jumped backwards must not silently delete live drafts. */
check(
  'a future timestamp does not expire the draft',
  draftHasExpired({ body: 'x', saved_at: Date.now() + 5 * DAY }),
  false
);

/* The reply surface, lifted and run against a stub store.
 *
 * Independent review 2026-08-04 (F6) found reply drafts stored as a bare
 * string and restored with no expiry check, while the two other surfaces were
 * correct. The contract tests passed because they asserted two surfaces. Only
 * a behavioural check of the third one closes that gap. */
const readReplyMatch = source.match(
  /function readReplyDraft\(targetKey\) \{[\s\S]*?\n  \}/
);
if (!readReplyMatch) {
  console.error('FAIL: could not locate readReplyDraft in community-v1.js');
  process.exit(1);
}

function replyHarness(stored) {
  const store = { value: stored };
  const localStorage = {
    getItem() {
      return store.value;
    },
    removeItem() {
      store.value = null;
    }
  };
  const run = new Function(
    'localStorage',
    'DRAFT_IDLE_LIMIT_MS',
    `${expiryMatch[0]}
     ${readReplyMatch[0]}
     return readReplyDraft('any-key');`
  );
  return { body: run(localStorage, DRAFT_IDLE_LIMIT_MS), remaining: store.value };
}

check(
  'a fresh reply draft is returned',
  replyHarness(JSON.stringify({ body: 'unsent reply', saved_at: Date.now() })).body,
  'unsent reply'
);

check(
  'a reply draft untouched for 31 days is not returned',
  replyHarness(JSON.stringify({ body: 'stale', saved_at: Date.now() - 31 * DAY })).body,
  ''
);

check(
  'an expired reply draft is removed from the device, not merely hidden',
  replyHarness(JSON.stringify({ body: 'stale', saved_at: Date.now() - 31 * DAY }))
    .remaining,
  null
);

check(
  'a reply draft written before the envelope existed is preserved',
  replyHarness('a plain string from the previous release').body,
  'a plain string from the previous release'
);

check('an absent reply draft yields an empty box', replyHarness(null).body, '');

/* Editing an existing post shares the composer with create-post drafts, but it
 * must not consume that separate unsent draft or its pending idempotency key.
 * Successful create cleanup also has to survive the subsequent close path:
 * closeComposer normally saves a nonempty create form before closing. */
const clearCreateDraftMatch = source.match(
  /function clearCreateDraftAfterSuccessfulMutation\(editing\) \{[\s\S]*?\n  \}/
);
const saveDraftMatch = source.match(
  /function saveDraft\(\) \{[\s\S]*?\n  \}/
);
const finalizeComposerDraftMatch = source.match(
  /function finalizeComposerDraftAfterClose\(\) \{[\s\S]*?\n  \}/
);
const closeComposerMatch = source.match(
  /function closeComposer\(options\) \{[\s\S]*?\n  \}/
);
if (!clearCreateDraftMatch || !saveDraftMatch || !finalizeComposerDraftMatch || !closeComposerMatch) {
  console.error('FAIL: could not locate the create-draft mutation lifecycle');
  process.exit(1);
}

function mutationCleanupHarness(editing, successfulMutation) {
  const values = new Map([
    ['create-draft', JSON.stringify({body: 'unrelated unsent draft'})],
    ['create-draft:pending-command', 'pending-command']
  ]);
  const localStorage = {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, value);
    },
    removeItem(key) {
      values.delete(key);
    }
  };
  const state = {
    editPost: editing ? {key: 'existing-post'} : null,
    composerReturnFocus: null,
    suppressNextComposerCloseDraftSave: false
  };
  const fields = {
    body: {value: successfulMutation ? 'published body' : 'unsent body'},
    intent: {value: 'post'},
    response_posture: {value: 'open_feedback'}
  };
  const run = new Function(
    'state',
    'draftKey',
    'postCommandStorageKey',
    'localStorage',
    'fields',
    'successfulMutation',
    'owner',
    'composerForm',
    'formField',
    'draftStatus',
    'composerVoiceController',
    'composer',
    'quickCompose',
    'restoreComposerHome',
    `${saveDraftMatch[0]}
     ${clearCreateDraftMatch[0]}
     ${finalizeComposerDraftMatch[0]}
     ${closeComposerMatch[0]}
     if (successfulMutation) {
       clearCreateDraftAfterSuccessfulMutation(Boolean(state.editPost));
       closeComposer({saveDraft: false});
     } else {
       closeComposer();
     }
     finalizeComposerDraftAfterClose();
     return {
       draft: localStorage.getItem(draftKey),
       command: localStorage.getItem(postCommandStorageKey)
     };`
  );
  return run(
    state,
    'create-draft',
    'create-draft:pending-command',
    localStorage,
    fields,
    successfulMutation,
    true,
    {},
    function (_form, name) { return fields[name]; },
    function () {},
    null,
    {open: true, close() { this.open = false; }},
    null,
    function () {}
  );
}

check(
  'a successful edit preserves the unrelated create draft and command key',
  JSON.stringify(mutationCleanupHarness(true, true)),
  JSON.stringify({
    draft: JSON.stringify({body: 'unrelated unsent draft'}),
    command: 'pending-command'
  })
);

check(
  'a successful new post leaves its draft and command key absent after close',
  JSON.stringify(mutationCleanupHarness(false, true)),
  JSON.stringify({draft: null, command: null})
);

check(
  'an ordinary create-composer close still saves unsent text privately',
  JSON.parse(mutationCleanupHarness(false, false).draft).body,
  'unsent body'
);

console.log(`${checks} behavioral checks passed`);
