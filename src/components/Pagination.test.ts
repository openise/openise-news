import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { Window } from "happy-dom";
import { expect, it } from "vitest";
import Pagination from "./Pagination.astro";
import { routes } from "../domain/routes";

it.each([1, 4, 7])("全 7 ページの %i ページ目のリンクと無効状態を描画する", async (currentPage) => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(Pagination, {
    props: { currentPage, lastPage: 7, hrefForPage: routes.news },
  });
  const window = new Window();
  const document = new window.DOMParser().parseFromString(html, "text/html");
  const nav = document.querySelector('nav[aria-label="ページ"]');
  expect(nav).not.toBeNull();
  const links = Array.from(document.querySelectorAll("a"), (link) => [link.textContent, link.getAttribute("href")]);
  expect(links).toEqual(currentPage === 1 ? [
    ["1", "/news/"], ["2", "/news/2/"], ["7", "/news/7/"], ["次へ", "/news/2/"],
  ] : currentPage === 4 ? [
    ["前へ", "/news/3/"], ["1", "/news/"], ["3", "/news/3/"], ["4", "/news/4/"],
    ["5", "/news/5/"], ["7", "/news/7/"], ["次へ", "/news/5/"],
  ] : [
    ["前へ", "/news/6/"], ["1", "/news/"], ["6", "/news/6/"], ["7", "/news/7/"],
  ]);
  const selected = document.querySelectorAll('[aria-current="page"]');
  expect(selected).toHaveLength(1);
  expect(selected[0].textContent).toBe(String(currentPage));
  expect(Array.from(document.querySelectorAll('[aria-disabled="true"]'), (item) => item.textContent))
    .toEqual(currentPage === 1 ? ["前へ"] : currentPage === 7 ? ["次へ"] : []);
  expect(document.querySelectorAll('[aria-disabled="true"][href]')).toHaveLength(0);
  expect(document.querySelectorAll('.pagination-ellipsis[aria-hidden="true"]')).toHaveLength(currentPage === 4 ? 2 : 1);
});

it("1 ページならナビゲーションを描画しない", async () => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(Pagination, {
    props: { currentPage: 1, lastPage: 1, hrefForPage: routes.news },
  });
  expect(html).not.toContain("<nav");
});
