# Copyright (C) @Wolfy004
# Pyrogram-compatible version
# FIXED VERSION - Memory leaks, bare excepts, and garbage code removed

import os
import gc
import asyncio
from time import time
from logger import LOGGER
from typing import Optional
from asyncio.subprocess import PIPE
from asyncio import create_subprocess_exec, create_subprocess_shell, wait_for

def get_intra_request_delay(is_premium):
    """
    Get the appropriate delay between items in media groups or batch downloads.
    
    Args:
        is_premium: Boolean indicating if user is premium/admin (True) or free (False)
        
    Returns:
        int: Delay in seconds (1s for premium, 3s for free users)
    """
    from config import PyroConf
    return PyroConf.PREMIUM_INTRA_DELAY if is_premium else PyroConf.FREE_INTRA_DELAY

from helpers.files import (
    fileSizeLimit,
    cleanup_download,
    cleanup_download_delayed,
    get_download_path
)

from helpers.msg import (
    get_parsed_msg,
    get_file_name
)

from helpers.transfer import download_media_fast


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    try:
        stdout = stdout.decode().strip()
    except Exception:
        stdout = "Unable to decode the response!"
    try:
        stderr = stderr.decode().strip()
    except Exception:
        stderr = "Unable to decode the error!"
    return stdout, stderr, proc.returncode


async def has_video_stream(video_path):
    """
    Check if a file has a video stream using ffprobe.
    Properly handles process cleanup to prevent resource leaks.
    
    Returns:
        tuple: (has_video: bool, duration: float or None, error_msg: str or None)
    """
    proc = None
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_type,duration",
            "-of", "csv=p=0", video_path
        ]
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        
        try:
            stdout, stderr = await wait_for(proc.communicate(), timeout=10.0)
        except asyncio.TimeoutError:
            if proc:
                try:
                    proc.kill()
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except Exception:
                    pass
            return False, None, "ffprobe timed out"
        
        stdout_str = stdout.decode().strip() if stdout else ""
        stderr_str = stderr.decode().strip() if stderr else ""
        
        if proc.returncode != 0 or not stdout_str:
            return False, None, stderr_str or "No video stream found"
        
        parts = stdout_str.split(',')
        if parts and 'video' in str(parts[0]).lower():
            duration = None
            if len(parts) > 1 and parts[1] and parts[1] != 'N/A':
                try:
                    duration = float(parts[1])
                except ValueError:
                    pass
            return True, duration, None
        return False, None, "No video stream detected"
    except Exception as e:
        if proc and proc.returncode is None:
            try:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except Exception:
                pass
        return False, None, str(e)


async def generate_thumbnail(video_path, thumb_path=None, duration=None):
    """
    Generate a thumbnail from a video file using ffmpeg.
    Multi-pass approach with proper resource cleanup to prevent hangs and leaks.
    
    Args:
        video_path: Path to the video file
        thumb_path: Optional path for thumbnail. If None, uses video_path + ".jpg"
        duration: Optional video duration in seconds (for calculating middle frame)
    
    Returns:
        str: Path to generated thumbnail, or None if failed
    """
    if thumb_path is None:
        thumb_path = video_path + ".thumb.jpg"
    
    has_video, probe_duration, error_msg = await has_video_stream(video_path)
    if not has_video:
        LOGGER(__name__).info(f"Skipping thumbnail for {os.path.basename(video_path)}: {error_msg}")
        return None
    
    if probe_duration and not duration:
        duration = probe_duration
    
    file_size = 0
    try:
        file_size = os.path.getsize(video_path)
    except OSError:
        pass
    
    base_timeout = 10.0
    if file_size > 100 * 1024 * 1024:
        base_timeout = 20.0
    if file_size > 500 * 1024 * 1024:
        base_timeout = 30.0
    
    seek_time = 0
    if duration and duration > 1:
        seek_time = min(max(1, int(duration // 4)), 5)
    
    strategies = [
        {
            "name": "standard",
            "cmd": [
                "ffmpeg", "-y", "-ss", str(seek_time), "-i", video_path,
                "-vframes", "1", "-vf", "scale=320:-1", "-q:v", "5", thumb_path
            ],
            "timeout": base_timeout
        },
        {
            "name": "thumbnail_filter",
            "cmd": [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", "thumbnail,scale=320:-1", "-frames:v", "1", "-q:v", "5", thumb_path
            ],
            "timeout": base_timeout * 1.5
        },
        {
            "name": "first_frame",
            "cmd": [
                "ffmpeg", "-y", "-analyzeduration", "20M", "-probesize", "20M",
                "-i", video_path, "-ss", "0", "-vframes", "1",
                "-vf", "scale=320:-1", "-q:v", "5", thumb_path
            ],
            "timeout": base_timeout * 2
        }
    ]
    
    for strategy in strategies:
        proc = None
        try:
            proc = await create_subprocess_exec(*strategy["cmd"], stdout=PIPE, stderr=PIPE)
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=strategy["timeout"])
            except asyncio.TimeoutError:
                if proc:
                    try:
                        proc.kill()
                        await asyncio.wait_for(proc.wait(), timeout=3.0)
                    except Exception:
                        pass
                continue
            
            if proc.returncode == 0:
                try:
                    if os.path.exists(thumb_path):
                        thumb_size = os.path.getsize(thumb_path)
                        if thumb_size > 0:
                            return thumb_path
                        else:
                            try:
                                os.remove(thumb_path)
                            except OSError:
                                pass
                except OSError:
                    pass
        except Exception:
            if proc:
                try:
                    if proc.returncode is None:
                        proc.kill()
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                except Exception:
                    pass
        finally:
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except Exception:
                    pass
                finally:
                    proc = None
    
    LOGGER(__name__).warning(f"Thumbnail generation failed: {os.path.basename(video_path)}")
    try:
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
    except OSError:
        pass
    return None


async def get_media_info(path):
    try:
        result = await cmd_exec([
            "ffprobe", "-hide_banner", "-loglevel", "error",
            "-print_format", "json", "-show_format", "-show_streams", path,
        ])
    except Exception:
        return 0, None, None
    
    if result[0] and result[2] == 0:
        try:
            try:
                import orjson
                data = orjson.loads(result[0])
            except ImportError:
                import json
                data = json.loads(result[0])
        except Exception as e:
            LOGGER(__name__).error(f"Failed to parse ffprobe JSON: {e}")
            return 0, None, None
        
        duration = 0
        artist = None
        title = None
        
        # Try to get duration from format first
        format_info = data.get("format", {})
        if format_info:
            try:
                duration_str = format_info.get("duration", "0")
                if duration_str and duration_str != "N/A":
                    duration = round(float(duration_str))
            except (ValueError, TypeError):
                pass
            
            # Get tags from format
            tags = format_info.get("tags", {})
            artist = tags.get("artist") or tags.get("ARTIST") or tags.get("Artist")
            title = tags.get("title") or tags.get("TITLE") or tags.get("Title")
        
        # If format duration is 0 or missing, try to get from video stream
        if duration == 0:
            streams = data.get("streams", [])
            for stream in streams:
                if stream.get("codec_type") == "video":
                    try:
                        stream_duration = stream.get("duration")
                        if stream_duration and stream_duration != "N/A":
                            duration = round(float(stream_duration))
                            LOGGER(__name__).info(f"Got duration from video stream: {duration}s")
                            break
                    except (ValueError, TypeError):
                        continue
        
        return duration, artist, title
    return 0, None, None


# Progress Throttle Helper to prevent Telegram API rate limits
class ProgressThrottle:
    """
    Centralized progress throttling to prevent Telegram API rate limits.
    Enforces minimum time between updates and handles rate limit errors gracefully.
    Also tracks transfer progress for accurate speed calculations.
    
    FIXED: More aggressive cleanup to prevent memory accumulation.
    """
    def __init__(self):
        self.message_throttles = {}  # message_id -> throttle data
        self._last_sweep = time()
        self._sweep_interval = 180  # FIXED: Sweep every 3 minutes (was 5)
        self._max_age = 1800  # FIXED: Remove entries older than 30 min (was 1 hour)
    
    def _sweep_stale_entries(self, now):
        """Remove stale throttle entries to prevent memory accumulation"""
        if now - self._last_sweep < self._sweep_interval:
            return
        
        self._last_sweep = now
        stale_keys = [
            msg_id for msg_id, data in self.message_throttles.items()
            if now - data.get('last_update_time', 0) > self._max_age
        ]
        
        for key in stale_keys:
            del self.message_throttles[key]
        
        if stale_keys:
            LOGGER(__name__).debug(f"Cleaned up {len(stale_keys)} stale throttle entries")
    
    def should_update(self, message_id, current, total, now):
        """
        Determine if progress should be updated based on throttle rules.
        
        Rules:
        - Minimum 5 seconds between updates (or 10% progress change)
        - If rate limited, exponential backoff up to 60 seconds
        - Always allow 100% completion
        """
        self._sweep_stale_entries(now)
        
        if message_id not in self.message_throttles:
            self.message_throttles[message_id] = {
                'last_update_time': 0,
                'last_percentage': 0,
                'last_bytes': 0,
                'last_speed_time': now,
                'rate_limited': False,
                'backoff_duration': 5,  # Start with 5 seconds
                'cooldown_until': 0
            }
        
        throttle = self.message_throttles[message_id]
        percentage = (current / total) * 100 if total > 0 else 0
        
        # Always allow 100% completion
        if percentage >= 100:
            return True
        
        # If we're in cooldown from rate limiting, don't update
        if throttle['cooldown_until'] > now:
            return False
        
        # Check time and percentage thresholds
        time_diff = now - throttle['last_update_time']
        percentage_diff = percentage - throttle['last_percentage']
        
        # Require minimum 5 seconds OR 10% progress
        min_time = throttle['backoff_duration']
        return time_diff >= min_time or percentage_diff >= 10
    
    def get_current_speed(self, message_id, current, now):
        """
        Calculate current transfer speed based on bytes transferred since last update.
        Returns speed in bytes per second.
        """
        if message_id not in self.message_throttles:
            return 0
        
        throttle = self.message_throttles[message_id]
        last_bytes = throttle.get('last_bytes', 0)
        last_time = throttle.get('last_speed_time', now)
        
        time_diff = now - last_time
        bytes_diff = current - last_bytes
        
        if time_diff > 0 and bytes_diff > 0:
            return bytes_diff / time_diff
        return 0
    
    def mark_updated(self, message_id, percentage, now, current_bytes=0):
        """Mark that an update was successfully sent"""
        if message_id in self.message_throttles:
            throttle = self.message_throttles[message_id]
            throttle['last_update_time'] = now
            throttle['last_percentage'] = percentage
            throttle['last_bytes'] = current_bytes
            throttle['last_speed_time'] = now
            # Reset backoff on successful update
            throttle['rate_limited'] = False
            throttle['backoff_duration'] = 5
    
    def mark_rate_limited(self, message_id, now):
        """Mark that we hit a rate limit and implement exponential backoff"""
        if message_id in self.message_throttles:
            throttle = self.message_throttles[message_id]
            throttle['rate_limited'] = True
            # Exponential backoff: 5s -> 10s -> 20s -> 40s -> 60s (max)
            throttle['backoff_duration'] = min(throttle['backoff_duration'] * 2, 60)
            throttle['cooldown_until'] = now + throttle['backoff_duration']
            LOGGER(__name__).info(f"Rate limited - backing off for {throttle['backoff_duration']}s")
    
    def cleanup(self, message_id):
        """Remove throttle data when done"""
        if message_id in self.message_throttles:
            del self.message_throttles[message_id]

# Global throttle instance
_progress_throttle = ProgressThrottle()

# Native Pyrogram progress callback (replaces Pyleaves to reduce RAM)
async def safe_progress_callback(current, total, *args):
    """
    Native Pyrogram progress callback - lightweight and RAM-efficient
    Pyrogram progress callback signature: callback(current, total)
    
    Args:
        current: Current bytes transferred
        total: Total bytes to transfer
        *args: (action, progress_message, start_time)
    """
    progress_message = None
    try:
        # Unpack args
        action = args[0] if len(args) > 0 else "Progress"
        progress_message = args[1] if len(args) > 1 else None
        start_time = args[2] if len(args) > 2 else time()
        
        # Guard against None progress_message
        if not progress_message:
            return
        
        now = time()
        percentage = (current / total) * 100 if total > 0 else 0
        message_id = progress_message.id
        
        # Check throttle - only update if allowed
        if not _progress_throttle.should_update(message_id, current, total, now):
            return
        
        # Calculate current speed based on bytes transferred since last update
        current_speed = _progress_throttle.get_current_speed(message_id, current, now)
        
        # Fallback to average speed if no previous data (first update)
        elapsed_time = now - start_time
        if current_speed == 0 and elapsed_time > 0:
            current_speed = current / elapsed_time
        
        # Calculate ETA based on current speed
        eta = (total - current) / current_speed if current_speed > 0 else 0
        
        # Import here to avoid circular dependency
        from helpers.files import get_readable_file_size, get_readable_time
        
        # RAM-efficient visual progress bar using string slicing
        pct = int(percentage)
        filled_count = pct // 5  # 0-20 filled blocks
        
        FILLED_BAR = "████████████████████"  # 20 filled chars
        EMPTY_BAR = "░░░░░░░░░░░░░░░░░░░░"   # 20 empty chars
        
        progress_bar = f"[{FILLED_BAR[:filled_count]}{EMPTY_BAR[:20-filled_count]}]"
        
        progress_text = f"**{action}** `{pct}%`\n{progress_bar}\n{get_readable_file_size(current)}/{get_readable_file_size(total)} • {get_readable_file_size(current_speed)}/s • {get_readable_time(int(eta))}"
        
        # Try to update message
        await progress_message.edit(progress_text)
        # Mark successful update with current bytes for next speed calculation
        _progress_throttle.mark_updated(message_id, percentage, now, current)
            
    except Exception as e:
        error_str = str(e).lower()
        
        # Check if it's a rate limit error
        if 'wait of' in error_str and 'seconds is required' in error_str:
            if progress_message:
                _progress_throttle.mark_rate_limited(progress_message.id, time())
            LOGGER(__name__).warning("Rate limited by Telegram API - backing off")
        elif any(err in error_str for err in ['message_id_invalid', 'message not found', 'message to edit not found', "message can't be edited"]):
            pass  # Silently ignore deleted/invalid messages
        else:
            LOGGER(__name__).warning(f"Progress callback error: {e}")


async def forward_to_dump_channel(bot, sent_message, user_id, caption=None, source_url=None):
    """
    Send media to dump channel for monitoring (if configured).
    Uses copy_message to avoid "forwarded from" tag.
    """
    from config import PyroConf
    
    if not PyroConf.DUMP_CHANNEL_ID:
        return
    
    try:
        channel_id = int(PyroConf.DUMP_CHANNEL_ID)
        
        if channel_id > 0:
            LOGGER(__name__).warning(f"[DUMP_CHANNEL] Invalid dump channel ID (positive): {channel_id}")
            return
        
        dump_caption = f"👤 User ID: {user_id}"
        if source_url:
            dump_caption += f"\n🔗 Source: {source_url}"
        if caption:
            dump_caption += f"\n\n{caption}"
        
        try:
            await bot.copy_message(
                chat_id=channel_id,
                from_chat_id=sent_message.chat.id,
                message_id=sent_message.id,
                caption=dump_caption
            )
            LOGGER(__name__).info(f"[DUMP_CHANNEL] ✅ Media copied to dump channel for user {user_id}")
                
        except Exception as copy_error:
            LOGGER(__name__).warning(f"[DUMP_CHANNEL] Failed to copy media for user {user_id}: {copy_error}")
            
    except Exception as e:
        LOGGER(__name__).error(f"[DUMP_CHANNEL] Unexpected error: {e}")


def progressArgs(action: str, progress_message, start_time):
    """Generate progress args for downloading/uploading (minimal tuple - low RAM)"""
    return (action, progress_message, start_time)


async def send_media(
    bot, message, media_path, media_type, caption, progress_message, start_time, user_id=None, source_url=None
):
    """Upload media with all safeguards (size checks, fast uploads, thumbnails, dump channel).
    
    Returns:
        bool: True if upload succeeded, False if it was rejected or failed
    """
    file_size = os.path.getsize(media_path)

    if not await fileSizeLimit(file_size, message, "upload"):
        return False

    from memory_monitor import memory_monitor
    memory_monitor.log_memory_snapshot("Upload Start", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} ({media_type})", silent=True)
    
    # Create sync upload progress callback with throttling
    last_update = {"time": time(), "percent": 0}
    
    def create_upload_progress_callback():
        def upload_progress(current, total):
            try:
                if total > 0 and progress_message:
                    now = time()
                    percent = int((current / total) * 100)
                    elapsed = now - start_time
                    
                    should_update = (
                        (now - last_update["time"] >= 5) or
                        (percent - last_update["percent"] >= 10) or
                        (percent == 100)
                    )
                    
                    if should_update and elapsed > 0:
                        last_update["time"] = now
                        last_update["percent"] = percent
                        
                        speed_mbps = (current / elapsed) / 1024 / 1024
                        remaining_time = (total - current) / (current / elapsed) if current > 0 else 0
                        eta_str = f"{int(remaining_time)}s" if remaining_time < 60 else f"{int(remaining_time / 60)}m"
                        try:
                            asyncio.create_task(progress_message.edit_text(
                                f"**📤 Uploading: {percent}%**\n"
                                f"Speed: {speed_mbps:.1f} MB/s\n"
                                f"ETA: {eta_str}"
                            ))
                        except Exception:
                            pass
            except Exception:
                pass
        return upload_progress

    if media_type == "photo":
        from helpers.transfer import upload_media_fast
        
        fast_file = await upload_media_fast(bot, media_path, progress_callback=None)
        
        sent_message = None
        if fast_file:
            sent_message = await bot.send_photo(
                message.chat.id,
                photo=fast_file,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        else:
            sent_message = await bot.send_photo(
                message.chat.id,
                photo=media_path,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        
        if user_id and sent_message:
            await forward_to_dump_channel(bot, sent_message, user_id, caption, source_url)
        
        memory_monitor.log_memory_snapshot("Upload Complete", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} (photo)", silent=True)
        return True
        
    elif media_type == "video":
        try:
            media_info = await get_media_info(media_path)
            duration = media_info[0] if media_info and len(media_info) > 0 else None
        except Exception:
            duration = None
        
        width = 480 if duration and duration > 0 else None
        height = 320 if duration and duration > 0 else None
        
        thumb_path = None
        try:
            thumb_path = await generate_thumbnail(media_path, duration=duration)
        except Exception:
            thumb_path = None
        
        sent_message = None
        try:
            from helpers.transfer import upload_media_fast
            
            fast_file = await upload_media_fast(bot, media_path, progress_callback=None)
            
            send_kwargs = {
                "chat_id": message.chat.id,
                "video": fast_file if fast_file else media_path,
                "caption": caption or "",
                "progress": create_upload_progress_callback(),
                "supports_streaming": True
            }
            
            if duration and duration > 0:
                send_kwargs["duration"] = int(duration)
            if width and width > 0:
                send_kwargs["width"] = width
            if height and height > 0:
                send_kwargs["height"] = height
            if thumb_path and os.path.exists(thumb_path):
                send_kwargs["thumb"] = thumb_path
            
            sent_message = await bot.send_video(**send_kwargs)
        except Exception as e:
            LOGGER(__name__).error(f"Upload failed: {e}")
            raise
        finally:
            if thumb_path and os.path.exists(thumb_path):
                try:
                    os.remove(thumb_path)
                except OSError:
                    pass
        
        if user_id and sent_message:
            await forward_to_dump_channel(bot, sent_message, user_id, caption, source_url)
        
        memory_monitor.log_memory_snapshot("Upload Complete", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} (video)", silent=True)
        return True
        
    elif media_type == "audio":
        duration, artist, title = await get_media_info(media_path)
        
        from helpers.transfer import upload_media_fast
        
        fast_file = await upload_media_fast(bot, media_path, progress_callback=None)
        
        sent_message = None
        if fast_file:
            sent_message = await bot.send_audio(
                message.chat.id,
                audio=fast_file,
                duration=duration if duration and duration > 0 else None,
                performer=artist,
                title=title,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        else:
            sent_message = await bot.send_audio(
                message.chat.id,
                audio=media_path,
                duration=duration if duration and duration > 0 else None,
                performer=artist,
                title=title,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        
        if user_id and sent_message:
            await forward_to_dump_channel(bot, sent_message, user_id, caption, source_url)
        
        memory_monitor.log_memory_snapshot("Upload Complete", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} (audio)", silent=True)
        return True
        
    elif media_type == "document":
        from helpers.transfer import upload_media_fast
        
        fast_file = await upload_media_fast(bot, media_path, progress_callback=None)
        
        sent_message = None
        if fast_file:
            sent_message = await bot.send_document(
                message.chat.id,
                document=fast_file,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        else:
            sent_message = await bot.send_document(
                message.chat.id,
                document=media_path,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        
        if user_id and sent_message:
            await forward_to_dump_channel(bot, sent_message, user_id, caption, source_url)
        
        memory_monitor.log_memory_snapshot("Upload Complete", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} (document)", silent=True)
        return True
        
    elif media_type == "voice":
        from helpers.transfer import upload_media_fast
        duration, _, _ = await get_media_info(media_path)
        
        fast_file = await upload_media_fast(bot, media_path, progress_callback=None)
        sent_message = None
        if fast_file:
            sent_message = await bot.send_voice(
                message.chat.id,
                voice=fast_file,
                duration=duration if duration and duration > 0 else None,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        else:
            sent_message = await bot.send_voice(
                message.chat.id,
                voice=media_path,
                duration=duration if duration and duration > 0 else None,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        
        if user_id and sent_message:
            await forward_to_dump_channel(bot, sent_message, user_id, caption, source_url)
        
        memory_monitor.log_memory_snapshot("Upload Complete", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} (voice)", silent=True)
        return True
        
    elif media_type == "video_note":
        duration, _, _ = await get_media_info(media_path)
        
        from helpers.transfer import upload_media_fast
        fast_file = await upload_media_fast(bot, media_path, progress_callback=None)
        sent_message = None
        if fast_file:
            sent_message = await bot.send_video_note(
                message.chat.id,
                video_note=fast_file,
                duration=duration if duration and duration > 0 else None,
                progress=create_upload_progress_callback()
            )
        else:
            sent_message = await bot.send_video_note(
                message.chat.id,
                video_note=media_path,
                duration=duration if duration and duration > 0 else None,
                progress=create_upload_progress_callback()
            )
        
        if user_id and sent_message:
            await forward_to_dump_channel(bot, sent_message, user_id, None, source_url)
        
        memory_monitor.log_memory_snapshot("Upload Complete", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} (video_note)", silent=True)
        return True
        
    elif media_type == "animation":
        duration, _, _ = await get_media_info(media_path)
        
        from helpers.transfer import upload_media_fast
        fast_file = await upload_media_fast(bot, media_path, progress_callback=None)
        sent_message = None
        if fast_file:
            sent_message = await bot.send_animation(
                message.chat.id,
                animation=fast_file,
                duration=duration if duration and duration > 0 else None,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        else:
            sent_message = await bot.send_animation(
                message.chat.id,
                animation=media_path,
                duration=duration if duration and duration > 0 else None,
                caption=caption or "",
                progress=create_upload_progress_callback()
            )
        
        if user_id and sent_message:
            await forward_to_dump_channel(bot, sent_message, user_id, caption, source_url)
        
        memory_monitor.log_memory_snapshot("Upload Complete", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} (animation)", silent=True)
        return True
        
    elif media_type == "sticker":
        from helpers.transfer import upload_media_fast
        fast_file = await upload_media_fast(bot, media_path, progress_callback=None)
        sent_message = None
        if fast_file:
            sent_message = await bot.send_sticker(
                message.chat.id,
                sticker=fast_file,
                progress=create_upload_progress_callback()
            )
        else:
            sent_message = await bot.send_sticker(
                message.chat.id,
                sticker=media_path,
                progress=create_upload_progress_callback()
            )
        
        if user_id and sent_message:
            await forward_to_dump_channel(bot, sent_message, user_id, None, source_url)
        
        memory_monitor.log_memory_snapshot("Upload Complete", f"User {user_id or 'unknown'}: {os.path.basename(media_path)} (sticker)", silent=True)
        return True
    
    return False


PER_FILE_TIMEOUT_SECONDS = 2700


async def _process_single_media_file(
    client_for_download, bot, user_message, msg, download_path, 
    idx, total_files, progress_message, file_start_time, user_id, source_url
):
    """
    Process a single file from a media group - download and upload.
    
    CRITICAL: This function is defined OUTSIDE processMediaGroup to prevent closure capture.
    All parameters are passed explicitly to avoid holding references to Pyrogram Message objects.
    """
    # STEP 1: Download this file
    def media_group_download_progress(current, total):
        try:
            if total > 0 and progress_message:
                percent = int((current / total) * 100)
                elapsed = time() - file_start_time
                if elapsed > 0:
                    speed_mbps = (current / elapsed) / 1024 / 1024
                    remaining_time = (total - current) / (current / elapsed) if current > 0 else 0
                    eta_str = f"{int(remaining_time)}s" if remaining_time < 60 else f"{int(remaining_time / 60)}m"
                    try:
                        asyncio.create_task(progress_message.edit_text(
                            f"**📥 Downloading {idx}/{total_files}: {percent}%**\n"
                            f"Speed: {speed_mbps:.1f} MB/s\n"
                            f"ETA: {eta_str}"
                        ))
                    except Exception:
                        pass
        except Exception:
            pass
    
    result_path = await download_media_fast(
        client=client_for_download,
        message=msg,
        file=download_path,
        progress_callback=media_group_download_progress
    )
    
    if not result_path:
        LOGGER(__name__).warning(f"File {idx}/{total_files} download failed: no media path returned")
        return None, False
    
    # RAM OPTIMIZATION: Release download buffers before upload starts
    gc.collect()
    
    # Determine media type from msg attributes
    media_type = (
        "photo" if msg.photo
        else "video" if msg.video
        else "audio" if msg.audio
        else "voice" if msg.voice
        else "video_note" if msg.video_note
        else "animation" if msg.animation
        else "sticker" if msg.sticker
        else "document"
    )
    
    caption_text = msg.text or ""
    
    # STEP 2: Upload this file
    LOGGER(__name__).info(f"Uploading file {idx}/{total_files} to user (via send_media)")
    upload_success = await send_media(
        bot=bot,
        message=user_message,
        media_path=result_path,
        media_type=media_type,
        caption=caption_text,
        progress_message=progress_message,
        start_time=file_start_time,
        user_id=user_id,
        source_url=source_url
    )
    
    return result_path, upload_success


async def processMediaGroup(chat_message, bot, message, user_id=None, user_client=None, source_url=None):
    """Process and download a media group (multiple files in one post)
    
    ONE-AT-A-TIME APPROACH: Downloads and uploads each file sequentially to minimize RAM usage.
    """
    from memory_monitor import memory_monitor
    
    memory_monitor.log_memory_snapshot("MediaGroup Start", f"User {user_id or 'unknown'}: Starting media group processing", silent=True)
    
    client_for_download = user_client if user_client else bot
    
    chat_id = chat_message.chat.id
    grouped_id = chat_message.media_group_id
    
    media_group_messages = await client_for_download.get_messages(
        chat_id,
        message_ids=[chat_message.id + i for i in range(-10, 11)]
    )
    
    # CRITICAL RAM FIX: Extract only message IDs, then immediately clear the message list
    message_ids = []
    if grouped_id:
        for msg in media_group_messages:
            if msg and hasattr(msg, 'media_group_id') and msg.media_group_id == grouped_id:
                message_ids.append(msg.id)
    else:
        message_ids = [chat_message.id]
    
    message_ids.sort()
    
    # CRITICAL: Clear references to message objects immediately
    del media_group_messages
    gc.collect()
    
    total_files = len(message_ids)
    files_sent_count = 0
    
    # Determine user tier once for all files
    is_premium = False
    if user_id:
        try:
            from database_sqlite import db
            user_type = db.get_user_type(user_id)
            is_premium = user_type in ['paid', 'admin']
        except Exception as e:
            LOGGER(__name__).warning(f"Could not determine user tier, using free tier: {e}")
    
    start_time = time()
    progress_message = await message.reply(f"📥 Processing media group ({total_files} files)...")
    LOGGER(__name__).info(f"Processing media group with {total_files} items (one-at-a-time mode)...")

    for idx, msg_id in enumerate(message_ids, 1):
        msg = None
        media_path = None
        file_start_time = time()
        
        try:
            await progress_message.edit(f"📥 Processing file {idx}/{total_files} (45min timeout per file)...")
            
            # CRITICAL RAM FIX: Re-fetch the message fresh for each file
            msg = await client_for_download.get_messages(chat_id, message_ids=msg_id)
            
            if not msg or not (msg.media or msg.photo or msg.video or msg.document or msg.audio or msg.voice or msg.video_note or msg.animation or msg.sticker):
                LOGGER(__name__).warning(f"File {idx}/{total_files}: No media found in message {msg_id}")
                continue
            
            filename = get_file_name(msg.id, msg)
            download_path = get_download_path(message.id, filename)
            media_path = download_path
            
            LOGGER(__name__).info(f"Downloading file {idx}/{total_files}: {filename} (45min timeout)")
            
            try:
                result_path, upload_success = await asyncio.wait_for(
                    _process_single_media_file(
                        client_for_download=client_for_download,
                        bot=bot,
                        user_message=message,
                        msg=msg,
                        download_path=download_path,
                        idx=idx,
                        total_files=total_files,
                        progress_message=progress_message,
                        file_start_time=file_start_time,
                        user_id=user_id,
                        source_url=source_url
                    ),
                    timeout=PER_FILE_TIMEOUT_SECONDS
                )
                
                if result_path:
                    media_path = result_path
                
                if upload_success:
                    files_sent_count += 1
                    elapsed = time() - file_start_time
                    LOGGER(__name__).info(f"Successfully processed file {idx}/{total_files} in {elapsed:.1f}s")
                else:
                    LOGGER(__name__).warning(f"File {idx}/{total_files} was not sent (rejected by size limit or other error)")
                    
            except asyncio.TimeoutError:
                elapsed = time() - file_start_time
                LOGGER(__name__).error(
                    f"PER-FILE TIMEOUT: File {idx}/{total_files} timed out after {elapsed:.1f}s "
                    f"(limit: {PER_FILE_TIMEOUT_SECONDS}s / 45min)"
                )
                try:
                    await progress_message.edit(f"⏰ File {idx}/{total_files} timed out after 45 minutes. Moving to next file...")
                except Exception:
                    pass
            
            # STEP 3: Delete the file and release RAM
            if media_path:
                try:
                    from database_sqlite import db
                    await cleanup_download_delayed(media_path, user_id, db)
                    LOGGER(__name__).info(f"Cleaned up file {idx}/{total_files}: {os.path.basename(media_path)}")
                except Exception as cleanup_err:
                    LOGGER(__name__).warning(f"Failed to cleanup file {idx}/{total_files}: {cleanup_err}")
            
            # STEP 4: Tier-aware cooldown between files
            if idx < total_files:
                delay = get_intra_request_delay(is_premium)
                LOGGER(__name__).info(f"⏳ Waiting {delay}s before next file (RAM cooldown)")
                await asyncio.sleep(delay)
            
        except asyncio.CancelledError:
            LOGGER(__name__).info(f"File {idx}/{total_files} processing cancelled")
            if media_path:
                try:
                    from database_sqlite import db
                    await cleanup_download_delayed(media_path, user_id, db)
                except Exception:
                    pass
            raise
            
        except Exception as e:
            LOGGER(__name__).error(f"Error processing file {idx}/{total_files} from message {msg_id}: {e}")
            if media_path:
                try:
                    from database_sqlite import db
                    await cleanup_download_delayed(media_path, user_id, db)
                except Exception:
                    pass
            
            if idx < total_files:
                delay = get_intra_request_delay(is_premium)
                LOGGER(__name__).info(f"⏳ Waiting {delay}s after error before next file")
                await asyncio.sleep(delay)
            
            continue
        
        finally:
            # CRITICAL RAM FIX: Explicitly delete msg reference after each iteration
            if msg is not None:
                del msg
                msg = None
            if media_path is not None:
                del media_path
                media_path = None
            gc.collect()

    # Cleanup throttle data
    _progress_throttle.cleanup(progress_message.id)
    
    await progress_message.delete()
    
    memory_monitor.log_memory_snapshot("MediaGroup Complete", f"User {user_id or 'unknown'}: {files_sent_count}/{total_files} files processed", silent=True)
    
    gc.collect()
    
    if files_sent_count == 0:
        await message.reply("**❌ No valid media found in the group**")
        return 0
    
    LOGGER(__name__).info(f"Media group complete: {files_sent_count}/{total_files} files sent successfully")
    return files_sent_count
