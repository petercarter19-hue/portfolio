import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(here, "../../../../..");
const localRequire = createRequire(import.meta.url);
const nodeModules = process.env.PEERSLATE_NODE_MODULES;
const playwright = nodeModules
  ? localRequire(path.join(nodeModules, "playwright"))
  : localRequire("playwright");

const baseUrl =
  process.env.PEERSLATE_OVERVIEW_BASE_URL ?? "http://127.0.0.1:5022";
const evidenceRoot = path.resolve(
  repositoryRoot,
  process.env.PEERSLATE_EVIDENCE_PATH ??
    "output/playwright/work-impact-style-switch-final",
);

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

const cases = [
  ["work-impact", 2560, 1440],
  ["story-career", 2560, 1440],
  ["work-impact", 1920, 1080],
  ["story-career", 1920, 1080],
  ["work-impact", 1440, 900],
  ["story-career", 1440, 900],
  ["work-impact", 390, 844],
  ["story-career", 390, 844],
  ["work-impact", 320, 844],
];

fs.mkdirSync(evidenceRoot, { recursive: true });

const browser = await playwright.chromium.launch({
  executablePath,
  headless: true,
  args: ["--force-device-scale-factor=1"],
});

const results = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  browserExecutable: executablePath,
  widthAmendment: {
    priorCenterMaximumCssPx: 960,
    revisedCenterMaximumCssPx: 1104,
    increasePercent: 15,
  },
  cases: [],
};

for (const [style, width, height] of cases) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    isMobile: width <= 390,
    hasTouch: width <= 390,
  });
  const page = await context.newPage();
  const url = new URL("/petec/resume", baseUrl);
  url.searchParams.set("overviewStyle", style);

  const response = await page.goto(url.toString(), { waitUntil: "networkidle" });
  if (!response || response.status() !== 200) {
    throw new Error(
      `${style} ${width}x${height} returned ${response?.status() ?? "no response"}`,
    );
  }
  const renderedOverview = page.locator(
    `[data-overview-root][data-style-id="${style}"]`,
  );
  if ((await renderedOverview.count()) !== 1) {
    throw new Error(
      `${style} ${width}x${height} did not render exactly one matching Overview`,
    );
  }
  await page.evaluate(async () => {
    if (document.fonts?.ready) {
      await document.fonts.ready;
    }
  });

  const measurements = await page.evaluate(() => {
    const rect = (selector) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const box = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return {
        x: Number(box.x.toFixed(2)),
        y: Number(box.y.toFixed(2)),
        width: Number(box.width.toFixed(2)),
        height: Number(box.height.toFixed(2)),
        fontSize: style.fontSize,
        lineHeight: style.lineHeight,
      };
    };

    const proofContainment = [
      ...document.querySelectorAll(".work-impact-proof article"),
    ].map((article) => {
      const value = article.querySelector("strong");
      const articleBox = article.getBoundingClientRect();
      const valueBox = value?.getBoundingClientRect();
      return {
        value: value?.textContent?.trim() ?? "",
        contained:
          Boolean(valueBox) &&
          valueBox.left >= articleBox.left &&
          valueBox.right <= articleBox.right,
        cardWidth: Number(articleBox.width.toFixed(2)),
        valueWidth: valueBox ? Number(valueBox.width.toFixed(2)) : null,
      };
    });

    const workSummaryCards = [
      ...document.querySelectorAll(".work-impact-summary-card"),
    ].map((card) => {
      const box = card.getBoundingClientRect();
      return {
        label: card.querySelector("h2")?.textContent?.trim() ?? "",
        height: Number(box.height.toFixed(2)),
      };
    });

    const workFeatures = [
      ...document.querySelectorAll(
        ".work-impact-features > :is(.work-impact-feature, .work-impact-outcomes)",
      ),
    ].map((feature) => {
      const box = feature.getBoundingClientRect();
      return {
        label: feature.querySelector("h2")?.textContent?.trim() ?? "",
        height: Number(box.height.toFixed(2)),
      };
    });

    const workMedia = [
      ...document.querySelectorAll(".member-overview-work img"),
    ].map((image) => ({
      src: image.getAttribute("src"),
      complete: image.complete,
      naturalWidth: image.naturalWidth,
      naturalHeight: image.naturalHeight,
    }));

    return {
      viewport: {
        innerWidth,
        innerHeight,
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        horizontalOverflow:
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth,
      },
      shell: rect(".r2-page-grid"),
      leftRail: rect(".r2-overview-context-rail"),
      center: rect(".r2-content"),
      rightRail: rect(".r2-overview-ai-rail"),
      desktopStylePicker: rect(".r2-overview-style-picker"),
      mobileStylePicker: rect(".r2-overview-mobile-style-picker"),
      activeStyleLinks: [
        ...document.querySelectorAll(
          '.r2-overview-style-picker a[aria-current="page"], ' +
            '.r2-overview-mobile-style-picker a[aria-current="page"]',
        ),
      ].map((link) => link.textContent?.trim() ?? ""),
      overview: rect(".member-overview"),
      workHero: rect(".work-impact-hero"),
      workIntro: rect(".work-impact-intro"),
      workProof: rect(".work-impact-proof"),
      workBody: rect(".work-impact-body"),
      workClosing: rect(".work-impact-closing"),
      storyHero: rect(".overview-hero"),
      storyOpening: rect(".overview-opening"),
      storyProof: rect(".overview-proof"),
      storyBand: rect(".overview-story"),
      proofContainment,
      workSummaryCards,
      workFeatures,
      workMedia,
      pageTransform: getComputedStyle(
        document.querySelector("#living-resume-page"),
      ).transform,
      bodyZoom: getComputedStyle(document.body).zoom || "1",
    };
  });
  if (measurements.viewport.horizontalOverflow !== 0) {
    throw new Error(`${style} ${width}x${height} has horizontal overflow`);
  }
  const expectedStyleLabel =
    style === "work-impact" ? "Work & Impact" : "Story & Career";
  if (
    measurements.activeStyleLinks.length !== 2 ||
    measurements.activeStyleLinks.some((label) => label !== expectedStyleLabel)
  ) {
    throw new Error(`${style} ${width}x${height} has an incorrect style switch`);
  }
  if (
    width > 960 &&
    (!measurements.desktopStylePicker || measurements.desktopStylePicker.width === 0)
  ) {
    throw new Error(`${style} ${width}x${height} is missing the desktop style switch`);
  }
  if (
    width <= 960 &&
    (!measurements.mobileStylePicker || measurements.mobileStylePicker.width === 0)
  ) {
    throw new Error(`${style} ${width}x${height} is missing the mobile style switch`);
  }
  if (style === "work-impact") {
    if (measurements.proofContainment.some((item) => !item.contained)) {
      throw new Error(`${style} ${width}x${height} clips a proof value`);
    }
    if (
      measurements.workMedia.some(
        (item) => !item.complete || !item.naturalWidth || !item.naturalHeight,
      )
    ) {
      throw new Error(`${style} ${width}x${height} has unloaded presentation media`);
    }
  }

  const name = `${style}-${width}x${height}`;
  await page.screenshot({
    path: path.join(evidenceRoot, `${name}.png`),
    fullPage: false,
  });
  if (width === 1920 && height === 1080) {
    await page.screenshot({
      path: path.join(evidenceRoot, `${name}-full-page.png`),
      fullPage: true,
    });
  }
  results.cases.push({ name, style, width, height, measurements });
  await context.close();
}

await browser.close();
fs.writeFileSync(
  path.join(evidenceRoot, "measurements.json"),
  `${JSON.stringify(results, null, 2)}\n`,
);

console.log(`Captured ${results.cases.length} cases in ${evidenceRoot}`);
