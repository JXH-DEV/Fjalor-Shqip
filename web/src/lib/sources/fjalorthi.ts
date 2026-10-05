import { load } from "cheerio";
import { emptyEntry, type Quote, type SourceEntry, type SourceResult } from "@/lib/types";
import { collapse, splitNumberedSenses, unique, wordUrl } from "@/lib/text";
import { upstreamGet } from "@/lib/upstream";

const BASE = "https://fjalorthi.com";
const TRENDING =
  "https://fjalorthi-trending-top-words-bucket-prod.s3.eu-central-1.amazonaws.com/top_ga_words.json";

const POS_HINTS = ["emër", "folje", "mbiemër", "ndajfolje", "përemër", "pjesore", "lidhëz", "parafjalë", "pasthirrmë", "numëror", "pjesëz"];

function fjalorthiText(html: string): [string, string[]] {
  const page = load(`<div>${html}</div>`);
  const labels: string[] = [];
  page("span.SHRT").each((_, node) => {
    const label = collapse(page(node).text()).replace(/;$/, "");
    if (label) labels.push(label);
    page(node).replaceWith(label ? ` (${label}) ` : " ");
  });
  page("a").each((_, node) => {
    page(node).replaceWith(page(node).text());
  });
  return [collapse(page.text()), unique(labels)];
}

function entryFromMatch(raw: Record<string, unknown>, exactMatch: boolean): SourceEntry {
  const [text, labels] = fjalorthiText(String(raw.wordDefinition || ""));
  const pos = labels.filter((label) => POS_HINTS.some((hint) => label.toLocaleLowerCase("sq").includes(hint)));
  const extra = labels.filter((label) => !pos.includes(label));
  const numbered = splitNumberedSenses(text);
  const senses = numbered.map(([number, gloss], index) => ({
    number,
    gloss,
    examples: [] as string[],
    labels: index === 0 ? unique(extra) : [],
  }));
  const inflections = unique([
    String(raw.word5 || ""),
    String(raw.wordOrig || ""),
    ...Array.from({ length: 9 }, (_, i) => String(raw[`wordDer${i + 1}`] || "")),
  ]);
  const headword = String(raw.canonicalWord || raw.word || raw.word2 || "").trim();
  return emptyEntry({
    headword,
    lemma: String(raw.word5 || headword),
    part_of_speech: unique(pos),
    senses,
    synonyms: unique((raw.synonyms as string[]) || []),
    antonyms: unique((raw.antonyms as string[]) || []),
    inflections,
    exact_match: Boolean(raw.exactMatch ?? exactMatch),
  });
}

export function parseDefine(payload: Record<string, unknown>): SourceEntry[] {
  const exact = (payload.exactMatches as Record<string, unknown>[]) || [];
  const fuzzy = (payload.fuzzyMatches as Record<string, unknown>[]) || [];
  const entries: SourceEntry[] = [];
  const seen = new Set<string>();
  for (const [raw, exactMatch] of [
    ...exact.map((item) => [item, true] as const),
    ...fuzzy.map((item) => [item, false] as const),
  ]) {
    const entry = entryFromMatch(raw, exactMatch);
    const key = `${entry.headword.toLocaleLowerCase("sq")}:${entry.senses[0]?.gloss.slice(0, 80) || ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    entries.push(entry);
  }
  return entries;
}

export async function lookupFjalorthi(word: string): Promise<SourceResult> {
  const url = wordUrl(BASE, "prod", "define", word);
  const meta = {
    source: "fjalorthi" as const,
    title: "Fjalorthi",
    homepage: BASE,
    license: "fjalorthi.com",
  };
  try {
    const response = await upstreamGet(url, { Accept: "application/json" });
    if (response.status >= 400) {
      return { ...meta, url, found: false, error: `fjalorthi.com returned HTTP ${response.status}`, entries: [] };
    }
    const payload = JSON.parse(response.text) as Record<string, unknown>;
    const entries = parseDefine(payload);
    return {
      ...meta,
      url: wordUrl(BASE, word),
      found: entries.length > 0,
      error: null,
      entries,
    };
  } catch (error) {
    const name = error instanceof Error ? error.name : "Error";
    return { ...meta, url, found: false, error: `Could not reach fjalorthi.com (${name})`, entries: [] };
  }
}

export async function wordOfTheDay(): Promise<{ word: string; definition: string | null } | null> {
  const response = await upstreamGet(wordUrl(BASE, "prod", "wordoftheday"), { Accept: "application/json" });
  if (response.status >= 400) return null;
  const data = JSON.parse(response.text) as { word?: string; definition?: string };
  if (!data.word) return null;
  const [definition] = fjalorthiText(data.definition || "");
  return { word: data.word, definition: definition || null };
}

export async function quotesFor(word: string): Promise<Quote[]> {
  const response = await upstreamGet(wordUrl(BASE, "prod", "highlight", word), { Accept: "application/json" });
  if (response.status >= 400) return [];
  const payload = JSON.parse(response.text) as { author?: string; title?: string; highlightedFragments?: string[] }[];
  if (!Array.isArray(payload)) return [];
  return payload
    .map((item) => {
      const excerpt = collapse((item.highlightedFragments || []).join(" ").replace(/<\/?B>/g, ""));
      return {
        author: item.author || null,
        title: item.title || null,
        excerpt,
      };
    })
    .filter((item) => item.excerpt);
}

export async function trendingWords(limit: number): Promise<{ word: string; views: number | null }[]> {
  const response = await upstreamGet(TRENDING, { Accept: "application/json" });
  if (response.status >= 400) return [];
  const payload = JSON.parse(response.text) as { word?: string; uniquePageViews?: string }[];
  if (!Array.isArray(payload)) return [];
  return payload.slice(0, limit).flatMap((item) => {
    const word = (item.word || "").trim();
    if (!word) return [];
    const views = /^\d+$/.test(String(item.uniquePageViews || "")) ? Number(item.uniquePageViews) : null;
    return [{ word, views }];
  });
}
