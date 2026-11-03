import { experimental_AstroContainer as AstroContainer } from "astro/container";
import type { MarkdownHeading } from "astro";
import { describe, expect, it } from "vitest";
import MobileTocBar from "./MobileTocBar.astro";

const headings: MarkdownHeading[] = Array.from({ length: 10 }, (_, index) => ({
  depth: 2,
  slug: `heading-${index + 1}`,
  text: `見出し ${index + 1}`,
}));

async function render(): Promise<string> {
  const container = await AstroContainer.create();
  return container.renderToString(MobileTocBar, { props: { headings } });
}

describe("MobileTocBar", () => {
  it("目次とアイコンを持つ button で初期の閉じたパネルを制御する", async () => {
    const html = await render();

    expect(html).toMatch(/class="[^"]*mobile-toc-bar[^"]*not-prose[^"]*"/);
    expect(html).toMatch(/<button\b[^>]*type="button"[^>]*class="[^"]*mobile-toc-toggle[^>]*aria-expanded="false"[^>]*aria-controls="mobile-toc-panel"/);
    expect(html).toContain("目次");
    expect(html).toMatch(/<svg\b[^>]*aria-hidden="true"/);
    expect(html).toMatch(/<span\b[^>]*data-mobile-toc-current[^>]*><\/span>/);
    expect(html).toMatch(/<div\b[^>]*id="mobile-toc-panel"[^>]*\bhidden(?:\s|>)/);
  });

  it("パネルの TOC は全 10 件の見出しを追加の開閉操作なしで表示する", async () => {
    const html = await render();

    expect(Array.from(html.matchAll(/href="#([^"]+)"/g), (match) => match[1])).toEqual([
      "heading-1", "heading-2", "heading-3", "heading-4", "heading-5",
      "heading-6", "heading-7", "heading-8", "heading-9", "heading-10",
    ]);
    expect(html).toMatch(/<summary\b[^>]*\bhidden(?:\s|>)/);
    expect(html).not.toContain("toc-expand-btn");
    expect(html).not.toContain("toc-extra");
  });
});
