import { load, type Cheerio } from "cheerio";
import type { AnyNode } from "domhandler";
import { emptyEntry, type SourceResult } from "@/lib/types";
import { collapse, unique, wordUrl } from "@/lib/text";
import { upstreamGet } from "@/lib/upstream";

const BASE = "https://fjale.al";
const LABEL_RE =
  /^(zakon|keq|bised|libr|fig|mjek|fol|sh|kj|v|përh|rrall|ngusht|gjeog|bot|zool|kim|mat|fiz|muz|fet|hist|bujq|usht|iron|poh|moh)\b/i;

function inner(node: Cheerio<AnyNode> | undefined): string {
  if (!node || node.length === 0) return "";
  return collapse(node.text());
}

export function parseFjale(html: string) {
  const page = load(html);
  const block = page("#e.def");
  if (!block.length) return [];
  const body = inner(block);
  const lowered = body.toLocaleLowerCase("sq");
  if (lowered.includes("nuk ekziston") || lowered.includes("kemi mbetur pa fjalë")) return [];
  if (lowered.includes("mos e kishe llafin")) {
    const hint = inner(block.find("h3 a").first());
    return hint ? [emptyEntry({ headword: "", related: [hint], exact_match: false })] : [];
  }

  const head = block.find("strong, b").first();
  let pos = "";
  if (head.length) {
    pos = inner(head.next("em"));
    if (!pos) {
      const parent = collapse(head.parent().text());
      const leftover = parent.replace(inner(head), "").replace(/^[ .,;]+|[ .,;]+$/g, "");
      if (leftover && leftover.length <= 16) pos = leftover;
    }
  }
  const headword = inner(head);
  const slug = (block.attr("data-slug") || headword).trim();
  const items = block.find("ol > li").length ? block.find("ol > li") : block.find("ul > li");
  const senses = items
    .toArray()
    .map((item, index) => {
      const li = page(item);
      const labels: string[] = [];
      const examples: string[] = [];
      li.find("em").each((_, em) => {
        const text = collapse(page(em).text());
        page(em).remove();
        if (!text) return;
        if (LABEL_RE.test(text) && text.length <= 48) labels.push(text);
        else examples.push(text);
      });
      const gloss = collapse(li.text()).replace(/^\d+\.\s*/, "");
      return {
        number: index + 1,
        gloss: gloss || examples[0] || "",
        examples: unique(examples),
        labels: unique(labels),
      };
    })
    .filter((sense) => sense.gloss || sense.examples.length);

  const related = unique(block.find(".rel a").toArray().map((node) => collapse(page(node).text())));
  if (!senses.length && !headword) return [];
  return [
    emptyEntry({
      headword: headword || slug,
      lemma: slug || null,
      part_of_speech: pos ? [pos] : [],
      senses: senses.length ? senses : [{ number: null, gloss: body, examples: [], labels: [] }],
      related,
    }),
  ];
}

export async function lookupFjale(word: string): Promise<SourceResult> {
  const url = wordUrl(BASE, word);
  try {
    const response = await upstreamGet(url);
    if (response.status === 404) {
      const hint = parseFjale(response.text)[0];
      return {
        source: "fjale",
        title: "FJALË",
        homepage: BASE,
        license: "fjale.al",
        url: response.url,
        found: false,
        error: null,
        entries: hint?.related.length ? [hint] : [],
      };
    }
    if (response.status >= 400) {
      return miss("fjale", url, `fjale.al returned HTTP ${response.status}`);
    }
    const entries = parseFjale(response.text).filter((entry) => entry.exact_match && entry.headword);
    return {
      source: "fjale",
      title: "FJALË",
      homepage: BASE,
      license: "fjale.al",
      url: response.url,
      found: entries.length > 0,
      error: null,
      entries,
    };
  } catch (error) {
    return miss("fjale", url, `Could not reach fjale.al (${errorName(error)})`);
  }
}

function miss(source: "fjale", url: string, error: string): SourceResult {
  return {
    source,
    title: "FJALË",
    homepage: BASE,
    license: "fjale.al",
    url,
    found: false,
    error,
    entries: [],
  };
}

function errorName(error: unknown): string {
  return error instanceof Error ? error.name : "Error";
}
