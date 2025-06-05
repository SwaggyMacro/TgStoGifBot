"""
Export `.tgs` files for single stickers or entire sticker sets, including conversion logic.
"""
import os
import zipfile
import asyncio
import shutil

from httpx import ConnectError
from telegram.error import RetryAfter, TimedOut
from loguru import logger

from config import load_config
from retry_utils import retry_on_exception
from utils import split_and_upload_document
from converter import tgs_convert
from typing import Dict, Any


_config = load_config()
DOWNLOAD_WORKERS = _config.get("download_workers", 15)
CONVERT_WORKERS = _config.get("convert_workers", 5)
BOT_USER_NAME = _config.get("bot_user_name", "@sticker\\_to\\_gif\\_01\\_bot")

def get_script_path(format_type: str) -> str:
    """
    Return the conversion script path based on format type and platform.

    :param format_type: One of "gif", "png", "webp", "apng".
    :return: Path to the shell script.
    :raises ValueError: If format_type is invalid.
    """
    import platform
    PLAT = f"{platform.system().lower()}_{platform.machine().lower()}"
    if PLAT == "linux_x86_64":
        PLAT = "linux_amd64"
    if PLAT not in ["linux_amd64", "windows_amd64"]:
        raise ValueError(f"Unsupported platform: {PLAT}")

    script_map = {
        "gif": f"lib/{PLAT}/lottie_to_gif.sh",
        "png": f"lib/{PLAT}/lottie_to_png.sh",
        "webp": f"lib/{PLAT}/lottie_to_webp.sh",
        "apng": f"lib/{PLAT}/lottie_to_apng.sh",
    }
    if format_type not in script_map:
        raise ValueError(f"Invalid format type: {format_type}")
    return script_map[format_type]


@retry_on_exception((ConnectError, TimedOut, Exception), max_retries=None)
async def get_file_retry(bot, file_id):
    return await bot.get_file(file_id)

@retry_on_exception((ConnectError, TimedOut, Exception), max_retries=None)
async def download_to_drive_retry(file_obj, path):
    return await file_obj.download_to_drive(path)


async def process_single_export(
    bot,
    single_info: Dict[str, Any],
    feedback_msg,
) -> None:
    """
    Download a single sticker's `.tgs`, package into a ZIP, and send to user.

    :param bot: Telegram Bot instance.
    :param single_info: Dict with keys `file_id`, `file_unique_id`, and `set_name`.
    :param feedback_msg: Telegram message object to reply to.
    """
    sticker_file_id = single_info["file_id"]
    unique_id = single_info["file_unique_id"]
    set_name = single_info["set_name"]
    user_id = feedback_msg.from_user.id

    tmp_dir = f"tmp/{set_name}-{user_id}-{unique_id}-export"
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        await feedback_msg.reply_text("📥 Downloading .tgs file…", parse_mode="Markdown")
        tgs_path = f"{tmp_dir}/{unique_id}.tgs"

        for attempt in range(3):
            try:
                file = await get_file_retry(bot, sticker_file_id)
                await download_to_drive_retry(file, tgs_path)
                break
            except (RetryAfter, TimedOut) as e:
                wait_time = getattr(e, "retry_after", 60)
                await feedback_msg.reply_text(
                    f"⚠️ Rate limited, retrying ({attempt+1}/3)… waiting {wait_time}s",
                    parse_mode="Markdown",
                )
                await asyncio.sleep(wait_time)

        if not os.path.exists(tgs_path):
            await feedback_msg.reply_text("❌ Failed to download .tgs file.", parse_mode="Markdown")
            return

        zip_name = f"{set_name}_{unique_id}_tgs.zip"
        zip_path = f"{tmp_dir}/{zip_name}"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(tgs_path, arcname=f"{set_name}/{unique_id}.tgs")

        await feedback_msg.reply_text("📤 Sending .tgs ZIP…", parse_mode="Markdown")
        await split_and_upload_document(
            feedback_msg,
            caption=(
                f"✅ *Export Completed!*\n"
                f"• Only `.tgs` file included.\n"
                f"• From sticker set: `{set_name}`"
            ),
            zip_path=zip_path,
            chunk_size=50_000_000,
        )

    except Exception as e:
        logger.error(f"Error in process_single_export: {e}")
        await feedback_msg.reply_text(f"❌ *Error:* `{e}`", parse_mode="Markdown")
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


async def process_set_export(
    bot,
    sticker_set,
    sticker_set_name: str,
    feedback_msg,
) -> None:
    """
    Download all `.tgs` in a sticker set, package into a ZIP, and send to user.

    :param bot: Telegram Bot instance.
    :param sticker_set: StickerSet object from Telegram.
    :param sticker_set_name: Name of the sticker set.
    :param feedback_msg: Telegram message object to reply to.
    """
    user_id = feedback_msg.from_user.id
    tmp_dir = f"tmp/{sticker_set_name}-{user_id}-export"
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        await feedback_msg.reply_text(
            f"🚀 *Exporting* `{sticker_set_name}` (only .tgs)", parse_mode="Markdown"
        )

        animated = [s for s in sticker_set.stickers if s.is_animated]
        if not animated:
            await feedback_msg.reply_text("ℹ️ No animated stickers found.")
            return

        total = len(animated)
        await feedback_msg.reply_text(
            f"📥 Downloading {total} animated .tgs…", parse_mode="Markdown"
        )

        sem_dl = asyncio.Semaphore(DOWNLOAD_WORKERS)

        async def download_one(idx: int, sticker):
            async with sem_dl:
                for attempt in range(3):
                    if idx % 5 == 0:
                        await feedback_msg.reply_text(f"⏳ Downloading .tgs {idx + 1}/{total}…")
                    out_path = f"{tmp_dir}/{sticker.file_unique_id}.tgs"
                    try:
                        file = await bot.get_file(sticker.file_id)
                        await download_to_drive_retry(file, out_path)
                        logger.info(f"Downloaded {sticker.file_unique_id}.tgs")
                        break
                    except (RetryAfter, TimedOut) as e:
                        wait_time = getattr(e, "retry_after", 60)
                        await feedback_msg.reply_text(
                            f"⚠️ Rate limited, waiting {wait_time}s (retry {attempt + 1}/3)…", parse_mode="Markdown"
                        )
                        await asyncio.sleep(wait_time)
                    except Exception as ex:
                        logger.error(f"Failed downloading {sticker.file_unique_id}: {ex}")

        await asyncio.gather(
            *(download_one(i, st) for i, st in enumerate(animated))
        )

        # 打包 ZIP
        zip_path = f"{tmp_dir}/{sticker_set_name}_tgs.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for st in animated:
                tgs_path = f"{tmp_dir}/{st.file_unique_id}.tgs"
                if os.path.exists(tgs_path):
                    zf.write(
                        tgs_path,
                        f"{sticker_set_name}/tgs/{st.file_unique_id}.tgs"
                    )

        await feedback_msg.reply_text("📤 Sending .tgs ZIP…", parse_mode="Markdown")
        await split_and_upload_document(
            feedback_msg,
            caption=(
                f"✅ *Export Completed!*\n"
                f"• Only `.tgs` files included.\n"
                f"• Sticker set: `{sticker_set_name}`"
            ),
            zip_path=zip_path,
            chunk_size=50_000_000,
        )

    except Exception as e:
        logger.error(f"Error in process_set_export: {e}")
        await feedback_msg.reply_text(f"❌ *Error:* `{e}`", parse_mode="Markdown")
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


async def process_single_sticker(
    bot,
    single_info: Dict[str, Any],
    chosen_format: str,
    quality: int,
    width: int,
    height: int,
    fps: int,
    feedback_msg,
) -> None:
    """
    Download, convert, and package a single sticker; then send to user.

    :param bot: Telegram Bot instance.
    :param single_info: Dict with keys `file_id`, `file_unique_id`, and `set_name`.
    :param chosen_format: Desired output format (`gif`, `png`, `webp`, `apng`).
    :param quality: Conversion quality (percentage).
    :param width: Output width.
    :param height: Output height.
    :param fps: Frame rate for conversion.
    :param feedback_msg: Telegram message object to reply to.
    """
    sticker_file_id = single_info["file_id"]
    unique_id = single_info["file_unique_id"]
    set_name = single_info["set_name"]
    user_id = feedback_msg.from_user.id

    tmp_dir = f"tmp/{set_name}-{user_id}-{unique_id}"
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        await feedback_msg.reply_text(
            f"🚀 *Processing* single sticker from `{set_name}`\n"
            f"**Format:** `{chosen_format.upper()}`\n"
            f"**Size:** `{width}×{height}`\n"
            f"**Quality:** `{quality}`%\n"
            f"**FPS:** `{fps}`",
            parse_mode="Markdown",
        )

        # 1) Download .tgs
        await feedback_msg.reply_text("📥 Downloading sticker…", parse_mode="Markdown")
        tgs_path = f"{tmp_dir}/{unique_id}.tgs"
        for attempt in range(3):
            try:
                file = await bot.get_file(sticker_file_id)
                await download_to_drive_retry(file, tgs_path)
                break
            except (RetryAfter, TimedOut) as e:
                wait_time = getattr(e, "retry_after", 60)
                await feedback_msg.reply_text(
                    f"⚠️ Rate limited, waiting {wait_time}s (retry {attempt+1}/3)…", parse_mode="Markdown"
                )
                await asyncio.sleep(wait_time)
        if not os.path.exists(tgs_path):
            await feedback_msg.reply_text("❌ Failed to download sticker.", parse_mode="Markdown")
            return

        # 2) Convert using tgs_convert
        await feedback_msg.reply_text(
            f"⚙️ Converting to {chosen_format.upper()}…", parse_mode="Markdown"
        )
        out_path = f"{tmp_dir}/{unique_id}.{chosen_format}"
        script_path = get_script_path(chosen_format)
        await asyncio.to_thread(
            tgs_convert,
            tgs_path,
            out_path,
            width,
            height,
            fps,
            quality,
            script_path,
        )
        logger.info(f"Converted {unique_id}.tgs → {out_path}")

        # 3) Package into ZIP
        zip_path = f"{tmp_dir}/{set_name}_{unique_id}.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(
                out_path,
                f"{set_name}/{chosen_format}/{unique_id}.{chosen_format}"
            )
            zf.write(
                tgs_path,
                f"{set_name}/tgs/{unique_id}.tgs"
            )

        # 4) Send ZIP
        await feedback_msg.reply_text("📤 Uploading file…", parse_mode="Markdown")
        await split_and_upload_document(
            feedback_msg,
            caption=(
                f"✅ *Task Completed!*\n"
                f"• *Credits:* {BOT_USER_NAME}\n"
                f"• [Add Stickers to Telegram](https://t.me/addstickers/{set_name})"
            ),
            zip_path=zip_path,
            chunk_size=50_000_000,
        )

    except Exception as e:
        logger.error(f"Error in process_single_sticker: {e}")
        await feedback_msg.reply_text(f"❌ *Error:* `{e}`", parse_mode="Markdown")
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


async def process_sticker_set(
    bot,
    sticker_set,
    sticker_set_name: str,
    chosen_format: str,
    quality: int,
    width: int,
    height: int,
    fps: int,
    feedback_msg,
) -> None:
    """
    Download, convert, and package an entire sticker set; then send to user.

    :param bot: Telegram Bot instance.
    :param sticker_set: StickerSet object from Telegram.
    :param sticker_set_name: Name of the sticker set.
    :param chosen_format: Desired output format (`gif`, `png`, `webp`, `apng`).
    :param quality: Conversion quality (percentage).
    :param width: Output width.
    :param height: Output height.
    :param fps: Frame rate for conversion.
    :param feedback_msg: Telegram message object to reply to.
    """
    user_id = feedback_msg.from_user.id
    tmp_dir = f"tmp/{sticker_set_name}-{user_id}"
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        await feedback_msg.reply_text(
            f"🚀 *Processing* `{sticker_set_name}`\n"
            f"**Format:** `{chosen_format.upper()}`\n"
            f"**Size:** `{width}×{height}`\n"
            f"**Quality:** `{quality}`%\n"
            f"**FPS:** `{fps}`",
            parse_mode="Markdown",
        )

        # 1) Download all .tgs
        animated = [s for s in sticker_set.stickers if s.is_animated]
        total = len(animated)
        if not animated:
            await feedback_msg.reply_text("ℹ️ No animated stickers found in this set.")
            return

        await feedback_msg.reply_text(
            f"📥 Downloading `{sticker_set_name}` ({total} total)…\n_Downloading .tgs files…_",
            parse_mode="Markdown"
        )

        sem_dl = asyncio.Semaphore(DOWNLOAD_WORKERS)

        async def download_one(idx: int, sticker):
            async with sem_dl:
                if idx % 5 == 0:
                    await feedback_msg.reply_text(f"⏳ Downloading sticker {idx + 1}/{total}…")
                out_path = f"{tmp_dir}/{sticker.file_unique_id}.tgs"
                for attempt in range(3):
                    try:
                        file = await get_file_retry(bot,sticker.file_id)
                        await download_to_drive_retry(file, out_path)
                        logger.info(f"Downloaded {sticker.file_unique_id}.tgs")
                        break
                    except (RetryAfter, TimedOut) as e:
                        wait_time = getattr(e, "retry_after", 60)
                        await feedback_msg.reply_text(
                            f"⚠️ Rate limited, waiting {wait_time}s (retry {attempt + 1}/3)…", parse_mode="Markdown"
                        )
                        await asyncio.sleep(wait_time)
                    except Exception as ex:
                        logger.error(f"Failed downloading {sticker.file_unique_id}: {ex}")

        await asyncio.gather(
            *(download_one(i, st) for i, st in enumerate(animated))
        )

        # 2) Convert each .tgs concurrently
        await feedback_msg.reply_text(
            f"⚙️ Converting `{sticker_set_name}` to {chosen_format.upper()}…", parse_mode="Markdown"
        )
        script_path = get_script_path(chosen_format)
        sem_conv = asyncio.Semaphore(CONVERT_WORKERS)

        async def convert_one(idx: int, sticker_obj):
            async with sem_conv:
                if idx % 5 == 0:
                    await feedback_msg.reply_text(f"⏳ Converting sticker {idx + 1}/{total}…")
                in_tgs = f"{tmp_dir}/{sticker_obj.file_unique_id}.tgs"
                out_img = f"{tmp_dir}/{sticker_obj.file_unique_id}.{chosen_format}"
                await asyncio.to_thread(
                    tgs_convert,
                    in_tgs,
                    out_img,
                    width,
                    height,
                    fps,
                    quality,
                    script_path,
                )
                logger.info(f"Converted {sticker_obj.file_unique_id}.tgs → {out_img}")

        await asyncio.gather(
            *(convert_one(i, st) for i, st in enumerate(animated))
        )

        # 3) Package all converted files plus original .tgs
        await feedback_msg.reply_text("📦 Zipping up results…", parse_mode="Markdown")
        zip_path = f"{tmp_dir}/{sticker_set_name}.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for sticker_obj in animated:
                img_path = f"{tmp_dir}/{sticker_obj.file_unique_id}.{chosen_format}"
                tgs_path = f"{tmp_dir}/{sticker_obj.file_unique_id}.tgs"
                if os.path.exists(img_path):
                    zf.write(
                        img_path,
                        f"{sticker_set_name}/{chosen_format}/{sticker_obj.file_unique_id}.{chosen_format}"
                    )
                if os.path.exists(tgs_path):
                    zf.write(
                        tgs_path,
                        f"{sticker_set_name}/tgs/{sticker_obj.file_unique_id}.tgs"
                    )

        # 4) Upload ZIP
        await feedback_msg.reply_text(
            f"📤 Uploading ZIP for `{sticker_set_name}` now…", parse_mode="Markdown"
        )
        await split_and_upload_document(
            feedback_msg,
            caption=(
                f"✅ *Task Completed!*\n"
                f"• *Credits:* {BOT_USER_NAME}"
                f"• [Add Stickers to Telegram](https://t.me/addstickers/{sticker_set_name})"
            ),
            zip_path=zip_path,
            chunk_size=50_000_000,
        )

    except Exception as e:
        logger.error(f"Error in process_sticker_set: {e}")
        await feedback_msg.reply_text(f"❌ *Error:* `{e}`", parse_mode="Markdown")
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)