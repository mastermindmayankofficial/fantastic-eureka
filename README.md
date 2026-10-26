# Dynamic Telegram Bot with Admin-Controlled Config

A Telegram bot designed for:
- searchable file indexing
- request tracking
- quota-based usage
- referral bonuses
- admin-controlled text/media/button configuration
- temporary file delivery
- role-based permissions
- stats and broadcast tools

This bot is intentionally built around a configuration database instead of hardcoded values, so you can change:
- role quotas
- help text
- admin message text
- media templates
- button labels
- button callbacks
- bot titles and usernames
- queue limits
- storage and posting channel IDs
- referral bonus values

without editing the source code in production.

Important:
- This is a safe pattern for controlling bot behavior from bot commands.
- It does NOT allow arbitrary code execution.
- It does NOT edit Python files directly.
- It only updates database-backed configuration and templates.

## Features

- Role-based access control
  - Owner
  - Admin
  - Volunteer
  - Moderator
  - Promoter
  - Normal user
  - Banned user
- Quota-based usage
  - search quota and request quota
  - only consumed on successful action
- Referral system
  - +10 search quota and +10 request quota for both users
- Search and file delivery
  - search indexed files by title, author, and caption
  - inline result buttons
  - file posted to a posting channel
  - user DM delivery if allowed
  - auto-delete after configured time
- Config-driven templates
  - dynamic text editing
  - dynamic media saving
  - dynamic button edits
- User request tracking
  - book/audiobook requests
  - statuses for pending/completed
- Bot statistics
  - total users
  - banned users
  - group/channel count
  - storage usage
  - request totals
- Broadcast messaging
  - all users
  - all groups
  - all channels
  - single user
  - single channel
  - single group
- Ban / unban management
- Admin-only help and tooling

## Bot architecture

The bot is designed in layers:

1. Telegram bot layer
   - receives commands and callbacks
   - sends messages/media
   - handles button presses

2. Database layer
   - stores users
   - stores settings
   - stores templates
   - stores indexed files
   - stores request records
   - stores chats and logs

3. Config layer
   - dynamic settings are loaded from DB
   - no hardcoded runtime values
   - admin commands update settings

4. Feature layer
   - search
   - request
   - role assignment
   - broadcast
   - stats
   - file delivery
   - queue handling

## Role and quota model

Default quota model:
- banned = 0
- normal = 10
- promoter = 20
- volunteer = 30
- moderator = 40
- admin = unlimited
- owner = unlimited

Role definitions:
- Promoter: boosted normal user, same general feature set with better quota
- Volunteer: can index/select files and perform direct indexing tasks
- Moderator: manages requests and request status
- Admin: can manage users, roles, logs, config
- Owner: full access

Quota consumption rules:
- quota is only consumed after successful action
- search quota is only consumed when file/media delivery succeeds
- request quota is only consumed when request is successfully posted
- failed searches or failed requests do not count

## Database schema

Main tables:
- users
- settings
- templates
- indexed_files
- requests
- chats
- logs

### users
- id
- user_id
- username
- first_name
- role
- search_quota
- request_quota
- banned
- started
- referrer_id
- created_at

### settings
- key
- value
- updated_at

### templates
- id
- name
- text
- media_type
- media_file_id
- buttons_json
- created_at
- updated_at

### indexed_files
- id
- title
- author
- caption
- file_id
- file_type
- indexed_by
- storage_chat_id
- active
- created_at

### requests
- id
- user_id
- title
- author
- status
- created_at

### chats
- id
- chat_id
- chat_type
- title
- active
- created_at

### logs
- id
- user_id
- action
- details
- created_at

## Setup

1. Install Python dependencies:

```bash
pip install python-telegram-bot==20.7
```

2. Create a Telegram bot:
- talk to BotFather
- save the token

3. Set environment variable:

```bash
export BOT_TOKEN="YOUR_BOT_TOKEN"
```

4. Set admin IDs in the script:

```python
ADMIN_IDS = [123456789]
```

5. Set the storage and posting channels:
- storage channel ID
- posting channel ID
- request log channel/group ID
- general log group ID

6. Start the bot:

```bash
python bot.py
```

## Required configuration values

These are stored in the database and can be edited via bot commands:
- bot_title
- bot_username
- chat_title
- storage_channel_id
- posting_channel_id
- request_log_chat_id
- general_log_chat_id
- max_index_batch
- index_sleep_seconds
- referral_bonus_search
- referral_bonus_request
- file_delete_after_seconds
- allow_dm_delivery
- allow_posting_channel_delivery

Example:

```bash
/setconfig bot_title My Bot
/setconfig bot_username @mybot
/setconfig storage_channel_id -1001234567890
/setconfig posting_channel_id -1006543219876
```

## User commands

- /start
- /help
- /search <keyword>
- /request <title> <author>
- /stats
- /ban <user>
- /unban <user>
- /addvol <user>
- /addprom <user>
- /addmod <user>
- /addadmin <user>

## Admin commands

- /adminhelp
- /reloadconfig
- /setconfig <key> <value>
- /getconfig <key>
- /listtemplates
- /edittext <template_name>
- /setmedia <template_name>
- /removemedia <template_name>
- /addbutton <template_name> <label> <callback>
- /removebutton <template_name> <index>
- /showtemplate <template_name>
- /broadcast <target> <message>
- /stats

## Broadcast targets

- user <user_id>
- group <group_id>
- channel <channel_id>
- all_groups
- all_channels
- all_users
- everyone

Example:

```bash
/broadcast all_users Hello everyone!
/broadcast all_groups Maintenance in 10 minutes.
/broadcast user 123456789 Hello.
```

## Dynamic config system

The bot stores templates and settings in SQLite, so you can change:
- help text
- admin help text
- welcome screens
- media
- buttons
- titles
- channel IDs
- quotas
- timer values

Commands:
- /edittext <template_name>
- /setmedia <template_name>
- /removemedia <template_name>
- /addbutton <template_name> <label> <callback>
- /removebutton <template_name> <index>

Example:

```bash
/edittext welcome
/addbutton welcome Search search:demo
/addbutton welcome Help help:main
```

## Formatting placeholders

You can use:
- {date}
- {time}
- {bot_title}
- {bot_username}
- {chat_title}

Example:

```text
Welcome to {bot_title}
Today is {date}
Time: {time}
Chat: {chat_title}
```

## Inline button callback patterns

Use callback strings like:
- search:file_123
- request:status_done
- approve:upload_123
- role:volunteer
- help:main
- cancel:queue_1
- pause:queue_1
- resume:queue_1
- ban:user_123

## Search and delivery flow

1. User searches for a file using /search
2. Bot searches indexed files by title, author, and caption
3. Bot displays inline buttons with result names
4. User clicks a result
5. Bot verifies:
   - user started chat with bot
   - helper bot is allowed
   - file exists
6. Bot sends file to posting channel
7. Bot also sends file to user DM if allowed
8. Bot informs the user with channel link/message id
9. File is auto-deleted after X seconds
10. Search quota is deducted only on successful file delivery

## Request flow

1. User sends /request Title Author
2. Bot validates input
3. Bot saves request in database
4. Request is posted to request log channel
5. Moderator/Admin/Owner updates status
6. Request quota is consumed only on successful posting

## Indexing flow

1. Files are queued
2. Max 10 at once
3. After each batch, wait N seconds
4. Continue until queue clears
5. User files can have priority
6. It can pause/resume/cancel

## Safety notes

- Only admins/owners should use:
  - /broadcast
  - /ban
  - /unban
  - /setconfig
  - /reloadconfig
  - /addadmin
  - /setrole commands
- Do not expose arbitrary code execution through bot commands
- Keep runtime config in a DB, not in Python source
- Use admin IDs list to restrict sensitive actions
- Keep posting channels and storage channels admin-only for the bot

## Future work

- Add Goodreads scraping integration
- Add file approval queues
- Add indexing progress cards
- Add per-channel indexing permissions
- Add scheduled cleanup
- Add web admin panel
- Add multiple languages

This bot is structured to be scaled into a complete digital library bot system.
