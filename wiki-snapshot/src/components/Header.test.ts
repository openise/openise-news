import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { beforeAll, describe, expect, it } from "vitest";
import Header from "./Header.astro";
import source from "./Header.astro?raw";

describe("Header", () => {
  let html = "";

  beforeAll(async () => {
    const container = await AstroContainer.create();
    html = await container.renderToString(Header);
  });

  it("Openise Wiki が home route への link として表示される", () => {
    expect(html).toMatch(
      /<a class="site-nav-brand"[^>]*href="\/openise-wiki\/"[^>]*>Openise Wiki<\/a>/,
    );
  });

  it("Wiki、Clips、News、Tags が指定順で表示され、Graph が表示されない", () => {
    const nav = html.match(/<ul class="site-nav-list"[^>]*>([\s\S]*?)<\/ul>/)?.[1] ?? "";

    expect(nav).toMatch(/>Wiki<\/a>[\s\S]*>Clips<\/a>[\s\S]*>News<\/a>[\s\S]*>Tags<\/a>/);
    expect(nav).not.toContain("Graph");
  });

  it("brand、primary nav、theme toggle 用の layout が定義される", () => {
    expect(html).toContain('class="site-nav-actions"');
    expect(html).toContain('id="theme-toggle"');
    expect(html).toContain('aria-pressed="false"');
    expect(source).toMatch(
      /\.site-nav\s*\{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\) auto minmax\(0, 1fr\);/,
    );
    expect(source).toContain(".site-nav-brand");
    expect(source).toContain(".site-nav-actions");
  });

  it("現在の URL に一致する nav link だけに aria-current を付与する", async () => {
    const container = await AstroContainer.create();
    const clipsHtml = await container.renderToString(Header, {
      request: new Request("http://localhost:43215/openise-wiki/clips/"),
    });

    expect(clipsHtml).toMatch(
      /<a href="\/openise-wiki\/clips\/" aria-current="page"[^>]*>Clips<\/a>/,
    );
    expect(clipsHtml).toMatch(/<a href="\/openise-wiki\/wiki\/"[^>]*>Wiki<\/a>/);
    expect(clipsHtml).toMatch(/<a href="\/openise-wiki\/news\/"[^>]*>News<\/a>/);
    expect(clipsHtml).toMatch(/<a href="\/openise-wiki\/tags\/"[^>]*>Tags<\/a>/);
    expect(clipsHtml).not.toMatch(
      /<a href="\/openise-wiki\/wiki\/" aria-current="page"[^>]*>Wiki<\/a>/,
    );
    expect(clipsHtml).not.toMatch(
      /<a href="\/openise-wiki\/tags\/" aria-current="page"[^>]*>Tags<\/a>/,
    );

    const wikiHtml = await container.renderToString(Header, {
      request: new Request("http://localhost:43215/openise-wiki/wiki/syntheses/"),
    });
    expect(wikiHtml).toMatch(
      /<a href="\/openise-wiki\/wiki\/" aria-current="page"[^>]*>Wiki<\/a>/,
    );
    expect(wikiHtml).not.toMatch(
      /<a href="\/openise-wiki\/clips\/" aria-current="page"[^>]*>Clips<\/a>/,
    );
  });

  it("News URL では News だけを current にする", async () => {
    const container = await AstroContainer.create();
    const newsHtml = await container.renderToString(Header, {
      request: new Request("http://localhost:43215/openise-wiki/news/20260828/"),
    });

    expect(newsHtml).toMatch(
      /<a href="\/openise-wiki\/news\/" aria-current="page"[^>]*>News<\/a>/,
    );
    expect(newsHtml).not.toMatch(
      /<a href="\/openise-wiki\/wiki\/" aria-current="page"[^>]*>Wiki<\/a>/,
    );
    expect(newsHtml).not.toMatch(
      /<a href="\/openise-wiki\/clips\/" aria-current="page"[^>]*>Clips<\/a>/,
    );
    expect(newsHtml).not.toMatch(
      /<a href="\/openise-wiki\/tags\/" aria-current="page"[^>]*>Tags<\/a>/,
    );
  });
});
