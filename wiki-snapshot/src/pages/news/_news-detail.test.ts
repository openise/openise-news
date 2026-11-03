import { describe, expect, it } from "vitest";
import source from "./[id].astro?raw";

describe("News 詳細 page", () => {
  it("ContentLayout に title・description・TOC を渡す", () => {
    expect(source).toContain("title={item.data.title}");
    expect(source).toContain("description={item.data.description}");
    expect(source).toContain("headings={headings}");
  });

  it("backlink・関連 commit・前後 navigation を追加しない", () => {
    expect(source).not.toMatch(/Backlinks|RelatedCommits|prev|next/);
    expect(source).not.toContain("redirect");
  });
});
