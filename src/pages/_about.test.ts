import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { Window, type Document } from "happy-dom";
import { beforeAll, describe, expect, it } from "vitest";
import About from "./about.astro";

describe("About page", () => {
  let document: Document;

  beforeAll(async () => {
    const container = await AstroContainer.create();
    const html = await container.renderToString(About);
    const window = new Window();
    document = new window.DOMParser().parseFromString(html, "text/html");
  });

  it("title と h1 を About にする", () => {
    expect(document.querySelector("title")?.textContent).toBe("About | Openise News");
    expect(document.querySelectorAll("h1")).toHaveLength(1);
    expect(document.querySelector("h1")?.textContent).toBe("About");
  });

  it("仕組み・ピックアップ・各セクションの見出しがある", () => {
    const headings = Array.from(document.querySelectorAll("h2, h3"), (h) => h.textContent);

    expect(headings).toEqual([
      "仕組み",
      "今日のピックアップ",
      "各セクション",
      "はてなブックマーク",
      "Zenn",
      "Qiita",
      "GitHub Trending",
      "Hacker News",
      "Reddit",
    ]);
  });

  it("各セクションの取得元へのリンクがある", () => {
    const hrefs = Array.from(document.querySelectorAll("a"), (a) => a.getAttribute("href"));

    expect(hrefs).toEqual(
      expect.arrayContaining([
        "https://b.hatena.ne.jp/entrylist/it/%E3%83%97%E3%83%AD%E3%82%B0%E3%83%A9%E3%83%9F%E3%83%B3%E3%82%B0",
        "https://zenn.dev/",
        "https://qiita.com/popular-items/feed.atom",
        "https://github.com/trending?since=daily",
        "https://hn.algolia.com/",
        "https://www.reddit.com/r/ClaudeCode/",
        "https://www.reddit.com/r/LocalLLaMA/",
        "https://www.reddit.com/r/ChatGPTCoding/",
      ]),
    );
  });
});
