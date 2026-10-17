import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://amsect.org/members/job-opportunities"
STATE_PATH = Path("seen_jobs.json")
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def extract_jobs(html):
    soup = BeautifulSoup(html, "html.parser")
    jobs = {}
    for a in soup.find_all("a", href=True):
        title = clean(a.get_text(" ", strip=True))
        href = urljoin(PAGE_URL, a["href"])

        # Individual AmSECT job-detail pages use this URL path.
        if "/members/job-opportunities/" not in href.lower():
            continue
        if href.rstrip("/").lower() == PAGE_URL.rstrip("/").lower():
            continue
        if not title or title.lower() in {"next", "last", "1", "2", "3"}:
            continue

        # Capture the surrounding listing card/text for location and posting date.
        parent = a
        for _ in range(4):
            if parent.parent:
                parent = parent.parent
        context = clean(parent.get_text(" ", strip=True))
        context = context.replace(title, "", 1).strip(" |•-")
        # Avoid including unrelated text if the parent container is too broad.
        location = ""
        date = ""
        date_match = re.search(
            r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
            r"[A-Z][a-z]+ \d{1,2}, \d{4}", context
        )
        if date_match:
            date = date_match.group(0)
            context = clean(context.replace(date, ""))
        if context and len(context) < 120:
            location = context

        key = href.rstrip("/")
        jobs[key] = {
            "title": title,
            "url": href,
            "location": location or "See listing",
            "date": date or "See listing",
        }
    return jobs

def send_discord(job):
    message = (
        f"🫀 **New AmSECT Job Posting**\n"
        f"**{job['title']}**\n"
        f"📍 {job['location']}\n"
        f"🗓️ {job['date']}\n"
        f"🔗 {job['url']}"
    )
    response = requests.post(
        WEBHOOK,
        json={"content": message, "allowed_mentions": {"parse": []}},
        timeout=20,
    )
    response.raise_for_status()

def main():
    response = requests.get(
        PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AmSECTJobAlert/1.0)"},
        timeout=30,
    )
    response.raise_for_status()
    current = extract_jobs(response.text)
    if not current:
        raise RuntimeError(
            "No job links were detected. The page structure may have changed; "
            "stopping so the saved baseline is not overwritten."
        )

    old = {}
    if STATE_PATH.exists():
        old = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    # First run seeds the baseline without posting every existing listing.
    if not old:
        STATE_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
        print(f"Initialized baseline with {len(current)} existing listings; no alerts sent.")
        return

    new_jobs = [job for key, job in current.items() if key not in old]
    # Send alerts before updating state so a failed Discord post can retry next run.
    for job in reversed(new_jobs):
        send_discord(job)
        print(f"Alerted: {job['title']} — {job['url']}")

    merged = {**old, **current}
    STATE_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Checked {len(current)} current listings; {len(new_jobs)} new listing(s).")

if __name__ == "__main__":
    main()
