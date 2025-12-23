# Telegram Media Bot - Replit Deployment

## Project Overview
A production-ready Telegram bot for downloading restricted media content with features including:
- User authentication with phone number
- One-time password (OTP) verification
- Session management (max 3 concurrent sessions)
- Download queue management with priority for premium users
- Ad monetization system
- Legal terms acceptance
- Payment integration (PayPal, UPI, Crypto)
- Admin controls and broadcast messaging

## Recent Changes (Session 2 - Dec 23, 2025)

### Crash Recovery System Implementation ✅
**Status:** Complete and operational

1. **Created recovery.py** - Intelligent crash recovery wrapper
   - Automatic restart on bot crashes
   - Exponential backoff (10s to 5 min retries)
   - Max 5 restart attempts with auto-reset after 1 hour
   - Smart error detection and recovery

2. **Enhanced Authentication Recovery**
   - Detects invalid session errors
   - Auto-removes corrupted session files
   - Clears invalid env vars
   - Preserves API credentials

3. **Updated Workflow**
   - Changed from `python main.py` to `python recovery.py`
   - Ensures recovery system always active
   - Graceful session cleanup on shutdown

### Key Features of Recovery System
- **Automatic Restart**: On any uncaught exception
- **Exponential Backoff**: Prevents API rate limiting
- **Auth Error Handling**: Clears bad sessions automatically
- **Comprehensive Logging**: Full crash history tracking
- **Graceful Cleanup**: Disconnects sessions before restart
- **Max Retries**: Prevents infinite restart loops

## Project Structure

```
.
├── main.py                 # Bot core logic and handlers
├── recovery.py             # Crash recovery wrapper (ENTRY POINT)
├── config.py               # Configuration (API keys, settings)
├── database_sqlite.py      # SQLite database management
├── logger.py               # Logging system
├── attribution.py          # Creator attribution
├── legal_acceptance.py     # Legal terms handling
├── phone_auth.py           # Phone authentication handler
├── access_control.py       # User access control
├── admin_commands.py       # Admin command handlers
├── ad_monetization.py      # Ad system integration
├── queue_manager.py        # Download queue management
├── server_wsgi.py          # Web server (if needed)
├── cloud_backup.py         # Cloud backup integration
├── cache.py                # Caching system
│
├── helpers/
│   ├── __init__.py
│   ├── utils.py            # Utility functions
│   ├── files.py            # File operations
│   ├── transfer.py         # Media transfer
│   ├── msg.py              # Message parsing
│   ├── session_manager.py  # User session management
│   ├── cleanup.py          # Cleanup operations
│
├── templates/
│   └── verify_success.html # Success verification page
│
├── legal/
│   ├── README_IMPORTANT.md
│   ├── privacy_policy.txt
│   └── terms_and_conditions.txt
│
└── requirements.txt        # Python dependencies
```

## Dependencies

### Core
- pyrogram >= 2.0.0 (Telegram client library)
- tgcrypto (Telegram encryption)
- cryptg (Cryptography)

### System
- psutil (System monitoring)
- uvloop (Async event loop optimization)

### Web
- flask (Web framework)
- waitress (WSGI server)
- orjson (JSON serialization)

## Environment Variables Required

```
# Telegram Credentials (REQUIRED)
API_ID=<your_api_id>
API_HASH=<your_api_hash>
BOT_TOKEN=<your_bot_token>

# Bot Configuration
OWNER_ID=<owner_telegram_id>
BOT_USERNAME=<bot_username>

# Optional: Force Subscribe
FORCE_SUBSCRIBE_CHANNEL=<channel_id>

# Optional: Media Dump Channel
DUMP_CHANNEL_ID=<channel_id>

# Payment Methods
ADMIN_USERNAME=<username>
PAYPAL_URL=<paypal_link>
UPI_ID=<upi_id>
TELEGRAM_TON=<ton_address>
CRYPTO_ADDRESS=<crypto_address>

# Cloud Backup (GitHub)
CLOUD_BACKUP_SERVICE=github
GITHUB_TOKEN=<token>
GITHUB_BACKUP_REPO=<repo>
```

## Workflow Configuration

Current workflow runs:
```bash
python recovery.py
```

This ensures:
- Automatic crash recovery
- Intelligent restart logic
- Graceful error handling
- Persistent bot operation

## Resource Management (Replit)

- **Memory**: Optimized for 512MB limit
  - Max 3 concurrent user sessions
  - Aggressive worker thread reduction
  - In-memory sessions only
  
- **CPU**: 1 worker thread (constrained environment)

- **Storage**: SQLite database + temporary downloads
  - Auto-cleanup every 30 minutes
  - Prevents disk space overflow

## Getting Started

1. **Set environment variables** in Replit Secrets
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Run bot**: Workflow automatically starts with recovery
4. **Monitor**: Check logs for recovery messages

## Troubleshooting

### Bot keeps restarting
- Check logs for error messages
- Verify API credentials are correct
- Ensure BOT_TOKEN is valid

### Auth errors in logs
- Recovery system will auto-clear bad sessions
- No manual action needed

### Out of memory errors
- Reduce concurrent downloads in config
- Check for hanging user sessions
- Monitor with `memory_monitor.py`

## Deployment Checklist

- [x] Core bot functionality
- [x] Session management
- [x] Download queue
- [x] Auth handling
- [x] Ad monetization
- [x] Admin controls
- [x] **Crash recovery system**
- [ ] Custom domain (optional)
- [ ] Database backup automation

## User Preferences
- Production-ready code only
- Comprehensive error handling
- Memory-efficient design
- Smart recovery mechanisms

## Last Updated
December 23, 2025 - Crash Recovery System Implementation
