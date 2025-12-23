# Copyright (C) @Wolfy004
# Channel: https://t.me/Wolfy004

import asyncio
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram_helpers import parse_command, get_command_args
from access_control import admin_only, register_user
from database_sqlite import db
from logger import LOGGER

@admin_only
async def add_admin_command(client, message):
    """Add a new admin"""
    try:
        args = get_command_args(message.text)
        if len(args) < 1:
            await client.send_message(message.chat.id, "**Usage:** `/addadmin <user_id>`")
            return

        target_user_id = int(args[0])
        admin_user_id = message.from_user.id

        if db.add_admin(target_user_id, admin_user_id):
            try:
                user_info = await client.get_chat(target_user_id)
                user_name = user_info.first_name or "Unknown"
            except:
                user_name = str(target_user_id)

            await client.send_message(message.chat.id, f"✅ **Successfully added {user_name} as admin.**")
            LOGGER(__name__).info(f"Admin {admin_user_id} added {target_user_id} as admin")
        else:
            await client.send_message(message.chat.id, "❌ **Failed to add admin. User might already be an admin.**")

    except ValueError:
        await client.send_message(message.chat.id, "❌ **Invalid user ID. Please provide a numeric user ID.**")
    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error: {str(e)}**")
        LOGGER(__name__).error(f"Error in add_admin_command: {e}")

@admin_only
async def remove_admin_command(client, message):
    """Remove admin privileges"""
    try:
        args = get_command_args(message.text)
        if len(args) < 1:
            await client.send_message(message.chat.id, "**Usage:** `/removeadmin <user_id>`")
            return

        target_user_id = int(args[0])

        if db.remove_admin(target_user_id):
            await client.send_message(message.chat.id, f"✅ **Successfully removed admin privileges from user {target_user_id}.**")
            LOGGER(__name__).info(f"Admin {message.from_user.id} removed admin privileges from {target_user_id}")
        else:
            await client.send_message(message.chat.id, "❌ **User is not an admin or error occurred.**")

    except ValueError:
        await client.send_message(message.chat.id, "❌ **Invalid user ID. Please provide a numeric user ID.**")
    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error: {str(e)}**")

@admin_only
async def set_premium_command(client, message):
    """Set user as premium"""
    try:
        args = get_command_args(message.text)

        if len(args) < 1:
            await client.send_message(message.chat.id, "**Usage:** `/setpremium <user_id> [days]`\n\n**Default:** 30 days")
            return

        target_user_id = int(args[0])
        days = int(args[1]) if len(args) > 1 else 30

        if db.set_user_type(target_user_id, 'paid', days):
            await client.send_message(message.chat.id, f"✅ **Successfully upgraded user {target_user_id} to premium for {days} days.**")
            LOGGER(__name__).info(f"Admin {message.from_user.id} set {target_user_id} as premium for {days} days")
        else:
            await client.send_message(message.chat.id, "❌ **Failed to upgrade user.**")

    except ValueError:
        await client.send_message(message.chat.id, "❌ **Invalid input. Use numeric values only.**")
    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error: {str(e)}**")

@admin_only
async def remove_premium_command(client, message):
    """Remove premium subscription"""
    try:
        args = get_command_args(message.text)
        if len(args) < 1:
            await client.send_message(message.chat.id, "**Usage:** `/removepremium <user_id>`")
            return

        target_user_id = int(args[0])

        if db.set_user_type(target_user_id, 'free'):
            await client.send_message(message.chat.id, f"✅ **Successfully downgraded user {target_user_id} to free plan.**")
            LOGGER(__name__).info(f"Admin {message.from_user.id} removed premium from {target_user_id}")
        else:
            await client.send_message(message.chat.id, "❌ **Failed to downgrade user.**")

    except ValueError:
        await client.send_message(message.chat.id, "❌ **Invalid user ID. Please provide a numeric user ID.**")
    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error: {str(e)}**")

@admin_only
async def ban_user_command(client, message):
    """Ban a user"""
    try:
        args = get_command_args(message.text)
        if len(args) < 1:
            await client.send_message(message.chat.id, "**Usage:** `/ban <user_id>`")
            return

        target_user_id = int(args[0])

        if target_user_id == message.from_user.id:
            await client.send_message(message.chat.id, "❌ **You cannot ban yourself.**")
            return

        if db.is_admin(target_user_id):
            await client.send_message(message.chat.id, "❌ **Cannot ban another admin.**")
            return

        if db.ban_user(target_user_id):
            await client.send_message(message.chat.id, f"✅ **Successfully banned user {target_user_id}.**")
            LOGGER(__name__).info(f"Admin {message.from_user.id} banned {target_user_id}")
        else:
            await client.send_message(message.chat.id, "❌ **Failed to ban user.**")

    except ValueError:
        await client.send_message(message.chat.id, "❌ **Invalid user ID. Please provide a numeric user ID.**")
    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error: {str(e)}**")

@admin_only
async def unban_user_command(client, message):
    """Unban a user"""
    try:
        args = get_command_args(message.text)
        if len(args) < 1:
            await client.send_message(message.chat.id, "**Usage:** `/unban <user_id>`")
            return

        target_user_id = int(args[0])

        if db.unban_user(target_user_id):
            await client.send_message(message.chat.id, f"✅ **Successfully unbanned user {target_user_id}.**")
            LOGGER(__name__).info(f"Admin {message.from_user.id} unbanned {target_user_id}")
        else:
            await client.send_message(message.chat.id, "❌ **Failed to unban user or user was not banned.**")

    except ValueError:
        await client.send_message(message.chat.id, "❌ **Invalid user ID. Please provide a numeric user ID.**")
    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error: {str(e)}**")

@admin_only
async def broadcast_command(client, message):
    """Broadcast message/media to all users or specific users
    
    Usage:
    - All users: /broadcast <message>
    - Specific users: /broadcast @user_id1,user_id2 <message>
    - Media: Reply to a photo/video/audio/document/GIF with /broadcast [@user_ids] <optional caption>
    """
    try:
        broadcast_data = {}
        target_user_ids = None
        
        replied_msg = message.reply_to_message
        args = get_command_args(message.text)
        
        if len(args) > 0 and args[0].startswith('@'):
            user_ids_str = args[0][1:]
            if user_ids_str and all(c.isdigit() or c == ',' for c in user_ids_str):
                try:
                    target_user_ids = [int(uid.strip()) for uid in user_ids_str.split(',') if uid.strip()]
                except ValueError:
                    pass
        
        if replied_msg:
            caption = None
            if target_user_ids and len(args) > 1:
                caption = message.text.split(' ', 2)[2] if len(message.text.split(' ', 2)) > 2 else None
            elif not target_user_ids and len(args) > 0:
                caption = message.text.split(' ', 1)[1]
            elif replied_msg.text:
                caption = replied_msg.text
            
            if replied_msg.photo:
                broadcast_data = {'type': 'photo', 'file': replied_msg.photo.file_id, 'caption': caption}
            elif replied_msg.video:
                broadcast_data = {'type': 'video', 'file': replied_msg.video.file_id, 'caption': caption}
            elif replied_msg.audio:
                broadcast_data = {'type': 'audio', 'file': replied_msg.audio.file_id, 'caption': caption}
            elif replied_msg.voice:
                broadcast_data = {'type': 'voice', 'file': replied_msg.voice.file_id, 'caption': caption}
            elif replied_msg.document:
                if replied_msg.animation:
                    broadcast_data = {'type': 'animation', 'file': replied_msg.animation.file_id, 'caption': caption}
                else:
                    broadcast_data = {'type': 'document', 'file': replied_msg.document.file_id, 'caption': caption}
            elif replied_msg.sticker:
                broadcast_data = {'type': 'sticker', 'file': replied_msg.sticker.file_id, 'caption': None}
            else:
                await client.send_message(message.chat.id, "❌ **Unsupported media type or no media found in the replied message.**")
                return
        else:
            if len(args) < 1:
                await client.send_message(
                    message.chat.id,
                    "**📢 Broadcast Usage:**\n\n"
                    "**To All Users:**\n"
                    "• `/broadcast <message>`\n"
                    "• Reply to media: `/broadcast <optional caption>`\n\n"
                    "**To Specific Users:**\n"
                    "• `/broadcast @123456789 <message>`\n"
                    "• `/broadcast @123456789,987654321 <message>`\n"
                    "• Reply to media: `/broadcast @123456789 <caption>`\n\n"
                    "**Examples:**\n"
                    "• `/broadcast Hello everyone!` → All users\n"
                    "• `/broadcast @123456789 Hi there!` → One user\n"
                    "• `/broadcast @123,456,789 Notice!` → Multiple users"
                )
                return
            
            if target_user_ids:
                if len(args) < 2:
                    await client.send_message(message.chat.id, "❌ **Please provide a message after the user ID(s).**")
                    return
                message_text = message.text.split(' ', 2)[2] if len(message.text.split(' ', 2)) > 2 else ""
            else:
                message_text = message.text.split(' ', 1)[1]
            
            if not message_text:
                await client.send_message(message.chat.id, "❌ **Please provide a message to send.**")
                return
            
            broadcast_data = {'type': 'text', 'message': message_text}
        
        if target_user_ids:
            broadcast_data['target_users'] = target_user_ids
        
        if broadcast_data['type'] == 'text':
            preview = broadcast_data['message'][:100] + "..." if len(broadcast_data['message']) > 100 else broadcast_data['message']
            preview_text = f"**📢 Broadcast Preview (Text):**\n\n{preview}"
        else:
            media_type = broadcast_data['type'].upper()
            caption_preview = broadcast_data.get('caption', 'No caption')
            if caption_preview and len(caption_preview) > 100:
                caption_preview = caption_preview[:100] + "..."
            preview_text = f"**📢 Broadcast Preview ({media_type}):**\n\n{caption_preview or 'No caption'}"
        
        if target_user_ids:
            user_count = len(target_user_ids)
            user_list = ', '.join([f"`{uid}`" for uid in target_user_ids[:5]])
            if user_count > 5:
                user_list += f" ... +{user_count - 5} more"
            target_text = f"**Target ({user_count} users):** {user_list}"
        else:
            target_text = "**Target:** All users"
        
        # FIXED: Use InlineKeyboardButton with callback_data parameter (Pyrogram style)
        confirm_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Send Broadcast", callback_data=f"broadcast_confirm:{message.from_user.id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
            ]
        ])
        
        await client.send_message(
            message.chat.id,
            f"{preview_text}\n\n{target_text}\n\n**Confirm sending?**",
            reply_markup=confirm_markup
        )
        
        setattr(client, f'pending_broadcast_{message.from_user.id}', broadcast_data)
        
    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error: {str(e)}**")
        LOGGER(__name__).error(f"Error in broadcast_command: {e}")

async def execute_broadcast(client, admin_id: int, broadcast_data: dict):
    """Execute the actual broadcast - supports text and all media types, to all or specific users"""
    target_users = broadcast_data.get('target_users')
    
    if target_users:
        users_to_send = target_users
    else:
        users_to_send = db.get_all_users()
    
    total_users = len(users_to_send)
    successful_sends = 0

    if total_users == 0:
        return 0, 0

    broadcast_type = broadcast_data.get('type', 'text')
    
    for user_id in users_to_send:
        try:
            if broadcast_type == 'text':
                await client.send_message(user_id, broadcast_data['message'])
            elif broadcast_type == 'photo':
                await client.send_photo(
                    user_id, 
                    broadcast_data['file'],
                    caption=broadcast_data.get('caption')
                )
            elif broadcast_type == 'video':
                await client.send_video(
                    user_id, 
                    broadcast_data['file'],
                    caption=broadcast_data.get('caption')
                )
            elif broadcast_type == 'audio':
                await client.send_audio(
                    user_id, 
                    broadcast_data['file'],
                    caption=broadcast_data.get('caption')
                )
            elif broadcast_type == 'voice':
                await client.send_voice(
                    user_id, 
                    broadcast_data['file'],
                    caption=broadcast_data.get('caption')
                )
            elif broadcast_type == 'document':
                await client.send_document(
                    user_id, 
                    broadcast_data['file'],
                    caption=broadcast_data.get('caption')
                )
            elif broadcast_type == 'animation':
                await client.send_animation(
                    user_id, 
                    broadcast_data['file'],
                    caption=broadcast_data.get('caption')
                )
            elif broadcast_type == 'sticker':
                await client.send_sticker(user_id, broadcast_data['file'])
            
            successful_sends += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            LOGGER(__name__).debug(f"Failed to send broadcast to {user_id}: {e}")
            continue

    broadcast_content = broadcast_data.get('message') or broadcast_data.get('caption') or f"[{broadcast_type.upper()} broadcast]"
    db.save_broadcast(broadcast_content, admin_id, total_users, successful_sends)

    return total_users, successful_sends

@admin_only
async def admin_stats_command(client, message, download_mgr=None):
    """Show detailed admin statistics"""
    try:
        stats = db.get_stats()
        
        active_downloads = 0
        if download_mgr:
            active_downloads = len(download_mgr.active_downloads)

        stats_text = (
            "👑 **ADMIN DASHBOARD**\n"
            "——————————————————————————\n\n"
            "👥 **User Analytics:**\n"
            f"📊 Total Users: `{stats.get('total_users', 0)}`\n"
            f"💎 Premium Users: `{stats.get('paid_users', 0)}`\n"
            f"🟢 Active (7d): `{stats.get('active_users', 0)}`\n"
            f"🆕 New Today: `{stats.get('today_new_users', 0)}`\n"
            f"🔐 Admins: `{stats.get('admin_count', 0)}`\n\n"
            "📈 **Download Activity:**\n"
            f"📥 Today: `{stats.get('today_downloads', 0)}`\n"
            f"⚡ Active: `{active_downloads}`\n\n"
            "——————————————————————————\n\n"
            "⚙️ **Quick Admin Actions:**\n"
            "• `/killall` - Cancel all downloads\n"
            "• `/broadcast` - Send message to all\n"
            "• `/logs` - View bot logs"
        )

        await client.send_message(message.chat.id, stats_text)

    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error getting stats: {str(e)}**")
        LOGGER(__name__).error(f"Error in admin_stats_command: {e}")

@register_user
async def user_info_command(client, message):
    """Show user information"""
    try:
        user_id = message.from_user.id
        user_type = db.get_user_type(user_id)
        daily_usage = db.get_daily_usage(user_id)

        user_info_text = (
            f"**👤 Your Account Information**\n\n"
            f"**User ID:** `{user_id}`\n"
            f"**Account Type:** `{user_type.title()}`\n"
        )

        if user_type == 'free':
            ad_downloads = db.get_ad_downloads(user_id)
            remaining = 5 - daily_usage
            user_info_text += (
                f"**Today's Downloads:** `{daily_usage}/5`\n"
                f"**Remaining:** `{remaining}`\n"
                f"**Ad Downloads:** `{ad_downloads}`\n\n"
                "💎 **Upgrade to Premium for unlimited downloads!**\n"
                "🎁 **Or use** `/getpremium` **to watch ads and get more downloads!**"
            )
        elif user_type == 'paid':
            user = db.get_user(user_id)
            if user and user['subscription_end']:
                user_info_text += f"**Subscription Valid Until:** `{user['subscription_end']}`\n"
            user_info_text += f"**Today's Downloads:** `{daily_usage}` (unlimited)\n"
        else:
            user_info_text += f"**Today's Downloads:** `{daily_usage}` (unlimited)\n**Privileges:** `Administrator`\n"

        await client.send_message(message.chat.id, user_info_text)

    except Exception as e:
        await client.send_message(message.chat.id, f"❌ **Error: {str(e)}**")
        LOGGER(__name__).error(f"Error in user_info_command: {e}")

async def broadcast_callback_handler(client, callback_query):
    """Handle broadcast confirmation callbacks"""
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data == "broadcast_cancel":
        await callback_query.edit_message_text("❌ **Broadcast cancelled.**")
        return

    if data.startswith("broadcast_confirm:"):
        admin_id = int(data.split(":")[1])

        if user_id != admin_id:
            await callback_query.answer("❌ You are not authorized to confirm this broadcast.", show_alert=True)
            return

        broadcast_data = getattr(client, f'pending_broadcast_{admin_id}', None)

        if not broadcast_data:
            await callback_query.edit_message_text("❌ **Broadcast data not found. Please try again.**")
            return

        await callback_query.edit_message_text("📡 **Sending broadcast... Please wait.**")

        total_users, successful_sends = await execute_broadcast(client, admin_id, broadcast_data)

        if hasattr(client, f'pending_broadcast_{admin_id}'):
            delattr(client, f'pending_broadcast_{admin_id}')

        result_text = (
            f"✅ **Broadcast Completed!**\n\n"
            f"**Total Users:** `{total_users}`\n"
            f"**Successful Sends:** `{successful_sends}`\n"
            f"**Failed Sends:** `{total_users - successful_sends}`\n"
            f"**Success Rate:** `{(successful_sends/total_users*100):.1f}%`" if total_users > 0 else "**Success Rate:** `0%`"
        )

        await callback_query.edit_message_text(result_text)
