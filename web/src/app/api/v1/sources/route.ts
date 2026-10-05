import { json } from "@/lib/api";

export function GET() {
  return json([
    { id: "fjale", title: "FJALË", homepage: "https://fjale.al/" },
    { id: "fjalorthi", title: "Fjalorthi", homepage: "https://fjalorthi.com/" },
    { id: "fjalorth", title: "Fjalorth.com", homepage: "https://www.fjalorth.com/" },
    { id: "wiktionary_en", title: "English Wiktionary", homepage: "https://en.wiktionary.org/" },
    { id: "wiktionary_sq", title: "Wiktionary shqip", homepage: "https://sq.wiktionary.org/" },
  ]);
}
