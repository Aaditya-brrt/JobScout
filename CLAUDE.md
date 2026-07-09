# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Single-script cron job that polls Runway's internal `jobPosting.getJobs` tRPC
endpoint every 5 minutes via GitHub Actions and emails new internship postings
scoring `>= MIN_MATCH_SCORE` (default 80). No framework, no dependencies —
stdlib only (`urllib`, `smtplib`, `json`).

## Run / test

```bash
# Local run — requires the three secrets in the environment
RUNWAY_COOKIE='<full cookie header>' \
GMAIL_ADDRESS='you@gmail.com' \
GMAIL_APP_PASSWORD='<16-char app password>' \
MIN_MATCH_SCORE=80 \
  python check_jobs.py
```

No test suite, no linter, no build. `.env` / `env.example` document the vars
but nothing loads `.env` automatically — vars must be exported (Actions passes
them via `env:` from GitHub Secrets).

## Architecture

`check_jobs.py` is the whole app. Flow in `main()`:

1. `fetch_jobs()` builds a tRPC batch URL (`build_url()`) with a hardcoded
   filter payload, authenticates via the `RUNWAY_COOKIE` header, and digs the
   jobs list out of the nested batch response
   (`data[0]["result"]["data"]["json"]["jobs"]`).
2. State lives in `seen_ids.json` — a committed list of Runway job IDs only
   (no job content). `.github/workflows/check_jobs.yml` commits it back after
   each run so state persists across Actions runs.
3. **First run baselines**: if `seen_ids.json` is absent, it saves current IDs
   and sends no email. This is intentional, not a bug.
4. Subsequent runs diff fresh jobs against seen IDs and email only new matches
   via Gmail SMTP SSL (port 465).

## Things that break and why

- **Cookie expiry**: `RUNWAY_COOKIE` is a NextAuth session token that expires
  (~30 days, sooner without active browsing). Script starts failing → re-extract
  from DevTools and update the `RUNWAY_COOKIE` GitHub Secret. There is no
  long-lived API key alternative.
- **Runway schema drift**: the response-unwrap path and filter payload assume
  Runway's current tRPC shape. If they change it, `fetch_jobs()` /
  `build_url()` need updating.

## Changing behavior

- Match threshold: `MIN_MATCH_SCORE` in the workflow's `env:` block.
- Poll frequency: the `cron` in `check_jobs.yml` (Actions cron is best-effort,
  runs can lag a few minutes).
- Other job filters (remote-only, companies, employment type): the `filters`
  dict in `build_url()`.

## Secrets

Repo is intended to be public. The Runway cookie and Gmail credentials live
**only** in GitHub Secrets (`RUNWAY_COOKIE`, `GMAIL_ADDRESS`,
`GMAIL_APP_PASSWORD`, optional `TO_EMAIL`) — never in files. `seen_ids.json`
holds only opaque job IDs and is safe to commit.
