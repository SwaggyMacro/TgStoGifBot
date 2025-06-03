"""
Export `.tgs` files for single stickers or entire sticker sets, including conversion logic.
"""
import os
import zipfile
import asyncio
import shutil
from telegram.error import RetryAfter, TimedOut
from loguru import logger
from utils import split_and_upload_document
from converter import tgs_convert
from typing import Dict, Any


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
                file = await bot.get_file(sticker_file_id)
                await file.download_to_drive(tgs_path)
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

        for idx, sticker in enumerate(animated):
            if idx % 5 == 0:
                await feedback_msg.reply_text(f"⏳ Downloading .tgs {idx+1}/{total}…")
            out_path = f"{tmp_dir}/{sticker.file_unique_id}.tgs"
            try:
                file = await bot.get_file(sticker.file_id)
                await file.download_to_drive(out_path)
            except (RetryAfter, TimedOut):
                continue  # skip or retry logic could be added here

        zip_path = f"{tmp_dir}/{sticker_set_name}_tgs.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for sticker in animated:
                tgs_path = f"{tmp_dir}/{sticker.file_unique_id}.tgs"
                if os.path.exists(tgs_path):
                    zf.write(
                        tgs_path,
                        f"{sticker_set_name}/tgs/{sticker.file_unique_id}.tgs"
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
                await file.download_to_drive(tgs_path)
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
                f"• *Credits:* @sticker_to_gif_01_bot\n"
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
        if not animated:
            await feedback_msg.reply_text("ℹ️ No animated stickers found in this set.")
            return
        total = len(animated)
        await feedback_msg.reply_text(
            f"📥 Downloading `{sticker_set_name}` ({total} total)…\n_Downloading .tgs files one by one…_", parse_mode="Markdown"
        )
        for idx, sticker in enumerate(animated):
            if idx % 5 == 0:
                await feedback_msg.reply_text(f"⏳ Downloading sticker {idx+1} of {total}…")
            out_path = f"{tmp_dir}/{sticker.file_unique_id}.tgs"
            try:
                file = await bot.get_file(sticker.file_id)
                await file.download_to_drive(out_path)
                logger.info(f"Downloaded {sticker.file_unique_id}.tgs")
            except (RetryAfter, TimedOut) as e:
                wait_time = getattr(e, "retry_after", 60)
                await feedback_msg.reply_text(f"⚠️ Rate limited, waiting {wait_time}s (retry)…")
                await asyncio.sleep(wait_time)
                try:
                    file = await bot.get_file(sticker.file_id)
                    await file.download_to_drive(out_path)
                except Exception as ex2:
                    logger.error(f"Failed to download after retry {sticker.file_unique_id}: {ex2}")
            except Exception as ex:
                logger.error(f"Failed to download {sticker.file_unique_id}: {ex}")

        # 2) Convert each .tgs concurrently
        await feedback_msg.reply_text(
            f"⚙️ Converting `{sticker_set_name}` to {chosen_format.upper()}…\n_This may take a while…_", parse_mode="Markdown"
        )
        script_path = get_script_path(chosen_format)
        sem = asyncio.Semaphore(5)
        async def convert_one(sticker_obj, idx):
            async with sem:
                if idx % 5 == 0:
                    await feedback_msg.reply_text(f"⏳ Converting sticker {idx+1} of {total}…")
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
        tasks = [convert_one(st, i) for i, st in enumerate(animated)]
        await asyncio.gather(*tasks)

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
                f"• *Credits:* @sticker_to_gif_01_bot\n"
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