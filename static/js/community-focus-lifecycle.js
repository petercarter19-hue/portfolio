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

  function focusElement(element, documentRef) {
    if (!element || typeof element.focus !== 'function') { return false; }

    var ownerDocument = documentRef || element.ownerDocument || null;
    // BODY is the browser's implicit fallback when an overlay removes its
    // focused control. It is never an intentional place to resume this flow.
    if (ownerDocument &&
        (element === ownerDocument.body || element === ownerDocument.documentElement)) {
      return false;
    }

    try {
      element.focus({ preventScroll: true });
    } catch (error) {
      try {
        element.focus();
      } catch (fallbackError) {
        return false;
      }
    }

    // Native focus is synchronous. When activeElement is available, a no-op
    // focus call is not success; restoration must keep trying other controls.
    if (ownerDocument && 'activeElement' in ownerDocument) {
      return ownerDocument.activeElement === element;
    }
    return false;
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

  function intersectsViewport(windowRef, element) {
    if (!windowRef || !element || typeof element.getBoundingClientRect !== 'function') {
      return false;
    }
    var rect = element.getBoundingClientRect();
    var documentRef = element.ownerDocument;
    var documentElement = documentRef && documentRef.documentElement;
    var viewportWidth = windowRef.innerWidth || (documentElement && documentElement.clientWidth) || 0;
    var viewportHeight = windowRef.innerHeight || (documentElement && documentElement.clientHeight) || 0;
    return rect.bottom > 0 && rect.right > 0 &&
      rect.top < viewportHeight && rect.left < viewportWidth;
  }

  function revealFocusedElement(windowRef, element) {
    var documentRef = element && element.ownerDocument;
    if (!documentRef || documentRef.activeElement !== element) { return false; }
    if (intersectsViewport(windowRef, element)) { return true; }
    if (typeof element.scrollIntoView !== 'function') { return false; }

    try {
      element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'auto' });
    } catch (error) {
      element.scrollIntoView();
    }
    return intersectsViewport(windowRef, element);
  }

  function createReturnFocus(documentRef, fallbackResolver) {
    var directTarget = null;
    var logicalSelector = null;

    function remember(element, selector) {
      directTarget = element || null;
      logicalSelector = selector || null;
    }

    function restore() {
      var target = null;

      function restoreCandidates(candidates) {
        var candidateList = Array.isArray(candidates) ? candidates : [candidates];
        for (var index = 0; index < candidateList.length; index += 1) {
          var candidate = candidateList[index];
          if (isVisibleConnected(documentRef, candidate) &&
              focusElement(candidate, documentRef)) {
            return candidate;
          }
        }
        return null;
      }

      target = restoreCandidates(directTarget);
      if (!target && logicalSelector && documentRef.querySelector) {
        target = restoreCandidates(documentRef.querySelector(logicalSelector));
      }
      if (!target && typeof fallbackResolver === 'function') {
        // Direct-entry overlays have no real invoker. The page-level resolver
        // intentionally chooses its visible Feed tab, then its composer.
        target = restoreCandidates(fallbackResolver());
      }
      directTarget = null;
      logicalSelector = null;
      return target;
    }

    return { remember: remember, restore: restore };
  }

  return {
    createReturnFocus: createReturnFocus,
    focusElement: focusElement,
    intersectsViewport: intersectsViewport,
    isVisibleConnected: isVisibleConnected,
    moveBeforePanelHide: moveBeforePanelHide,
    revealFocusedElement: revealFocusedElement
  };
});
