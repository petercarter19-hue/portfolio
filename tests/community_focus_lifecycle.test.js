'use strict';

const assert = require('node:assert/strict');
const focus = require('../static/js/community-focus-lifecycle.js');

function harness() {
  const bySelector = {};
  const documentRef = {
    activeElement: null,
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

testBreakReturnMovesBeforeHide();
testComposerCancelRestoresInvoker();
testReviewBackThenCancelKeepsOriginalInvoker();
testPreviewCompletionRestoresConnectedReplacement();
console.log('community focus lifecycle: 4 behavioral checks passed');
