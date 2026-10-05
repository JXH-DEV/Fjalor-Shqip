import { lookupFjale } from "@/lib/sources/fjale";
import { lookupFjalorth } from "@/lib/sources/fjalorth";
import { lookupFjalorthi } from "@/lib/sources/fjalorthi";
import { lookupWiktionaryEn, lookupWiktionarySq } from "@/lib/sources/wiktionary";
import { canonicalPos, lookupVariants, normalizeWord, unique } from "@/lib/text";
import {
  ALL_SOURCES,
  type LookupResponse,
  type MergedEntry,
  type Sense,
  type SourceEntry,
  type SourceId,
  type SourceResult,
} from "@/lib/types";

const FETCHERS: Record<SourceId, (word: string) => Promise<SourceResult>> = {
  fjale: lookupFjale,
  fjalorthi: lookupFjalorthi,
  fjalorth: lookupFjalorth,
  wiktionary_en: lookupWiktionaryEn,
  wiktionary_sq: lookupWiktionarySq,
};

const cache = new Map<string, { expires: number; value: LookupResponse }>();

export async function lookupWord(word: string, sources?: SourceId[]): Promise<LookupResponse> {
  const query = normalizeWord(word);
  const wanted = sources?.length ? sources : ALL_SOURCES;
  const cacheId = `${query.toLocaleLowerCase("sq")}:${wanted.join(",")}`;
  const hit = cache.get(cacheId);
  if (hit && hit.expires > Date.now()) return hit.value;

  const settled = await Promise.all(
    wanted.map(async (source) => {
      try {
        return await FETCHERS[source](query);
      } catch (error) {
        const name = error instanceof Error ? error.name : "Error";
        return blank(source, `Lookup failed (${name})`);
      }
    }),
  );
  const results = await fillVariants(query, wanted, settled);
  const foundEntries = primaryEntries(results, query);
  const canonical = foundEntries[0]?.headword || null;
  const response: LookupResponse = {
    query,
    canonical,
    found: foundEntries.length > 0,
    merged: foundEntries.length ? mergeEntries(canonical || query, foundEntries) : null,
    sources: results,
    suggestions: suggestionsFrom(results, query),
    attribution: {
      notice: "Cite the source URLs. Wiktionary text is CC BY-SA 4.0.",
      licenses: unique(results.filter((item) => item.found).map((item) => item.license)),
      cited_urls: unique(results.filter((item) => item.found).map((item) => item.url || item.homepage)),
    },
  };
  cache.set(cacheId, { expires: Date.now() + 45 * 60 * 1000, value: response });
  if (cache.size > 400) {
    const oldest = cache.keys().next().value;
    if (oldest) cache.delete(oldest);
  }
  return response;
}

function primaryEntries(results: SourceResult[], query: string): SourceEntry[] {
  const exact = results.flatMap((result) => (result.found ? result.entries.filter((entry) => entry.exact_match) : []));
  const fuzzy = results.flatMap((result) => (result.found ? result.entries.filter((entry) => !entry.exact_match) : []));
  const pool = exact.length ? exact : fuzzy;
  if (!pool.length) return [];
  const folded = query.toLocaleLowerCase("sq");
  const matched = pool.filter((entry) => entry.headword.toLocaleLowerCase("sq") === folded);
  return matched.length ? matched : pool.slice(0, 1);
}

function mergeEntries(headword: string, entries: SourceEntry[]): MergedEntry {
  const ranked = [...entries].sort(
    (a, b) =>
      b.senses.reduce((sum, sense) => sum + sense.gloss.length, 0) -
      a.senses.reduce((sum, sense) => sum + sense.gloss.length, 0),
  );
  const pos: string[] = [];
  const senses: Sense[] = [];
  const synonyms: string[] = [];
  const antonyms: string[] = [];
  const related: string[] = [];
  const translations: Record<string, string[]> = {};
  const seen = new Set<string>();
  for (const entry of ranked) {
    pos.push(...entry.part_of_speech);
    synonyms.push(...entry.synonyms);
    antonyms.push(...entry.antonyms);
    related.push(...entry.related);
    for (const [lang, words] of Object.entries(entry.translations)) {
      translations[lang] = [...(translations[lang] || []), ...words];
    }
    for (const sense of entry.senses) {
      const key = sense.gloss.toLocaleLowerCase("sq");
      if (!key || seen.has(key)) continue;
      seen.add(key);
      senses.push(sense);
    }
  }
  return {
    headword,
    pos: canonicalPos(pos),
    part_of_speech: unique(pos),
    senses: senses.map((sense, index) => ({ ...sense, number: index + 1 })),
    synonyms: unique(synonyms),
    antonyms: unique(antonyms),
    related: unique(related),
    translations: Object.fromEntries(Object.entries(translations).map(([lang, words]) => [lang, unique(words)])),
  };
}

async function fillVariants(query: string, wanted: SourceId[], results: SourceResult[]): Promise<SourceResult[]> {
  const variant = lookupVariants(query).find((item) => item.toLocaleLowerCase("sq") !== query.toLocaleLowerCase("sq"));
  if (!variant) return results;
  const retries = results
    .map((result, index) => ({ result, index, source: wanted[index] }))
    .filter((item) => !item.result.found && !item.result.error);
  if (!retries.length) return results;
  const next = await Promise.all(
    retries.map(async (item) => {
      try {
        return await FETCHERS[item.source](variant);
      } catch {
        return item.result;
      }
    }),
  );
  const copy = [...results];
  retries.forEach((item, index) => {
    if (next[index].found) copy[item.index] = next[index];
  });
  return copy;
}

function suggestionsFrom(results: SourceResult[], query: string): string[] {
  const folded = query.toLocaleLowerCase("sq");
  const words = results.flatMap((result) =>
    result.entries.flatMap((entry) => [entry.headword, ...entry.related, ...entry.synonyms]),
  );
  return unique(words.filter((word) => word.toLocaleLowerCase("sq") !== folded)).slice(0, 12);
}

function blank(source: SourceId, error: string): SourceResult {
  const titles: Record<SourceId, [string, string, string]> = {
    fjale: ["FJALË", "https://fjale.al/", "fjale.al"],
    fjalorthi: ["Fjalorthi", "https://fjalorthi.com/", "fjalorthi.com"],
    fjalorth: ["Fjalorth.com", "https://www.fjalorth.com/", "fjalorth.com"],
    wiktionary_en: ["English Wiktionary", "https://en.wiktionary.org/", "CC BY-SA 4.0"],
    wiktionary_sq: ["Wiktionary shqip", "https://sq.wiktionary.org/", "CC BY-SA 4.0"],
  };
  const [title, homepage, license] = titles[source];
  return { source, title, homepage, license, url: null, found: false, error, entries: [] };
}

export function parseSources(values: string[]): SourceId[] | null {
  const known = new Set(ALL_SOURCES);
  const picked = values.filter(Boolean) as SourceId[];
  if (picked.some((item) => !known.has(item))) return null;
  return picked;
}
