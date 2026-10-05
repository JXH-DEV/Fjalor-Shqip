import { json } from "@/lib/api";
import { trendingWords } from "@/lib/sources/fjalorthi";
import { NextResponse } from "next/server";

export const maxDuration = 15;
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const limit = Math.min(40, Math.max(1, Number(new URL(request.url).searchParams.get("limit") || 12)));
  try {
    return json({ words: await trendingWords(limit) });
  } catch (error) {
    const name = error instanceof Error ? error.name : "Error";
    return NextResponse.json(
      { error: "upstream_error", detail: `Trending words are unavailable (${name})` },
      { status: 502 },
    );
  }
}
