import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import { expect, test } from 'vitest';
import Index from '../src/pages/index.astro';
import NotFound from '../src/pages/404.astro';

test('トップページにサイト名が表示される', async () => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(Index);
  expect(html).toContain('<h1>Openise News</h1>');
});

test('404 ページにトップページへのリンクがある', async () => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(NotFound);
  expect(html).toContain('href="/"');
});
