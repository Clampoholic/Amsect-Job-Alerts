import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://amsect.org/members/job-opportunities"
STATE_FILE = Path("seen_jobs.json")


def get_webhook():
    url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL is empty. Check that monitor.yml maps "
            "DISCORD_WEBHOOK_URL to secrets.AMSECTPOSTINGS, and that "
            "AMSECTPOSTINGS contains the full Discord webhook URL."
        )
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in {
        "discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"
    } or not parsed.path.startswith("/api/webhooks/"):
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL is not a valid Discord webhook URL. "
            "It should begin with https://discord.com/api/webhooks/"
        )
    print("Discord webhook configuration verified (URL hidden).")
    return url


def find_jobs(html):
    soup = BeautifulSoup(html, "html.parser")
    jobs = {}
    for link in soup.find_all("a", href=True):
        title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
        url = urljoin(PAGE_URL, link["href"])
        parsed = urlparse(url)
        if parsed.netloc.lower() not in {"amsect.org", "www.amsect.org"}:
            continue
        if not parsed.path.lower().startswith("/members/job-opportunities/"):
            continue
        if not title or title.lower() in {"next", "last", "1", "2", "3"}:
            continue
        jobs[url.rstrip("/")] = {"title": title, "url": url}
    return jobs


def main():
    webhook = get_webhook()
    response = requests.get(
        PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AmSECTJobAlert/1.0)"},
        timeout=30,
    )
    response.raise_for_status()
    jobs = find_jobs(response.text)
    print(f"Found {len(jobs)} AmSECT job links.")
    if not jobs:
        raise RuntimeError(
            "No individual job links found on AmSECT. The page layout or "
            "job URL pattern may have changed. No saved data was changed."
        )

    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
        print("First run: saved existing jobs as baseline; no alerts sent.")
        return

    seen = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    new_jobs = [job for key, job in jobs.items() if key not in seen]
    for job in reversed(new_jobs):
        content = f"ð« **New AmSECT Job Posting**\n**{job['title']}**\n{job['url']}"
        result = requests.post(
            webhook,
            json={"content": content, "allowed_mentions": {"parse": []}},
            timeout=20,
        )
        result.raise_for_status()
        print(f"Sent Discord alert: {job['title']}")

    seen.update(jobs)
    STATE_FILE.write_text(json.dumps(seen, indent=2), encoding="utf-8")
    print(f"Finished: {len(new_jobs)} new jobs; {len(jobs)} current jobs.")


if __name__ == "__main__":
    main()
