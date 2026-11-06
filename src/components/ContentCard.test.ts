import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { Window } from "happy-dom";
import { beforeAll, describe, expect, it } from "vitest";
import ContentCard from "./ContentCard.astro";
import source from "./ContentCard.astro?raw";

const props = {
  title: "固定 News",
  href: "/news/20261011/",
};

describe("ContentCard", () => {
  let html = "";

  beforeAll(async () => {
    const container = await AstroContainer.create();
    html = await container.renderToString(ContentCard, { props });
  });

  it("title だけを表示し、日時と description は表示しない", () => {
    expect(html).toContain(">固定 News</span></h3>");
    expect(html).not.toContain("<time");
    expect(html).not.toContain("content-card-description");
  });

  it.each([2, 3, 4, 5, 6])("heading level %i を prop で指定した見出しを描画する", async (headingLevel) => {
    const container = await AstroContainer.create();
    const headingHtml = await container.renderToString(ContentCard, {
      props: { ...props, headingLevel },
    });

    expect(headingHtml).toMatch(new RegExp(`<h${headingLevel}[^>]*><span[^>]*>固定 News</span></h${headingLevel}>`));
  });

  it("heading level を指定しない場合は h3 を描画する", () => {
    expect(html).toMatch(/<h3[^>]*><span[^>]*>固定 News<\/span><\/h3>/);
  });

  it("カードのタイトルは収まらない語を途中で折り返し、一覧を横に広げない", () => {
    const rule = source.match(/\.content-card-title-text\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(rule).toMatch(/overflow-wrap:\s*anywhere;/);
  });

  it("リンク名はタイトルのみにする", async () => {
    const doc = new Window().document;
    doc.body.innerHTML = html;
    const link = doc.querySelector("a");
    if (!link) throw new Error("ContentCard のリンクが見つかりません");
    const labelledBy = link.getAttribute("aria-labelledby");
    if (!labelledBy) throw new Error("ContentCard のリンクに aria-labelledby がありません");

    expect(link.getAttribute("href")).toBe("/news/20261011/");
    expect(doc.getElementById(labelledBy)?.textContent).toBe("固定 News");
  });

  it("同じ href の card でも id が一意になる", async () => {
    const container = await AstroContainer.create();
    const doc = new Window().document;
    doc.body.innerHTML =
      (await container.renderToString(ContentCard, { props })) +
      (await container.renderToString(ContentCard, { props }));
    const ids = [...doc.querySelectorAll("[id]")].map((element) => element.id);

    expect(ids.length).toBeGreaterThan(0);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
