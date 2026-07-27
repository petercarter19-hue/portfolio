const params = new URLSearchParams(window.location.search);

const allowed = {
  style: new Set(["story", "work"]),
  state: new Set(["sparse", "standard", "rich", "text"]),
  view: new Set(["public", "editor"]),
  editor: new Set([
    "setup",
    "compose",
    "metric-ai",
    "save-failed",
    "publish",
    "unpublish",
    "blocked",
    "restore",
  ]),
  proof: new Set(["0", "1", "4"]),
};

const pick = (key, fallback) => {
  const value = params.get(key);
  return value && allowed[key].has(value) ? value : fallback;
};

const state = {
  style: pick("style", "story"),
  density: pick("state", "standard"),
  view: pick("view", "public"),
  editor: pick("editor", "setup"),
  proof: pick("proof", "4"),
  capture: params.get("capture") === "1",
  largeText: params.get("largeText") === "1",
  focus: params.get("focus") === "1",
};

document.body.classList.add(
  `style-${state.style}`,
  `state-${state.density}`,
  `view-${state.view}`,
  `proof-count-${state.proof}`,
);

if (state.capture) document.body.classList.add("capture");
if (state.largeText) document.body.classList.add("large-text");

for (const panel of document.querySelectorAll("[data-style-panel]")) {
  panel.hidden = panel.dataset.stylePanel !== state.style;
}

for (const group of document.querySelectorAll("[data-proof-group]")) {
  const items = [...group.querySelectorAll("[data-proof-item]")];
  const visibleCount = Number(state.proof);
  items.forEach((item, index) => {
    item.hidden = index >= visibleCount;
  });
}

const controls = {
  style: document.querySelector("#style-control"),
  density: document.querySelector("#state-control"),
  proof: document.querySelector("#proof-control"),
};

if (controls.style) controls.style.value = state.style;
if (controls.density) controls.density.value = state.density;
if (controls.proof) controls.proof.value = state.proof;

const updateLocation = () => {
  const next = new URLSearchParams(window.location.search);
  next.set("style", controls.style.value);
  next.set("state", controls.density.value);
  next.set("proof", controls.proof.value);
  window.location.search = next.toString();
};

for (const control of Object.values(controls)) {
  control?.addEventListener("change", updateLocation);
}

const editorPanel = document.querySelector("[data-editor-panel]");
if (state.view === "editor" && editorPanel) {
  editorPanel.hidden = false;

  const editorStates = {
    setup: {
      title: "Choose how to begin",
      copy: "Start from your résumé, build manually, or ask AI for a proposal. Every path remains editable.",
      status: "No public Overview",
    },
    compose: {
      title: "Build your Overview",
      copy: "Add, reorder, hide, or edit bounded blocks. Empty sections disappear from the visitor preview.",
      status: "Draft saved",
    },
    "metric-ai": {
      title: "Refine a proof label",
      copy: "AI can propose clearer label wording. The member-supplied value stays locked and cannot be changed by AI.",
      status: "Value locked · label awaiting decision",
    },
    "save-failed": {
      title: "Draft not saved",
      copy: "Your last change remains visible locally. Retry saving before closing or publishing.",
      status: "Save failed · retry available",
    },
    publish: {
      title: "Publish this Overview?",
      copy: "Review the exact visitor preview. Publishing replaces the current Summary opening but does not change résumé records.",
      status: "Ready for member confirmation",
    },
    unpublish: {
      title: "Unpublish Overview?",
      copy: "The current résumé Summary returns automatically. The private Overview draft is retained.",
      status: "Public Overview currently visible",
    },
    blocked: {
      title: "Resolve before publishing",
      copy: "One selected image or destination is no longer public. Remove or replace it; private material fails closed.",
      status: "Publication blocked",
    },
    restore: {
      title: "Restore prior version",
      copy: "Compare the saved version with the current public Overview before restoring. Nothing changes without confirmation.",
      status: "Prior publication available",
    },
  };

  const copy = editorStates[state.editor] || editorStates.setup;
  editorPanel.querySelector("[data-editor-title]").textContent = copy.title;
  editorPanel.querySelector("[data-editor-copy]").textContent = copy.copy;
  editorPanel.querySelector("[data-editor-status]").textContent = copy.status;
}

if (state.focus) {
  requestAnimationFrame(() => {
    document
      .querySelector("[data-style-panel]:not([hidden]) [data-view-resume]")
      ?.focus();
  });
}
