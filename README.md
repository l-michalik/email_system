# Email System

`main.py` runs the monitoring pass immediately and logs module summaries plus the fetched items to stdout.
Chatbot-created briefs are also stored locally in `data/briefs.sqlite3`.

Run it once:

```bash
uv run python main.py
```

Cron example every 5 minutes:

```cron
*/5 * * * * cd /Users/lukaszmichalik/Desktop/email_system && uv run python main.py >> monitor.log 2>&1
```

Send a test email

```bash
uv run python send_email.py
```
