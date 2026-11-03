import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { Window } from "happy-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";
import Homepage from "./index.astro";
import source from "./index.astro?raw";

const collections = vi.hoisted(() => ({
  wiki: Array.from({ length: 10 }, (_, index) => ({
    id: `concepts/fixed-wiki-${index + 1}`,
    data: {
      title: `固定 Wiki ${index + 1}`,
      description: `Wiki の説明 ${index + 1}`,
      createdDate: `202610${String(10 - index).padStart(2, "0")}120000`,
      tags: [],
      type: "concept",
    },
  })),
  clips: Array.from({ length: 10 }, (_, index) => ({
    id: `90${String(index + 1).padStart(2, "0")}`,
    data: {
      title: `固定 Clip ${index + 1}`,
      description: `Clip の説明 ${index + 1}`,
      createdDate: `202610${String(10 - index).padStart(2, "0")}120000`,
      tags: [],
      pinned: false,
    },
  })),
  news: [
    {
      id: "20261011",
      data: {
        title: "固定 News",
        createdDate: "20261011120000",
        description: "固定 News の説明",
      },
    },
  ],
}));

vi.mock("astro:content", () => ({
  getCollection: vi.fn(async (collection: keyof typeof collections) => collections[collection]),
}));

async function renderHomepage(): Promise<string> {
  const container = await AstroContainer.create();
  return container.renderToString(Homepage);
}

async function renderHomepageWithNews(news: typeof collections.news): Promise<string> {
  const originalNews = collections.news;
  collections.news = news;

  try {
    return await renderHomepage();
  } finally {
    collections.news = originalNews;
  }
}

function documentFromHtml(html: string): Document {
  const document = new Window().document;
  document.body.innerHTML = html;
  return document as unknown as Document;
}

describe("Homepage", () => {
  let html = "";

  beforeAll(async () => {
    html = await renderHomepage();
  });

  it("dashboard に h1 を 1 つだけ描画する", () => {
    expect(html.match(/<h1\b/g) ?? []).toHaveLength(1);
    expect(html).toMatch(/<h1[^>]*class="sr-only"[^>]*>Openise Wiki<\/h1>/);
  });

  it("dashboard の card title を section heading より下位に描画する", () => {
    const wikiSection = html.match(/<section[^>]*aria-labelledby="latest-wiki-title"[^>]*>([\s\S]*?)<\/section>/)?.[1] ?? "";
    const headings = [...wikiSection.matchAll(/<h([1-6])\b/g)].map((match) => Number(match[1]));

    expect(headings[0]).toBe(2);
    expect(headings.slice(1)).toEqual(Array(10).fill(3));
    expect(source.match(/headingLevel=\{3\}/g) ?? []).toHaveLength(2);
  });

  it("最新 Wiki と最新 Clips を各 10 件まで描画し、一覧 link を解決する", () => {
    const wikiSection = html.match(/<section[^>]*aria-labelledby="latest-wiki-title"[^>]*>([\s\S]*?)<\/section>/)?.[1] ?? "";
    const clipSection = html.match(/<section[^>]*aria-labelledby="latest-clips-title"[^>]*>([\s\S]*?)<\/section>/)?.[1] ?? "";

    expect(html).toMatch(/<h2[^>]*id="latest-wiki-title"[^>]*>最新 Wiki<\/h2>/);
    expect(html).toMatch(/<h2[^>]*id="latest-clips-title"[^>]*>最新 Clips<\/h2>/);
    expect(html).toContain('href="/openise-wiki/wiki/syntheses/"');
    expect(html).toContain('href="/openise-wiki/clips/"');
    expect(wikiSection.match(/class="content-card-link"/g)).toHaveLength(10);
    expect(clipSection.match(/class="content-card-link"/g)).toHaveLength(10);
  });

  it("wide viewport で 2 column、狭い viewport で 1 column にする", () => {
    expect(source).toMatch(/\.dashboard-grid\s*\{\s*display: grid;\s*gap: 2rem;\s*\}/s);
    expect(source).toMatch(
      /@media \(min-width: 40rem\)[\s\S]*?\.dashboard-grid\s*\{\s*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\);\s*\}/s,
    );
    expect(source).toMatch(/\.section-heading\s*\{[\s\S]*flex-wrap: wrap;/);
  });

  it("Clip card に作成日時と optional な更新日時を渡す", () => {
    expect(source).toContain("createdDate={item.data.createdDate}");
    expect(source).toContain("updatedDate={item.data.updatedDate}");
    expect(source).toContain("showDateLabels");
  });

  it("最新 News へのボタンを dashboard の先頭に 1 つだけ描画する", () => {
    const document = documentFromHtml(html);
    const button = document.querySelector(".latest-news-button");
    const time = button?.querySelector("time");

    expect(document.querySelectorAll(".latest-news-button")).toHaveLength(1);
    expect(button?.getAttribute("href")).toBe("/openise-wiki/news/20261011/");
    expect(button?.querySelector(".latest-news-label")?.textContent).toBe("最新 News");
    expect(time?.getAttribute("datetime")).toBe("2026-10-11");
    expect(time?.textContent).toContain("（日）");
    expect(html.indexOf('class="latest-news-button"')).toBeLessThan(html.indexOf('aria-labelledby="latest-wiki-title"'));
  });

  it("News が空の場合は button を描画しない", async () => {
    const document = documentFromHtml(await renderHomepageWithNews([]));

    expect(document.querySelectorAll(".latest-news-button")).toHaveLength(0);
  });

  it("News fixture を切り替えた後も他 collection の描画を維持する", async () => {
    const emptyNewsDocument = documentFromHtml(await renderHomepageWithNews([]));
    const fixedNewsDocument = documentFromHtml(await renderHomepage());

    expect(emptyNewsDocument.querySelectorAll(".latest-news-button")).toHaveLength(0);
    expect(emptyNewsDocument.querySelectorAll(".content-card-link")).toHaveLength(20);
    expect(fixedNewsDocument.querySelectorAll(".latest-news-button")).toHaveLength(1);
    expect(fixedNewsDocument.querySelector(".latest-news-button")?.getAttribute("href")).toBe(
      "/openise-wiki/news/20261011/",
    );
    expect(fixedNewsDocument.querySelectorAll(".content-card-link")).toHaveLength(20);
  });

  it("ボタンを全幅 ・ 1 行に保つ", () => {
    expect(source).toMatch(/\.latest-news-button\s*\{[^}]*grid-column: 1 \/ -1;[^}]*white-space: nowrap;/s);
    expect(source).toMatch(/\.latest-news-button\s*\{[^}]*width: 100%;[^}]*min-width: 0;/s);
  });

  it("青いボタンにし、ホバーとキーボードフォーカスで濃い青にする", () => {
    expect(source).toMatch(/\.latest-news-button\s*\{[^}]*background: var\(--color-clip-btn-bg\);[^}]*color: var\(--color-clip-btn-text\);/s);
    expect(source).toMatch(/\.latest-news-button:hover,\s*\.latest-news-button:focus-visible\s*\{[^}]*background: var\(--color-clip-btn-bg-hover\);/s);
    expect(source).toMatch(/\.latest-news-button:focus-visible\s*\{[^}]*outline: 2px solid var\(--color-accent\);/s);
  });

  it("News の一覧 section と card はホームに追加しない", () => {
    expect(html).not.toMatch(/aria-labelledby="latest-news-title"/);
    expect(html.match(/href="\/openise-wiki\/news\/\d{8}\/"/g)).toHaveLength(1);
  });
});
