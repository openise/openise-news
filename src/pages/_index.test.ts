import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { createComponent, render } from "astro/runtime/server/index.js";
import { Window } from "happy-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";
import Homepage from "./index.astro";

const collections = vi.hoisted(() => ({
  news: [
    { id: "20261010", data: { title: "古い News", createdDate: "20261010120000" } },
    { id: "20261011", data: { title: "最新 News のタイトル", createdDate: "20261011120000" } },
  ],
}));

vi.mock("astro:content", () => ({
  getCollection: vi.fn(async (collection: keyof typeof collections) => collections[collection]),
  render: vi.fn(async (entry: { id: string }) => ({
    Content: createComponent(() => render`<p class="news-body">${entry.id} の本文</p>`),
  })),
}));

async function renderHomepage(): Promise<Document> {
  const container = await AstroContainer.create();
  const html = await container.renderToString(Homepage);
  const window = new Window();
  return new window.DOMParser().parseFromString(html, "text/html") as unknown as Document;
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

  it("最新 News のタイトルを h1 として 1 つだけ描画する", () => {
    expect(document.querySelectorAll("h1")).toHaveLength(1);
    expect(document.querySelector("h1")?.textContent).toBe("最新 News のタイトル");
  });

  it("最新 News の日付を描画する", () => {
    const time = document.querySelector(".content-header time");

    expect(time?.getAttribute("datetime")).toBe("2026-10-11");
    expect(time?.textContent).toContain("（日）");
  });

  it("最新 News の本文を描画する", () => {
    expect(document.querySelectorAll(".news-body")).toHaveLength(1);
    expect(document.querySelector(".content-article .news-body")?.textContent).toBe("20261011 の本文");
  });

  it("title はサイト名のままにする", () => {
    expect(document.querySelector("title")?.textContent).toBe("Openise News");
  });

  it("最新 News へのボタンを描画しない", () => {
    expect(document.querySelectorAll(".latest-news-button")).toHaveLength(0);
  });

  it("News の一覧へのリンクを描画する", () => {
    expect(document.querySelector(".news-list-link")?.getAttribute("href")).toBe("/news/");
  });

  it("News が空の場合はサイト名を h1 にし、一覧へのリンクを残す", async () => {
    const emptyDocument = await renderHomepageWithNews([]);

    expect(emptyDocument.querySelectorAll("h1")).toHaveLength(1);
    expect(emptyDocument.querySelector("h1")?.textContent).toBe("Openise News");
    expect(emptyDocument.querySelector(".news-body")).toBeNull();
    expect(emptyDocument.querySelector(".news-list-link")?.getAttribute("href")).toBe("/news/");
  });
});
