import { isValidWord, normalizeWord } from "@/lib/text";
import { NextResponse } from "next/server";

export function badWord() {
  return NextResponse.json(
    { error: "bad_request", detail: "Use a single Albanian word (letters, hyphen, or apostrophe)." },
    { status: 400 },
  );
}

export function readWord(value: string | null): string | NextResponse {
  const cleaned = normalizeWord(value || "");
  if (!isValidWord(cleaned)) return badWord();
  return cleaned;
}

export function json<T>(body: T, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: { "Cache-Control": "public, s-maxage=120, stale-while-revalidate=600" },
  });
}
