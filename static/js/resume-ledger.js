/* Resume 2 — Experience Ledger interaction controller.
   Progressive enhancement only: the server renders the correct state for any
   URL, so without JS every role and panel is still reachable by link/refresh.
   This script swaps state in place (no reload), keeps the URL deep-linkable,
   supports Escape + browser Back, and returns focus to the invoking row. */
(function () {
  "use strict";

  var root = document.getElementById("resume-ledger");
  if (!root) return;

  var baseUrl = root.dataset.baseUrl || "";
  var lensPanels = root.querySelectorAll("[data-lens-panel]");
  var lensTabs = root.querySelectorAll("[data-lens]");
  var dossiers = root.querySelectorAll("[data-dossier]");

  // Remember which timeline/roles row opened a dossier so we can restore focus.
  var lastOpener = null;

  function setHidden(el, hidden) {
    if (!el) return;
    if (hidden) el.setAttribute("hidden", "");
    else el.removeAttribute("hidden");
  }

  function panelById(id) {
    return root.querySelector('[data-role-panel="' + id + '"]');
  }

  function render(state, opts) {
    opts = opts || {};
    var role = state.role || null;
    var tab = state.tab || "overview";
    var lens = state.lens || "timeline";

    // Lenses vs dossiers are mutually exclusive inside the active sheet.
    lensPanels.forEach(function (panel) {
      setHidden(panel, role || panel.dataset.lensPanel !== lens);
    });
    dossiers.forEach(function (dossier) {
      setHidden(dossier, dossier.dataset.dossier !== role);
    });

    // Lens tab active state (suppressed while a role is open).
    lensTabs.forEach(function (t) {
      var on = !role && t.dataset.lens === lens;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });

    if (role) {
      var dossier = root.querySelector('[data-dossier="' + role + '"]');
      if (dossier) {
        var tabs = dossier.querySelectorAll("[data-role-tab]");
        tabs.forEach(function (t) {
          var on = t.dataset.roleTab === tab;
          t.classList.toggle("is-active", on);
          t.setAttribute("aria-selected", on ? "true" : "false");
        });
        dossier.querySelectorAll("[data-role-panel]").forEach(function (panel) {
          setHidden(panel, panel.dataset.rolePanel !== tab);
        });
        if (opts.focus === "dossier") {
          var back = dossier.querySelector("[data-dossier-back]");
          if (back) back.focus();
        }
      }
    } else if (opts.focus === "opener" && lastOpener) {
      lastOpener.focus();
    }

    root.dataset.activeRole = role || "";
    root.dataset.activeTab = tab;
    root.dataset.activeLens = lens;
  }

  function urlFor(state) {
    if (state.role) return baseUrl + "?role=" + state.role + "&tab=" + (state.tab || "overview");
    return baseUrl + "?view=" + (state.lens || "timeline");
  }

  function go(state, opts) {
    render(state, opts);
    try {
      history.pushState(state, "", urlFor(state));
    } catch (e) {
      /* pushState can throw in odd sandboxes; state already rendered */
    }
  }

  // ---- Open a role (timeline row or roles card) ----
  root.querySelectorAll("[data-role-open]").forEach(function (opener) {
    opener.addEventListener("click", function (ev) {
      ev.preventDefault();
      lastOpener = opener;
      go({ role: opener.dataset.roleOpen, tab: "overview" }, { focus: "dossier" });
      window.scrollTo({ top: root.offsetTop - 20, behavior: "auto" });
    });
  });

  // ---- Switch role detail tabs ----
  root.querySelectorAll("[data-role-tab]").forEach(function (tab) {
    tab.addEventListener("click", function (ev) {
      ev.preventDefault();
      var dossier = tab.closest("[data-dossier]");
      go({ role: dossier.dataset.dossier, tab: tab.dataset.roleTab });
    });
  });

  // ---- Back to timeline ----
  root.querySelectorAll("[data-dossier-back]").forEach(function (back) {
    back.addEventListener("click", function (ev) {
      ev.preventDefault();
      go({ lens: "timeline" }, { focus: "opener" });
    });
  });

  // ---- Career lens tabs ----
  lensTabs.forEach(function (tab) {
    tab.addEventListener("click", function (ev) {
      ev.preventDefault();
      go({ lens: tab.dataset.lens });
    });
  });

  // ---- Escape closes an open dossier ----
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && root.dataset.activeRole) {
      go({ lens: "timeline" }, { focus: "opener" });
    }
  });

  // ---- Browser Back/Forward ----
  window.addEventListener("popstate", function (ev) {
    var params = new URLSearchParams(window.location.search);
    var state = ev.state || {
      role: params.get("role"),
      tab: params.get("tab") || "overview",
      lens: params.get("view") || "timeline",
    };
    render(state);
  });
})();
