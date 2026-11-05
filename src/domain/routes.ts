const BASE = "/";

const path = (value = "") =>
  `${BASE}${value.replace(/^\/+|\/+$/g, "")}${value ? "/" : ""}`;

const withPage = (base: string, page?: number) =>
  path(page && page > 1 ? `${base}/${page}` : base);

export const routes = {
  home: () => BASE,
  news: (page?: number) => withPage("news", page),
  newsItem: (id: string) => path(`news/${id}`),
  about: () => path("about"),
};
