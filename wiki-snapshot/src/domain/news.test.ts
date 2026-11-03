import { describe, expect, it } from "vitest";
import { groupNewsByMonth, latestNews, sortNewsByCreatedDate } from "./news";

const item = (id: string, createdDate: string) => ({ id, data: { createdDate } });

describe("News 一覧 data", () => {
  it("createdDate が最も新しい 1 件を返す", () => {
    const result = latestNews([
      item("20260827", "20260827110000"),
      item("20260828a", "20260828090000"),
      item("20260828b", "20260828110000"),
    ]);

    expect(result?.id).toBe("20260828b");
  });

  it("空配列では undefined を返す", () => {
    expect(latestNews([])).toBeUndefined();
  });

  it("createdDate の降順へ並べる", () => {
    const result = sortNewsByCreatedDate([
      item("20260827", "20260827110000"),
      item("20260828", "20260828110000"),
    ]);

    expect(result.map((entry) => entry.id)).toEqual(["20260828", "20260827"]);
  });

  it("入力順を保って月別にグループ化する", () => {
    const result = groupNewsByMonth([
      item("20260828", "20260828110000"),
      item("20260827", "20260827110000"),
      item("20260731", "20260731110000"),
    ]);

    expect(result.map((group) => [
      group.month,
      group.label,
      group.items.map((entry) => entry.id),
    ])).toEqual([
      ["202608", "2026年08月", ["20260828", "20260827"]],
      ["202607", "2026年07月", ["20260731"]],
    ]);
  });

  it("月別にグループ化しても入力配列を変更しない", () => {
    const items = [
      item("20260828", "20260828110000"),
      item("20260731", "20260731110000"),
    ];
    const originalItems = [...items];

    groupNewsByMonth(items);

    expect(items).toEqual(originalItems);
  });
});
