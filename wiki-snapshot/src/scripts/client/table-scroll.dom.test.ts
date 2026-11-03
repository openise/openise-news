/* @vitest-environment happy-dom */

import { afterEach, describe, expect, it } from "vitest";
import { wrapTables } from "./table-scroll";

const table = "<table><tbody><tr><td>1</td></tr></tbody></table>";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("wrapTables", () => {
  it("記事内の表を横スクロール用の要素で包む", () => {
    document.body.innerHTML = `<article class="content-article"><p>前</p>${table}<p>後</p></article>`;

    wrapTables();

    const wrapper = document.querySelector(".content-article > .table-scroll");
    expect(wrapper?.firstElementChild?.tagName).toBe("TABLE");
    expect(wrapper?.previousElementSibling?.textContent).toBe("前");
    expect(wrapper?.nextElementSibling?.textContent).toBe("後");
  });

  it("包む要素をキーボードでスクロールできる領域にする", () => {
    document.body.innerHTML = `<article class="content-article">${table}</article>`;

    wrapTables();

    const wrapper = document.querySelector<HTMLElement>(".table-scroll");
    expect(wrapper?.tabIndex).toBe(0);
    expect(wrapper?.getAttribute("role")).toBe("region");
    expect(wrapper?.getAttribute("aria-label")).toBe("横にスクロールできる表");
  });

  it("2 回呼んでも二重に包まない", () => {
    document.body.innerHTML = `<article class="content-article">${table}</article>`;

    wrapTables();
    wrapTables();

    expect(document.querySelectorAll(".table-scroll")).toHaveLength(1);
  });

  it("表の中の表は包まない", () => {
    document.body.innerHTML = `<article class="content-article"><table><tbody><tr><td>${table}</td></tr></tbody></table></article>`;

    wrapTables();

    expect(document.querySelectorAll(".table-scroll")).toHaveLength(1);
    expect(document.querySelector(".table-scroll > table td > table")).not.toBeNull();
  });

  it("記事の外の表は包まない", () => {
    document.body.innerHTML = `<main>${table}</main><article class="content-article"></article>`;

    wrapTables();

    expect(document.querySelector(".table-scroll")).toBeNull();
  });
});
