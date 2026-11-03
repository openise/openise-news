const DAY_LABELS = ["日", "月", "火", "水", "木", "金", "土"];

/** 実在しない日付（2 月 30 日など）は Date が別の日へ繰り上がるため、往復で一致するか確かめる */
function parseDate(dateString: string): Date | null {
  const year = Number(dateString.slice(0, 4));
  const month = Number(dateString.slice(4, 6));
  const day = Number(dateString.slice(6, 8));
  const date = new Date(year, month - 1, day);
  const isReal =
    date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day;
  return isReal ? date : null;
}

export function formatDate(dateString: string): string {
  const date = parseDate(dateString);
  if (!date) return dateString;
  const base = `${dateString.slice(0, 4)}年${dateString.slice(4, 6)}月${dateString.slice(6, 8)}日（${DAY_LABELS[date.getDay()]}）`;
  const time = dateString.slice(8, 12);
  return time === "0000" ? base : `${base} ${time.slice(0, 2)}:${time.slice(2, 4)}`;
}

export function toISODate(dateString: string): string {
  return `${dateString.slice(0, 4)}-${dateString.slice(4, 6)}-${dateString.slice(6, 8)}`;
}
