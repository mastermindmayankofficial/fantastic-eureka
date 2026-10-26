# fantastic-eureka

A Telegram bot for managing ebook/library workflows, request handling, admin controls, and Goodreads-enriched indexing.

## Features

- Telegram bot with command-based admin tools
- User onboarding and referral quota tracking
- Request submission and request logging
- Template and media management
- Searchable indexed ebook metadata
- Auto-enrichment using Goodreads metadata
- File indexing into a configured storage group
- SQLite-backed persistence

## Tech Stack

- Python
- python-telegram-bot
- SQLite
- python-dotenv
- aiohttp

## Project Structure

```text
fantastic-eureka/
├── app/
│   ├── __init__.py
│   ├── bot.py
│   ├── config.py
│   └── db.py
├── modules/
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── file_db.py
│   └── goodreads_scraper.py
├── data/
│   └── bot.db
├── .env.example
├── main.py
├── requirements.txt
├── render.yaml
└── README.md
```

## Installation

1. Clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

## Environment Variables

Update `.env` with your real values:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789
STORAGE_GROUP_ID=-1001234567890
LOGGER_GROUP_ID=-1001234567891
INDEX_LOG_TOPIC_ID=12345
```

### Notes

- `BOT_TOKEN` is required for the bot to start.
- `ADMIN_IDS` is a comma-separated list of admin Telegram user IDs.
- `STORAGE_GROUP_ID` is where indexed ebooks are uploaded.
- `LOGGER_GROUP_ID` is where log events can be sent.
- `INDEX_LOG_TOPIC_ID` is optional if using a Telegram forum topic.

## Running the Bot

```bash
python main.py
```

## Deploy to Render

This project includes a `render.yaml` file for easy deployment on Render.

### Option 1: Deploy from GitHub with Render Blueprint

1. Push this repository to GitHub.
2. In Render, click New -> Blueprint.
3. Select this repository.
4. Render will read `render.yaml` and create the service automatically.

### Option 2: Manual Render Web Service

1. Create a new Web Service in Render.
2. Connect this GitHub repository.
3. Use these settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
4. Add the same environment variables from `.env.example` in the Render dashboard.
5. Click Create Web Service.

### Render configuration

The included `render.yaml` defines:

```yaml
services:
  - type: web
    name: fantastic-eureka
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
```

> Note: Because this bot uses long-lived polling, it should run as a persistent web service on Render.

## Common Commands

### User Commands

- `/start`
- `/help`
- `/search <keyword>`
- `/request <title> <author>`

### Admin Commands

- `/adminhelp`
- `/stats`
- `/ban <user>`
- `/unban <user>`
- `/addvol <user>`
- `/addprom <user>`
- `/addmod <user>`
- `/addadmin <user>`
- `/reloadconfig`
- `/setconfig <key> <value>`
- `/getconfig <key>`
- `/edittext <template_name>`
- `/setmedia <template_name>`
- `/removemedia <template_name>`
- `/addbutton <template_name> <label> <callback>`
- `/removebutton <template_name> <index>`
- `/listtemplates`
- `/showtemplate <template_name>`
- `/broadcast <target> <message>`
- `/broadcast_confirm everyone <message>`

## Goodreads Indexing

When an ebook file with an allowed extension is uploaded, the bot attempts to:

- validate the file extension
- clean the filename for search
- query Goodreads metadata
- index the file into the storage group
- save metadata in the local SQLite database

Supported ebook extensions:

- `.epub`
- `.pdf`
- `.mobi`

## Database

The bot uses SQLite and creates the database automatically at:

```text
data/bot.db
```

## Notes

- The bot expects the data folder to exist.
- The app will create SQLite tables automatically on startup.
- If `BOT_TOKEN` is missing, the bot exits with a runtime error.

## License

This project is provided as-is for educational and personal use unless otherwise specified.
