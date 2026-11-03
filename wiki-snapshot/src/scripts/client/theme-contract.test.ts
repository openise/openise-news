/* @vitest-environment happy-dom */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getThemeBootstrapScript,
  THEME_MEDIA_QUERY,
  THEME_STORAGE_KEY,
} from "./theme-contract";

function executeThemeBootstrap(stored: string | null, systemTheme: "light" | "dark"): string | undefined {
  vi.stubGlobal("localStorage", {
    getItem: () => stored,
  });
  vi.stubGlobal("window", {
    matchMedia: (query: string) => ({
      matches: query === THEME_MEDIA_QUERY && systemTheme === "dark",
    }),
  });

  new Function(getThemeBootstrapScript())();
  return document.documentElement.dataset.theme;
}

describe("getThemeBootstrapScript", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    document.documentElement.removeAttribute("data-theme");
  });

  it("should apply the stored theme when evaluating the bootstrap script", () => {
    expect(executeThemeBootstrap("dark", "light")).toBe("dark");
  });

  it("should fall back to the system theme when the stored value is invalid", () => {
    expect(executeThemeBootstrap("blue", "dark")).toBe("dark");
  });

  it("should apply the system theme when localStorage access throws", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new Error("storage unavailable");
      },
    });
    vi.stubGlobal("window", {
      matchMedia: () => ({ matches: true }),
    });

    expect(() => new Function(getThemeBootstrapScript())()).not.toThrow();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("should not embed serialized function sources in the bootstrap script", () => {
    expect(getThemeBootstrapScript()).not.toMatch(
      /var (?:isTheme|resolveTheme|resolveSystemTheme)\s*=\s*function/,
    );
  });

  it("should embed the storage key from THEME_STORAGE_KEY", () => {
    expect(getThemeBootstrapScript()).toContain(JSON.stringify(THEME_STORAGE_KEY));
  });
});
