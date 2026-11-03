import { describe, expect, it } from "vitest";
import source from "./[...page].astro?raw";

describe("News 一覧 page", () => {
  it("20 件 pagination と月別 group を使う", () => {
    expect(source).toContain("pageSize: PAGE_SIZE");
    expect(source).toContain("groupNewsByMonth(page.data)");
    expect(source).toContain("hrefForPage={routes.news}");
  });

  it("filter を追加しない", () => {
    expect(source).not.toContain("FilterPanel");
    expect(source).not.toContain("redirect");
  });

  it("月別 section 配下の News card title を h3 で描画する", () => {
    expect(source).toContain("headingLevel={3}");
  });
});
