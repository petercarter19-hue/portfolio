'use strict';

const assert = require('node:assert/strict');
const focus = require('../static/js/community-focus-lifecycle.js');

function harness() {
  const bySelector = {};
  const documentRef = {
    activeElement: null,
    body: null,
    documentElement: null,
    defaultView: {
      getComputedStyle(element) {
        return { display: element.display || 'block', visibility: element.visibility || 'visible' };
      }
    },
    contains(element) { return !!(element && element.connected); },
    querySelector(selector) { return bySelector[selector] || null; }
  };

  function element(name) {
    return {
      name,
      ownerDocument: documentRef,
      connected: true,
      disabled: false,
      hidden: false,
      attributes: {},
      focusCount: 0,
      focus() { this.focusCount += 1; documentRef.activeElement = this; },
      getAttribute(key) { return this.attributes[key] || null; },
      getClientRects() { return this.rectless ? [] : [{}]; }
    };
  }

  return { bySelector, documentRef, element };
}

function testBreakReturnMovesBeforeHide() {
  const h = harness();
  const breakControl = h.element('Back to the Feed');
  const feedTab = h.element('Feed tab');
  const feedPanel = h.element('Feed panel');
  const breakPanel = h.element('Break panel');
  feedPanel.attributes['data-tab-panel'] = 'feed';
  breakPanel.attributes['data-tab-panel'] = 'break';
  feedPanel.contains = () => false;
  breakPanel.contains = candidate => candidate === breakControl;
  feedTab.focus = function () {
    assert.equal(breakPanel.hidden, false, 'focus must move before the Break panel is hidden');
    this.focusCount += 1;
    h.documentRef.activeElement = this;
  };

  const moved = focus.moveBeforePanelHide(
    [feedPanel, breakPanel], 'feed', breakControl, feedTab);
  breakPanel.hidden = true;

  assert.equal(moved, true);
  assert.equal(h.documentRef.activeElement, feedTab);
  assert.equal(feedTab.focusCount, 1);
}

function testComposerCancelRestoresInvoker() {
  const h = harness();
  const composer = h.element('Composer');
  const lifecycle = focus.createReturnFocus(h.documentRef);
  lifecycle.remember(composer, '[data-composer-return]');

  assert.equal(lifecycle.restore(), composer);
  assert.equal(h.documentRef.activeElement, composer);
  assert.equal(composer.focusCount, 1);
}

function testReviewBackThenCancelKeepsOriginalInvoker() {
  const h = harness();
  const composer = h.element('Composer');
  const reviewButton = h.element('Continue to preview');
  const lifecycle = focus.createReturnFocus(h.documentRef);

  lifecycle.remember(composer, '[data-composer-return]');
  h.documentRef.activeElement = reviewButton;
  // Production review-stage rerenders deliberately do not call remember again.
  assert.equal(lifecycle.restore(), composer);
  assert.equal(h.documentRef.activeElement, composer);
}

function testPreviewCompletionRestoresConnectedReplacement() {
  const h = harness();
  const oldComposer = h.element('Old composer');
  const newComposer = h.element('New composer');
  const lifecycle = focus.createReturnFocus(h.documentRef);
  lifecycle.remember(oldComposer, '[data-composer-return]');

  oldComposer.connected = false;
  h.bySelector['[data-composer-return]'] = newComposer;

  assert.equal(lifecycle.restore(), newComposer);
  assert.equal(h.documentRef.activeElement, newComposer);
  assert.equal(newComposer.focusCount, 1);
}

function testDirectStateBodyTargetUsesIntentionalFeedFallback() {
  const h = harness();
  const body = h.element('BODY');
  const feedTab = h.element('Feed tab');
  h.documentRef.body = body;
  h.documentRef.activeElement = body;
  const lifecycle = focus.createReturnFocus(h.documentRef, () => feedTab);
  lifecycle.remember(body, null);

  assert.equal(lifecycle.restore(), feedTab);
  assert.equal(h.documentRef.activeElement, feedTab);
  assert.equal(body.focusCount, 0, 'BODY must not be accepted as an intentional target');
  assert.equal(feedTab.focusCount, 1);
}

function testNoOpDirectTargetFallsThroughToLogicalReplacement() {
  const h = harness();
  const staleInvoker = h.element('Non-focusable invoker');
  const newComposer = h.element('New composer');
  staleInvoker.focus = function () {
    this.focusCount += 1;
    // Simulate a connected element whose focus method does not take focus.
  };
  h.bySelector['[data-composer-return]'] = newComposer;
  const lifecycle = focus.createReturnFocus(h.documentRef, () => null);
  lifecycle.remember(staleInvoker, '[data-composer-return]');

  assert.equal(lifecycle.restore(), newComposer);
  assert.equal(staleInvoker.focusCount, 1);
  assert.equal(h.documentRef.activeElement, newComposer);
}

function testFailedFocusAttemptsReportFailure() {
  const h = harness();
  const noOpTarget = h.element('No-op target');
  const throwingTarget = h.element('Throwing target');
  noOpTarget.focus = function () { this.focusCount += 1; };
  throwingTarget.focus = function () {
    this.focusCount += 1;
    throw new Error('not focusable');
  };

  assert.equal(focus.focusElement(noOpTarget), false);
  assert.equal(focus.focusElement(throwingTarget), false);
  assert.equal(throwingTarget.focusCount, 2,
    'options and compatibility attempts both fail safely');
}

function testSuccessfulFocusPreventsScrollJump() {
  const h = harness();
  const target = h.element('Feed tab');
  let receivedOptions = null;
  target.focus = function (options) {
    this.focusCount += 1;
    receivedOptions = options;
    h.documentRef.activeElement = this;
  };

  assert.equal(focus.focusElement(target), true);
  assert.deepEqual(receivedOptions, { preventScroll: true });
}

function testDirectStateFallbackTriesComposerWhenFeedCannotTakeFocus() {
  const h = harness();
  const body = h.element('BODY');
  const feedTab = h.element('Feed tab');
  const composer = h.element('Composer');
  h.documentRef.body = body;
  h.documentRef.activeElement = body;
  feedTab.focus = function () { this.focusCount += 1; };
  const lifecycle = focus.createReturnFocus(h.documentRef, () => [feedTab, composer]);
  lifecycle.remember(body, null);

  assert.equal(lifecycle.restore(), composer);
  assert.equal(feedTab.focusCount, 1);
  assert.equal(h.documentRef.activeElement, composer);
}

function testBottomBreakReturnRevealsItsFocusedFeedDestination() {
  const h = harness();
  const feedTab = h.element('Feed tab');
  const windowRef = { innerWidth: 1280, innerHeight: 720 };
  let rect = { top: -1667, bottom: -1621, left: 100, right: 240 };
  let receivedOptions = null;
  feedTab.getBoundingClientRect = () => rect;
  feedTab.scrollIntoView = function (options) {
    receivedOptions = options;
    rect = { top: 337, bottom: 383, left: 100, right: 240 };
  };
  feedTab.focus();

  assert.equal(focus.intersectsViewport(windowRef, feedTab), false);
  assert.equal(focus.revealFocusedElement(windowRef, feedTab), true);
  assert.equal(h.documentRef.activeElement, feedTab);
  assert.equal(focus.intersectsViewport(windowRef, feedTab), true);
  assert.deepEqual(receivedOptions,
    { block: 'center', inline: 'nearest', behavior: 'auto' });
}

testBreakReturnMovesBeforeHide();
testComposerCancelRestoresInvoker();
testReviewBackThenCancelKeepsOriginalInvoker();
testPreviewCompletionRestoresConnectedReplacement();
testDirectStateBodyTargetUsesIntentionalFeedFallback();
testNoOpDirectTargetFallsThroughToLogicalReplacement();
testFailedFocusAttemptsReportFailure();
testSuccessfulFocusPreventsScrollJump();
testDirectStateFallbackTriesComposerWhenFeedCannotTakeFocus();
testBottomBreakReturnRevealsItsFocusedFeedDestination();
console.log('community focus lifecycle: 10 behavioral checks passed');
