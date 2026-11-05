import { describe, expect, it } from "vitest";
import { routes } from "./routes";

describe("routes", () => {
  it("トップの route はサイトルートを返す", () => {
    expect(routes.home()).toBe("/");
  });

  it("News 一覧と詳細 route を trailing slash 付きで生成する", () => {
    expect(routes.news()).toBe("/news/");
    expect(routes.news(1)).toBe("/news/");
    expect(routes.news(2)).toBe("/news/2/");
    expect(routes.newsItem("20260828")).toBe("/news/20260828/");
  });

  it("About の route を trailing slash 付きで生成する", () => {
    expect(routes.about()).toBe("/about/");
  });
});
