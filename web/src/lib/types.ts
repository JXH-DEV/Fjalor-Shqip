export type SourceId =
  | "fjale"
  | "fjalorthi"
  | "fjalorth"
  | "wiktionary_en"
  | "wiktionary_sq";

export const ALL_SOURCES: SourceId[] = [
  "fjale",
  "fjalorthi",
  "fjalorth",
  "wiktionary_en",
  "wiktionary_sq",
];

export type Sense = {
  number: number | null;
  gloss: string;
  examples: string[];
  labels: string[];
};

export type SourceEntry = {
  headword: string;
  lemma?: string | null;
  part_of_speech: string[];
  senses: Sense[];
  synonyms: string[];
  antonyms: string[];
  related: string[];
  translations: Record<string, string[]>;
  inflections: string[];
  exact_match: boolean;
};

export type SourceResult = {
  source: SourceId;
  title: string;
  homepage: string;
  license: string;
  url: string | null;
  found: boolean;
  error: string | null;
  entries: SourceEntry[];
};

export type MergedEntry = {
  headword: string;
  pos: string[];
  part_of_speech: string[];
  senses: Sense[];
  synonyms: string[];
  antonyms: string[];
  related: string[];
  translations: Record<string, string[]>;
};

export type LookupResponse = {
  query: string;
  canonical: string | null;
  found: boolean;
  merged: MergedEntry | null;
  sources: SourceResult[];
  suggestions: string[];
  attribution: {
    notice: string;
    licenses: string[];
    cited_urls: string[];
  } | null;
};

export type Quote = {
  author: string | null;
  title: string | null;
  excerpt: string;
};

export function emptyEntry(partial: Partial<SourceEntry> & { headword: string }): SourceEntry {
  return {
    lemma: null,
    part_of_speech: [],
    senses: [],
    synonyms: [],
    antonyms: [],
    related: [],
    translations: {},
    inflections: [],
    exact_match: true,
    ...partial,
  };
}
