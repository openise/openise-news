export type PaginationItem = number | "ellipsis";

const MAX_PAGE_SLOTS = 5;

export function buildPageNumbers(currentPage: number, lastPage: number): PaginationItem[] {
  if (lastPage <= MAX_PAGE_SLOTS) {
    return Array.from({ length: lastPage }, (_, index) => index + 1);
  }

  const candidates = [...new Set([1, currentPage - 1, currentPage, currentPage + 1, lastPage])]
    .filter((page) => page >= 1 && page <= lastPage)
    .sort((a, b) => a - b);

  const items: PaginationItem[] = [];
  for (const [index, page] of candidates.entries()) {
    if (index > 0 && page - candidates[index - 1] > 1) {
      items.push("ellipsis");
    }
    items.push(page);
  }
  return items;
}
