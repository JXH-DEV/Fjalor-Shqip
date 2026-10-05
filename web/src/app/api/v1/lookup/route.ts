import { json, readWord } from "@/lib/api";
import { lookupWord, parseSources } from "@/lib/lookup";
import { NextResponse } from "next/server";

export const maxDuration = 20;
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const word = readWord(url.searchParams.get("q"));
  if (word instanceof NextResponse) return word;
  const sources = parseSources(url.searchParams.getAll("source"));
  if (sources === null) {
    return NextResponse.json({ error: "bad_request", detail: "Unknown source." }, { status: 400 });
  }
  const result = await lookupWord(word, sources);
  return json(result);
}
