import { json } from "@/lib/api";
import { lookupWord } from "@/lib/lookup";
import { wordOfTheDay } from "@/lib/sources/fjalorthi";
import { NextResponse } from "next/server";

export const maxDuration = 20;
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const payload = await wordOfTheDay();
    if (!payload) {
      return NextResponse.json({ error: "upstream_error", detail: "Word of the day is unavailable" }, { status: 502 });
    }
    const lookup = await lookupWord(payload.word, ["fjalorthi"]);
    return json({
      word: payload.word,
      definition: payload.definition,
      source: "fjalorthi",
      url: `https://fjalorthi.com/${encodeURIComponent(payload.word)}`,
      lookup,
    });
  } catch (error) {
    const name = error instanceof Error ? error.name : "Error";
    return NextResponse.json(
      { error: "upstream_error", detail: `Word of the day is unavailable (${name})` },
      { status: 502 },
    );
  }
}
