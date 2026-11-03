import { describe, expect, it } from "vitest";
import { buildPageNumbers } from "./pagination";

describe("buildPageNumbers", () => {
  it("lastPage が 1 のとき 1 ページ目だけを返す", () => {
    expect(buildPageNumbers(1, 1)).toEqual([1]);
  });

  it("総ページ数が表示対象数（5）以下なら省略記号なしで全ページを返す", () => {
    expect(buildPageNumbers(1, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(buildPageNumbers(3, 3)).toEqual([1, 2, 3]);
  });

  it("先頭・末尾・現在ページの前後1ページの間に空きがあれば ellipsis を挟む", () => {
    expect(buildPageNumbers(5, 10)).toEqual([1, "ellipsis", 4, 5, 6, "ellipsis", 10]);
  });

  it("現在ページが先頭付近なら前方の候補が連続し ellipsis は後方だけになる", () => {
    expect(buildPageNumbers(1, 10)).toEqual([1, 2, "ellipsis", 10]);
    expect(buildPageNumbers(2, 10)).toEqual([1, 2, 3, "ellipsis", 10]);
  });

  it("lastPage が 6 で先頭ページなら末尾の前に ellipsis を挟む", () => {
    expect(buildPageNumbers(1, 6)).toEqual([1, 2, "ellipsis", 6]);
  });

  it("現在ページが末尾付近なら後方の候補が連続し ellipsis は前方だけになる", () => {
    expect(buildPageNumbers(10, 10)).toEqual([1, "ellipsis", 9, 10]);
    expect(buildPageNumbers(9, 10)).toEqual([1, "ellipsis", 8, 9, 10]);
  });
});
