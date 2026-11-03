// JS が動かない環境でも全パネルを読めるよう、描画時は section を並べるだけにし、tablist はここで組み立てる。
let groupCount = 0;

function fragmentTarget(): HTMLElement | null {
  try {
    const id = decodeURIComponent(window.location.hash.slice(1));
    return id ? document.getElementById(id) : null;
  } catch {
    return null;
  }
}

export function initTabs(root: ParentNode = document): void {
  for (const container of Array.from(root.querySelectorAll<HTMLElement>("[data-tabs]:not([data-tabs-ready])"))) {
    const panels = Array.from(container.children).filter(
      (child): child is HTMLElement => child instanceof HTMLElement && child.matches("section[data-tab-label]"),
    );
    if (panels.length === 0) continue;

    const prefix = `content-tabs-${groupCount++}`;
    const tablist = document.createElement("div");
    tablist.className = "content-tabs-list";
    tablist.setAttribute("role", "tablist");

    const tabs = panels.map((panel, index) => {
      const tab = document.createElement("button");
      tab.type = "button";
      tab.id = `${prefix}-tab-${index}`;
      tab.textContent = panel.dataset.tabLabel ?? "";
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", `${prefix}-panel-${index}`);
      panel.id = `${prefix}-panel-${index}`;
      panel.setAttribute("role", "tabpanel");
      panel.tabIndex = 0;
      panel.setAttribute("aria-labelledby", tab.id);
      const label = panel.firstElementChild;
      if (label instanceof HTMLElement && label.classList.contains("content-tab-label")) label.hidden = true;
      tablist.append(tab);
      return tab;
    });

    const select = (index: number, focus: boolean): void => {
      for (const [i, tab] of tabs.entries()) {
        const selected = i === index;
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
        panels[i].hidden = !selected;
      }
      if (focus) tabs[index].focus();
    };

    const selectFragment = (): void => {
      const target = fragmentTarget();
      if (!target) return;
      const index = panels.findIndex((panel) => panel.contains(target));
      if (index !== -1) select(index, false);
    };

    for (const [index, tab] of tabs.entries()) {
      tab.addEventListener("click", () => select(index, false));
    }

    const last = tabs.length - 1;
    tablist.addEventListener("keydown", (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const current = tabs.findIndex((tab) => tab === document.activeElement);
      if (current === -1) return;
      const targets: Record<string, number | undefined> = {
        ArrowRight: current === last ? 0 : current + 1,
        ArrowLeft: current === 0 ? last : current - 1,
        Home: 0,
        End: last,
      };
      const next = targets[event.key];
      if (next === undefined) return;
      event.preventDefault();
      select(next, true);
    });

    container.prepend(tablist);
    container.dataset.tabsReady = "";
    select(0, false);
    selectFragment();
    window.addEventListener("hashchange", selectFragment);
  }
}
