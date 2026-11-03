/* @vitest-environment happy-dom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { initTabs } from "./tabs";
import { initTocActive } from "./toc-active";

const items = `
  <li><a class="toc-link" href="#intro">はじめに</a></li>
  <li><a class="toc-link" href="#%E6%8E%A5%E7%B6%9A">接続</a></li>
  <li><a class="toc-link" href="#hidden">非表示</a></li>
  <li><a class="toc-link" href="#missing">対応なし</a></li>
  <li><a class="toc-link" href="#%E0%A4%A">不正な encoding</a></li>`;
const fixture = `
  <aside><nav class="toc"><details open><ul>${items}</ul></details></nav></aside>
  <div class="mobile-toc-bar">
    <button class="mobile-toc-toggle"><span data-mobile-toc-current></span></button>
    <div id="mobile-toc-panel" hidden><nav class="toc"><details open><ul>${items}</ul></details></nav></div>
  </div>
  <article>
    <h2 id="intro" style="scroll-margin-top: 80px">はじめに</h2>
    <h3 id="接続" style="scroll-margin-top: 80px">接続</h3>
    <h3 id="hidden" style="scroll-margin-top: 80px">非表示</h3>
  </article>`;

let frames: FrameRequestCallback[];
let cleanupListeners: (() => void)[];
let positions: Map<string, number | null>;

function currentTexts(): string[] {
  return Array.from(document.querySelectorAll<HTMLAnchorElement>('.toc-link[aria-current="location"]'))
    .map((link) => link.textContent ?? "");
}
function currentLabel(): string | null | undefined {
  return document.querySelector("[data-mobile-toc-current]")?.textContent;
}
function placeHeading(id: string, top: number | null): void {
  const heading = document.getElementById(id);
  if (!heading) throw new Error(`見出しがありません: ${id}`);
  if (!positions.has(id)) {
    vi.spyOn(heading, "getBoundingClientRect").mockImplementation(() =>
      DOMRect.fromRect({ y: positions.get(id) ?? 0 }),
    );
    vi.spyOn(heading, "getClientRects").mockImplementation(() =>
      (positions.get(id) === null || heading.closest("[hidden]") ? [] : [DOMRect.fromRect({})]) as unknown as DOMRectList,
    );
  }
  positions.set(id, top);
}
function flushFrames(): void {
  const pending = frames;
  frames = [];
  pending.forEach((callback) => callback(0));
}
function tabsFixture(): void {
  document.querySelector("article")!.innerHTML = `
    <div data-tabs>
      <section data-tab-label="A"><h2 id="intro" style="scroll-margin-top: 80px">はじめに</h2></section>
      <section data-tab-label="B"><h2 id="接続" style="scroll-margin-top: 80px">接続</h2></section>
      <section data-tab-label="C"><h2 id="hidden" style="scroll-margin-top: 80px">非表示</h2></section>
    </div>`;
  positions.clear();
  placeHeading("intro", 10);
  placeHeading("接続", 20);
  placeHeading("hidden", 30);
  initTabs();
  initTocActive();
}
function tabs(): HTMLButtonElement[] {
  return Array.from(document.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
}
beforeEach(() => {
  document.body.innerHTML = fixture;
  frames = [];
  cleanupListeners = [];
  positions = new Map();
  // layout がない happy-dom に viewport 内の位置と描画有無だけを与える。
  placeHeading("intro", 10);
  placeHeading("接続", 600);
  placeHeading("hidden", null);
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    frames.push(callback);
    return frames.length;
  });
  // 実際の listener を登録し、前の test の購読だけを後で取り除く。
  const windowAdd = window.addEventListener.bind(window);
  vi.spyOn(window, "addEventListener").mockImplementation((type, listener, options) => {
    windowAdd(type, listener, options);
    cleanupListeners.push(() => window.removeEventListener(type, listener, options));
  });
  const documentAdd = document.addEventListener.bind(document);
  vi.spyOn(document, "addEventListener").mockImplementation((type, listener, options) => {
    documentAdd(type, listener, options);
    cleanupListeners.push(() => document.removeEventListener(type, listener, options));
  });
});
afterEach(() => {
  cleanupListeners.forEach((cleanup) => cleanup());
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
  window.history.replaceState(null, "", "/");
});

describe("initTocActive", () => {
  it("同じ見出しへの PC とモバイルのリンクと現在ラベルを同期する", () => {
    placeHeading("intro", -500);
    placeHeading("接続", 84);
    initTocActive();
    expect(currentTexts()).toEqual(["接続", "接続"]);
    expect(currentLabel()).toBe("接続");
  });
  it("computed scroll margin に 4px を足した判定線の手前では現在位置を空にする", () => {
    placeHeading("intro", 85);
    document.querySelector("[data-mobile-toc-current]")!.textContent = "以前の見出し";
    initTocActive();
    expect(currentTexts()).toEqual([]);
    expect(currentLabel()).toBe("");
  });
  it("日本語 slug を解決し非表示と対応なしと不正な encoding を除外する", () => {
    placeHeading("intro", -500);
    placeHeading("接続", 50);
    expect(() => initTocActive()).not.toThrow();
    expect(currentTexts()).toEqual(["接続", "接続"]);
    expect(currentLabel()).toBe("接続");
  });
  it.each(["scroll", "resize", "hashchange"])("%s 後の frame で現在位置を更新する", (eventType) => {
    initTocActive();
    expect(currentTexts()).toEqual(["はじめに", "はじめに"]);
    placeHeading("intro", -600);
    placeHeading("接続", 0);
    window.dispatchEvent(new Event(eventType));
    expect(currentTexts()).toEqual(["はじめに", "はじめに"]);
    flushFrames();
    expect(currentTexts()).toEqual(["接続", "接続"]);
    expect(currentLabel()).toBe("接続");
  });
  it("scroll と resize と hashchange を同じ frame の位置にまとめる", () => {
    initTocActive();
    placeHeading("接続", 0);
    window.dispatchEvent(new Event("scroll"));
    window.dispatchEvent(new Event("resize"));
    window.dispatchEvent(new Event("hashchange"));
    expect(frames).toHaveLength(1);
    flushFrames();
    expect(currentTexts()).toEqual(["接続", "接続"]);
  });
  it("ページ最下部でも未通過の見出しを強制選択しない", () => {
    vi.spyOn(document.documentElement, "scrollHeight", "get").mockReturnValue(window.innerHeight);
    placeHeading("接続", 300);
    initTocActive();
    expect(currentTexts()).toEqual(["はじめに", "はじめに"]);
  });
  it("tab の click 後に新しく表示された見出しを現在位置にする", () => {
    tabsFixture();
    expect(currentLabel()).toBe("はじめに");
    tabs()[1].click();
    expect(currentLabel()).toBe("はじめに");
    flushFrames();
    expect(currentTexts()).toEqual(["接続", "接続"]);
    expect(currentLabel()).toBe("接続");
  });
  it.each([
    { start: 0, key: "ArrowRight", label: "接続" },
    { start: 0, key: "ArrowLeft", label: "非表示" },
    { start: 1, key: "Home", label: "はじめに" },
    { start: 0, key: "End", label: "非表示" },
  ])("tab の $key による切り替え後も現在位置を同期する", ({ start, key, label }) => {
    tabsFixture();
    tabs()[start].click();
    flushFrames();
    tabs()[start].focus();
    tabs()[start].dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
    flushFrames();
    expect(currentTexts()).toEqual([label, label]);
    expect(currentLabel()).toBe(label);
  });
  it("hashchange で tab が変わった後の表示を現在位置へ反映する", () => {
    tabsFixture();
    window.history.replaceState(null, "", "#%E6%8E%A5%E7%B6%9A");
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    flushFrames();
    expect(currentTexts()).toEqual(["接続", "接続"]);
  });
  it("9 件の PC 目次を展開し、別の目次の残件を変更しない", () => {
    const nineItems = Array.from({ length: 9 }, (_, index) => `
      <li class="toc-item${index === 8 ? " toc-extra hidden" : ""}"><a class="toc-link" href="#h${index}">見出し ${index}</a></li>`).join("");
    document.body.innerHTML = `
      <nav id="pc-toc" class="toc"><details open><ul>${nineItems}<li><button class="toc-expand-btn">+ 1 件</button></li></ul></details></nav>
      <nav id="other-toc" class="toc"><details open><ul>${nineItems}<li><button class="toc-expand-btn">+ 1 件</button></li></ul></details></nav>`;
    initTocActive();
    document.querySelector<HTMLButtonElement>("#pc-toc .toc-expand-btn")!.click();
    expect(document.querySelectorAll("#pc-toc .toc-item:not(.hidden)")).toHaveLength(9);
    expect(document.querySelector("#pc-toc .toc-expand-btn")).toBeNull();
    expect(document.querySelectorAll("#other-toc .toc-extra.hidden")).toHaveLength(1);
    expect(document.querySelector("#other-toc .toc-expand-btn")).not.toBeNull();
  });
});
