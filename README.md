# Fjalor Shqip

Looks up Albanian words on fjale.al, Fjalorthi, Fjalorth.com and Wiktionary.

The site is in `web`. `app` is the same thing as a FastAPI server, if you'd rather run that.

## Site

```bash
cd web
npm install
npm run dev
```

Open the address it prints. `dashuri` and `shtëpi` are decent words to try.

## Vercel

Push the repo to GitHub and import it on Vercel. Set the root directory to `web`. No environment variables.

## Routes

- `GET /api/v1/lookup?q=dashuri`
- `GET /api/v1/suggest?q=dash`
- `GET /api/v1/word-of-the-day`
- `GET /api/v1/quotes?q=dashuri`
- `GET /api/v1/trending`
- `GET /api/v1/sources`
- `GET /api/v1/health`

Pass `source` more than once if you only want some of them: `fjale`, `fjalorthi`, `fjalorth`, `wiktionary_en`, `wiktionary_sq`.

## Python

```bash
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`docker compose up --build` also works. `pytest` for the tests.

Wiktionary text is CC BY-SA 4.0. The code here is MIT.
