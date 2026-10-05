const USER_AGENT = "FjalorShqip/1.0";

export async function upstreamGet(
  url: string,
  headers: Record<string, string> = {},
): Promise<{ ok: boolean; status: number; url: string; text: string }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 9000);
  try {
    const response = await fetch(url, {
      headers: {
        "User-Agent": USER_AGENT,
        Accept: "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "sq,en;q=0.8",
        ...headers,
      },
      redirect: "follow",
      signal: controller.signal,
      cache: "no-store",
    });
    return {
      ok: response.ok,
      status: response.status,
      url: response.url,
      text: await response.text(),
    };
  } finally {
    clearTimeout(timer);
  }
}
