# Telegram Restricted Content Downloader Bot

## Overview
A Telegram bot that allows users to download restricted content from Telegram channels. Built with Pyrogram and includes a web server for ad verification callbacks.

## Architecture
- **Backend**: Python with Pyrogram (Telegram MTProto API)
- **Web Server**: Waitress WSGI server on port 5000
- **Database**: SQLite (telegram_bot.db)
- **Deployment**: Single process running both bot and web server

## Key Files
- `server_wsgi.py` - Main entry point (runs WSGI server + bot in background thread)
- `main.py` - Telegram bot handlers and commands
- `config.py` - Configuration from environment variables
- `database_sqlite.py` - SQLite database operations
- `ad_monetization.py` - Ad verification system
- `helpers/` - Utility functions for downloads, sessions, etc.

## Environment Variables Required
- `API_ID` - Telegram API ID
- `API_HASH` - Telegram API Hash
- `BOT_TOKEN` - Telegram Bot Token
- `OWNER_ID` - Bot owner's Telegram user ID
- `BOT_USERNAME` - Bot username (optional)
- `GITHUB_TOKEN` - For cloud backups (optional)
- `GITHUB_BACKUP_REPO` - GitHub repo for backups (optional)
- `CLOUD_BACKUP_SERVICE` - Set to "github" to enable backups (optional)
- `ADMIN_PASSWORD` - Password for admin web panel (optional)

## Running
The workflow runs `python server_wsgi.py` which:
1. Starts Waitress WSGI server on 0.0.0.0:5000
2. Starts Telegram bot in a background thread
3. Handles web requests for ad verification

## Web Endpoints
- `/` - Status endpoint (returns JSON)
- `/health` - Health check (204 No Content)
- `/verify-ad` - Ad verification callback
- `/admin/login` - Admin panel login
- `/files` - Admin file browser (requires auth)
