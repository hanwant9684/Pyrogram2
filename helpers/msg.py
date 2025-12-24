# Copyright (C) @Wolfy004
# Migrated to Pyrogram
# FIXED VERSION - Made async compatible, handles entities parameter

from typing import Tuple, Union
from pyrogram_helpers import parse_message_link


# FIX: Made async and accepts optional entities parameter for backward compatibility
async def get_parsed_msg(text: str, entities=None) -> str:
    """
    Parse message text.
    Pyrogram handles entities automatically, so this just returns the text.
    
    Args:
        text: Message text
        entities: Optional entities (ignored, kept for backward compatibility)
        
    Returns:
        Parsed text (plain text, entities are preserved by Pyrogram)
    """
    if not text:
        return ""
    return text


def getChatMsgID(link: str) -> Tuple[Union[int, str], int]:
    """
    Parse Telegram message link to extract chat ID and message ID
    
    Args:
        link: Telegram message link
        
    Returns:
        Tuple of (chat_id, message_id)
        - chat_id is int for private channels (e.g., -1001940263820)
        - chat_id is str for public usernames (e.g., "channelname")
    Raises:
        ValueError: If link is invalid
    """
    from logger import LOGGER
    chat_id, thread_id, message_id = parse_message_link(link)
    
    if not chat_id or not message_id:
        LOGGER(__name__).warning(f"[URL_PARSE] Invalid URL format: {link}")
        raise ValueError("Please send a valid Telegram post URL.")
    
    # CRITICAL FIX: Convert numeric chat_id to int for Pyrogram
    # Private channels return "-100XXXXXXXXXX" which must be an int
    # Public usernames remain as strings
    if isinstance(chat_id, str):
        # Try to convert to int (private channels have numeric IDs)
        try:
            chat_id = int(chat_id)
        except ValueError:
            # It's a username like "channelname", keep as string
            pass
    
    return chat_id, message_id


def get_file_name(message_id: int, message) -> str:
    """
    Get filename from message media (Pyrogram Message object)
    
    Args:
        message_id: Message ID (used as fallback)
        message: Pyrogram Message object
        
    Returns:
        Filename string
    """
    if not message:
        return f"{message_id}"
    
    # Document (file, video, audio, etc.)
    if message.document:
        doc = message.document
        
        # Check if document has a file name
        if doc.file_name:
            return doc.file_name
        
        # Check mime type for default extensions
        if doc.mime_type:
            if 'video' in doc.mime_type:
                return f"{message_id}.mp4"
            elif 'audio' in doc.mime_type:
                if 'ogg' in doc.mime_type:
                    return f"{message_id}.ogg"
                return f"{message_id}.mp3"
            elif 'image' in doc.mime_type:
                return f"{message_id}.jpg"
        
        return f"{message_id}"
    
    # Photo
    elif message.photo:
        return f"{message_id}.jpg"
    
    # Video
    elif message.video:
        # Try to get original filename if available
        if hasattr(message.video, 'file_name') and message.video.file_name:
            return message.video.file_name
        return f"{message_id}.mp4"
    
    # Audio
    elif message.audio:
        if hasattr(message.audio, 'file_name') and message.audio.file_name:
            return message.audio.file_name
        return f"{message_id}.mp3"
    
    # Voice
    elif message.voice:
        return f"{message_id}.ogg"
    
    # Animation (GIF)
    elif message.animation:
        return f"{message_id}.gif"
    
    # Sticker
    elif message.sticker:
        return f"{message_id}.webp"
    
    # Video note
    elif message.video_note:
        return f"{message_id}.mp4"
    
    return f"{message_id}"
