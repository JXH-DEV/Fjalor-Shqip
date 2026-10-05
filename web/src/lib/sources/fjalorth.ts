import { load } from "cheerio";
import { emptyEntry, type SourceResult } from "@/lib/types";
import { collapse, unique, wordUrl } from "@/lib/text";
import { upstreamGet } from "@/lib/upstream";

const BASE = "https://www.fjalorth.com";

export function parseFjalorth(html: string) {
  const page = load(html);
  const section = page("section.word-section");
  if (!section.length) return [];
  const heading = collapse(section.find("h2.word").first().text());
  if (heading.toLocaleLowerCase("sq").includes("nuk u gjend")) return [];
  const definition = section.find(".definition").first();
  if (!definition.length) return [];
  const head = collapse(definition.find("strong").first().text());
  const pos = collapse(definition.find("em").first().text());
  const senses = definition
    .find("ol > li")
    .toArray()
    .map((item, index) => {
      const li = page(item);
      const examples = unique(
        li
          .find("em")
          .toArray()
          .map((em) => collapse(page(em).text())),
      );
      li.find("em").remove();
      return {
        number: index + 1,
        gloss: collapse(li.text()),
        examples,
        labels: [] as string[],
      };
    })
    .filter((sense) => sense.gloss);
  const translations: Record<string, string[]> = {};
  const line = collapse(page(".translations").text());
  const colon = line.indexOf(":");
  if (colon >= 0) {
    const value = line.slice(colon + 1).trim();
    if (value) translations.en = [value];
  }
  if (!senses.length) return [];
  return [
    emptyEntry({
      headword: head || heading.replace(/^Fjala:\s*/i, ""),
      part_of_speech: pos ? [pos] : [],
      senses,
      translations,
    }),
  ];
}

export async function lookupFjalorth(word: string): Promise<SourceResult> {
  const url = wordUrl(BASE, word);
  const base = {
    source: "fjalorth" as const,
    title: "Fjalorth.com",
    homepage: BASE,
    license: "fjalorth.com",
  };
  try {
    const response = await upstreamGet(url);
    if (response.status === 404) {
      return { ...base, url: response.url, found: false, error: null, entries: [] };
    }
    if (response.status >= 400) {
      return { ...base, url: response.url, found: false, error: `fjalorth.com returned HTTP ${response.status}`, entries: [] };
    }
    const entries = parseFjalorth(response.text);
    return { ...base, url: response.url, found: entries.length > 0, error: null, entries };
  } catch (error) {
    const name = error instanceof Error ? error.name : "Error";
    return { ...base, url, found: false, error: `Could not reach fjalorth.com (${name})`, entries: [] };
  }
}
