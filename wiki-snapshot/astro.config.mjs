import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";
import { satteri } from "@astrojs/markdown-satteri";
import expressiveCode from "astro-expressive-code";
import { pluginLineNumbers } from "@expressive-code/plugin-line-numbers";
import { contentEnvGuard } from "./scripts/utils/content-env-guard.mjs";
import { astroMdastPlugins, markdownFeatures } from "./src/markdown/plugins";

export default defineConfig({
  base: "/openise-wiki/",
  trailingSlash: "always",
  server: {
    port: 43215,
  },
  integrations: [
    expressiveCode({
      themes: ["github-dark", "github-light"],
      useDarkModeMediaQuery: false,
      themeCssSelector: (theme) =>
        theme.type === "dark" ? "[data-theme='dark']" : ":root:not([data-theme='dark'])",
      plugins: [pluginLineNumbers()],
    }),
  ],
  markdown: {
    processor: satteri({
      mdastPlugins: astroMdastPlugins(),
      features: markdownFeatures,
    }),
  },
  vite: {
    plugins: [tailwindcss(), contentEnvGuard()],
    server: {
      strictPort: true,
    },
  },
});
