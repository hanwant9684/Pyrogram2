# Copyright (C) @Wolfy004
# Channel: https://t.me/Wolfy004

import asyncio
from functools import wraps
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChannelPrivate
from database_sqlite import db
from logger import LOGGER
from config import PyroConf

# Helper function to avoid redundant DB calls in decorators
async def _register_and_check_user(client, message) -> tuple[int, bool]:
    """
    Register user and check ban status in one go.
    Returns (user_id, is_banned)
    """
    user_id = message.from_user.id
    
    # Get sender info (Pyrogram Message has from_user directly)
    sender = message.from_user
    
    # Check if user is new
    user_exists = db.get_user(user_id) is not None
    
    # Add user to database if not exists
    db.add_user(
        user_id=user_id,
        username=sender.username if sender else None,
        first_name=sender.first_name if sender else None,
        last_name=sender.last_name if hasattr(sender, 'last_name') and sender else None
    )
    
    # Log new user registration
    if not user_exists:
        username = f"@{sender.username}" if sender.username else "No username"
        name = sender.first_name if sender.first_name else "Unknown"
        LOGGER(__name__).info(f"📝 NEW USER REGISTERED | ID: {user_id} | Username: {username} | Name: {name}")
    
    # Check if banned (uses cache)
    is_banned = db.is_banned(user_id)
    if is_banned:
        username = f"@{sender.username}" if sender.username else user_id
        LOGGER(__name__).warning(f"🚫 BANNED USER ATTEMPTED ACCESS | ID: {user_id} | Username: {username}")
    
    return user_id, is_banned

def admin_only(func):
    """Decorator to restrict command to admins only (optimized)"""
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        user_id, is_banned = await _register_and_check_user(client, message)
        
        if is_banned:
            await client.send_message(message.chat.id, "❌ **You are banned from using this bot.**")
            return

        # Check admin status (uses cache)
        if not db.is_admin(user_id):
            await client.send_message(message.chat.id, "❌ **This command is restricted to administrators only.**")
            return

        return await func(client, message, *args, **kwargs)
    return wrapper

def paid_or_admin_only(func):
    """Decorator to restrict command to paid users and admins (optimized)"""
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        user_id, is_banned = await _register_and_check_user(client, message)
        
        if is_banned:
            await client.send_message(message.chat.id, "❌ **You are banned from using this bot.**")
            return

        user_type = db.get_user_type(user_id)
        if user_type not in ['paid', 'admin']:
            await client.send_message(
                message.chat.id,
                "❌ **This feature is available for premium users only.**\n\n"
                "💎 **Get Premium Access:**\n\n"
                "🎁 **FREE Option:** Use `/watchad` - Watch a quick ad!\n"
                "💰 **Paid Option:** Use `/upgrade` - Only $1/month\n\n"
                "✅ **Premium Benefits:**\n"
                "• Unlimited downloads\n"
                "• Batch download feature\n"
                "• Priority support"
            )
            return

        return await func(client, message, *args, **kwargs)
    return wrapper

def check_download_limit(func):
    """Decorator to check download limits for free users (optimized)"""
    @wraps(func)
    async def wrapper(client, message):
        user_id, is_banned = await _register_and_check_user(client, message)
        
        if is_banned:
            await client.send_message(message.chat.id, "❌ **You are banned from using this bot.**")
            return

        # Check download limits
        can_download, message_text = db.can_download(user_id)
        if not can_download:
            from ad_monetization import PREMIUM_DOWNLOADS
            # FIXED: Use InlineKeyboardButton with callback_data parameter (Pyrogram style)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎁 Watch Ad & Get {PREMIUM_DOWNLOADS} Downloads", callback_data="watch_ad_now")],
                [InlineKeyboardButton("💰 Upgrade to Premium", callback_data="upgrade_premium")]
            ])
            sent_msg = await client.send_message(message.chat.id, message_text, reply_markup=keyboard)
            
            # Auto-delete after 30 seconds (fire-and-forget, cleaned up automatically)
            async def delete_after_delay():
                try:
                    await asyncio.sleep(30)
                    await sent_msg.delete()
                except asyncio.CancelledError:
                    pass  # Task cancelled during shutdown, ignore
                except Exception as e:
                    pass
            
            # Create task with name for debugging; task auto-cleans when done
            task = asyncio.create_task(delete_after_delay())
            task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
            return

        return await func(client, message)
    return wrapper

def register_user(func):
    """Decorator to register user in database (optimized)"""
    @wraps(func)
    async def wrapper(client, message):
        user_id, is_banned = await _register_and_check_user(client, message)
        
        if is_banned:
            await client.send_message(message.chat.id, "❌ **You are banned from using this bot.**")
            return

        return await func(client, message)
    return wrapper

async def check_user_session(user_id: int):
    """Check if user has their own session string"""
    session = db.get_user_session(user_id)
    return session is not None

async def get_user_client(user_id: int):
    """
    Get user's personal client if they have session
    
    CRITICAL: Uses SessionManager to limit concurrent sessions and prevent memory exhaustion
    On Render/Replit (512MB RAM), limits to 10 concurrent user sessions (~5-10MB each due to StringSession)
    Sessions are reused across downloads - DO NOT call client.stop() after each download!
    
    Returns:
        tuple: (client, error_code) where:
            - (Client, None) if successful
            - (None, 'no_session') if user hasn't logged in yet
            - (None, 'slots_full') if all session slots are busy with active downloads
            - (None, 'error') for other errors
    """
    session = db.get_user_session(user_id)
    if not session:
        return (None, 'no_session')
    
    from config import PyroConf
    from helpers.session_manager import session_manager
    import traceback

    try:
        # Use SessionManager to get or create session
        # This prevents memory leaks by limiting concurrent sessions and reusing existing ones
        user_client, error_code = await session_manager.get_or_create_session(
            user_id=user_id,
            session_string=session,
            api_id=PyroConf.API_ID,
            api_hash=PyroConf.API_HASH
        )
        
        if user_client:
            LOGGER(__name__).info(f"Got user client for {user_id} from SessionManager")
            return (user_client, None)
        
        # Handle different error codes from SessionManager
        if error_code == 'slots_full':
            LOGGER(__name__).warning(f"All session slots busy, user {user_id} must wait")
            return (None, 'slots_full')
        elif error_code == 'invalid_session':
            # Session is not authorized - clear it from DB so user can relogin
            LOGGER(__name__).warning(f"Clearing invalid/unauthorized session for user {user_id}")
            db.set_user_session(user_id, None)
            await session_manager.remove_session(user_id)
            return (None, 'error')
        elif error_code == 'creation_failed':
            # Session creation failed - might be network issue, don't clear DB
            LOGGER(__name__).error(f"Session creation failed for user {user_id}")
            return (None, 'error')
        else:
            # Unknown error
            LOGGER(__name__).error(f"Unknown error code from SessionManager: {error_code}")
            return (None, 'error')
            
    except Exception as e:
        LOGGER(__name__).error(f"Failed to get user client for {user_id}: {e}")
        LOGGER(__name__).error(f"Full traceback: {traceback.format_exc()}")
        # Unexpected exception - check if it's an auth error
        error_msg = str(e).lower()
        if 'auth' in error_msg or 'session' in error_msg or 'expired' in error_msg:
            LOGGER(__name__).warning(f"Clearing invalid session for user {user_id}")
            db.set_user_session(user_id, None)
            await session_manager.remove_session(user_id)
        return (None, 'error')

def force_subscribe(func):
    """Decorator to enforce channel subscription before using bot features"""
    @wraps(func)
    async def wrapper(client, message):
        # Skip if no force subscribe channel is configured
        if not PyroConf.FORCE_SUBSCRIBE_CHANNEL:
            return await func(client, message)
        
        user_id = message.from_user.id
        
        # Admins and owner bypass force subscribe
        if db.is_admin(user_id) or user_id == PyroConf.OWNER_ID:
            return await func(client, message)
        
        # Check if user is member of the channel
        try:
            channel = PyroConf.FORCE_SUBSCRIBE_CHANNEL
            # Remove @ if present
            if channel.startswith('@'):
                channel = channel[1:]
            
            # Use Pyrogram's get_chat_member to check membership
            try:
                # Get channel chat first
                chat_entity = await client.get_chat(channel)
                
                # Try to get user as member
                try:
                    member = await client.get_chat_member(chat_entity.id, user_id)
                    if member:
                        # User is a member
                        return await func(client, message)
                except UserNotParticipant:
                    # User is not in channel, fall through to show join message
                    pass
            except Exception as e:
                # If get_chat or get_chat_member fails, try to allow access
                # Allow access to avoid blocking users on channel check errors
                return await func(client, message)
                    
        except (ChatAdminRequired, ChannelPrivate) as e:
            LOGGER(__name__).error(f"Bot lacks permission to check channel membership: {e}")
            # If bot can't check, allow access (don't block users due to config error)
            return await func(client, message)
        except Exception as e:
            LOGGER(__name__).error(f"Error checking channel membership: {e}")
            # If there's an error checking, allow access to avoid blocking users
            return await func(client, message)
        
        # User is not subscribed, show join message
        channel_username = PyroConf.FORCE_SUBSCRIBE_CHANNEL
        if not channel_username.startswith('@'):
            channel_username = f"@{channel_username}"
        
        # FIXED: Use InlineKeyboardButton with url parameter (Pyrogram style)
        join_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{channel_username.replace('@', '')}")]
        ])
        
        await client.send_message(
            message.chat.id,
            f"❌ **Access Denied!**\n\n"
            f"🔒 You must join our channel to use this bot.\n\n"
            f"👉 **Channel:** {channel_username}\n\n"
            f"After joining, try your command again!",
            reply_markup=join_button
        )
    
    return wrapper
