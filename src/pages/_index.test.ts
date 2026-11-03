import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { Window } from "happy-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";
import Homepage from "./index.astro";
import source from "./index.astro?raw";

const collections = vi.hoisted(() => ({
  news: [
    { id: "20261010", data: { title: "古い News", createdDate: "20261010120000" } },
    { id: "20261011", data: { title: "固定 News", createdDate: "20261011120000" } },
  ],
}));

vi.mock("astro:content", () => ({
  getCollection: vi.fn(async (collection: keyof typeof collections) => collections[collection]),
}));

async function renderHomepage(): Promise<Document> {
  const container = await AstroContainer.create();
  const document = new Window().document;
  document.body.innerHTML = await container.renderToString(Homepage);
  return document as unknown as Document;
}

async function renderHomepageWithNews(news: typeof collections.news): Promise<Document> {
  const originalNews = collections.news;
  collections.news = news;
  try {
    return await renderHomepage();
  } finally {
    collections.news = originalNews;
  }
}

describe("Homepage", () => {
  let document: Document;

  beforeAll(async () => {
    document = await renderHomepage();
  });

  it("h1 を 1 つだけ描画する", () => {
    expect(document.querySelectorAll("h1")).toHaveLength(1);
    expect(document.querySelector("h1")?.textContent).toBe("Openise News");
  });

  it("最新 News へのボタンを 1 つだけ描画する", () => {
    const button = document.querySelector(".latest-news-button");
    const time = button?.querySelector("time");

    expect(document.querySelectorAll(".latest-news-button")).toHaveLength(1);
    expect(button?.getAttribute("href")).toBe("/news/20261011/");
    expect(button?.querySelector(".latest-news-label")?.textContent).toBe("最新 News");
    expect(time?.getAttribute("datetime")).toBe("2026-10-11");
    expect(time?.textContent).toContain("（日）");
  });

  it("News の一覧へのリンクを描画する", () => {
    expect(document.querySelector(".news-list-link")?.getAttribute("href")).toBe("/news/");
  });

  it("News が空の場合はボタンを描画せず、一覧へのリンクは残す", async () => {
    const emptyDocument = await renderHomepageWithNews([]);

    expect(emptyDocument.querySelectorAll(".latest-news-button")).toHaveLength(0);
    expect(emptyDocument.querySelector(".news-list-link")?.getAttribute("href")).toBe("/news/");
  });

  it("ボタンを全幅 ・ 1 行に保つ", () => {
    expect(source).toMatch(/\.latest-news-button\s*\{[^}]*width: 100%;[^}]*min-width: 0;[^}]*white-space: nowrap;/s);
  });

  it("青いボタンにし、ホバーとキーボードフォーカスで濃い青にする", () => {
    expect(source).toMatch(/\.latest-news-button\s*\{[^}]*background: var\(--color-button-bg\);[^}]*color: var\(--color-button-text\);/s);
    expect(source).toMatch(/\.latest-news-button:hover,\s*\.latest-news-button:focus-visible\s*\{[^}]*background: var\(--color-button-bg-hover\);/s);
    expect(source).toMatch(/\.latest-news-button:focus-visible\s*\{[^}]*outline: 2px solid var\(--color-accent\);/s);
  });
});
