import { beforeEach, describe, expect, it, vi } from "vitest";
import { initTheme, toggleTheme } from "./theme";

type ThemeFixture = {
  documentElement: { dataset: Record<string, string> };
  toggle: { attributes: Record<string, string>; setAttribute: (name: string, value: string) => void };
};

function createThemeFixture(systemTheme: "light" | "dark" = "light"): ThemeFixture {
  const documentElement = { dataset: {} };
  const attributes: Record<string, string> = {};
  const toggle = {
    attributes,
    setAttribute(name: string, value: string) {
      toggle.attributes[name] = value;
    },
  };
  vi.stubGlobal("document", {
    documentElement,
    getElementById: () => toggle,
  });
  vi.stubGlobal("window", {
    matchMedia: () => ({ matches: systemTheme === "dark" }),
  });
  return { documentElement, toggle };
}

describe("theme", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("localStorage が throw しても system theme へ fallback する", () => {
    const fixture = createThemeFixture("dark");
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new Error("storage unavailable");
      },
    });

    expect(() => initTheme()).not.toThrow();
    expect(fixture.documentElement.dataset.theme).toBe("dark");
    expect(fixture.toggle.attributes["aria-pressed"]).toBe("true");
  });

  it("localStorage が利用できなくても theme toggle は throw しない", () => {
    const fixture = createThemeFixture();
    vi.stubGlobal("localStorage", {
      setItem: () => {
        throw new Error("storage unavailable");
      },
    });
    fixture.documentElement.dataset.theme = "light";

    expect(() => toggleTheme()).not.toThrow();
    expect(fixture.documentElement.dataset.theme).toBe("dark");
    expect(fixture.toggle.attributes["aria-pressed"]).toBe("true");
  });
});
