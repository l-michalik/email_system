# Email System

`main.py` runs the monitoring pass immediately and logs module summaries plus the fetched items to stdout.

Run it once:

```bash
uv run python main.py
```

Cron example every 5 minutes:

```cron
*/5 * * * * cd /Users/lukaszmichalik/Desktop/email_system && uv run python main.py >> monitor.log 2>&1
```
