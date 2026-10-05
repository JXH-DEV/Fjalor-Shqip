import { json, readWord } from "@/lib/api";
import { lookupFjalorthi } from "@/lib/sources/fjalorthi";
import { suggestWords } from "@/lib/sources/wiktionary";
import { unique } from "@/lib/text";
import { NextResponse } from "next/server";

export const maxDuration = 15;
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const word = readWord(url.searchParams.get("q"));
  if (word instanceof NextResponse) return word;
  const limit = Math.min(20, Math.max(1, Number(url.searchParams.get("limit") || 8)));
  let suggestions: string[] = [];
  try {
    suggestions = await suggestWords(word, limit);
  } catch {
    suggestions = [];
  }
  if (suggestions.length < limit) {
    try {
      const defined = await lookupFjalorthi(word);
      const extra = defined.entries.flatMap((entry) => [entry.headword, ...entry.related, ...entry.inflections]);
      suggestions = unique([...suggestions, ...extra]).slice(0, limit);
    } catch {
      suggestions = suggestions.slice(0, limit);
    }
  }
  return json({ query: word, suggestions: suggestions.slice(0, limit) });
}
