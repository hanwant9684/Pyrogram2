# Pyrogram Helper Utilities
# Migration helpers for Pyrogram

from typing import List, Optional, Tuple

def parse_command(text: str) -> List[str]:
    """
    Parse command and arguments from message text
    Mimics Pyrogram's message.command behavior
    
    Args:
        text: Message text
        
    Returns:
        List of command parts (command is first element)
    """
    if not text or not text.startswith('/'):
        return []
    return text.split()

def get_command_args(text: str) -> List[str]:
    """Get command arguments only (without command itself)"""
    parts = parse_command(text)
    return parts[1:] if len(parts) > 1 else []

def get_message_link(chat_id: int, message_id: int, username: Optional[str] = None) -> str:
    """
    Generate Telegram message link
    
    Args:
        chat_id: Chat ID
        message_id: Message ID  
        username: Chat username (if public)
        
    Returns:
        Message link URL
    """
    if username:
        return f"https://t.me/{username}/{message_id}"
    else:
        # For private chats/channels, use c/ format
        # Remove the -100 prefix if present
        chat_id_str = str(chat_id)
        if chat_id_str.startswith('-100'):
            chat_id_str = chat_id_str[4:]
        return f"https://t.me/c/{chat_id_str}/{message_id}"

def parse_message_link(link: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """
    Parse Telegram message link to extract chat and message IDs
    
    Args:
        link: Telegram message link
        
    Returns:
        Tuple of (chat_id_or_username, message_thread_id, message_id)
    """
    import re
    link = link.strip()
    
    # Remove query parameters
    if '?' in link:
        link = link.split('?')[0]
    
    parts = link.rstrip('/').split('/')
    
    try:
        # Format: https://t.me/c/CHANNEL_ID/MESSAGE_ID or /c/CHANNEL_ID/THREAD_ID/MESSAGE_ID
        if '/c/' in link:
            if len(parts) >= 7:  # With thread (https://t.me/c/CHANNEL_ID/THREAD_ID/MESSAGE_ID)
                channel_id = int(parts[-3])
                thread_id = int(parts[-2])
                message_id = int(parts[-1])
                # Add -100 prefix for channels
                return f"-100{channel_id}", thread_id, message_id
            elif len(parts) >= 6:  # Without thread (https://t.me/c/CHANNEL_ID/MESSAGE_ID)
                channel_id = int(parts[-2])
                message_id = int(parts[-1])
                return f"-100{channel_id}", None, message_id
        
        # Format: https://t.me/USERNAME/MESSAGE_ID or /USERNAME/THREAD_ID/MESSAGE_ID
        else:
            if len(parts) >= 5:  # With thread (https://t.me/USERNAME/THREAD_ID/MESSAGE_ID)
                # Check if second-to-last part is numeric (thread_id)
                try:
                    thread_id = int(parts[-2])
                    message_id = int(parts[-1])
                    username = parts[-3]
                    return username, thread_id, message_id
                except ValueError:
                    pass
            
            if len(parts) >= 4:  # Without thread (https://t.me/USERNAME/MESSAGE_ID)
                message_id = int(parts[-1])
                username = parts[-2]
                return username, None, message_id
    except (ValueError, IndexError) as e:
        pass
    
    return None, None, None


def has_downloadable_media(message) -> bool:
    """
    FIXED: Check if a Pyrogram Message has downloadable media.
    More reliable than checking .media attribute which can be EMPTY or None.
    
    Args:
        message: Pyrogram Message object
        
    Returns:
        bool: True if message has downloadable media
    """
    if not message:
        return False
    return any([
        getattr(message, 'photo', None),
        getattr(message, 'video', None),
        getattr(message, 'audio', None),
        getattr(message, 'document', None),
        getattr(message, 'voice', None),
        getattr(message, 'video_note', None),
        getattr(message, 'animation', None),
        getattr(message, 'sticker', None)
    ])
