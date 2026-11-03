import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { Window } from "happy-dom";
import { beforeAll, describe, expect, it } from "vitest";
import ContentCard from "./ContentCard.astro";
import source from "./ContentCard.astro?raw";

describe("ContentCard", () => {
  let html = "";

  beforeAll(async () => {
    const container = await AstroContainer.create();
    html = await container.renderToString(ContentCard, {
      props: {
        title: "Claude Code Best Practices",
        href: "/openise-wiki/wiki/syntheses/claude-code-best-practices/",
        createdDate: "20260726085316",
        description:
          "Claude Code を効果的に運用するためのベストプラクティス集。セッション管理・コンテキスト管理をカバーする。",
        tags: ["claude-code", "best-practices"],
      },
    });
  });

  it("作成日時、title、description、tag を指定順で表示する", () => {
    const dateIndex = html.indexOf("2026年07月26日（日） 08:53");
    const titleIndex = html.indexOf(">Claude Code Best Practices</span></h3>");
    const descriptionIndex = html.indexOf(
      "Claude Code を効果的に運用するためのベストプラクティス集。",
    );
    const tagIndex = html.indexOf("#claude-code");

    expect(html).toMatch(
      /<time datetime="2026-07-26"[^>]*>2026年07月26日（日） 08:53<\/time>/,
    );
    expect(dateIndex).toBeGreaterThanOrEqual(0);
    expect(titleIndex).toBeGreaterThan(dateIndex);
    expect(descriptionIndex).toBeGreaterThan(titleIndex);
    expect(tagIndex).toBeGreaterThan(descriptionIndex);
    expect(html).toContain("#best-practices");
  });

  it("pinned のとき title の先頭に pin を表示する", async () => {
    const container = await AstroContainer.create();
    const pinnedHtml = await container.renderToString(ContentCard, {
      props: {
        title: "Pinned Clip",
        href: "/openise-wiki/clips/0001/",
        createdDate: "20260813120000",
        description: "説明",
        pinned: true,
      },
    });

    expect(pinnedHtml).toMatch(
      /<h3[^>]*>\s*<span[^>]*><span[^>]*aria-hidden="true"[^>]*>📌<\/span><span[^>]*>ピン留め<\/span><\/span>\s*<span[^>]*>Pinned Clip<\/span><\/h3>/,
    );
  });

  it("heading level を prop で指定した見出しを描画する", async () => {
    const container = await AstroContainer.create();
    const headingHtml = await container.renderToString(ContentCard, {
      props: {
        title: "Heading level 4",
        href: "/openise-wiki/wiki/syntheses/heading-level-4/",
        createdDate: "20260813120000",
        description: "説明",
        headingLevel: 4,
      },
    });

    expect(headingHtml).toMatch(/<h4[^>]*><span[^>]*>Heading level 4<\/span><\/h4>/);
  });

  it("heading level を指定しない場合は h3 を描画する", () => {
    expect(html).toMatch(/<h3[^>]*><span[^>]*>Claude Code Best Practices<\/span><\/h3>/);
  });

  it("renders the description with the dedicated clamp class", () => {
    expect(html).toMatch(/<p[^>]*class="content-card-description"[^>]*>/);
  });

  it("declares a two-line clamp for the description class", () => {
    expect(source).toMatch(
      /\.content-card-description\s*\{\s*display: -webkit-box;\s*overflow: hidden;\s*-webkit-box-orient: vertical;\s*-webkit-line-clamp: 2;/s,
    );
  });

  it("カードのタイトルは収まらない語を途中で折り返し、一覧を横に広げない", () => {
    const rule = source.match(/\.content-card-title-text\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(rule).toMatch(/overflow-wrap:\s*anywhere;/);
  });

  it("Clip は作成日時と更新日時を label 付きで表示する", async () => {
    const container = await AstroContainer.create();
    const clipHtml = await container.renderToString(ContentCard, {
      props: {
        title: "Updated Clip",
        href: "/openise-wiki/clips/0001/",
        createdDate: "20260813120000",
        updatedDate: "20260814230000",
        description: "説明",
        showDateLabels: true,
      },
    });

    expect(clipHtml).toMatch(/作成:\s*<time[^>]*>2026年08月13日（木） 12:00<\/time>/);
    expect(clipHtml).toMatch(/更新:\s*<time[^>]*>2026年08月14日（金） 23:00<\/time>/);
  });

  it("未更新の Clip は作成日時だけを表示する", async () => {
    const container = await AstroContainer.create();
    const clipHtml = await container.renderToString(ContentCard, {
      props: {
        title: "Created Clip",
        href: "/openise-wiki/clips/0002/",
        createdDate: "20260813120000",
        description: "説明",
        showDateLabels: true,
      },
    });

    expect(clipHtml).toContain("作成:");
    expect(clipHtml).not.toContain("更新:");
  });
  it("リンク名はタイトルのみ、補足は日付・説明・ tag ・ピン留めを参照する", async () => {
    const container = await AstroContainer.create();
    const props = {
      title: "Pinned Clip", href: "/openise-wiki/clips/0001/",
      createdDate: "20260813120000", description: "説明", tags: ["astro"], pinned: true,
    };
    const doc = new Window().document;
    doc.body.innerHTML = await container.renderToString(ContentCard, { props });
    const link = doc.querySelector("a")!;
    expect(link.hasAttribute("aria-label")).toBe(false);
    expect(doc.getElementById(link.getAttribute("aria-labelledby")!)?.textContent).toBe("Pinned Clip");
    const refs = link.getAttribute("aria-describedby")!.split(" ");
    expect(refs.map((id) => doc.getElementById(id)?.textContent?.trim())).toEqual([
      "2026年08月13日（木） 12:00", "説明", "#astro", "ピン留め",
    ]);
    expect(link.querySelector(".content-card-pin [aria-hidden='true']")?.textContent).toBe("📌");
    expect(link.querySelector(".content-card-pin .sr-only")?.textContent).toBe("ピン留め");
  });

  it("同じ href の card でも id が一意で、tag 無しの参照も有効になる", async () => {
    const container = await AstroContainer.create();
    const props = {
      title: "同じタイトル", href: "/openise-wiki/clips/0001/",
      createdDate: "20260813120000", description: "説明",
    };
    const doc = new Window().document;
    doc.body.innerHTML = await container.renderToString(ContentCard, { props })
      + await container.renderToString(ContentCard, { props });
    const ids = [...doc.querySelectorAll("[id]")].map((element) => element.id);
    expect(ids.length).toBeGreaterThan(0);
    expect(new Set(ids).size).toBe(ids.length);
    for (const link of doc.querySelectorAll("a")) {
      const name = link.getAttribute("aria-labelledby");
      const description = link.getAttribute("aria-describedby");
      expect(name).toBeTruthy();
      expect(description).toBeTruthy();
      for (const id of `${name} ${description}`.split(" ")) {
        expect(link.contains(doc.getElementById(id)!)).toBe(true);
      }
      expect(description?.split(" ")).toHaveLength(2);
    }
  });

});
