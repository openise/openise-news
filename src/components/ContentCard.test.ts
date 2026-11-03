import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { Window } from "happy-dom";
import { beforeAll, describe, expect, it } from "vitest";
import ContentCard from "./ContentCard.astro";
import source from "./ContentCard.astro?raw";

const props = {
  title: "固定 News",
  href: "/news/20261011/",
  createdDate: "20261011120000",
  description: "固定 News の説明",
};

describe("ContentCard", () => {
  let html = "";

  beforeAll(async () => {
    const container = await AstroContainer.create();
    html = await container.renderToString(ContentCard, { props });
  });

  it("作成日時、title、description を指定順で表示する", () => {
    const dateIndex = html.indexOf("2026年10月11日（日） 12:00");
    const titleIndex = html.indexOf(">固定 News</span></h3>");
    const descriptionIndex = html.indexOf("固定 News の説明");

    expect(html).toMatch(/<time datetime="2026-10-11"[^>]*>2026年10月11日（日） 12:00<\/time>/);
    expect(dateIndex).toBeGreaterThanOrEqual(0);
    expect(titleIndex).toBeGreaterThan(dateIndex);
    expect(descriptionIndex).toBeGreaterThan(titleIndex);
  });

  it("heading level を prop で指定した見出しを描画する", async () => {
    const container = await AstroContainer.create();
    const headingHtml = await container.renderToString(ContentCard, {
      props: { ...props, headingLevel: 4 },
    });

    expect(headingHtml).toMatch(/<h4[^>]*><span[^>]*>固定 News<\/span><\/h4>/);
  });

  it("heading level を指定しない場合は h3 を描画する", () => {
    expect(html).toMatch(/<h3[^>]*><span[^>]*>固定 News<\/span><\/h3>/);
  });

  it("description を 2 行で切り詰める", () => {
    expect(html).toMatch(/<p[^>]*class="content-card-description"[^>]*>/);
    expect(source).toMatch(
      /\.content-card-description\s*\{\s*display: -webkit-box;\s*overflow: hidden;\s*-webkit-box-orient: vertical;\s*-webkit-line-clamp: 2;/s,
    );
  });

  it("カードのタイトルは収まらない語を途中で折り返し、一覧を横に広げない", () => {
    const rule = source.match(/\.content-card-title-text\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(rule).toMatch(/overflow-wrap:\s*anywhere;/);
  });

  it("リンク名はタイトルのみ、補足は日付と説明を参照する", async () => {
    const doc = new Window().document;
    doc.body.innerHTML = html;
    const link = doc.querySelector("a")!;

    expect(link.getAttribute("href")).toBe("/news/20261011/");
    expect(doc.getElementById(link.getAttribute("aria-labelledby")!)?.textContent).toBe("固定 News");
    const refs = link.getAttribute("aria-describedby")!.split(" ");
    expect(refs.map((id) => doc.getElementById(id)?.textContent?.trim())).toEqual([
      "2026年10月11日（日） 12:00",
      "固定 News の説明",
    ]);
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
