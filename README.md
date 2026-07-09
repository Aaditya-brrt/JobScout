# Runway Internship Notifier

Polls Runway's `jobPosting.getJobs` endpoint every 5 minutes via GitHub Actions,
and emails you when a new **internship** posting appears with a match score
of 80 or higher.

## How it works

- `check_jobs.py` calls Runway's internal API using your logged-in session
  cookie, filters to internships with `matchScore >= 80`, and diffs the
  results against `seen_ids.json` (committed to the repo) to find only
  postings it hasn't alerted on before.
- New matches trigger an email via Gmail SMTP.
- `.github/workflows/check_jobs.yml` runs this on a 5-minute cron schedule
  and commits the updated `seen_ids.json` back to the repo so state persists
  between runs.

`seen_ids.json` only ever contains Runway's internal job IDs (e.g.
`cmrcd6c1a000552iuzk7k28xo`) — not job content or anything sensitive, so it's
safe to commit even in a public repo.

## ⚠️ Important: this repo is public — keep secrets OUT of the code

Since you're planning to make this repo public, **never commit**:
- Your Runway session cookie
- Your Gmail address/app password

These must live only in **GitHub Secrets** (Settings → Secrets and variables →
Actions), which are encrypted and never appear in your repo's files or logs.
The `.gitignore` in this repo also excludes any local `.env` file if you test
locally, so a stray file doesn't get committed by accident.

## One-time setup

### 1. Create the repo
Push these files to a new GitHub repo (public is fine — no secrets live in
the files themselves).

### 2. Get your Runway session cookie
1. Log into https://app.joinrunway.io in Chrome.
2. Open DevTools → Network tab → Fetch/XHR filter.
3. Reload `/explore`, click any request to `app.joinrunway.io`.
4. Under Request Headers, copy the **entire** `cookie:` value (the whole
   string, all the `key=value; key=value; ...` pairs).

This cookie is a NextAuth session token — it will expire after some period of
inactivity (commonly ~30 days, but background polling doesn't refresh it the
way active browsing does). If the script starts failing, re-extract a fresh
cookie the same way and update the secret.

### 3. Get a Gmail App Password
1. Go to https://myaccount.google.com/apppasswords (requires 2-Step
   Verification enabled on the account).
2. Generate an app password for "Mail".
3. Copy the 16-character password.

### 4. Add GitHub Secrets
In your repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add:
- `RUNWAY_COOKIE` — the full cookie string from step 2
- `GMAIL_ADDRESS` — your Gmail address
- `GMAIL_APP_PASSWORD` — the app password from step 3

(Optional: add `TO_EMAIL` as a secret too if you want alerts sent somewhere
other than `GMAIL_ADDRESS`, and update the workflow's `env:` block to pass it
through.)

### 5. Enable Actions and test
1. Go to the **Actions** tab in your repo, enable workflows if prompted.
2. Click into "Check Runway Jobs" → **Run workflow** to trigger it manually.
3. Check the run logs. The **first run** just establishes a baseline (saves
   current job IDs, sends no email) — this is expected, not a bug.
4. After that, each run only emails you about jobs that are genuinely new
   since the last check.

## Adjusting settings

- **Match score threshold**: change `MIN_MATCH_SCORE: "80"` in
  `.github/workflows/check_jobs.yml`.
- **Poll frequency**: change the cron expression in the same file (GitHub
  Actions schedules are best-effort and may run a few minutes late under
  load — this isn't a bug, it's a platform limitation).
- **Other filters** (remote-only, specific companies, etc.): can be added to
  the `filters` dict in `check_jobs.py`'s `build_url()` function.

## Known limitations

- Not truly instant — bounded by the 5-minute cron interval (and GitHub's
  scheduling can add its own delay).
- Depends on Runway's internal API shape staying the same; if they change
  their tRPC schema, `check_jobs.py` will need updating.
- Cookie-based auth means periodic manual refresh is needed (no long-lived
  API key is available here).