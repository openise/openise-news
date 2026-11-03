import { experimental_AstroContainer as AstroContainer } from "astro/container";
import type { MarkdownHeading } from "astro";
import { describe, expect, it } from "vitest";
import TOC from "./TOC.astro";
import source from "./TOC.astro?raw";

const manyHeadings: MarkdownHeading[] = Array.from({ length: 9 }, (_, index) => ({
  depth: 2,
  slug: `heading-${index + 1}`,
  text: `見出し ${index + 1}`,
}));

async function render(headings: MarkdownHeading[], options: { showToggle?: boolean; collapse?: boolean } = {}) {
  const container = await AstroContainer.create();
  return container.renderToString(TOC, { props: { headings, ...options } });
}

describe("TOC", () => {
  it("H1 を除外し H2〜H6 のリンクを文書順に表示する", async () => {
    const html = await render([
      { depth: 1, slug: "h1", text: "タイトル" },
      { depth: 2, slug: "h2", text: "節" },
      { depth: 4, slug: "h4", text: "小節" },
      { depth: 3, slug: "h3", text: "補足" },
      { depth: 5, slug: "h5", text: "詳細" },
      { depth: 6, slug: "h6", text: "末端" },
    ]);

    expect(html).not.toContain('href="#h1"');
    expect(Array.from(html.matchAll(/href="#([^"]+)"/g), (match) => match[1])).toEqual([
      "h2", "h4", "h3", "h5", "h6",
    ]);
    expect(Array.from(html.matchAll(/--toc-indent:\s*(\d+)/g), (match) => match[1])).toEqual([
      "0", "2", "1", "3", "4",
    ]);
  });

  it("最小 depth が H3 の場合も先頭階層の字下げを 0 にする", async () => {
    const html = await render([
      { depth: 3, slug: "start", text: "開始" },
      { depth: 6, slug: "nested", text: "詳細" },
      { depth: 4, slug: "end", text: "補足" },
    ]);

    expect(Array.from(html.matchAll(/--toc-indent:\s*(\d+)/g), (match) => match[1])).toEqual([
      "0", "3", "1",
    ]);
  });

  it("8 件では全件を表示し残件ボタンを描画しない", async () => {
    const html = await render(manyHeadings.slice(0, 8));

    expect(html.match(/class="toc-link"/g)).toHaveLength(8);
    expect(html).not.toContain("toc-extra");
    expect(html).not.toContain("toc-expand-btn");
  });

  it("9 件では 8 件を表示し残る 1 件を展開対象にする", async () => {
    const html = await render(manyHeadings);
    const items = Array.from(html.matchAll(/<li\b[^>]*class="([^"]*toc-item[^"]*)"[^>]*>/g));

    expect(items.filter((match) => !match[1].includes("toc-extra"))).toHaveLength(8);
    expect(items.filter((match) => match[1].includes("toc-extra"))).toHaveLength(1);
    expect(html).toMatch(/<li\b[^>]*class="[^"]*toc-extra[^"]*hidden[^>]*>[\s\S]*?href="#heading-9"/);
    expect(html).toMatch(/<button\b[^>]*class="toc-expand-btn"[^>]*type="button"/);
    expect(html).toContain("+ 1 件");
  });

  it("collapse が false なら 9 件すべてを表示する", async () => {
    const html = await render(manyHeadings, { collapse: false });

    expect(html.match(/class="toc-link"/g)).toHaveLength(9);
    expect(html).not.toContain("toc-extra");
    expect(html).not.toContain("toc-expand-btn");
  });

  it("初期 details は開いた状態で summary を表示する", async () => {
    const html = await render(manyHeadings.slice(0, 1));

    expect(html).toMatch(/<details\b[^>]*\bopen(?:\s|>)/);
    expect(html).toMatch(/<summary\b[^>]*>/);
    expect(html).not.toMatch(/<summary\b[^>]*\bhidden(?:\s|>)/);
  });

  it("showToggle が false でも一覧を表示する", async () => {
    const html = await render(manyHeadings.slice(0, 1), { showToggle: false });

    expect(html).toMatch(/<summary\b[^>]*\bhidden(?:\s|>)/);
    expect(html).toMatch(/<details\b[^>]*\bopen(?:\s|>)/);
    expect(html).toContain('href="#heading-1"');
  });

  it.each([
    { name: "空配列", headings: [] },
    { name: "H1 のみ", headings: [{ depth: 1, slug: "title", text: "タイトル" }] },
  ])("$name の場合は nav を描画しない", async ({ headings }) => {
    expect(await render(headings)).not.toContain("<nav");
  });

  it("リンクに Daily の寸法と階層ごとの 1rem の字下げを適用する", () => {
    expect(source).toMatch(/\.toc-link\s*\{[^}]*padding:\s*0\.375rem 0\.25rem 0\.375rem 0\.625rem;/s);
    expect(source).toMatch(/\.toc-link\s*\{[^}]*font-size:\s*0\.8125rem;/s);
    expect(source).toMatch(/\.toc-link\s*\{[^}]*line-height:\s*1\.5;/s);
    expect(source).toMatch(/\.toc-link\s*\{[^}]*border-left:\s*2px solid transparent;/s);
    expect(source).toMatch(/padding-left:\s*calc\(var\(--toc-indent, 0\) \* 1rem\);/);
  });

  it("現在のリンクを Wiki の文字色と左罫線で示す", () => {
    expect(source).toMatch(/\.toc-link\[aria-current="location"\]\s*\{[^}]*color:\s*var\(--color-text\);[^}]*font-weight:\s*600;[^}]*border-left-color:\s*var\(--color-text\);/s);
    expect(source).not.toContain('aria-current="location"]::before');
  });
});
