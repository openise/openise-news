import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { describe, expect, it } from "vitest";
import BaseLayout from "./BaseLayout.astro";

const headers = readFileSync(new URL("../../public/_headers", import.meta.url), "utf-8");

function getHeader(name: string): string {
  const value = headers.match(new RegExp(`^\\s+${name}:\\s*(.+)$`, "m"))?.[1];
  if (!value) throw new Error(`public/_headers に ${name} がありません。`);
  return value.trim();
}

function sha256(source: string): string {
  return `'sha256-${createHash("sha256").update(source).digest("base64")}'`;
}

describe("public/_headers", () => {
  it("should apply the headers to every path", () => {
    expect(headers).toMatch(/^\/\*$/m);
  });

  it("should allow every inline script in BaseLayout by hash", async () => {
    const container = await AstroContainer.create();
    const html = await container.renderToString(BaseLayout);
    const inlineScripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
    const scriptSrc = getHeader("Content-Security-Policy").match(/script-src ([^;]+)/)?.[1] ?? "";

    expect(inlineScripts.length).toBeGreaterThan(0);
    for (const script of inlineScripts) {
      expect(scriptSrc, `script-src に ${sha256(script)} を追加してください`).toContain(sha256(script));
    }
  });

  it("should not allow unsafe-inline", () => {
    expect(getHeader("Content-Security-Policy")).not.toContain("'unsafe-inline'");
  });

  it("should set nosniff and referrer policy", () => {
    expect(getHeader("X-Content-Type-Options")).toBe("nosniff");
    expect(getHeader("Referrer-Policy")).toBe("strict-origin-when-cross-origin");
  });
});
