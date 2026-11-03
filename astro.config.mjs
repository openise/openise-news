// @ts-check
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://news.openise.jp',
  output: 'static',
  vite: {
    plugins: [tailwindcss()],
  },
});
