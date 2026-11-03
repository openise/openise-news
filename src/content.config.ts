import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { newsSchema } from "./schemas/content";

const news = defineCollection({
  loader: glob({
    pattern: "*/index.md",
    base: "./src/content/news",
    generateId: ({ entry }) => entry.replace(/\/index\.md$/, ""),
  }),
  schema: newsSchema,
});

export const collections = { news };
