const path = (value: string) => `/${value.replace(/^\/+|\/+$/g, "")}/`;

export const routes = {
  home: () => "/",
  news: () => path("news"),
};
