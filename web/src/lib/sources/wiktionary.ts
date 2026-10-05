import { load } from "cheerio";
import { emptyEntry, type SourceEntry, type SourceResult } from "@/lib/types";
import { collapse, unique, wordUrl } from "@/lib/text";
import { upstreamGet } from "@/lib/upstream";

const EN = "https://en.wiktionary.org";
const SQ = "https://sq.wiktionary.org";
const POS_HEADING =
  /^(Emër|Folje|Mbiemër|Ndajfolje|Përemër|Lidhëz|Parafjalë|Pasthirrmë|Pjesëz|Numëror)\b/i;

function stripHtml(html: string): string {
  return collapse(load(`<div>${html}</div>`).text());
}

export async function lookupWiktionaryEn(word: string): Promise<SourceResult> {
  const url = wordUrl(EN, "api", "rest_v1", "page", "definition", word);
  const homepage = wordUrl(EN, "wiki", word);
  const meta = {
    source: "wiktionary_en" as const,
    title: "English Wiktionary",
    homepage: EN,
    license: "CC BY-SA 4.0",
  };
  try {
    const response = await upstreamGet(url, { Accept: "application/json" });
    if (response.status === 404) return { ...meta, url: homepage, found: false, error: null, entries: [] };
    if (response.status >= 400) {
      return { ...meta, url: homepage, found: false, error: `English Wiktionary returned HTTP ${response.status}`, entries: [] };
    }
    const payload = JSON.parse(response.text) as {
      sq?: { partOfSpeech?: string; definitions?: { definition?: string; examples?: string[] }[] }[];
    };
    const entries = (payload.sq || [])
      .map((item) => {
        const senses = (item.definitions || [])
          .map((definition, index) => ({
            number: index + 1,
            gloss: stripHtml(definition.definition || ""),
            examples: (definition.examples || []).map(stripHtml).filter(Boolean),
            labels: [] as string[],
          }))
          .filter((sense) => sense.gloss);
        if (!senses.length) return null;
        return emptyEntry({
          headword: word,
          part_of_speech: item.partOfSpeech ? [item.partOfSpeech] : [],
          senses,
          translations: { en: senses.map((sense) => sense.gloss) },
        });
      })
      .filter((entry) => entry !== null);
    return { ...meta, url: homepage, found: entries.length > 0, error: null, entries };
  } catch (error) {
    const name = error instanceof Error ? error.name : "Error";
    return { ...meta, url: homepage, found: false, error: `Could not reach English Wiktionary (${name})`, entries: [] };
  }
}

export function parseSqHtml(word: string, html: string) {
  const page = load(html);
  const entries: SourceEntry[] = [];
  let currentPos: string | null = null;
  page(".mw-parser-output > *").each((_, node) => {
    const el = page(node);
    const heading = el.find("h2, h3, h4").first();
    if (heading.length) {
      const title = collapse(heading.text());
      const match = title.match(POS_HEADING);
      if (match) currentPos = match[1];
      return;
    }
    if (el.is("ol") && currentPos) {
      const senses = el
        .find("> li")
        .toArray()
        .map((item, index) => ({
          number: index + 1,
          gloss: collapse(page(item).text()),
          examples: [] as string[],
          labels: [] as string[],
        }))
        .filter((sense) => sense.gloss);
      if (senses.length) {
        entries.push(
          emptyEntry({
            headword: word,
            part_of_speech: [currentPos],
            senses,
          }),
        );
      }
    }
  });
  if (entries.length) return entries;
  const first = page(".mw-parser-output ol").first();
  if (!first.length) return [];
  const senses = first
    .find("> li")
    .toArray()
    .map((item, index) => ({
      number: index + 1,
      gloss: collapse(page(item).text()),
      examples: [] as string[],
      labels: [] as string[],
    }))
    .filter((sense) => sense.gloss);
  return senses.length ? [emptyEntry({ headword: word, senses })] : [];
}

export async function lookupWiktionarySq(word: string): Promise<SourceResult> {
  const homepage = wordUrl(SQ, "wiki", word);
  const api = `${SQ}/w/api.php?${new URLSearchParams({
    action: "parse",
    page: word,
    prop: "text",
    format: "json",
    redirects: "1",
    disablelimitreport: "1",
  })}`;
  const meta = {
    source: "wiktionary_sq" as const,
    title: "Wiktionary shqip",
    homepage: SQ,
    license: "CC BY-SA 4.0",
  };
  try {
    const response = await upstreamGet(api, { Accept: "application/json" });
    if (response.status >= 400) {
      return { ...meta, url: homepage, found: false, error: `Albanian Wiktionary returned HTTP ${response.status}`, entries: [] };
    }
    const payload = JSON.parse(response.text) as { error?: unknown; parse?: { title?: string; text?: { "*"?: string } } };
    if (payload.error) return { ...meta, url: homepage, found: false, error: null, entries: [] };
    const html = payload.parse?.text?.["*"] || "";
    const title = payload.parse?.title || word;
    const entries = parseSqHtml(title, html);
    return { ...meta, url: homepage, found: entries.length > 0, error: null, entries };
  } catch (error) {
    const name = error instanceof Error ? error.name : "Error";
    return { ...meta, url: homepage, found: false, error: `Could not reach Albanian Wiktionary (${name})`, entries: [] };
  }
}

export async function suggestWords(query: string, limit: number): Promise<string[]> {
  const api = `${SQ}/w/api.php?${new URLSearchParams({
    action: "opensearch",
    search: query,
    limit: String(limit),
    namespace: "0",
    format: "json",
  })}`;
  const response = await upstreamGet(api, { Accept: "application/json" });
  if (response.status >= 400) return [];
  const payload = JSON.parse(response.text) as unknown[];
  if (!Array.isArray(payload) || !Array.isArray(payload[1])) return [];
  return unique(payload[1].map(String));
}
