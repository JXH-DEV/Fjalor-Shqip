import { json } from "@/lib/api";

export function GET() {
  return json({
    status: "ok",
    version: "1.0.0",
    sources: {
      fjale: "https://fjale.al/",
      fjalorthi: "https://fjalorthi.com/",
      fjalorth: "https://www.fjalorth.com/",
      wiktionary_en: "https://en.wiktionary.org/",
      wiktionary_sq: "https://sq.wiktionary.org/",
    },
  });
}
