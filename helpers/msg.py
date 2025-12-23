# Copyright (C) @Wolfy004
# Migrated to Pyrogram

from typing import Optional, List, Tuple, Union
from pyrogram_helpers import parse_message_link

async def get_parsed_msg(text: str, entities: Optional[List] = None) -> str:
    """
    Parse message text with entities
    
    Args:
        text: Message text
        entities: List of MessageEntity objects
        
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
    if not message or not message.media:
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
        return f"{message_id}.mp4"
    
    # Audio
    elif message.audio:
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
    
    return f"{message_id}"
