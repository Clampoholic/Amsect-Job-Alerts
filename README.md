# AmSECT → Discord Job Alerts (free)

This GitHub Actions workflow checks the public AmSECT job board hourly and posts new listing links to a Discord channel via webhook.

## Setup

1. Create a **public** GitHub repository.
2. Upload `monitor.py` to the repository root.
3. Create `.github/workflows/monitor.yml` and paste in the contents of the supplied workflow file.
4. In Discord, open the target channel's **Edit Channel → Integrations → Webhooks**, create a webhook, and copy its URL.
5. In GitHub, open the repository's **Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `DISCORD_WEBHOOK_URL`
   - Secret: paste the webhook URL
6. Open the repository's **Actions** tab and enable workflows if prompted.
7. Open **AmSECT Discord Job Alerts** and choose **Run workflow** once. This first run records current listings as a baseline and does not send alerts for existing jobs.
8. Subsequent scheduled runs send alerts for new listing URLs.

## Notes

- The schedule runs hourly, at minute 17.
- On the first run, existing listings are saved without alerts.
- If the website changes its HTML structure, the script may need adjustment.
- The repository is public, so do not put the webhook URL in code or commit it. Store it only as the `DISCORD_WEBHOOK_URL` repository secret.
- GitHub may disable scheduled workflows in public repositories after 60 days without repository activity. Check the Actions tab periodically.
