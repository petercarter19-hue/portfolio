/* D0 local enhancement only. No storage, analytics, identity, or mutation. */
(() => {
  "use strict";
  const main = document.getElementById("profile-main");
  if (!main) return;
  // Preserve browser-native deep-link and Back/Forward behavior. Focus only
  // after an explicit same-document hash navigation through the skip link.
  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest('a[href="#profile-main"]') : null;
    if (!target) return;
    window.requestAnimationFrame(() => main.focus({ preventScroll: true }));
  });
})();
