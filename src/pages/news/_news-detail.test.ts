import { describe, expect, it } from "vitest";
import source from "./[id].astro?raw";

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
