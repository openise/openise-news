import { describe, expect, it } from "vitest";
import { formatDate, toISODate } from "./date";

describe("formatDate", () => {
  it("時刻が 0000 なら年月日と曜日だけを返す", () => {
    expect(formatDate("20260314000000")).toBe("2026年03月14日（土）");
  });

  it("時刻が 0000 以外なら HH:MM を後ろに付ける", () => {
    expect(formatDate("20260314093000")).toBe("2026年03月14日（土） 09:30");
  });

  it("月日は 0 埋めした 2 桁表記のままにする", () => {
    expect(formatDate("20260101000000")).toBe("2026年01月01日（木）");
  });

  it("実在しない日付は入力文字列をそのまま返す", () => {
    expect(formatDate("20260230000000")).toBe("20260230000000");
  });
});

describe("toISODate", () => {
  it("14 桁の日時を time 要素の datetime 用に変換する", () => {
    expect(toISODate("20260314000000")).toBe("2026-03-14");
  });
});
