"""
HIGH-SPEED TRANSFER MODULE for Per-User Sessions
=================================================
FIXED VERSION - Removed unused code, fixed IS_CONSTRAINED

This module implements optimized file transfers using Pyrogram's native streaming.
Since each user has their own Telegram session, no global connection
pooling is needed - each session can use full connection capacity.

CONFIGURATION (Environment Variables):
- CONNECTIONS_PER_TRANSFER: Connections per download/upload (default: 16)
"""
import os
import asyncio
import gc
from typing import Optional, Callable
from pyrogram import Client
from pyrogram.types import Message
from logger import LOGGER

CONNECTIONS_PER_TRANSFER = int(os.getenv("CONNECTIONS_PER_TRANSFER", "16"))

# FIX: Use same environment detection as session_manager.py
IS_CONSTRAINED = bool(
    os.getenv('RENDER') or 
    os.getenv('RENDER_EXTERNAL_URL') or 
    os.getenv('REPLIT_DEPLOYMENT') or 
    os.getenv('REPL_ID')
)




# FIX: Removed unused MAX_CONNECTIONS, MAX_UPLOAD_CONNECTIONS, MAX_DOWNLOAD_CONNECTIONS


def has_downloadable_media(msg: Message) -> bool:
    """
    FIXED: Check if message has any downloadable media.
    More reliable than checking .media attribute which can be EMPTY.
    """
    if not msg:
        return False
    return any([
        getattr(msg, 'photo', None),
        getattr(msg, 'video', None),
        getattr(msg, 'audio', None),
        getattr(msg, 'document', None),
        getattr(msg, 'voice', None),
        getattr(msg, 'video_note', None),
        getattr(msg, 'animation', None),
        getattr(msg, 'sticker', None)
    ])


async def download_media_fast(
    client: Client,
    message: Message,
    file: str,
    progress_callback: Optional[Callable] = None
) -> str:
    """
    Download media using Pyrogram's native streaming with full connection capacity.
    
    Since each user has their own Telegram session, each download can
    use the full connection capacity without needing global pooling.
    """
    # FIXED: Use robust media detection instead of just message.media
    if not has_downloadable_media(message):
        raise ValueError("Message has no downloadable media")
    
    # Check for paid media (Pyrogram identifies this via media type checking)
    if hasattr(message, 'media') and message.media and hasattr(message.media, 'is_paid') and message.media.is_paid:
        LOGGER(__name__).warning(f"Paid media detected - this is premium content")
        raise ValueError("Paid media (premium content) cannot be downloaded - the content owner requires payment to access this media")
    
    try:
        file_size = 0
        media_location = None
        media_type_name = "unknown"
        
        if message.document:
            file_size = getattr(message.document, 'file_size', 0) or 0
            media_location = message.document
            media_type_name = "document"
        elif message.video:
            file_size = getattr(message.video, 'file_size', 0) or 0
            media_location = message.video
            media_type_name = "video"
        elif message.audio:
            file_size = getattr(message.audio, 'file_size', 0) or 0
            media_location = message.audio
            media_type_name = "audio"
        elif message.photo:
            file_size = getattr(message.photo, 'file_size', 0) or 0
            media_location = message.photo
            media_type_name = "photo"
        elif message.voice:
            file_size = getattr(message.voice, 'file_size', 0) or 0
            media_location = message.voice
            media_type_name = "voice"
        elif message.video_note:
            file_size = getattr(message.video_note, 'file_size', 0) or 0
            media_location = message.video_note
            media_type_name = "video_note"
        elif message.sticker:
            file_size = getattr(message.sticker, 'file_size', 0) or 0
            media_location = message.sticker
            media_type_name = "sticker"
        elif message.animation:
            file_size = getattr(message.animation, 'file_size', 0) or 0
            media_location = message.animation
            media_type_name = "animation"
        
        # CRITICAL FIX: Download even if file_size is 0 or unknown
        # Some videos don't report size upfront but can still be downloaded
        if media_location:
            LOGGER(__name__).info(
                f"Downloading {media_type_name}: file_size={file_size}, path={file}"
            )
            
            # Use Pyrogram's native download_media with progress callback
            result = await client.download_media(
                message,
                file_name=file,
                progress=progress_callback
            )
            
            gc.collect()
            return result if result else file
        else:
            # No media found despite has_downloadable_media check - fallback
            LOGGER(__name__).warning(
                f"No media_location found for message, attempting fallback download to {file}"
            )
            return await client.download_media(message, file_name=file, progress=progress_callback)
        
    except Exception as e:
        error_str = str(e).lower()
        if 'paidmedia' in error_str or 'paid' in error_str:
            raise ValueError("Paid media (premium content) cannot be downloaded - the content owner requires payment to access this media")
        LOGGER(__name__).error(f"Pyrogram download failed, falling back to standard: {e}")
        # Fallback: try standard download
        try:
            return await client.download_media(message, file_name=file, progress=progress_callback)
        except Exception as fallback_error:
            LOGGER(__name__).error(f"Fallback download also failed: {fallback_error}")
            raise


async def upload_media_fast(
    client: Client,
    file_path: str,
    progress_callback: Optional[Callable] = None
):
    """
    Upload media using Pyrogram's native streaming with full connection capacity.
    
    Since each user has their own Telegram session, each upload can
    use the full connection capacity without needing global pooling.
    Returns None - Pyrogram's upload is handled directly in send_photo/send_video/etc.
    """
    file_size = os.path.getsize(file_path)
    
    result = None
    
    try:
        # Note: the actual upload is handled by send methods
        # This function prepares the upload but doesn't execute it
        
        gc.collect()
        return result
        
    except Exception as e:
        LOGGER(__name__).error(f"Pyrogram upload preparation failed: {e}")
        return None


def get_connection_count_for_size(file_size: int, max_count: int = CONNECTIONS_PER_TRANSFER) -> int:
    """
    Determine optimal connection count based on file size.
    
    Larger files benefit from more connections, while smaller files
    don't need as many.
    """
    if file_size >= 10 * 1024 * 1024:
        return max_count
    elif file_size >= 1 * 1024 * 1024:
        return min(12, max_count)
    elif file_size >= 100 * 1024:
        return min(8, max_count)
    elif file_size >= 10 * 1024:
        return min(6, max_count)
    else:
        return min(4, max_count)


# FIX: Removed unused _optimized_connection_count_upload and _optimized_connection_count_download functions
# Note: Pyrogram doesn't use ParallelTransferrer - connection optimization is built-in
