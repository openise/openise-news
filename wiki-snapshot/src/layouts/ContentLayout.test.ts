import { experimental_AstroContainer as AstroContainer } from "astro/container";
import type { MarkdownHeading } from "astro";
import { Window } from "happy-dom";
import { describe, expect, it } from "vitest";
import ContentLayout from "./ContentLayout.astro";
import source from "./ContentLayout.astro?raw";
import mobileSource from "../components/MobileTocBar.astro?raw";

async function render(headings: MarkdownHeading[]) {
  const container = await AstroContainer.create();
  const html = await container.renderToString(ContentLayout, {
    props: { title: "ページタイトル", headings },
    slots: { header: "<h1>ページタイトル</h1>", default: "<p>本文</p>" },
  });
  const window = new Window();
  return new window.DOMParser().parseFromString(html, "text/html");
}

describe("ContentLayout の TOC 配置", () => {
  it("モバイルバーを記事 header 直後、PC sidebar を記事の右側に配置する", async () => {
    const document = await render([{ depth: 2, slug: "section", text: "節" }]);
    const article = document.querySelector(".content-article");
    const header = article?.querySelector(".content-header");
    const bar = document.querySelector(".mobile-toc-bar");
    const sidebar = document.querySelector("aside.content-toc");

    expect(bar).not.toBeNull();
    expect(header?.classList.contains("has-toc")).toBe(true);
    expect(header?.nextElementSibling).toBe(bar);
    expect(bar?.nextElementSibling?.textContent).toBe("本文");
    expect(article?.nextElementSibling).toBe(sidebar);
    expect(sidebar?.querySelector(".content-toc-card > nav.toc")).not.toBeNull();
    expect(document.querySelectorAll('nav[aria-label="目次"]')).toHaveLength(2);
    expect(bar?.querySelector(".toc-summary")?.hasAttribute("hidden")).toBe(true);
    expect(sidebar?.querySelector(".toc-summary")?.hasAttribute("hidden")).toBe(false);
  });
});

describe("ContentLayout の Mermaid loader", () => {
  it("should initialize the client loader without inlining it", () => {
    expect(source).not.toMatch(/<script[^>]*is:inline[^>]*define:vars[^>]*mermaidSrc/);
    expect(source).toMatch(
      /<script>\s*import \{ initMermaid \} from "\.\.\/scripts\/client\/mermaid";\s*initMermaid\(\);\s*<\/script>/,
    );
  });
});

describe("ContentLayout の表の横スクロール", () => {
  it("should wrap tables with the client script", () => {
    expect(source).toMatch(
      /<script>\s*import \{ wrapTables \} from "\.\.\/scripts\/client\/table-scroll";\s*wrapTables\(\);\s*<\/script>/,
    );
  });
});

describe("ContentLayout の本文幅", () => {
  it(".content-article の最大幅を 50rem にする", () => {
    const rule = source.match(/\.content-article\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(rule).toMatch(/max-width:\s*50rem;/);
    expect(source).not.toContain("60rem");
  });
});

describe("ContentLayout の本文の左端", () => {
  // コメント内の } でルール本体の抽出が途切れないよう、先にコメントを取り除く
  const css = source.replace(/\/\*[\s\S]*?\*\//g, "");
  const [shell = "", ...overrides] = [...css.matchAll(/\.content-shell\s*\{([^}]*)\}/g)].map((rule) => rule[1]);

  it(".content-shell の幅を min(100% - 2rem, 1098px) にして中央に置き、本文の左端を daily に揃える", () => {
    expect(shell).toMatch(/width:\s*min\(100% - 2rem, 1098px\);/);
    expect(shell).toMatch(/margin-inline:\s*auto;/);
  });

  it("@media 内の .content-shell で幅を上書きしない", () => {
    expect(overrides.length).toBeGreaterThan(0);
    for (const rule of overrides) {
      expect(rule).not.toMatch(/(?:^|[\s;])(?:min-|max-)?width\s*:/);
    }
  });

  it(".content-shell と .content-article の左に padding / margin を足さない", () => {
    for (const rule of css.matchAll(/\.content-(?:shell|article)\s*\{([^}]*)\}/g)) {
      expect(rule[1]).not.toMatch(/(?:padding|margin)-(?:left|inline-start)\s*:|(?:padding|margin)(?:-inline)?\s*:(?!\s*auto;)/);
    }
  });

  it("本文の左端について openise-daily と openise-theme の対応箇所を示す", () => {
    expect(source).toContain("daily: src/layouts/BaseLayout.astro の <main>");
    expect(source).toContain("theme: src/styles/global.css の .site-main");
  });
});

describe("ContentLayout の TOC 表示条件", () => {
  it.each([
    { name: "見出しなし", headings: [] },
    { name: "H1 のみ", headings: [{ depth: 1, slug: "title", text: "タイトル" }] },
  ])("$name ではバーと sidebar の両方を省く", async ({ headings }) => {
    const document = await render(headings);

    expect(document.querySelector(".mobile-toc-bar")).toBeNull();
    expect(document.querySelector(".content-toc")).toBeNull();
    expect(document.querySelector('nav[aria-label="目次"]')).toBeNull();
    expect(document.querySelector(".content-header")?.classList.contains("has-toc")).toBe(false);
  });

  it("H2〜H6 を両方に表示し、モバイルでは全件、PC では 8 件を初期表示する", async () => {
    const document = await render([
      { depth: 1, slug: "title", text: "タイトル" },
      ...Array.from({ length: 9 }, (_, index) => ({
        depth: 2 + index % 5,
        slug: `heading-${index + 1}`,
        text: `見出し ${index + 1}`,
      })),
    ]);
    const bar = document.querySelector(".mobile-toc-bar");
    const sidebar = document.querySelector(".content-toc");
    const expected = [
      "#heading-1", "#heading-2", "#heading-3", "#heading-4", "#heading-5",
      "#heading-6", "#heading-7", "#heading-8", "#heading-9",
    ];

    for (const container of [bar, sidebar]) {
      expect(Array.from(container?.querySelectorAll(".toc-link") ?? [], (link) => link.getAttribute("href"))).toEqual(expected);
    }
    expect(bar?.querySelectorAll(".toc-item:not(.hidden)")).toHaveLength(9);
    expect(bar?.querySelector(".toc-expand-btn")).toBeNull();
    expect(sidebar?.querySelectorAll(".toc-item:not(.hidden)")).toHaveLength(8);
    expect(sidebar?.querySelector(".toc-expand-btn")?.textContent).toBe("+ 1 件");
  });

  it("1023px まで sidebar を隠し、1024px から右側の sticky sidebar を表示する", () => {
    const base = source.split("@media (min-width: 1024px)")[0];
    const desktop = source.split("@media (min-width: 1024px)")[1] ?? "";

    expect(base).toMatch(/\.content-toc\s*\{[^}]*display:\s*none;/s);
    expect(desktop).toMatch(/\.content-shell\s*\{[^}]*flex-direction:\s*row;/s);
    expect(desktop).toMatch(/\.content-toc\s*\{[^}]*display:\s*block;[^}]*position:\s*sticky;[^}]*top:\s*6rem;[^}]*width:\s*16rem;[^}]*max-height:\s*calc\(100vh - 6rem\);/s);
    expect(source).toMatch(/\.content-toc-card\s*\{[^}]*padding:\s*1rem;[^}]*border-radius:\s*1rem;/s);
  });

  it("TOC があるモバイル header の下を 0.5rem、PC では 2.5rem 空ける", () => {
    const base = source.split("@media (min-width: 1024px)")[0];
    const desktop = source.split("@media (min-width: 1024px)")[1] ?? "";

    expect(base).toMatch(/\.content-header\s*\{[^}]*margin-bottom:\s*2\.5rem;/s);
    expect(base).toMatch(/\.content-header\.has-toc\s*\{[^}]*margin-bottom:\s*0\.5rem;/s);
    expect(desktop).toMatch(/\.content-header\.has-toc\s*\{[^}]*margin-bottom:\s*2\.5rem;/s);
  });

  it("モバイルバーは上端 0 の sticky で高さ 2.75rem、下余白 2rem とし、1024px から隠す", () => {
    expect(mobileSource).toMatch(/\.mobile-toc-bar\s*\{[^}]*position:\s*sticky;[^}]*top:\s*0;[^}]*margin-bottom:\s*2rem;/s);
    expect(mobileSource).toMatch(/\.mobile-toc-toggle\s*\{[^}]*height:\s*2\.75rem;[^}]*padding:\s*0 1rem;/s);
    expect(mobileSource).toMatch(/@media \(min-width: 1024px\)\s*\{\s*\.mobile-toc-bar\s*\{\s*display:\s*none;/s);
  });

  it("H2〜H6 の scroll margin を 5rem にする", () => {
    expect(source).toMatch(/\.content-article :global\(:is\(h2, h3, h4, h5, h6\)\)\s*\{\s*scroll-margin-top:\s*5rem;/s);
  });

  it("tabs の後に現在位置とモバイルバーを同じ script で初期化する", () => {
    expect(source).toMatch(/<script>[^<]*initTabs\(\);\s*initTocActive\(\);\s*initMobileTocBar\(\);\s*<\/script>/);
    expect(source).not.toContain("content-toc-sync");
  });
});
