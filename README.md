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


  Status                                           316 `FD_316`
{'options': [{'id': 0, 'value': ''}], 'fieldDefinitionId': 4406, 'name': 'Link to Output Files (Client)'}
'fieldDefinitionId': 229, 'name': 'Assets'
{'options': [{'id': 0, 'value': '14994'}], 'fieldDefinitionId': 4660, 'name': 'Brief Number'}