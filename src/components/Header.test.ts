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

  it("Openise News がトップへの link として表示される", () => {
    expect(html).toMatch(/<a class="site-nav-brand"[^>]*href="\/"[^>]*>Openise News<\/a>/);
  });

  it("ナビゲーションには News と About を表示する", () => {
    const nav = html.match(/<ul class="site-nav-list"[^>]*>([\s\S]*?)<\/ul>/)?.[1] ?? "";
    const labels = Array.from(nav.matchAll(/>([^<>]+)<\/a>/g), (match) => match[1]);

    expect(labels).toEqual(["News", "About"]);
    expect(nav).toMatch(/<a href="\/news\/"/);
    expect(nav).toMatch(/<a href="\/about\/"/);
  });

  it("brand、primary nav、theme toggle 用の layout が定義される", () => {
    expect(html).toContain('class="site-nav-actions"');
    expect(html).toContain('id="theme-toggle"');
    expect(html).toContain('aria-pressed="false"');
    expect(source).toMatch(
      /\.site-nav\s*\{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\) auto minmax\(0, 1fr\);/,
    );
  });

  it("News 配下の URL では News を current にする", async () => {
    const container = await AstroContainer.create();
    const newsHtml = await container.renderToString(Header, {
      request: new Request("http://localhost/news/20261102/"),
    });

    expect(newsHtml).toMatch(/<a href="\/news\/" aria-current="page"[^>]*>News<\/a>/);
  });

  it("About の URL では About だけを current にする", async () => {
    const container = await AstroContainer.create();
    const aboutHtml = await container.renderToString(Header, {
      request: new Request("http://localhost/about/"),
    });

    expect(aboutHtml).toMatch(/<a href="\/about\/" aria-current="page"[^>]*>About<\/a>/);
    expect(aboutHtml).not.toMatch(/<a href="\/news\/" aria-current="page"/);
  });

  it("トップでは News を current にしない", () => {
    expect(html).not.toContain('aria-current="page"');
  });
});
