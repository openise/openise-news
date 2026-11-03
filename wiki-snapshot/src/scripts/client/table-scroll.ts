// 列の多い表が mobile でページ全体を横に押し広げないよう、記事内の表を横スクロール用の要素で包む。
// table 自体の display を変えると幅や支援技術での扱いが変わるため、外側の要素でスクロールさせる。
export function wrapTables(): void {
  for (const table of Array.from(document.querySelectorAll<HTMLTableElement>(".content-article table"))) {
    if (table.parentElement?.closest("table") || table.parentElement?.classList.contains("table-scroll")) continue;
    const wrapper = document.createElement("div");
    wrapper.className = "table-scroll";
    // マウスやタッチを使えない利用者も、focus して矢印キーで横スクロールできるようにする。
    wrapper.tabIndex = 0;
    wrapper.setAttribute("role", "region");
    wrapper.setAttribute("aria-label", "横にスクロールできる表");
    table.before(wrapper);
    wrapper.append(table);
  }
}
