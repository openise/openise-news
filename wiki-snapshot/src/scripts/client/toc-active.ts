import { findActiveHeadingIndex } from "../../domain/toc-active";

function headingFor(link: HTMLAnchorElement, root: Document): HTMLElement | null {
  try {
    const id = decodeURIComponent((link.getAttribute("href") ?? "").slice(1));
    return id ? root.getElementById(id) : null;
  } catch {
    return null;
  }
}

function topOf(heading: HTMLElement): number | null {
  if (heading.getClientRects().length === 0) return null;
  return heading.getBoundingClientRect().top;
}

export function initTocActive(root: Document = document): void {
  root.querySelectorAll<HTMLButtonElement>(".toc-expand-btn").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest(".toc")?.querySelectorAll(".toc-extra").forEach((item) => {
        item.classList.remove("hidden");
      });
      button.remove();
    });
  });

  const entries = Array.from(
    root.querySelectorAll<HTMLAnchorElement>('.toc .toc-link[href^="#"]'),
  ).map((link) => ({ link, heading: headingFor(link, root) }));
  if (entries.length === 0) return;
  const headings = Array.from(new Set(entries.map(({ heading }) => heading)))
    .filter((heading): heading is HTMLElement => heading !== null);
  const labels = root.querySelectorAll<HTMLElement>("[data-mobile-toc-current]");

  const update = (): void => {
    const margin = headings[0] ? parseFloat(window.getComputedStyle(headings[0]).scrollMarginTop) || 0 : 0;
    const index = findActiveHeadingIndex({
      headingTops: headings.map(topOf),
      offset: margin + 4,
    });
    const current = headings[index];
    entries.forEach(({ link, heading }) => {
      if (current && heading === current) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    });
    labels.forEach((label) => {
      label.textContent = current ? entries.find(({ heading }) => heading === current)?.link.textContent ?? "" : "";
    });
  };

  let scheduled = false;
  const schedule = (): void => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      update();
    });
  };

  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule, { passive: true });
  window.addEventListener("hashchange", schedule);
  root.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest('[data-tabs] button[role="tab"]')) {
      schedule();
    }
  });
  root.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    if (event.target instanceof Element && event.target.closest('[data-tabs] button[role="tab"]')) {
      schedule();
    }
  });
  update();
}
