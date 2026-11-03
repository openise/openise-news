// @ts-check
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://news.openise.jp',
  output: 'static',
  integrations: [sitemap()],
  // CSP（public/_headers）で 'unsafe-inline' を使わずに済むよう、CSS と script をインラインにせず外部ファイルとして出力する
  build: {
    inlineStylesheets: 'never',
  },
  vite: {
    plugins: [tailwindcss()],
    build: {
      assetsInlineLimit: 0,
    },
  },
});
