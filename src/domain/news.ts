export type NewsMonthGroup<T> = {
  month: string;
  label: string;
  items: T[];
};

type DatedNews = { data: { createdDate: string } };

export function sortNewsByCreatedDate<T extends DatedNews>(items: T[]): T[] {
  return [...items].sort((left, right) =>
    right.data.createdDate.localeCompare(left.data.createdDate),
  );
}

export function latestNews<T extends DatedNews>(items: T[]): T | undefined {
  return sortNewsByCreatedDate(items)[0];
}

export function groupNewsByMonth<T extends DatedNews>(items: T[]): NewsMonthGroup<T>[] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const month = item.data.createdDate.slice(0, 6);
    const monthItems = groups.get(month);
    if (monthItems) monthItems.push(item);
    else groups.set(month, [item]);
  }

  return [...groups].map(([month, monthItems]) => ({
    month,
    label: `${month.slice(0, 4)}年${month.slice(4, 6)}月`,
    items: monthItems,
  }));
}
