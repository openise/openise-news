import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { describe, expect, it, vi } from "vitest";
import { getEntry, render } from "astro:content";
import NewsDetail from "./[id].astro";
import source from "./[id].astro?raw";

vi.mock("astro:content", () => ({
  getCollection: vi.fn(async () => []),
  getEntry: vi.fn(async () => undefined),
  render: vi.fn(),
}));

describe("News 詳細 page", () => {
  it("ContentLayout に title だけを渡し、 description は BaseLayout の既定を使う", () => {
    expect(source).toContain("<ContentLayout title={item.data.title}>");
    expect(source).not.toContain("description");
  });

  it("backlink・関連 commit・前後 navigation を追加しない", () => {
    expect(source).not.toMatch(/Backlinks|RelatedCommits|prev|next/);
    expect(source).not.toContain("redirect");
  });
});


it("エントリが欠落した詳細ページは本文を描画せず 404 を返す", async () => {
  const container = await AstroContainer.create();
  const response = await container.renderToResponse(NewsDetail, {
    params: { id: "missing" },
    request: new Request("https://news.openise.jp/news/missing/"),
  });

  expect(getEntry).toHaveBeenCalledWith("news", "missing");
  expect(response.status).toBe(404);
  expect(await response.text()).toBe("");
  expect(render).not.toHaveBeenCalled();
});
