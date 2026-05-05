# Email System

Run the service on the server with Docker.

## 1. Prepare `.env`

Create `.env` in the project root with the required variables:

```env
CRM_BASE_URL=...
CRM_CLIENT_ID=...
CRM_CLIENT_SECRET=...
CRM_USERNAME=...
CRM_PASSWORD=...
SMTP_HOST=...
SMTP_PORT=...
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM=...
DEFAULT_RECIPIENT=...
```

## 2. Start the service

From `/var/www/joule_email_system`:

```bash
docker compose up -d --build
```

The container runs the monitor every 5 minutes and stores data in `./data`.

## 3. Preload existing CRM data

If the CRM already has active data, preload briefs before letting the monitor run:

```bash
docker compose run --rm email-system python -m scripts.fetch_briefs
```

## 4. Check logs

```bash
docker compose logs -f email-system
```

## 5. Run one manual pass

```bash
docker compose run --rm email-system python main.py
```

## 6. Stop the service

```bash
docker compose down
```
