/* Shared focus lifecycle for Community tab changes and in-page preview dialogs.
   The small CommonJS export keeps the same production code directly testable
   without a browser-only test dependency. */
(function (root, factory) {
  'use strict';

  var api = factory();
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.PeerSlateCommunityFocus = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function focusElement(element) {
    if (!element || typeof element.focus !== 'function') { return false; }
    try {
      element.focus({ preventScroll: true });
    } catch (error) {
      element.focus();
    }
    return true;
  }

  function isVisibleConnected(documentRef, element) {
    if (!documentRef || !element || !documentRef.contains(element) ||
        element.hidden || element.disabled ||
        (element.getAttribute && element.getAttribute('aria-hidden') === 'true')) {
      return false;
    }
    var view = documentRef.defaultView;
    var style = view && view.getComputedStyle ? view.getComputedStyle(element) : null;
    if (style && (style.display === 'none' || style.visibility === 'hidden')) { return false; }
    return !element.getClientRects || element.getClientRects().length > 0;
  }

  function moveBeforePanelHide(panels, nextKey, activeElement, nextTab) {
    var focusWillBeHidden = panels.some(function (panel) {
      return panel.getAttribute('data-tab-panel') !== nextKey &&
        typeof panel.contains === 'function' && panel.contains(activeElement);
    });
    return focusWillBeHidden ? focusElement(nextTab) : false;
  }

  function createReturnFocus(documentRef, fallbackResolver) {
    var directTarget = null;
    var logicalSelector = null;

    function remember(element, selector) {
      directTarget = element || null;
      logicalSelector = selector || null;
    }

    function restore() {
      var target = isVisibleConnected(documentRef, directTarget) ? directTarget : null;
      if (!target && logicalSelector && documentRef.querySelector) {
        var logicalTarget = documentRef.querySelector(logicalSelector);
        if (isVisibleConnected(documentRef, logicalTarget)) { target = logicalTarget; }
      }
      if (!target && typeof fallbackResolver === 'function') {
        var fallback = fallbackResolver();
        if (isVisibleConnected(documentRef, fallback)) { target = fallback; }
      }
      var focused = focusElement(target);
      directTarget = null;
      logicalSelector = null;
      return focused ? target : null;
    }

    return { remember: remember, restore: restore };
  }

  return {
    createReturnFocus: createReturnFocus,
    focusElement: focusElement,
    isVisibleConnected: isVisibleConnected,
    moveBeforePanelHide: moveBeforePanelHide
  };
});
