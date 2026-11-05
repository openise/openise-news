import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import { expect, test } from 'vitest';
import Index from '../src/pages/index.astro';
import NotFound from '../src/pages/404.astro';

test('トップページにサイト名が表示される', async () => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(Index);
  expect(html).toContain('<title>Openise News</title>');
});

test('404 ページにトップページへのリンクがある', async () => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(NotFound);
  expect(html).toContain('<a href="/">トップページへ戻る</a>');
});

test('404 ページは canonical を出さず noindex を出力する', async () => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(NotFound);
  expect(html).not.toContain('rel="canonical"');
  expect(html).toContain('<meta name="robots" content="noindex">');
});

test.each([
  ['トップページ', Index],
  ['404 ページ', NotFound],
])('%s が BaseLayout のヘッダーとテーマ切り替えを表示する', async (_, page) => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(page);
  expect(html).toContain('class="site-header"');
  expect(html).toContain('id="theme-toggle"');
});
