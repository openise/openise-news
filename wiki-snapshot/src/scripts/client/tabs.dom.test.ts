/* @vitest-environment happy-dom */

import { afterEach, describe, expect, it, vi } from "vitest";
import { initTabs } from "./tabs";
import { initTocActive } from "./toc-active";

function group(labels: string[]): string {
  const sections = labels.map((label) => (
    `<section class="content-tab" data-tab-label="${label}"><p class="content-tab-label"><strong>${label}</strong></p><p>本文 ${label}</p></section>`
  )).join("");
  return `<div class="content-tabs" data-tabs>${sections}</div>`;
}

function tabs(container: ParentNode = document): HTMLButtonElement[] {
  return Array.from(container.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
}

function panels(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>('[role="tabpanel"]'));
}

function press(target: HTMLElement, key: string): void {
  target.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
}

function setFragment(fragment: string): void {
  window.history.replaceState(null, "", `#${fragment}`);
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
  document.body.innerHTML = "";
});

describe("initTabs", () => {
  it("先頭に tablist を作り section ごとに tab を置く", () => {
    document.body.innerHTML = group(["A", "B", "C"]);
    initTabs();

    const tablist = document.querySelector("[data-tabs] > [role=\"tablist\"]:first-child");
    expect(tablist).not.toBeNull();
    expect(tabs().map((tab) => tab.textContent)).toEqual(["A", "B", "C"]);
    expect(tabs().every((tab) => tab.type === "button")).toBe(true);
  });

  it("最初のタブだけを選択して表示する", () => {
    document.body.innerHTML = group(["A", "B", "C"]);
    initTabs();

    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["true", "false", "false"]);
    expect(tabs().map((tab) => tab.tabIndex)).toEqual([0, -1, -1]);
    expect(panels().map((panel) => panel.hidden)).toEqual([false, true, true]);
  });

  it("初期 fragment が指す見出しの panel を表示する", () => {
    document.body.innerHTML = `
      <div data-tabs>
        <section data-tab-label="A"><h2 id="first-heading">A</h2></section>
        <section data-tab-label="B"><h2 id="second-heading">B</h2></section>
      </div>
    `;
    setFragment("second-heading");

    initTabs();

    expect(panels().map((panel) => panel.hidden)).toEqual([true, false]);
    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "true"]);
    expect(tabs().map((tab) => tab.tabIndex)).toEqual([-1, 0]);
  });

  it("目次 link の hashchange 後に対象 panel を表示し、次の frame で現在見出しを同期する", () => {
    const links = '<a class="toc-link" href="#first-heading">A の見出し</a><a class="toc-link" href="#second-heading">B の見出し</a>';
    document.body.innerHTML = `
      <aside><nav class="toc">${links}</nav></aside>
      <div class="mobile-toc-bar"><span data-mobile-toc-current></span><nav class="toc">${links}</nav></div>
      <div data-tabs>
        <section data-tab-label="A"><h2 id="first-heading" style="scroll-margin-top: 80px">A</h2></section>
        <section data-tab-label="B"><h2 id="second-heading" style="scroll-margin-top: 80px">B</h2></section>
      </div>
    `;
    const frames: FrameRequestCallback[] = [];
    const cleanupListeners: (() => void)[] = [];
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      frames.push(callback);
      return frames.length;
    });
    // 実 listener を登録し、この結合 test が追加した購読だけを後で取り除く。
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
    try {
      // happy-dom は layout を持たないため、位置と panel の描画有無だけを補う。
      for (const heading of document.querySelectorAll("h2")) {
        vi.spyOn(heading, "getBoundingClientRect").mockReturnValue(DOMRect.fromRect({ y: 20 }));
        vi.spyOn(heading, "getClientRects").mockImplementation(() =>
          (heading.closest("[hidden]") ? [] : [DOMRect.fromRect({})]) as unknown as DOMRectList,
        );
      }
      initTabs();
      initTocActive();
      expect(document.querySelector("[data-mobile-toc-current]")?.textContent).toBe("A の見出し");

      document.querySelector<HTMLAnchorElement>('.mobile-toc-bar a[href="#second-heading"]')!.click();
      setFragment("second-heading");
      window.dispatchEvent(new HashChangeEvent("hashchange"));

      expect(panels().map((panel) => panel.hidden)).toEqual([true, false]);
      expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "true"]);
      expect(tabs().map((tab) => tab.tabIndex)).toEqual([-1, 0]);
      expect(document.querySelector("[data-mobile-toc-current]")?.textContent).toBe("A の見出し");
      frames.splice(0).forEach((callback) => callback(0));
      expect(Array.from(document.querySelectorAll('.toc-link[aria-current="location"]'), (link) => link.getAttribute("href"))).toEqual([
        "#second-heading", "#second-heading",
      ]);
      expect(document.querySelector("[data-mobile-toc-current]")?.textContent).toBe("B の見出し");
    } finally {
      cleanupListeners.forEach((cleanup) => cleanup());
      vi.restoreAllMocks();
      vi.unstubAllGlobals();
    }
  });

  it("入れ子の fragment が外側と内側の panel を表示し選択状態を同期する", () => {
    document.body.innerHTML = `
      <div data-tabs>
        <section data-tab-label="外 A"><h2 id="outer-first">外 A</h2></section>
        <section data-tab-label="外 B">
          <div data-tabs>
            <section data-tab-label="内 A"><h3 id="inner-first">内 A</h3></section>
            <section data-tab-label="内 B"><h3 id="nested-heading">内 B</h3></section>
          </div>
        </section>
      </div>
    `;
    setFragment("nested-heading");

    initTabs();

    expect(panels().map((panel) => panel.hidden)).toEqual([true, false, true, false]);
    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "true", "false", "true"]);
    expect(tabs().map((tab) => tab.tabIndex)).toEqual([-1, 0, -1, 0]);
  });

  it("存在しない fragment と不正な encoding では選択状態を維持する", () => {
    document.body.innerHTML = group(["A", "B"]);
    setFragment("missing-heading");
    initTabs();

    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["true", "false"]);

    tabs()[1].click();
    setFragment("missing-heading");
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    expect(panels().map((panel) => panel.hidden)).toEqual([true, false]);

    setFragment("%E0%A4%A");
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    expect(panels().map((panel) => panel.hidden)).toEqual([true, false]);
    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "true"]);
    expect(tabs().map((tab) => tab.tabIndex)).toEqual([-1, 0]);
  });

  it("JS 無し用のラベル段落を隠す", () => {
    document.body.innerHTML = group(["A", "B"]);
    initTabs();

    expect(Array.from(document.querySelectorAll<HTMLElement>(".content-tab-label")).every((label) => label.hidden)).toBe(true);
  });

  it("tab と panel の id を対応させる", () => {
    document.body.innerHTML = group(["A", "B"]);
    initTabs();

    for (const [index, tab] of tabs().entries()) {
      const panel = panels()[index];
      expect(tab.getAttribute("aria-controls")).toBe(panel.id);
      expect(panel.getAttribute("aria-labelledby")).toBe(tab.id);
      expect(panel.tabIndex).toBe(0);
    }
  });

  it("複数のタブ群で id が重複しない", () => {
    document.body.innerHTML = group(["A", "B"]) + group(["C", "D"]);
    initTabs();

    const ids = [...tabs(), ...panels()].map((element) => element.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("クリックしたタブのパネルだけを表示する", () => {
    document.body.innerHTML = group(["A", "B", "C"]);
    initTabs();

    tabs()[2].click();

    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "false", "true"]);
    expect(panels().map((panel) => panel.hidden)).toEqual([true, true, false]);
  });

  it("矢印キーで隣のタブへ移り、端で反対側に回り込む", () => {
    document.body.innerHTML = group(["A", "B", "C"]);
    initTabs();
    tabs()[0].focus();

    press(tabs()[0], "ArrowLeft");
    expect(document.activeElement).toBe(tabs()[2]);
    expect(panels()[2].hidden).toBe(false);
    expect(tabs().map((tab) => tab.tabIndex)).toEqual([-1, -1, 0]);
    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "false", "true"]);

    press(tabs()[2], "ArrowRight");
    expect(document.activeElement).toBe(tabs()[0]);
    expect(tabs()[0].getAttribute("aria-selected")).toBe("true");
    expect(tabs().map((tab) => tab.tabIndex)).toEqual([0, -1, -1]);
    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["true", "false", "false"]);
  });

  it("Home と End で最初と最後のタブへ移る", () => {
    document.body.innerHTML = group(["A", "B", "C"]);
    initTabs();
    tabs()[1].focus();

    press(tabs()[1], "End");
    expect(document.activeElement).toBe(tabs()[2]);
    expect(tabs().map((tab) => tab.tabIndex)).toEqual([-1, -1, 0]);
    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "false", "true"]);

    press(tabs()[2], "Home");
    expect(document.activeElement).toBe(tabs()[0]);
    expect(tabs().map((tab) => tab.tabIndex)).toEqual([0, -1, -1]);
    expect(tabs().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["true", "false", "false"]);
  });

  it("修飾キー付きの矢印ではタブを切り替えない", () => {
    document.body.innerHTML = group(["A", "B", "C"]);
    initTabs();
    tabs()[0].focus();

    const event = new KeyboardEvent("keydown", { key: "ArrowRight", altKey: true, bubbles: true, cancelable: true });
    tabs()[0].dispatchEvent(event);

    expect(document.activeElement).toBe(tabs()[0]);
    expect(tabs()[0].getAttribute("aria-selected")).toBe("true");
    expect(event.defaultPrevented).toBe(false);
  });

  it("2 回呼んでも tablist を二重に作らない", () => {
    document.body.innerHTML = group(["A", "B"]);
    initTabs();
    initTabs();

    expect(document.querySelectorAll('[role="tablist"]')).toHaveLength(1);
    expect(document.querySelector("[data-tabs]")?.hasAttribute("data-tabs-ready")).toBe(true);
  });
});
