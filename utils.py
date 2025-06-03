"""
Utility functions for file uploads and ZIP management.
"""
import asyncio
import io
import os
import traceback

from loguru import logger
from telegram.error import RetryAfter, TimedOut


async def retry_upload_document(
    feedback_msg,
    file_obj,
    caption: str,
    parse_mode=None,
    max_retries: int = 5
) -> None:
    """
    Attempt to send a document (file path or BytesIO) with retry logic.

    :param feedback_msg: Telegram message object to reply to.
    :param file_obj: Either a file path (str) or a file-like object (e.g., BytesIO).
    :param caption: Caption text for the document.
    :param parse_mode: Parse mode for the caption (e.g., Markdown).
    :param max_retries: Maximum number of upload attempts.
    """
    for attempt in range(1, max_retries + 1):
        try:
            if isinstance(file_obj, str):
                # file_obj is a disk path
                with open(file_obj, "rb") as f:
                    await feedback_msg.reply_document(document=f, caption=caption, parse_mode=parse_mode)
            else:
                # file_obj is file-like (BytesIO)
                file_obj.seek(0)
                await feedback_msg.reply_document(document=file_obj, caption=caption, parse_mode=parse_mode)
            return  # successful upload
        except (RetryAfter, TimedOut) as e:
            logger.warning(f"Upload attempt {attempt} failed: {e}\n {traceback.format_exc()}")
            wait_secs = getattr(e, "retry_after", 5)
            await feedback_msg.reply_text(
                f"⚠️ Upload error: {e.__class__.__name__}. Retrying in {wait_secs}s (attempt {attempt}/{max_retries})…"
            )
            await asyncio.sleep(wait_secs)
        except Exception as e:
            await feedback_msg.reply_text(f"❌ Unexpected upload exception: `{e}`")
            raise

    await feedback_msg.reply_text(f"❌ Failed to upload after {max_retries} attempts.")


async def split_and_upload_document(
    feedback_msg,
    caption: str,
    zip_path: str,
    chunk_size: int = 50_000_000
) -> None:
    """
    Split a large ZIP into smaller parts and upload each.

    :param feedback_msg: Telegram message object to reply to.
    :param caption: Base caption for each part.
    :param zip_path: Path to the ZIP file.
    :param chunk_size: Maximum size (bytes) per part.
    """
    try:
        total_size = os.path.getsize(zip_path)
    except OSError as e:
        await feedback_msg.reply_text(f"❌ Could not stat '{zip_path}': {e}")
        return

    # If small enough, upload directly
    if total_size <= chunk_size:
        await retry_upload_document(feedback_msg, zip_path, caption, parse_mode="Markdown")
        return

    num_parts = (total_size + chunk_size - 1) // chunk_size
    await feedback_msg.reply_text(
        f"📦 Splitting large ZIP ({total_size // (1024*1024)} MB) into {num_parts} parts…"
    )

    with open(zip_path, "rb") as f:
        part_index = 1
        while True:
            chunk_data = f.read(chunk_size)
            if not chunk_data:
                break

            bio = io.BytesIO(chunk_data)
            base_name = os.path.basename(zip_path)
            bio.name = f"{base_name}.part{part_index:02d}"
            part_caption = f"{caption}\n(Part {part_index} of {num_parts})"
            await retry_upload_document(feedback_msg, bio, part_caption, parse_mode="Markdown")
            part_index += 1