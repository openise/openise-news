import { fileURLToPath } from "node:url";
import { defineMdastPlugin, type Features, type MdastPluginDefinition, type MdastPluginList } from "satteri";
import linkTitles from "../content/link-titles.json" with { type: "json" };
import xPosts from "../content/x-posts.json" with { type: "json" };
import { contentGroups } from "./content-groups";
import { contentLinks } from "./content-links";
import { inlineSvg } from "./inline-svg";
import { linkCard } from "./link-card";
import { mathBlock } from "./math-block";
import { mermaid } from "./mermaid";
import { relatedSection } from "./related-section";
import { smartPunctuationCompat } from "./smart-punctuation-compat";
import { wikiLinks } from "./wiki-links";
import { zennContainer } from "./zenn-container";
import { sourceDigest } from "./source-digest";

/**
 * 句読点は旧 SmartyPants と同じ出力にするため smartPunctuationCompat で処理する。
 * Astro は frontmatter を除いた本文を渡すため、本文先頭の `---` を frontmatter として読ませない
 */
export const markdownFeatures = { smartPunctuation: false, frontmatter: false } satisfies Features;

export const mdastPlugins: MdastPluginList = [
  smartPunctuationCompat,
  zennContainer,
  contentGroups,
  wikiLinks,
  contentLinks,
  relatedSection,
  // titles ・ xPosts を直列化できるプロパティとして持たせ、Astro の config digest に含める。
  // link-titles.json ・ x-posts.json を更新すると digest が変わり、content store の描画 cache が作り直される
  linkCard({ titles: linkTitles, xPosts }),
  mermaid,
  mathBlock,
  inlineSvg,
];

/** 変換はしない。cacheKey を Astro の config digest に載せるためだけに登録する */
function sourceDigestPlugin(cacheKey: string): MdastPluginDefinition {
  return defineMdastPlugin({ name: "source-digest", cacheKey });
}

/**
 * astro.config.mjs 用の plugin list。Astro は config の関数を digest に含めないため、plugin のコードを変えても
 * content store の描画 cache が残る。このファイルから辿れるソースの digest を cacheKey で渡し、コードの変更でも作り直させる。
 * management 経由でページの bundle からも読まれる mdastPlugins とは分け、bundle の評価時にソースを読まないようにする
 */
export function astroMdastPlugins(): MdastPluginList {
  return [sourceDigestPlugin(sourceDigest(fileURLToPath(import.meta.url))), ...mdastPlugins];
}
