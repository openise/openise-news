import {
  isTheme,
  resolveSystemTheme,
  resolveTheme,
  THEME_MEDIA_QUERY,
  THEME_STORAGE_KEY,
  type Theme,
} from "./theme-contract";

function systemTheme(): Theme {
  return resolveSystemTheme(window.matchMedia(THEME_MEDIA_QUERY).matches);
}

function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  document.getElementById("theme-toggle")?.setAttribute("aria-pressed", String(theme === "dark"));
}

export function getStoredTheme(): Theme | null {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(value) ? value : null;
  } catch {
    return null;
  }
}

/** localStorage 未保存時のみ OS の prefers-color-scheme を使う */
export function initTheme(): void {
  applyTheme(resolveTheme(getStoredTheme(), systemTheme()));
}

export function toggleTheme(): void {
  const current = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  const next: Theme = current === "dark" ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, next);
  } catch {
    // localStorage が利用できない環境でも theme の切り替えは継続する
  }
}
