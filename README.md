# Email System

System monitors Joule CRM for chatbot-created briefs and sends email notifications for:

- brief creation
- qualifying brief updates
- jobs moved to Client Review

Monitoring is designed to run every 5 minutes.

## Bootstrap Existing Data

If you want the local database to start with existing chatbot briefs and related jobs, run:

```bash
uv run python scripts/fetch_briefs.py
```

This is useful before enabling cron in an environment that already has active data in Joule.

## Run One Monitoring Pass

```bash
uv run python main.py
```

This command:

- loads settings from `.env`
- fetches CRM changes since the last successful sync
- evaluates notification triggers
- sends eligible emails
- updates local snapshots and checkpoints

## Cron: Every 5 Minutes

Open crontab:

```bash
crontab -e
```

Add this entry:

```cron
*/5 * * * * cd /Users/lukaszmichalik/Desktop/email_system && /opt/homebrew/bin/uv run python main.py >> /Users/lukaszmichalik/Desktop/email_system/monitor.log 2>&1
```

If `uv` is already available in cron `PATH`, you can use:

```cron
*/5 * * * * cd /Users/lukaszmichalik/Desktop/email_system && uv run python main.py >> /Users/lukaszmichalik/Desktop/email_system/monitor.log 2>&1
```

Recommended checks after adding cron:

- confirm `.env` exists in the repo root
- run `uv run python main.py` once manually
- verify `monitor.log` is being written
- verify the first run creates or updates `data/briefs.sqlite3`

## Manual Email Check

```bash
uv run python send_email.py
```

## Tests

Run:

```bash
uv run python -m unittest discover -s tests
```
