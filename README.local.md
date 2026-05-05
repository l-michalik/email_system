# Email System

Monitors Joule CRM every 5 minutes and sends email notifications for:

* New chatbot-created briefs
* Qualifying brief updates
* Jobs moved to Client Review

## Setup Existing CRM Data

To preload existing chatbot briefs and related jobs into the local database:

```bash
uv run -m scripts.fetch_briefs
```

Use this before enabling cron in an environment that already has active Joule data.

## Run Manually

Run one monitoring pass:

```bash
uv run python main.py
```

This will:

* Load `.env`
* Fetch CRM changes since the last successful sync
* Evaluate notification rules
* Send eligible emails
* Update local snapshots and sync checkpoints

## Schedule with Cron

Open crontab:

```bash
crontab -e
```

Add:

```cron
*/5 * * * * cd /Users/lukaszmichalik/Desktop/email_system && /opt/homebrew/bin/uv run python main.py >> /Users/lukaszmichalik/Desktop/email_system/monitor.log 2>&1
```

If `uv` is already available to cron:

```cron
*/5 * * * * cd /Users/lukaszmichalik/Desktop/email_system && uv run python main.py >> /Users/lukaszmichalik/Desktop/email_system/monitor.log 2>&1
```

After adding cron, check that:

* `.env` exists in the repo root
* `uv run python main.py` succeeds manually
* `monitor.log` is being written
* `data/briefs.sqlite3` is created or updated

## Send Test Email

```bash
uv run python send_email.py
```

## Run Tests

```bash
uv run python -m unittest discover -s tests
```
