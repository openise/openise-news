import { describe, expect, it } from "vitest";
import { routes } from "./routes";

describe("routes", () => {
  it("すべての route に base path と trailing slash を付ける", () => {
    expect(routes.home()).toBe("/openise-wiki/");
    expect(routes.wikiPage("concepts/astro")).toBe(
      "/openise-wiki/wiki/concepts/astro/",
    );
    expect(routes.source("openise-daily/docs/0082/index")).toBe(
      "/openise-wiki/sources/openise-daily/docs/0082/index/",
    );
  });

  it("dotted source file name を route に保持する", () => {
    expect(routes.source("openise-daily/astro.config.mjs")).toBe(
      "/openise-wiki/sources/openise-daily/astro.config.mjs/",
    );
  });

  it("WikiTypeDirectory を受け取り type 別一覧 route を生成する", () => {
    expect(routes.wikiType("concepts")).toBe("/openise-wiki/wiki/concepts/");
  });

  it("残りの route builder が期待する path を生成する", () => {
    expect(routes.wiki()).toBe("/openise-wiki/wiki/");
    expect(routes.clip("openai-intro")).toBe(
      "/openise-wiki/clips/openai-intro/",
    );
    expect(routes.tags()).toBe("/openise-wiki/tags/");
    expect(routes.tag("Astro & CSS")).toBe(
      "/openise-wiki/tags/Astro%20%26%20CSS/",
    );
    expect(routes.graph()).toBe("/openise-wiki/wiki/graph/");
    expect(routes.log()).toBe("/openise-wiki/wiki/log/");
    expect(routes.schema()).toBe("/openise-wiki/wiki/schema/");
  });

  it("favicon path に base path を付ける", () => {
    expect(routes.favicon()).toBe("/openise-wiki/favicon.svg");
  });

  it("wikiType は page 引数で 2 ページ目以降の route を生成し、1 ページ目は省略する", () => {
    expect(routes.wikiType("concepts", 2)).toBe("/openise-wiki/wiki/concepts/2/");
    expect(routes.wikiType("concepts", 1)).toBe("/openise-wiki/wiki/concepts/");
  });

  it("clips は base path と trailing slash 付きの route を生成する", () => {
    expect(routes.clips()).toBe("/openise-wiki/clips/");
  });

  it("News 一覧と詳細 route を生成する", () => {
    expect(routes.news()).toBe("/openise-wiki/news/");
    expect(routes.news(1)).toBe("/openise-wiki/news/");
    expect(routes.news(2)).toBe("/openise-wiki/news/2/");
    expect(routes.newsItem("20260828")).toBe("/openise-wiki/news/20260828/");
  });

  it("tagWiki は page 引数付きの route を生成し、tagClips は単一 route を生成する", () => {
    expect(routes.tagWiki("astro")).toBe("/openise-wiki/tags/astro/wiki/");
    expect(routes.tagWiki("astro", 2)).toBe("/openise-wiki/tags/astro/wiki/2/");
    expect(routes.tagClips("astro")).toBe("/openise-wiki/tags/astro/clips/");
  });
});
