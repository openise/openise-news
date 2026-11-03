import { describe, expect, it } from "vitest";
import { ARTICLE_TYPOGRAPHY_CLASSES } from "./typography";

describe("ARTICLE_TYPOGRAPHY_CLASSES", () => {
  it("applies the prose utility without constraining max width", () => {
    const classes = ARTICLE_TYPOGRAPHY_CLASSES.split(" ");
    expect(classes).toContain("prose");
    expect(classes).toContain("max-w-none");
  });

  it("uses prose-sm below 640px and prose-base from 640px to match openise-daily", () => {
    const classes = ARTICLE_TYPOGRAPHY_CLASSES.split(" ");
    expect(classes).toContain("prose-sm");
    expect(classes).toContain("sm:prose-base");
  });

  it("does not rely on prose-invert since theme toggling uses a data-theme attribute, not Tailwind's dark: variant", () => {
    expect(ARTICLE_TYPOGRAPHY_CLASSES).not.toContain("prose-invert");
  });
});
