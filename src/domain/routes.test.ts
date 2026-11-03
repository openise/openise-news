import { describe, expect, it } from "vitest";
import { routes } from "./routes";

describe("routes", () => {
  it("トップと News 一覧の route を trailing slash 付きで生成する", () => {
    expect(routes.home()).toBe("/");
    expect(routes.news()).toBe("/news/");
  });
});
