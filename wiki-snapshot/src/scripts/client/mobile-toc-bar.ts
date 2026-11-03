export function initMobileTocBar(root: Document = document): void {
  const bar = root.querySelector<HTMLElement>(".mobile-toc-bar");
  const toggle = bar?.querySelector<HTMLButtonElement>(".mobile-toc-toggle");
  const panel = bar?.querySelector<HTMLElement>("#mobile-toc-panel");
  if (!bar || !toggle || !panel) return;

  const setOpen = (open: boolean): void => {
    toggle.setAttribute("aria-expanded", String(open));
    panel.hidden = !open;
  };

  const updateHeight = (): void => {
    // バーが画面中ほどにある場合も、パネルが viewport の下端を越えないようにする。
    const room = Math.max(0, window.innerHeight - bar.getBoundingClientRect().bottom);
    panel.style.maxHeight = `min(60vh, ${room}px)`;
  };

  let scheduled = false;
  const scheduleHeight = (): void => {
    if (!bar.isConnected || panel.hidden || scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      if (bar.isConnected && !panel.hidden) updateHeight();
    });
  };

  window.addEventListener("scroll", scheduleHeight, { passive: true });
  window.addEventListener("resize", scheduleHeight, { passive: true });

  toggle.addEventListener("click", () => {
    if (panel.hidden) updateHeight();
    setOpen(panel.hidden);
  });

  panel.querySelectorAll(".toc-link").forEach((link) => {
    link.addEventListener("click", () => setOpen(false));
  });

  root.addEventListener("keydown", (event) => {
    if (!bar.isConnected || panel.hidden || event.key !== "Escape") return;
    setOpen(false);
    toggle.focus();
  });

  bar.addEventListener("focusout", (event) => {
    if (panel.hidden) return;
    // 移動先が null の場合は、非 focus 要素への click 判定に任せる。
    if (event.relatedTarget instanceof Node && !bar.contains(event.relatedTarget)) {
      setOpen(false);
    }
  });

  root.addEventListener("click", (event) => {
    if (!bar.isConnected || panel.hidden) return;
    if (event.target instanceof Node && !bar.contains(event.target)) {
      setOpen(false);
    }
  });
}
