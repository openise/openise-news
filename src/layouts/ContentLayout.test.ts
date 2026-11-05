import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { Window } from "happy-dom";
import { describe, expect, it } from "vitest";
import ContentLayout from "./ContentLayout.astro";
import source from "./ContentLayout.astro?raw";

async function render() {
  const container = await AstroContainer.create();
  const html = await container.renderToString(ContentLayout, {
    props: { title: "ページタイトル" },
    slots: { header: "<h1>ページタイトル</h1>", default: "<p>本文</p>" },
  });
  const window = new Window();
  return new window.DOMParser().parseFromString(html, "text/html");
}

describe("ContentLayout の構造", () => {
  it("記事の header の後に本文を置く", async () => {
    const document = await render();
    const header = document.querySelector(".content-article > .content-header");

    expect(header?.textContent).toBe("ページタイトル");
    expect(header?.nextElementSibling?.textContent).toBe("本文");
  });

  it("目次・ Mermaid ・タブに依存しない", async () => {
    const document = await render();

    expect(document.querySelector('nav[aria-label="目次"]')).toBeNull();
    expect(source).not.toMatch(/TOC|MobileTocBar|toc-active|mobile-toc-bar|mermaid|tabs/i);
  });
});

describe("ContentLayout の表の横スクロール", () => {
  it("should wrap tables with the client script", () => {
    expect(source).toMatch(
      /<script>\s*import \{ wrapTables \} from "\.\.\/scripts\/client\/table-scroll";\s*wrapTables\(\);\s*<\/script>/,
    );
  });
});

describe("ContentLayout の本文幅", () => {
  it(".content-article の最大幅を 50rem にする", () => {
    const rule = source.match(/\.content-article\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(rule).toMatch(/max-width:\s*50rem;/);
  });
});

describe("ContentLayout の本文の左端", () => {
  // コメント内の } でルール本体の抽出が途切れないよう、先にコメントを取り除く
  const css = source.replace(/\/\*[\s\S]*?\*\//g, "");
  const shell = css.match(/\.content-shell\s*\{([^}]*)\}/)?.[1] ?? "";

  it(".content-shell の幅を min(100% - 2rem, 1098px) にして中央に置き、本文の左端を daily に揃える", () => {
    expect(shell).toMatch(/width:\s*min\(100% - 2rem, 1098px\);/);
    expect(shell).toMatch(/margin-inline:\s*auto;/);
  });

  it(".content-article を外枠の中で中央に置く", () => {
    const article = css.match(/\.content-article\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(article).toMatch(/margin-inline:\s*auto;/);
  });

  it(".content-shell と .content-article の左に padding / margin を足さない", () => {
    for (const rule of css.matchAll(/\.content-(?:shell|article)\s*\{([^}]*)\}/g)) {
      expect(rule[1]).not.toMatch(/(?:padding|margin)-(?:left|inline-start)\s*:|(?:padding|margin)(?:-inline)?\s*:(?!\s*auto;)/);
    }
  });

  it("本文の左端について openise-daily と openise-theme の対応箇所を示す", () => {
    expect(source).toContain("daily: src/layouts/BaseLayout.astro の <main>");
    expect(source).toContain("theme: src/styles/global.css の .site-main");
  });
});
