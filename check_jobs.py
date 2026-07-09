"""
Polls Runway's internal jobPosting.getJobs endpoint, diffs against previously
seen job IDs, and emails any new INTERNSHIP postings at or above MIN_MATCH_SCORE.

Required environment variables (set as GitHub Secrets, never committed):
  RUNWAY_COOKIE       - full "cookie" request header value from a logged-in
                         browser session on app.joinrunway.io (DevTools > Network
                         > any request to app.joinrunway.io > Headers > Request
                         Headers > cookie). This expires periodically and will
                         need to be refreshed - see README.

  GMAIL_ADDRESS       - the Gmail address to send FROM
  GMAIL_APP_PASSWORD  - a Gmail App Password (not your normal password) -
                         generate at https://myaccount.google.com/apppasswords

Optional environment variables:
  TO_EMAIL            - where to send alerts (defaults to GMAIL_ADDRESS)
  MIN_MATCH_SCORE     - minimum match score to alert on (defaults to 80)
"""

import json
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage

RUNWAY_COOKIE = os.environ["RUNWAY_COOKIE"].strip()
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"].strip()
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"].strip()
TO_EMAIL = os.environ.get("TO_EMAIL", GMAIL_ADDRESS).strip()
MIN_MATCH_SCORE = int(os.environ.get("MIN_MATCH_SCORE", "80"))

SEEN_IDS_FILE = "seen_ids.json"
BASE_URL = "https://app.joinrunway.io/api/trpc/jobPosting.getJobs"


def build_url() -> str:
    """Builds the tRPC batch URL requesting internship postings sorted by match score."""
    payload = {
        "0": {
            "json": {
                "filters": {
                    "search": None,
                    "location": [],
                    "companies": None,
                    "dateFilter": "1",
                    "employmentType": "INTERNSHIP",
                    "minimumEducationLevel": None,
                    "workArrangement": None,
                    "minMatchScore": MIN_MATCH_SCORE,
                    "maxMatchScore": 100,
                    "startDate": None,
                    "startDateEnd": None,
                    "visaSponsorFilter": None,
                    "hideShittyJobs": None,
                    "topTierOnly": None,
                },
                "hasLogo": None,
                "limit": 40,
                "sortBy": "matchScore",
                "direction": "forward",
            }
        }
    }
    encoded = urllib.parse.quote(json.dumps(payload))
    return f"{BASE_URL}?batch=1&input={encoded}"


def fetch_jobs() -> list:
    url = build_url()
    req = urllib.request.Request(url)
    req.add_header("Cookie", RUNWAY_COOKIE)
    req.add_header("Accept", "*/*")
    req.add_header("Referer", "https://app.joinrunway.io/explore")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code} error from Runway. Response body:\n{error_body}")
        raise

    data = json.loads(body)
    # Single-query batch response: a list with one element holding our result
    return data[0]["result"]["data"]["json"]["jobs"]


def load_seen_ids() -> set:
    if os.path.exists(SEEN_IDS_FILE):
        with open(SEEN_IDS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ids(ids: set) -> None:
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump(sorted(ids), f, indent=2)


def send_email(new_jobs: list) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"{len(new_jobs)} new high-match internship(s) on Runway"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = TO_EMAIL

    lines = []
    for job in new_jobs:
        apply_link = job.get("applyUrl") or job.get("shortenedUrl") or ""
        lines.append(
            f"{job.get('title')} @ {job.get('company')}\n"
            f"Match: {job.get('matchScore')}  |  Location: {job.get('location')}  "
            f"|  {job.get('workArrangement')}\n"
            f"Apply: {apply_link}\n"
        )
    msg.set_content("\n".join(lines))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)


def main() -> None:
    first_run = not os.path.exists(SEEN_IDS_FILE)
    seen_ids = load_seen_ids()
    jobs = fetch_jobs()

    if first_run:
        # Establish a baseline on the very first run so we don't blast an
        # email for every job that already exists at setup time.
        print(f"First run: baselining {len(jobs)} existing job id(s), no email sent.")
        save_seen_ids({j["id"] for j in jobs})
        return

    new_jobs = [
        j for j in jobs
        if j["id"] not in seen_ids and j.get("matchScore", 0) >= MIN_MATCH_SCORE
    ]

    if new_jobs:
        print(f"Found {len(new_jobs)} new matching job(s). Sending email...")
        send_email(new_jobs)
    else:
        print("No new matching jobs this run.")

    save_seen_ids(seen_ids | {j["id"] for j in jobs})


if __name__ == "__main__":
    main()