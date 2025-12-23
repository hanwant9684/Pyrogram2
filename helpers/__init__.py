# Helpers module for Telegram Bot
# FIXED: Added proper exports to make this module useful

from helpers.files import (
    get_download_path,
    cleanup_download,
    cleanup_download_delayed,
    get_readable_file_size,
    get_readable_time,
    fileSizeLimit,
    cleanup_orphaned_files
)

from helpers.msg import (
    get_parsed_msg,
    getChatMsgID,
    get_file_name
)

from helpers.transfer import (
    download_media_fast,
    upload_media_fast,
    has_downloadable_media,
    get_connection_count_for_size
)

__all__ = [
    # files
    'get_download_path',
    'cleanup_download',
    'cleanup_download_delayed',
    'get_readable_file_size',
    'get_readable_time',
    'fileSizeLimit',
    'cleanup_orphaned_files',
    # msg
    'get_parsed_msg',
    'getChatMsgID',
    'get_file_name',
    # transfer
    'download_media_fast',
    'upload_media_fast',
    'has_downloadable_media',
    'get_connection_count_for_size',
]
