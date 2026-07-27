import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const authorityRoot = path.resolve(here, "..");
const prototypePath = path.join(authorityRoot, "prototype", "index.html");
const evidencePath = path.join(authorityRoot, "evidence");
const localRequire = createRequire(import.meta.url);
const nodeModules = process.env.PEERSLATE_NODE_MODULES;
const playwright = nodeModules
  ? localRequire(path.join(nodeModules, "playwright"))
  : localRequire("playwright");

const browserCandidates = [
  process.env.PEERSLATE_BROWSER_EXECUTABLE,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);

const executablePath = browserCandidates.find((candidate) =>
  fs.existsSync(candidate),
);

if (!executablePath) {
  throw new Error(
    "No Chrome or Edge executable was found. Set PEERSLATE_BROWSER_EXECUTABLE.",
  );
}

const desktopViewports = [
  [1440, 900],
  [1920, 1080],
  [2560, 1440],
  [3840, 2160],
];

const cases = [];

for (const style of ["story", "work"]) {
  for (const [width, height] of desktopViewports) {
    cases.push({
      name: `${style}-standard-${width}x${height}`,
      style,
      state: "standard",
      proof: "4",
      width,
      height,
    });
  }

  cases.push(
    {
      name: `${style}-standard-full-page-1920x1080`,
      style,
      state: "standard",
      proof: "4",
      width: 1920,
      height: 1080,
      fullPage: true,
    },
    {
      name: `${style}-mobile-standard-390x844`,
      style,
      state: "standard",
      proof: "4",
      width: 390,
      height: 844,
      mobile: true,
    },
    {
      name: `${style}-mobile-sparse-390x844`,
      style,
      state: "sparse",
      proof: "0",
      width: 390,
      height: 844,
      mobile: true,
    },
    {
      name: `${style}-sparse-1920x1080`,
      style,
      state: "sparse",
      proof: "1",
      width: 1920,
      height: 1080,
    },
    {
      name: `${style}-rich-1920x1080`,
      style,
      state: "rich",
      proof: "4",
      width: 1920,
      height: 1080,
    },
    {
      name: `${style}-text-only-1440x900`,
      style,
      state: "text",
      proof: "0",
      width: 1440,
      height: 900,
    },
    {
      name: `${style}-one-proof-1440x900`,
      style,
      state: "standard",
      proof: "1",
      width: 1440,
      height: 900,
    },
    {
      name: `${style}-no-proof-1440x900`,
      style,
      state: "standard",
      proof: "0",
      width: 1440,
      height: 900,
    },
    {
      name: `${style}-large-text-1440x900`,
      style,
      state: "standard",
      proof: "4",
      largeText: "1",
      width: 1440,
      height: 900,
    },
    {
      name: `${style}-focus-1440x900`,
      style,
      state: "standard",
      proof: "4",
      focus: "1",
      width: 1440,
      height: 900,
    },
    {
      name: `${style}-reduced-motion-1440x900`,
      style,
      state: "standard",
      proof: "4",
      reducedMotion: true,
      width: 1440,
      height: 900,
    },
  );
}

for (const editor of [
  "setup",
  "compose",
  "metric-ai",
  "save-failed",
  "publish",
  "unpublish",
  "blocked",
  "restore",
]) {
  cases.push({
    name: `story-editor-${editor}-1920x1080`,
    style: "story",
    state: "standard",
    proof: "4",
    view: "editor",
    editor,
    width: 1920,
    height: 1080,
  });
}

for (const editor of ["compose", "metric-ai"]) {
  cases.push({
    name: `work-editor-${editor}-1920x1080`,
    style: "work",
    state: "standard",
    proof: "4",
    view: "editor",
    editor,
    width: 1920,
    height: 1080,
  });
}

fs.mkdirSync(evidencePath, { recursive: true });

const browser = await playwright.chromium.launch({
  executablePath,
  headless: true,
  args: ["--allow-file-access-from-files", "--force-device-scale-factor=1"],
});

const measurements = {
  generatedAt: new Date().toISOString(),
  browserExecutable: executablePath,
  prototype: path.relative(authorityRoot, prototypePath).replaceAll("\\", "/"),
  requirements: {
    shellInlineSize: "min(92vw, 90rem)",
    overviewEdgeToleranceCssPx: 2,
    minimumPrimaryBodyCssPx: 16,
    requiredZoom: "1",
    requiredTransform: "none",
    rightSideRail: "absent",
  },
  cases: [],
};

const failures = [];

for (const item of cases) {
  const context = await browser.newContext({
    viewport: { width: item.width, height: item.height },
    deviceScaleFactor: 1,
    isMobile: Boolean(item.mobile),
    hasTouch: Boolean(item.mobile),
    reducedMotion: item.reducedMotion ? "reduce" : "no-preference",
  });
  const page = await context.newPage();
  const params = new URLSearchParams({
    style: item.style,
    state: item.state,
    view: item.view || "public",
    editor: item.editor || "setup",
    proof: item.proof,
    largeText: item.largeText || "0",
    focus: item.focus || "0",
    capture: "1",
  });
  const url = `${pathToFileURL(prototypePath).href}?${params.toString()}`;

  await page.goto(url, { waitUntil: "load" });
  await page.waitForFunction(
    ({ style, state }) =>
      document.body.classList.contains(`style-${style}`) &&
      document.body.classList.contains(`state-${state}`),
    { style: item.style, state: item.state },
  );
  await page.evaluate(async () => {
    if (document.fonts?.ready) {
      await document.fonts.ready;
    }
  });

  const measured = await page.evaluate(() => {
    const rectForElement = (element) => {
      if (!element) return null;
      const box = element.getBoundingClientRect();
      return {
        x: Number(box.x.toFixed(2)),
        y: Number(box.y.toFixed(2)),
        width: Number(box.width.toFixed(2)),
        height: Number(box.height.toFixed(2)),
        left: Number(box.left.toFixed(2)),
        right: Number(box.right.toFixed(2)),
        top: Number(box.top.toFixed(2)),
        bottom: Number(box.bottom.toFixed(2)),
      };
    };
    const rect = (selector) => rectForElement(document.querySelector(selector));
    const overview = [...document.querySelectorAll(".style-panel")].find(
      (element) => !element.hidden,
    );
    const bodyCopy = overview?.querySelector(".hero-intro");
    const overviewStyle = getComputedStyle(overview);
    const copyStyle = getComputedStyle(bodyCopy);
    const shell = rect(".mockup-stage");
    const canvas = rect(".mockup-canvas");
    const overviewRect = rectForElement(overview);
    const hero = rectForElement(
      overview?.querySelector(".story-hero, .work-hero"),
    );
    const header = rectForElement(
      overview?.querySelector(".story-site-header, .work-site-header"),
    );
    const prohibitedRail = document.querySelector(
      ".section-ribbon, [data-context-rail], .context-rail",
    );
    const prohibitedRailStyle = prohibitedRail
      ? getComputedStyle(prohibitedRail)
      : null;
    const rightSideRailPresent = Boolean(
      prohibitedRail &&
        prohibitedRailStyle.display !== "none" &&
        prohibitedRailStyle.visibility !== "hidden",
    );

    return {
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
        dpr: window.devicePixelRatio,
      },
      shell,
      canvas,
      overview: overviewRect,
      hero,
      header,
      rail: null,
      rightSideRailPresent,
      outerGutters: shell
        ? {
            left: shell.left,
            right: Number((window.innerWidth - shell.right).toFixed(2)),
          }
        : null,
      measuredGap: null,
      overviewEdgeDelta:
        canvas && overviewRect
          ? {
              left: Number(Math.abs(canvas.left - overviewRect.left).toFixed(2)),
              right: Number(
                Math.abs(canvas.right - overviewRect.right).toFixed(2),
              ),
            }
          : null,
      bodyFontPx: Number.parseFloat(getComputedStyle(document.body).fontSize),
      primaryBodyFontPx: Number.parseFloat(copyStyle.fontSize),
      primaryBodyLineHeightPx: Number.parseFloat(copyStyle.lineHeight),
      overviewZoom: overviewStyle.zoom || "1",
      overviewTransform: overviewStyle.transform,
      documentScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      horizontalOverflow:
        document.documentElement.scrollWidth > window.innerWidth + 1 ||
        document.body.scrollWidth > window.innerWidth + 1,
      reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
      activeElement:
        document.activeElement?.id ||
        document.activeElement?.className ||
        document.activeElement?.tagName ||
        null,
    };
  });

  const itemFailures = [];
  if (!measured.overviewEdgeDelta) {
    itemFailures.push("missing overview/canvas geometry");
  } else {
    if (measured.overviewEdgeDelta.left > 2) {
      itemFailures.push(
        `left edge delta ${measured.overviewEdgeDelta.left}px exceeds 2px`,
      );
    }
    if (measured.overviewEdgeDelta.right > 2) {
      itemFailures.push(
        `right edge delta ${measured.overviewEdgeDelta.right}px exceeds 2px`,
      );
    }
  }
  if (measured.primaryBodyFontPx < 16) {
    itemFailures.push(
      `primary body size ${measured.primaryBodyFontPx}px is below 16px`,
    );
  }
  if (!["1", "normal"].includes(String(measured.overviewZoom))) {
    itemFailures.push(`overview zoom is ${measured.overviewZoom}, expected 1`);
  }
  if (measured.overviewTransform !== "none") {
    itemFailures.push(
      `overview transform is ${measured.overviewTransform}, expected none`,
    );
  }
  if (measured.horizontalOverflow) {
    itemFailures.push(
      `horizontal overflow: document ${measured.documentScrollWidth}px / body ${measured.bodyScrollWidth}px / viewport ${measured.viewport.width}px`,
    );
  }
  if (measured.rightSideRailPresent) {
    itemFailures.push("a prohibited right-side rail is present");
  }

  const screenshotName = `${item.name}.jpg`;
  await page.screenshot({
    path: path.join(evidencePath, screenshotName),
    type: "jpeg",
    quality: 90,
    fullPage: Boolean(item.fullPage),
  });

  measurements.cases.push({
    name: item.name,
    query: params.toString(),
    screenshot: screenshotName,
    fullPage: Boolean(item.fullPage),
    ...measured,
    result: itemFailures.length ? "Fail" : "Pass",
    failures: itemFailures,
  });
  for (const failure of itemFailures) {
    failures.push(`${item.name}: ${failure}`);
  }
  await context.close();
}

await browser.close();

measurements.summary = {
  total: measurements.cases.length,
  passed: measurements.cases.filter((item) => item.result === "Pass").length,
  failed: measurements.cases.filter((item) => item.result === "Fail").length,
};

fs.writeFileSync(
  path.join(evidencePath, "measurements.json"),
  `${JSON.stringify(measurements, null, 2)}\n`,
  "utf8",
);

if (failures.length) {
  console.error(failures.join("\n"));
  process.exitCode = 1;
} else {
  console.log(
    `Rendered ${measurements.summary.total} visual-authority cases: all passed.`,
  );
}
