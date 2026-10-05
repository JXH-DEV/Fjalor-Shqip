const MARKS = new Set(["-", "'", "’", "ʼ", " ", "."]);
const MAX = 80;

export function collapse(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function unique(items: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of items) {
    const key = collapse(item);
    if (!key) continue;
    const folded = key.toLocaleLowerCase("sq");
    if (seen.has(folded)) continue;
    seen.add(folded);
    out.push(key);
  }
  return out;
}

export function normalizeWord(raw: string): string {
  return collapse((raw || "").normalize("NFC"));
}

export function isValidWord(word: string): boolean {
  if (!word || word.length > MAX) return false;
  let letters = 0;
  for (const ch of word) {
    if (/\p{L}/u.test(ch)) {
      letters += 1;
      continue;
    }
    if (!MARKS.has(ch)) return false;
  }
  return letters >= 1;
}

const FOLD: Record<string, string> = {
  ë: "e",
  Ë: "E",
  ç: "c",
  Ç: "C",
  á: "a",
  à: "a",
  é: "e",
  í: "i",
  ó: "o",
  ú: "u",
  ý: "y",
};

export function lookupVariants(word: string): string[] {
  const nfc = normalizeWord(word);
  const folded = [...nfc].map((ch) => FOLD[ch] ?? ch).join("");
  const variants = [nfc];
  if (folded !== nfc) variants.push(folded);
  const lowered = nfc.toLocaleLowerCase("sq");
  if (!variants.some((item) => item.toLocaleLowerCase("sq") === lowered)) {
    variants.push(lowered);
  }
  return variants;
}

export function wordUrl(base: string, ...parts: string[]): string {
  return `${base.replace(/\/$/, "")}/${parts.map((part) => encodeURIComponent(part)).join("/")}`;
}

const SHORT: Record<string, string> = {
  "f.": "noun",
  f: "noun",
  "m.": "noun",
  m: "noun",
  "sh.": "noun",
  "mb.": "adjective",
  mb: "adjective",
  "ndajf.": "adverb",
  ndajfolje: "adverb",
};

const CANONICAL: [string, string][] = [
  ["emër", "noun"],
  ["emra", "noun"],
  ["noun", "noun"],
  ["folje", "verb"],
  ["verb", "verb"],
  ["mbiemër", "adjective"],
  ["adjective", "adjective"],
  ["ndajfolje", "adverb"],
  ["adverb", "adverb"],
  ["përemër", "pronoun"],
  ["pronoun", "pronoun"],
  ["lidhëz", "conjunction"],
  ["conjunction", "conjunction"],
  ["parafjalë", "preposition"],
  ["preposition", "preposition"],
  ["pasthirrmë", "interjection"],
  ["interjection", "interjection"],
  ["numëror", "numeral"],
  ["numeral", "numeral"],
  ["pjesore", "participle"],
  ["participle", "participle"],
];

export function canonicalPos(labels: string[]): string[] {
  const found: string[] = [];
  for (const label of labels) {
    const text = (label || "").trim();
    if (!text) continue;
    const lowered = text.toLocaleLowerCase("sq").replace(/\.$/, "");
    if (SHORT[lowered]) {
      found.push(SHORT[lowered]);
      continue;
    }
    if (SHORT[text.toLocaleLowerCase("sq")]) {
      found.push(SHORT[text.toLocaleLowerCase("sq")]);
      continue;
    }
    const hit = CANONICAL.find(([needle]) => text.toLocaleLowerCase("sq").includes(needle));
    if (hit) found.push(hit[1]);
  }
  return unique(found);
}

const SENSE_SPLIT = /(?:(?<=^)|(?<=[\s;]))(\d+)\.\s+/;

export function splitNumberedSenses(text: string): [number | null, string][] {
  const clean = collapse(text);
  if (!clean) return [];
  const parts = clean.split(SENSE_SPLIT);
  if (parts.length === 1) return [[null, clean]];
  const senses: [number | null, string][] = [];
  const preamble = parts[0].replace(/^[ ;,]+|[ ;,]+$/g, "");
  for (let i = 1; i < parts.length; i += 2) {
    const number = Number(parts[i]);
    if (!Number.isFinite(number)) continue;
    const gloss = (parts[i + 1] || "").replace(/^[ ;]+|[ ;]+$/g, "");
    if (gloss) senses.push([number, gloss]);
  }
  if (!senses.length && preamble) return [[null, preamble]];
  return senses;
}
