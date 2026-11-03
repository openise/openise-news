/* @vitest-environment happy-dom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { initMobileTocBar } from "./mobile-toc-bar";

let bar: HTMLElement;
let toggle: HTMLButtonElement;
let panel: HTMLElement;
let link: HTMLAnchorElement;
let outside: HTMLButtonElement;
let frames: FrameRequestCallback[];

beforeEach(() => {
  frames = [];
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    frames.push(callback);
    return frames.length;
  });
  document.body.innerHTML = `
    <div class="mobile-toc-bar">
      <button type="button" class="mobile-toc-toggle" aria-expanded="false" aria-controls="mobile-toc-panel">目次</button>
      <div id="mobile-toc-panel" hidden><a class="toc-link" href="#heading">見出し</a></div>
    </div>
    <button type="button" id="outside">本文側の操作</button>
    <h2 id="heading">見出し</h2>
  `;
  bar = document.querySelector<HTMLElement>(".mobile-toc-bar")!;
  toggle = document.querySelector<HTMLButtonElement>(".mobile-toc-toggle")!;
  panel = document.querySelector<HTMLElement>("#mobile-toc-panel")!;
  link = document.querySelector<HTMLAnchorElement>(".toc-link")!;
  outside = document.querySelector<HTMLButtonElement>("#outside")!;
  initMobileTocBar();
});

afterEach(() => {
  document.body.innerHTML = "";
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function expectOpen(open: boolean): void {
  expect(panel.hidden).toBe(!open);
  expect(toggle.getAttribute("aria-expanded")).toBe(String(open));
}

function flushFrame(): void {
  const pending = frames.splice(0);
  pending.forEach((callback) => callback(0));
}

describe("initMobileTocBar", () => {
  it("toggle の click ごとに hidden と aria-expanded を同期する", () => {
    expectOpen(false);
    toggle.click();
    expectOpen(true);
    toggle.click();
    expectOpen(false);
  });

  it("目次リンクの click で閉じ、fragment 移動の default を止めない", () => {
    toggle.click();
    expectOpen(true);
    const event = new MouseEvent("click", { bubbles: true, cancelable: true });
    link.dispatchEvent(event);

    expectOpen(false);
    expect(event.defaultPrevented).toBe(false);
  });

  it("バー内の click では開いたままで、外側の click で閉じる", () => {
    toggle.click();
    expectOpen(true);
    panel.click();
    expectOpen(true);
    outside.click();
    expectOpen(false);
  });

  it("Escape で閉じて toggle に focus を戻す", () => {
    toggle.click();
    expectOpen(true);
    link.focus();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));

    expectOpen(false);
    expect(document.activeElement).toBe(toggle);
  });

  it("Escape 以外のキーはパネルを閉じない", () => {
    toggle.click();
    expectOpen(true);
    link.focus();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));

    expectOpen(true);
    expect(document.activeElement).toBe(link);
  });

  it("バー内への focus 移動では開いたままで、バー外への移動で閉じる", () => {
    toggle.focus();
    toggle.click();
    expectOpen(true);
    link.focus();
    expectOpen(true);
    outside.focus();
    expectOpen(false);
    expect(document.activeElement).toBe(outside);
  });

  it("移動先が null の focusout は click 判定に任せて閉じない", () => {
    toggle.click();
    expectOpen(true);
    bar.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));

    expectOpen(true);
  });

  it.each([
    { bottom: 220, expected: "min(60vh, 80px)" },
    { bottom: 300, expected: "min(60vh, 0px)" },
    { bottom: 350, expected: "min(60vh, 0px)" },
  ])("viewport が 300px、バー下端が $bottom px の開いたパネルを $expected に制限する", ({ bottom, expected }) => {
    vi.stubGlobal("innerHeight", 300);
    vi.spyOn(bar, "getBoundingClientRect").mockReturnValue(DOMRect.fromRect({ y: bottom, height: 0 }));

    toggle.click();

    expectOpen(true);
    expect(panel.style.maxHeight).toBe(expected);
  });

  it("開くたびに viewport の残り高さを計算し直す", () => {
    vi.stubGlobal("innerHeight", 300);
    const rect = vi.spyOn(bar, "getBoundingClientRect").mockReturnValue(DOMRect.fromRect({ y: 220 }));
    toggle.click();
    expect(panel.style.maxHeight).toBe("min(60vh, 80px)");
    toggle.click();
    rect.mockReturnValue(DOMRect.fromRect({ y: 100 }));
    toggle.click();

    expectOpen(true);
    expect(panel.style.maxHeight).toBe("min(60vh, 200px)");
  });

  it("開いた状態の scroll 後にバー下端の残り高さを計算し直す", () => {
    vi.stubGlobal("innerHeight", 812);
    const rect = vi.spyOn(bar, "getBoundingClientRect").mockReturnValue(DOMRect.fromRect({ y: 44 }));
    toggle.click();
    expect(panel.style.maxHeight).toBe("min(60vh, 768px)");
    rect.mockReturnValue(DOMRect.fromRect({ y: 443.84375 }));

    window.dispatchEvent(new Event("scroll"));
    flushFrame();

    expectOpen(true);
    expect(panel.style.maxHeight).toBe("min(60vh, 368.15625px)");
  });

  it("開いた状態の resize 後に新しい viewport で残り高さを計算し直す", () => {
    vi.stubGlobal("innerHeight", 812);
    vi.spyOn(bar, "getBoundingClientRect").mockReturnValue(DOMRect.fromRect({ y: 295.84375 }));
    toggle.click();
    vi.stubGlobal("innerHeight", 300);

    window.dispatchEvent(new Event("resize"));
    flushFrame();

    expectOpen(true);
    expect(panel.style.maxHeight).toBe("min(60vh, 4.15625px)");
  });

  it("連続する scroll と resize を同じ frame の最新の位置で 1 回だけ測定する", () => {
    vi.stubGlobal("innerHeight", 300);
    const rect = vi.spyOn(bar, "getBoundingClientRect").mockReturnValue(DOMRect.fromRect({ y: 44 }));
    toggle.click();
    rect.mockClear();
    window.dispatchEvent(new Event("scroll"));
    rect.mockReturnValue(DOMRect.fromRect({ y: 100 }));
    window.dispatchEvent(new Event("resize"));
    rect.mockReturnValue(DOMRect.fromRect({ y: 220 }));
    window.dispatchEvent(new Event("scroll"));
    expect(panel.style.maxHeight).toBe("min(60vh, 256px)");

    flushFrame();

    expect(panel.style.maxHeight).toBe("min(60vh, 80px)");
    expect(rect).toHaveBeenCalledTimes(1);
  });

  it("閉じている間と予約 frame 前に閉じた場合は高さを再計算しない", () => {
    vi.stubGlobal("innerHeight", 300);
    const rect = vi.spyOn(bar, "getBoundingClientRect").mockReturnValue(DOMRect.fromRect({ y: 220 }));
    toggle.click();
    window.dispatchEvent(new Event("scroll"));
    toggle.click();
    rect.mockReturnValue(DOMRect.fromRect({ y: 100 }));
    flushFrame();
    expectOpen(false);
    expect(panel.style.maxHeight).toBe("min(60vh, 80px)");

    window.dispatchEvent(new Event("resize"));
    window.dispatchEvent(new Event("scroll"));
    flushFrame();

    expectOpen(false);
    expect(panel.style.maxHeight).toBe("min(60vh, 80px)");
  });
});
