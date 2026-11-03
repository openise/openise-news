import type { WikiTypeDirectory } from "../constants/wiki";

const BASE = "/openise-wiki/";

const path = (value = "") =>
  `${BASE}${value.replace(/^\/+|\/+$/g, "")}${value ? "/" : ""}`;

const withPage = (base: string, page?: number) =>
  path(page && page > 1 ? `${base}/${page}` : base);

export const routes = {
  home: () => BASE,
  favicon: () => `${BASE}favicon.svg`,
  wiki: () => path("wiki"),
  wikiType: (type: WikiTypeDirectory, page?: number) => withPage(`wiki/${type}`, page),
  wikiPage: (id: string) => path(`wiki/${id}`),
  clips: () => path("clips"),
  clip: (id: string) => path(`clips/${id}`),
  news: (page?: number) => withPage("news", page),
  newsItem: (id: string) => path(`news/${id}`),
  tags: () => path("tags"),
  tag: (tag: string) => path(`tags/${encodeURIComponent(tag)}`),
  tagWiki: (tag: string, page?: number) => withPage(`tags/${encodeURIComponent(tag)}/wiki`, page),
  tagClips: (tag: string) => path(`tags/${encodeURIComponent(tag)}/clips`),
  graph: () => path("wiki/graph"),
  log: () => path("wiki/log"),
  schema: () => path("wiki/schema"),
  source: (id: string) => path(`sources/${id}`),
};
