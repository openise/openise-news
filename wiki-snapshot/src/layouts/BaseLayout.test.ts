import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { beforeAll, describe, expect, it } from "vitest";
import BaseLayout from "./BaseLayout.astro";

function extractThemeBootstrap(html: string): string {
  const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  if (!script) throw new Error("theme bootstrap script が見つかりません。");
  return script;
}

function executeThemeBootstrap(
  themeBootstrap: string,
  storage: { getItem: () => string | null },
  systemTheme: "light" | "dark",
): Record<string, string> {
  const documentElement = { dataset: {} as Record<string, string> };
  new Function("document", "localStorage", "window", themeBootstrap)(
    { documentElement },
    storage,
    { matchMedia: () => ({ matches: systemTheme === "dark" }) },
  );
  return documentElement.dataset;
}

describe("BaseLayout", () => {
  let themeBootstrap = "";

  beforeAll(async () => {
    const container = await AstroContainer.create();
    const html = await container.renderToString(BaseLayout, { props: { title: "テスト" } });
    themeBootstrap = extractThemeBootstrap(html);
  });

  it("localStorage が利用できなくても system theme を適用する", () => {
    const unavailableStorage = {
      getItem: () => {
        throw new Error("storage unavailable");
      },
    };

    let dataset: Record<string, string> = {};
    expect(() => {
      dataset = executeThemeBootstrap(themeBootstrap, unavailableStorage, "dark");
    }).not.toThrow();
    expect(dataset.theme).toBe("dark");
  });

  it("inline bootstrap に serialized function source を埋め込まない", () => {
    expect(themeBootstrap).not.toMatch(
      /var (?:isTheme|resolveTheme|resolveSystemTheme)\s*=\s*function/,
    );
  });

  it("保存済み theme を system theme より優先する", () => {
    const storage = { getItem: () => "light" };

    expect(executeThemeBootstrap(themeBootstrap, storage, "dark").theme).toBe("light");
  });
});
