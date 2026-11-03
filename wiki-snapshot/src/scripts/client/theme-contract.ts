export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "openise-wiki-theme";
export const THEME_MEDIA_QUERY = "(prefers-color-scheme: dark)";

export function isTheme(value: string | null): value is Theme {
  return value === "light" || value === "dark";
}

export function resolveTheme(stored: string | null, systemTheme: Theme): Theme {
  return isTheme(stored) ? stored : systemTheme;
}

export function resolveSystemTheme(prefersDark: boolean): Theme {
  return prefersDark ? "dark" : "light";
}

export function getThemeBootstrapScript(): string {
  return `// 描画前に同期実行して dark theme 時のちらつき（FOUC）を防ぐ
  (function () {
    var stored = null;
    try {
      stored = localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});
    } catch {
      // localStorage が利用できない場合は system theme を使う
    }
    var systemTheme = window.matchMedia(${JSON.stringify(THEME_MEDIA_QUERY)}).matches
      ? "dark"
      : "light";
    document.documentElement.dataset.theme =
      stored === "light" || stored === "dark" ? stored : systemTheme;
  })();`;
}
