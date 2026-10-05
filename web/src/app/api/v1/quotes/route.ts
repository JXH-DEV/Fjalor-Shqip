import { json, readWord } from "@/lib/api";
import { quotesFor } from "@/lib/sources/fjalorthi";
import { NextResponse } from "next/server";

export const maxDuration = 15;
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const word = readWord(new URL(request.url).searchParams.get("q"));
  if (word instanceof NextResponse) return word;
  try {
    return json({ query: word, quotes: await quotesFor(word) });
  } catch (error) {
    const name = error instanceof Error ? error.name : "Error";
    return NextResponse.json({ error: "upstream_error", detail: `Quotes are unavailable (${name})` }, { status: 502 });
  }
}
