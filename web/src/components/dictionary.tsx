"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { LookupResponse, Quote } from "@/lib/types";

const SAMPLES = ["dashuri", "shtëpi", "liri", "mal"];

type Trending = { word: string; views: number | null };
type Day = { word: string; definition: string | null };

export function Dictionary() {
  const params = useSearchParams();
  const router = useRouter();
  const query = params.get("q") || "";
  const [draft, setDraft] = useState(query);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [openSuggest, setOpenSuggest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<LookupResponse | null>(null);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [day, setDay] = useState<Day | null>(null);
  const [dayError, setDayError] = useState("");
  const [trending, setTrending] = useState<Trending[]>([]);
  const [trendError, setTrendError] = useState("");

  const runLookup = useCallback(async (word: string) => {
    setLoading(true);
    setError("");
    setResult(null);
    setQuotes([]);
    try {
      const [lookup, quoteData] = await Promise.all([
        getJson<LookupResponse>(`/api/v1/lookup?q=${encodeURIComponent(word)}`),
        getJson<{ quotes: Quote[] }>(`/api/v1/quotes?q=${encodeURIComponent(word)}`).catch(() => ({ quotes: [] })),
      ]);
      setResult(lookup);
      setQuotes(quoteData.quotes || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kërkimi dështoi.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setDraft(query);
    if (query) void runLookup(query);
  }, [query, runLookup]);

  useEffect(() => {
    void loadSide();
  }, []);

  useEffect(() => {
    const value = draft.trim();
    if (value.length < 2) {
      setSuggestions([]);
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        const data = await getJson<{ suggestions: string[] }>(`/api/v1/suggest?q=${encodeURIComponent(value)}`);
        setSuggestions(data.suggestions || []);
      } catch {
        setSuggestions([]);
      }
    }, 220);
    return () => window.clearTimeout(timer);
  }, [draft]);

  async function loadSide() {
    try {
      const data = await getJson<Day>("/api/v1/word-of-the-day");
      setDay(data);
    } catch {
      setDayError("Fjala e ditës nuk u ngarkua.");
    }
    try {
      const data = await getJson<{ words: Trending[] }>("/api/v1/trending");
      setTrending(data.words || []);
    } catch {
      setTrendError("Lista nuk u ngarkua.");
    }
  }

  function search(word: string) {
    const cleaned = word.trim();
    if (!cleaned) return;
    setOpenSuggest(false);
    router.replace(`/?q=${encodeURIComponent(cleaned)}`);
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 md:py-12">
      <header className="border-b border-foreground/15 pb-6">
        <p className="text-xs tracking-[0.18em] text-primary uppercase">Fjalor shqip</p>
        <h1 className="font-heading text-5xl tracking-tight md:text-6xl">Fjalë</h1>
        <p className="mt-2 max-w-xl text-lg text-muted-foreground">
          Kuptimet, shembujt dhe përkthimet nga FJALË, Fjalorthi, Fjalorth dhe Wiktionary.
        </p>
      </header>

      <form
        className="relative"
        onSubmit={(event) => {
          event.preventDefault();
          search(draft);
        }}
      >
        <label htmlFor="q" className="mb-2 block text-xs tracking-widest uppercase">
          Fjala
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            id="q"
            value={draft}
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
            placeholder="dashuri, shtëpi, liri"
            className="h-12 bg-card px-4 text-lg"
            onChange={(event) => {
              setDraft(event.target.value);
              setOpenSuggest(true);
            }}
            onFocus={() => setOpenSuggest(true)}
          />
          <Button type="submit" className="h-12 px-6 text-base sm:min-w-28">
            Kërko
          </Button>
        </div>
        {openSuggest && suggestions.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-xl bg-popover text-popover-foreground ring-1 ring-foreground/10">
            {suggestions.map((word) => (
              <li key={word}>
                <button
                  type="button"
                  className="w-full px-4 py-2 text-left hover:bg-accent"
                  onClick={() => search(word)}
                >
                  {word}
                </button>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-sm text-muted-foreground">
          Provo:{" "}
          {SAMPLES.map((word) => (
            <button key={word} type="button" className="mr-3 underline" onClick={() => search(word)}>
              {word}
            </button>
          ))}
        </p>
      </form>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section className="min-w-0">
          {loading && (
            <div className="space-y-3">
              <Skeleton className="h-12 w-48" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          )}
          {!loading && error && (
            <Card>
              <CardContent className="text-destructive">{error}</CardContent>
            </Card>
          )}
          {!loading && !error && result && !result.found && (
            <Card>
              <CardContent className="space-y-3">
                <p>Fjala «{result.query}» nuk u gjet.</p>
                {result.suggestions.length > 0 && (
                  <p>
                    Provo:{" "}
                    {result.suggestions.slice(0, 6).map((word) => (
                      <button key={word} type="button" className="mr-3 underline" onClick={() => search(word)}>
                        {word}
                      </button>
                    ))}
                  </p>
                )}
              </CardContent>
            </Card>
          )}
          {!loading && !error && result?.found && result.merged && (
            <article className="space-y-6">
              <div>
                <h2 className="font-heading text-4xl md:text-5xl">{result.merged.headword}</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  {result.merged.pos.map((item) => (
                    <Badge key={item}>{item}</Badge>
                  ))}
                  {result.merged.synonyms.slice(0, 5).map((item) => (
                    <Badge key={item} variant="outline">
                      sin. {item}
                    </Badge>
                  ))}
                </div>
              </div>
              <ol className="list-decimal space-y-4 pl-5 text-lg leading-relaxed">
                {result.merged.senses.map((sense) => (
                  <li key={`${sense.number}-${sense.gloss.slice(0, 24)}`}>
                    {sense.labels.length > 0 && (
                      <span className="mr-2 text-muted-foreground italic">{sense.labels.join(", ")}</span>
                    )}
                    {sense.gloss}
                    {sense.examples.length > 0 && (
                      <span className="mt-1 block text-base text-muted-foreground italic">
                        {sense.examples.join(" · ")}
                      </span>
                    )}
                  </li>
                ))}
              </ol>
              {Object.entries(result.merged.translations).map(([lang, words]) => (
                <p key={lang}>
                  <span className="font-medium">{lang}:</span> {words.join(", ")}
                </p>
              ))}
              {result.merged.related.length > 0 && (
                <p>
                  <span className="font-medium">Shih edhe: </span>
                  {result.merged.related.slice(0, 10).map((word) => (
                    <button key={word} type="button" className="mr-3 underline" onClick={() => search(word)}>
                      {word}
                    </button>
                  ))}
                </p>
              )}
              {quotes.slice(0, 2).map((quote) => (
                <blockquote key={quote.excerpt.slice(0, 40)} className="border-l-4 border-primary pl-4 text-muted-foreground">
                  «{quote.excerpt}»
                  {quote.author ? ` — ${quote.author}` : ""}
                  {quote.title ? `, ${quote.title}` : ""}
                </blockquote>
              ))}
              <div>
                <h3 className="font-heading mb-3 text-2xl">Sipas burimit</h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  {result.sources.map((source) => (
                    <Card key={source.source} size="sm">
                      <CardHeader>
                        <CardTitle>{source.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {source.error && <p className="text-destructive">{source.error}</p>}
                        {!source.error && !source.found && <p className="text-muted-foreground">Nuk u gjet.</p>}
                        {source.found && (
                          <ol className="list-decimal space-y-1 pl-4">
                            {source.entries[0]?.senses.slice(0, 2).map((sense) => (
                              <li key={sense.gloss}>{sense.gloss}</li>
                            ))}
                          </ol>
                        )}
                        <a className="underline" href={source.url || source.homepage} target="_blank" rel="noreferrer">
                          Burimi
                        </a>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
              {result.attribution && (
                <p className="text-sm text-muted-foreground">{result.attribution.notice}</p>
              )}
            </article>
          )}
          {!loading && !error && !result && (
            <p className="text-muted-foreground">Shkruaj një fjalë shqipe për të parë kuptimet.</p>
          )}
        </section>

        <aside className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Fjala e ditës</CardTitle>
            </CardHeader>
            <CardContent>
              {day ? (
                <div className="space-y-2">
                  <button type="button" className="font-heading text-2xl underline" onClick={() => search(day.word)}>
                    {day.word}
                  </button>
                  <p className="text-muted-foreground">{day.definition}</p>
                </div>
              ) : (
                <p className="text-muted-foreground">{dayError || "Duke u ngarkuar…"}</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Më të kërkuarat</CardTitle>
            </CardHeader>
            <CardContent>
              {trending.length > 0 ? (
                <ul className="divide-y divide-border">
                  {trending.map((item) => (
                    <li key={item.word} className="flex items-baseline justify-between gap-3 py-2">
                      <button type="button" className="underline" onClick={() => search(item.word)}>
                        {item.word}
                      </button>
                      {item.views ? <span className="text-xs text-muted-foreground">{item.views}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">{trendError || "Duke u ngarkuar…"}</p>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  const data = (await response.json().catch(() => ({}))) as { detail?: string };
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data as T;
}
