import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { cpSync, existsSync, mkdtempSync, mkdirSync, readdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { Window } from "happy-dom";
import { expect, it } from "vitest";

const repository = fileURLToPath(new URL("../", import.meta.url));

it.each([0, 1, 20, 21])("News %i 件を実際にビルドし、経路・ID・一覧・詳細を検証する", async (count) => {
  const root = mkdtempSync(join(tmpdir(), "openise-news-build-"));
  try {
    for (const path of ["src", "public", "astro.config.mjs", "tsconfig.json", "package.json"]) {
      cpSync(join(repository, path), join(root, path), { recursive: true });
    }
    symlinkSync(join(repository, "node_modules"), join(root, "node_modules"), "dir");
    const content = join(root, "src/content/news");
    rmSync(content, { recursive: true });
    mkdirSync(content);
    const articles = Array.from({ length: count }, (_, index) => {
      const date = new Date(Date.UTC(2026, 10, 1 - index)).toISOString().slice(0, 10).replaceAll("-", "");
      const title = `News ${date}`;
      mkdirSync(join(content, date));
      writeFileSync(join(content, date, "index.md"), `---\ntitle: "${title}"\ncreatedDate: "${date}120000"\n---\n\n本文 ${date}\n`);
      return { id: date, title };
    });
    await promisify(execFile)(process.execPath, [join(repository, "node_modules/astro/bin/astro.mjs"), "build"], {
      cwd: root,
      env: { ...process.env, ASTRO_TELEMETRY_DISABLED: "1" },
      timeout: 30_000,
    });
    const readPage = (path: string) => {
      const html = readFileSync(join(root, "dist", path), "utf-8");
      const window = new Window();
      return new window.DOMParser().parseFromString(html, "text/html");
    };
    const pageCount = count > 20 ? 2 : 1;
    for (let page = 1; page <= pageCount; page++) {
      const document = readPage(page === 1 ? "news/index.html" : `news/${page}/index.html`);
      const expected = articles.slice((page - 1) * 20, page * 20);
      expect(document.querySelector("h1")?.textContent).toBe("News");
      expect(Array.from(document.querySelectorAll(".content-card-link"), (link) => link.getAttribute("href")))
        .toEqual(expected.map((article) => `/news/${article.id}/`));
      expect(Array.from(document.querySelectorAll(".content-card h3"), (heading) => heading.textContent))
        .toEqual(expected.map((article) => article.title));
      const months = [...new Set(expected.map((article) => article.id.slice(0, 6)))];
      expect(Array.from(document.querySelectorAll("section h2"), (heading) => heading.textContent))
        .toEqual(months.map((month) => `${month.slice(0, 4)}年${month.slice(4)}月`));
      for (const section of document.querySelectorAll("section[aria-labelledby]")) {
        expect(section.querySelector("h2")?.id).toBe(section.getAttribute("aria-labelledby"));
      }
      if (count === 0) expect(document.querySelector("main")?.textContent).toContain("表示できる News はまだありません。");
      const nav = document.querySelector('nav[aria-label="ページ"]');
      if (pageCount === 1) {
        expect(nav).toBeNull();
      } else {
        expect(nav?.querySelector('[aria-current="page"]')?.textContent).toBe(String(page));
        expect(nav?.querySelector('[aria-current="page"]')?.getAttribute("href")).toBe(page === 1 ? "/news/" : "/news/2/");
        expect(Array.from(nav?.querySelectorAll("a") ?? [], (link) => [link.textContent, link.getAttribute("href")]))
          .toContainEqual(page === 1 ? ["次へ", "/news/2/"] : ["前へ", "/news/"]);
        expect(nav?.querySelector('[aria-disabled="true"]')?.textContent).toBe(page === 1 ? "前へ" : "次へ");
      }
    }
    expect(readdirSync(join(root, "dist/news"), { withFileTypes: true })
      .filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort())
      .toEqual([...articles.map((article) => article.id), ...(pageCount === 2 ? ["2"] : [])].sort());
    for (const article of articles) {
      // 既定の slug に戻って ID に index が混ざる退行も、実際の生成経路で検出する。
      const document = readPage(`news/${article.id}/index.html`);
      expect(document.querySelector("title")?.textContent).toBe(`${article.title} | Openise News`);
      expect(document.querySelector("h1")?.textContent).toBe(article.title);
      expect(document.querySelector(".content-article")?.textContent).toContain(`本文 ${article.id}`);
      expect(existsSync(join(root, `dist/news/${article.id}/index/index.html`))).toBe(false);
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}, 45_000);
