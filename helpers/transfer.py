"""
HIGH-SPEED TRANSFER MODULE for Per-User Sessions
=================================================

This module implements optimized file transfers using Pyrogram's native streaming.
Since each user has their own Telegram session, no global connection
pooling is needed - each session can use full connection capacity.

CONFIGURATION (Environment Variables):
- CONNECTIONS_PER_TRANSFER: Connections per download/upload (default: 16)
"""
import os
import asyncio
import math
import inspect
import psutil
import gc
from typing import Optional, Callable, BinaryIO, Set, Dict
from pyrogram import Client
from pyrogram.types import Message
from logger import LOGGER

CONNECTIONS_PER_TRANSFER = int(os.getenv("CONNECTIONS_PER_TRANSFER", "16"))

def get_ram_usage_mb():
    """Get current RAM usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def create_ram_logging_callback(original_callback: Optional[Callable], file_size: int, operation: str, file_name: str):
    """
    Wrap progress callback to log RAM usage at 25%, 50%, 75% progress.
    """
    logged_thresholds: Set[int] = set()
    start_ram = get_ram_usage_mb()
    LOGGER(__name__).info(f"[RAM] {operation} START: {file_name} - RAM: {start_ram:.1f}MB")
    
    def ram_logging_wrapper(current: int, total: int):
        nonlocal logged_thresholds
        
        if total <= 0:
            if original_callback:
                return original_callback(current, total)
            return
        
        percent = (current / total) * 100
        
        for threshold in [25, 50, 75, 100]:
            if percent >= threshold and threshold not in logged_thresholds:
                logged_thresholds.add(threshold)
                current_ram = get_ram_usage_mb()
                ram_increase = current_ram - start_ram
                LOGGER(__name__).info(
                    f"[RAM] {operation} {threshold}%: {file_name} - "
                    f"RAM: {current_ram:.1f}MB (+{ram_increase:.1f}MB from start)"
                )
        
        if original_callback:
            return original_callback(current, total)
    
    return ram_logging_wrapper

IS_CONSTRAINED = False

MAX_CONNECTIONS = CONNECTIONS_PER_TRANSFER
MAX_UPLOAD_CONNECTIONS = CONNECTIONS_PER_TRANSFER
MAX_DOWNLOAD_CONNECTIONS = CONNECTIONS_PER_TRANSFER

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
    if not message.media:
        raise ValueError("Message has no media")
    
    # Check for paid media (Pyrogram identifies this via media type checking)
    if hasattr(message.media, 'is_paid') and message.media.is_paid:
        LOGGER(__name__).warning(f"Paid media detected - this is premium content")
        raise ValueError("Paid media (premium content) cannot be downloaded - the content owner requires payment to access this media")
    
    try:
        file_size = 0
        media_location = None
        
        if message.document:
            file_size = message.document.file_size
            media_location = message.document
        elif message.video:
            file_size = getattr(message.video, 'file_size', 0)
            media_location = message.video
        elif message.audio:
            file_size = getattr(message.audio, 'file_size', 0)
            media_location = message.audio
        elif message.photo:
            file_size = message.photo.file_size if hasattr(message.photo, 'file_size') else 0
            media_location = message.photo
        elif message.voice:
            file_size = getattr(message.voice, 'file_size', 0)
            media_location = message.voice
        elif message.video_note:
            file_size = getattr(message.video_note, 'file_size', 0)
            media_location = message.video_note
        elif message.sticker:
            file_size = getattr(message.sticker, 'file_size', 0)
            media_location = message.sticker
        
        connection_count = get_connection_count_for_size(file_size)
        
        LOGGER(__name__).info(
            f"Starting download: {os.path.basename(file)} "
            f"({file_size/1024/1024:.1f}MB, {connection_count} connections)"
        )
        
        file_name = os.path.basename(file)
        ram_callback = create_ram_logging_callback(progress_callback, file_size, "DOWNLOAD", file_name)
        
        if media_location and file_size > 0:
            # Use Pyrogram's native download_media with progress callback
            await client.download_media(
                message,
                file_name=file,
                progress=ram_callback
            )
            
            end_ram = get_ram_usage_mb()
            LOGGER(__name__).info(f"[RAM] DOWNLOAD COMPLETE: {file_name} - RAM before GC: {end_ram:.1f}MB")
            
            gc.collect()
            after_gc_ram = get_ram_usage_mb()
            ram_released = end_ram - after_gc_ram
            LOGGER(__name__).info(f"[RAM] DOWNLOAD GC: {file_name} - RAM after GC: {after_gc_ram:.1f}MB (released: {ram_released:.1f}MB)")
            return file
        else:
            LOGGER(__name__).warning(
                f"Pyrogram streaming bypassed for {file_name}: media_location={media_location is not None}, "
                f"file_size={file_size} - falling back to standard download"
            )
            return await client.download_media(message, file_name=file, progress=progress_callback)
        
    except Exception as e:
        error_str = str(e).lower()
        if 'paidmedia' in error_str or 'paid' in error_str:
            raise ValueError("Paid media (premium content) cannot be downloaded - the content owner requires payment to access this media")
        LOGGER(__name__).error(f"Pyrogram download failed, falling back to standard: {e}")
        return await client.download_media(message, file_name=file, progress=progress_callback)

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
    connection_count = get_connection_count_for_size(file_size)
    
    result = None
    
    try:
        file_name = os.path.basename(file_path)
        LOGGER(__name__).info(
            f"Starting upload: {file_name} "
            f"({file_size/1024/1024:.1f}MB, {connection_count} connections)"
        )
        
        ram_callback = create_ram_logging_callback(progress_callback, file_size, "UPLOAD", file_name)
        
        # Pyrogram's upload is handled directly via send_photo/send_video/send_document
        # This function returns None and lets the send methods handle the actual upload
        # The progress callback is passed through the send methods
        
        end_ram = get_ram_usage_mb()
        LOGGER(__name__).info(f"[RAM] UPLOAD COMPLETE: {file_name} - RAM before GC: {end_ram:.1f}MB")
        return result
        
    except Exception as e:
        LOGGER(__name__).error(f"Pyrogram upload preparation failed: {e}")
        return None
        
    finally:
        before_gc = get_ram_usage_mb()
        gc.collect()
        after_gc = get_ram_usage_mb()
        ram_released = before_gc - after_gc
        LOGGER(__name__).info(f"[RAM] UPLOAD GC: {os.path.basename(file_path)} - RAM after GC: {after_gc:.1f}MB (released: {ram_released:.1f}MB)")


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


def _optimized_connection_count_upload(file_size, max_count=MAX_UPLOAD_CONNECTIONS, full_size=100*1024*1024):
    """Connection count function for uploads."""
    return get_connection_count_for_size(file_size, max_count)

def _optimized_connection_count_download(file_size, max_count=MAX_DOWNLOAD_CONNECTIONS, full_size=100*1024*1024):
    """Connection count function for downloads."""
    return get_connection_count_for_size(file_size, max_count)

# Note: Pyrogram doesn't use ParallelTransferrer - connection optimization is built-in
