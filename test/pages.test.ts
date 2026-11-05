import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import { expect, test } from 'vitest';
import { Window } from 'happy-dom';
import About from '../src/pages/about.astro';
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


test.each([
  ['トップページ', Index],
  ['About', About],
  ['404 ページ', NotFound],
])('%s が本文の後に共通フッターを 1 つ表示する', async (_, page) => {
  const container = await AstroContainer.create();
  const html = await container.renderToString(page);
  const window = new Window();
  const document = new window.DOMParser().parseFromString(html, 'text/html');
  expect(document.querySelectorAll('footer')).toHaveLength(1);
  expect(document.querySelector('footer')?.textContent?.trim()).toBe(
    '© 2026 Openise News. Built with Astro 7.4.4.',
  );
  expect(document.querySelector('main')?.nextElementSibling?.tagName).toBe('FOOTER');
});
