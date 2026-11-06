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
  const documentElement: { dataset: Record<string, string> } = { dataset: {} };
  new Function("document", "localStorage", "window", themeBootstrap)(
    { documentElement },
    storage,
    { matchMedia: () => ({ matches: systemTheme === "dark" }) },
  );
  return documentElement.dataset;
}

describe("BaseLayout", () => {
  let html = "";
  let themeBootstrap = "";

  beforeAll(async () => {
    const container = await AstroContainer.create();
    html = await container.renderToString(BaseLayout, { props: { title: "テスト" } });
    themeBootstrap = extractThemeBootstrap(html);
  });

  it("viewport の meta で初期倍率を 1 にする", () => {
    expect(html).toContain('<meta name="viewport" content="width=device-width, initial-scale=1">');
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

describe("BaseLayout の head", () => {
  async function renderHead(props: { title?: string; canonical?: boolean }, pathname: string): Promise<string> {
    const container = await AstroContainer.create({ astroConfig: { site: "https://news.openise.jp" } });
    return container.renderToString(BaseLayout, {
      props,
      request: new Request(`https://news.openise.jp${pathname}`),
    });
  }

  it("title を省略するとサイト名だけにする", async () => {
    const html = await renderHead({}, "/");

    expect(html).toContain("<title>Openise News</title>");
  });

  it("title を渡すと「| Openise News」を付ける", async () => {
    const html = await renderHead({ title: "News" }, "/news/");

    expect(html).toContain("<title>News | Openise News</title>");
  });

  it("そのページの URL を指す canonical を 1 つ出力する", async () => {
    const html = await renderHead({ title: "News" }, "/news/");
    const canonicals = [...html.matchAll(/<link rel="canonical" href="([^"]*)"/g)];

    expect(canonicals).toHaveLength(1);
    expect(canonicals[0][1]).toBe("https://news.openise.jp/news/");
    expect(html).not.toContain('name="robots"');
  });

  it("canonical={false} なら canonical を出さず noindex を出力する", async () => {
    const html = await renderHead({ title: "ページが見つかりません", canonical: false }, "/404");

    expect(html).not.toContain('rel="canonical"');
    expect(html).toContain('<meta name="robots" content="noindex">');
  });
});
