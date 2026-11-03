import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { WIKI_TYPE_DIRECTORIES } from "./constants/wiki";
import { clipSchema, newsSchema, sourceSchema, wikiSchema } from "./schemas/content";

const clips = defineCollection({
  loader: glob({ pattern: "*/index.md", base: "./src/content/clips" }),
  schema: clipSchema,
});

const wiki = defineCollection({
  loader: glob({
    pattern: Object.values(WIKI_TYPE_DIRECTORIES).map((directory) => `${directory}/*.md`),
    base: "./src/content/wiki",
  }),
  schema: wikiSchema,
});

const sources = defineCollection({
  loader: glob({
    pattern: "**/*.md",
    base: "./src/content/sources",
    generateId: ({ entry }) => entry.replace(/\.md$/, ""),
  }),
  schema: sourceSchema,
});

const news = defineCollection({
  loader: glob({
    pattern: "*/index.md",
    base: "./src/content/news",
    generateId: ({ entry }) => entry.replace(/\/index\.md$/, ""),
  }),
  schema: newsSchema,
});

export const collections = { clips, wiki, sources, news };
