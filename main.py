import json
import os
import platform
import shutil
import traceback

import pyrogram.errors.exceptions.flood_420
from pyrogram import Client, raw, enums
from pyrogram import filters
from loguru import logger

import subprocess
from lottie import parsers
import zipfile

from pyrogram.types import Message, Sticker

PLAT = f"{platform.system().lower()}_{platform.machine().lower()}"
if PLAT == "linux_x86_64":
    PLAT = "linux_amd64"

if PLAT not in ["linux_amd64", "windows_amd64"]:
    raise Exception(f"Unsupported platform: {PLAT}")


class TargetType:
    Gif = 0
    Png = 1
    Webp = 2
    Apng = 3
    ScriptPath = [
        f"lib/{PLAT}/lottie_to_gif.sh",
        f"lib/{PLAT}/lottie_to_png.sh",
        f"lib/{PLAT}/lottie_to_webp.sh",
        f"lib/{PLAT}/lottie_to_apng.sh"
    ]


def load_config():
    return json.loads(open("config.json").read())


config = load_config()

app = Client("Stickers To Gifs", api_id=config['api_id'], api_hash=config['api_hash'],
             bot_token=config['bot_token'])

if config['proxy']['status']:
    app.proxy = {
        "scheme": config['proxy']['scheme'],
        'hostname': config['proxy']['hostname'],
        'port': config['proxy']['port']
    }


async def tgs_convert(tgs_path, target_path, width=None, height=None, fps=60, quality=100, target_type=TargetType.Gif):
    animation = parsers.tgs.parse_tgs(tgs_path)
    if fps:
        animation.frame_rate = fps

    if width is None:
        width = animation.width
    if height is None:
        height = animation.height
    # exec .sh
    logger.info(
        f"bash {TargetType.ScriptPath[target_type]} --output {target_path} --height {height} --width {width}"
        f" --fps {fps} --quality {quality} {tgs_path}")
    subprocess.run(['bash', TargetType.ScriptPath[target_type], '--output', str(target_path), '--height',
                    str(height), '--width', str(width), '--fps', str(fps), '--quality', str(quality), tgs_path])
    # the following code will make the gif file motion freak
    # gif.export_gif(animation, gif_path, dpi=100, skip_frames=1)


@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text(
        "Hello! I can convert stickers to gifs. Send me a sticker and I will convert it to a gif for you.\n"
        "Only `animated stickers` are supported.\n"
        "Open source on [Github](https://github.com/SwaggyMacro/TgStoGifBot)", parse_mode=enums.ParseMode.MARKDOWN)


@app.on_message(filters.command("help"))
async def on_help(client: Client, message: Message):
    await message.reply_text(
        "1. Send me a sticker and I will convert it to a gif for you. \n"
        "2. You can also use /sets to convert a sticker set to gif. \n"
        "    `Example`: /sets https://t.me/addstickers/GumLoveIs \n")


@app.on_message(filters.command("about"))
async def on_about(client: Client, message: Message):
    await message.reply_text(
        "Stickers To Gifs Bot\n"
        "`Version`: 1.0.0\n"
        "`Github`: [Github/SwaggyMacro/TgStoGifBot](https://github.com/SwaggyMacro/TgStoGifBot)",
        parse_mode=enums.ParseMode.MARKDOWN
    )

@app.on_message(filters.command("sets"))
async def sticker_set_to_gif(client: Client, message: Message):
    stk_tmp_path = None
    try:
        logger.info(f"{message.from_user.username}#{message.from_user.id}: Sent Request.")
        sticker_set_name = message.text
        if "t.me/addstickers/" in sticker_set_name:
            sticker_set_name = sticker_set_name.split("/")[-1]
        else:
            await message.reply_text("Please send a link of sticker set or sticker!\n"
                                     "For example: /sets https://t.me/addstickers/GumLoveIs")
            return

        logger.info(f"Getting the sticker set of {sticker_set_name}.")
        await message.reply_text(f"Getting the sticker set of {sticker_set_name}.")

        try:
            info = await app.invoke(raw.functions.messages.GetStickerSet(stickerset=raw.types.InputStickerSetShortName(
                short_name=sticker_set_name), hash=0))
        except Exception as e:
            logger.error(f"Failed to get sticker set {sticker_set_name} with error {e}")
            traceback.print_exc()
            await message.reply_text(f"Failed to get sticker set {sticker_set_name} with error {e}")
            return

        logger.info(f"Starting parse and download the sticker set of {sticker_set_name}.")
        await message.reply_text(
            f"Starting parse and download the sticker set of {sticker_set_name}, It may take a while...")
        sticker_set = []
        for (index, stk) in enumerate(info.documents):
            try:
                sticker = await Sticker._parse(app, stk, {type(i): i for i in stk.attributes})
            except Exception as e:
                logger.error(f"Failed to parse sticker {index}:{stk} with error {e}")
                traceback.print_exc()
                await message.reply_text(f"Failed to parse sticker {index + 1}:{sticker_set_name} with error {e}")
                return
            if not sticker.is_animated:
                logger.warning(f"Only `animated stickers` are supported, skip {index}:{sticker.file_id}")
                await message.reply_text(f"Only `animated stickers` are supported, skip {index + 1}:{sticker.file_id}")
                continue
            sticker_set.append(sticker)
            stk_tmp_path = f"tmp/{sticker.set_name}-{message.from_user.id}"
            if not os.path.exists(stk_tmp_path):
                os.makedirs(stk_tmp_path)
            try:
                if index % 10 == 0:
                    await message.reply_text(f"Downloading sticker {index}:{sticker.emoji}, "
                                             f"set_name: {sticker.set_name}, count: {len(info.documents)}.")
                logger.info(f"{index}: Downloading sticker to {stk_tmp_path}-{sticker.file_unique_id}.tgs")
                await client.download_media(sticker.file_id,
                                            file_name=f"{stk_tmp_path}/{sticker.file_unique_id}.tgs")
            except Exception as e:
                logger.error(f"Failed to download sticker {index}:{sticker.file_id} with error {e}")
                traceback.print_exc()
                await message.reply_text(f"Failed to download sticker {index}:{sticker.file_id} with error {e}")
                continue

        logger.info(f"Starting convert the sticker set of {sticker_set_name} to gif.")
        await message.reply_text(
            f"Starting convert the sticker set of {sticker_set_name} to gif, It may take a while...")

        for (index, stk) in enumerate(sticker_set):
            gif_file_path = f"{stk_tmp_path}/{stk.file_unique_id}.gif"
            logger.info(f"Converting sticker {index}:{stk.file_id}, "
                        f"set_name: {stk.set_name}, count: {len(sticker_set)}")
            try:
                if index % 10 == 0:
                    await message.reply_text(f"Converting sticker {index + 1}:{stk.emoji}, "
                                             f"set_name: {stk.set_name}, count: {len(sticker_set)}")
                await tgs_convert(f"{stk_tmp_path}/{stk.file_unique_id}.tgs", gif_file_path)
            except Exception as e:
                logger.error(f"Failed to convert sticker {stk.file_id} to gif with error {e}")
                traceback.print_exc()
                await message.reply_text(f"Failed to convert sticker {stk.file_id} to gif with error {e}")
                continue

        logger.info(f"Converted gif of {sticker_set_name}, zipping the gif file.")
        await message.reply_text(f"Converted gif of {sticker_set_name}, zipping the gif file, It may take a while.")
        # zip the gif file
        gif_file_path_zip = f"{stk_tmp_path}/{sticker_set_name}.zip"
        with zipfile.ZipFile(gif_file_path_zip, 'w') as z:
            for stk in sticker_set:
                gif_file_path = f"{stk_tmp_path}/{stk.file_unique_id}.gif"
                z.write(gif_file_path, os.path.basename(gif_file_path))

        # upload the gif
        logger.info(f"Zipped, Uploading gif of {sticker_set_name}")
        await message.reply_text(f"Zipped, Uploading gif to {sticker_set_name}, It may take a while.")
        await message.reply_document(gif_file_path_zip, caption=f"Task Completed, Credits: @StoGifsBot.\n "
                                                                f"https://t.me/addstickers/{sticker_set_name}")
        logger.info(f"Uploaded gif of {sticker_set_name}")
    except pyrogram.errors.exceptions.flood_420.FloodWait as e:
        logger.error(f"Error: {e.MESSAGE}")
        await message.reply_text(f"Error: {e.MESSAGE}")
    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()
        await message.reply_text(f"Error: {e}")
    finally:
        if stk_tmp_path is None:
            return
        try:
            shutil.rmtree(stk_tmp_path)
        except Exception as e:
            logger.error(f"Delete tmp_sticker_path:{stk_tmp_path} failed: {e}")
            traceback.print_exc()


@app.on_message(filters.sticker)
async def sticker_to_gif(client: Client, message: Message):
    stk_tmp_path = None
    try:
        if message.sticker:
            if not message.sticker.is_animated:
                logger.warning(f"{message.from_user.username}#{message.from_user.id}: Only `animated stickers` are "
                               f"supported.")
                await message.reply_text("Only `animated stickers` are supported.")
                return
            logger.info(f"{message.from_user.username}#{message.from_user.id}: Sent Request.")
            logger.info(f"Converting sticker to gif for {message.sticker.file_id}")
            await message.reply_text(
                f"Converting sticker to gif for {message.sticker.set_name}：{message.sticker.emoji}")
            # getting the sticker info
            logger.info(f"Sticker set: {message.sticker.set_name}")
            logger.info(f"Sticker unique id: {message.sticker.file_unique_id}")
            # download the sticker
            await message.reply_text(f"Downloading sticker to convert to gif, It may take a while...")
            stk_tmp_path = f"tmp/{message.sticker.set_name}-{message.from_user.id}-{message.sticker.file_unique_id}"
            tgs_file_path = await message.download(
                file_name=f"{stk_tmp_path}/{message.sticker.file_unique_id}.tgs")
            logger.info(f"Downloaded sticker to {tgs_file_path}")
            await message.reply_text(
                f"Downloaded sticker of {message.sticker.emoji}-{message.sticker.file_unique_id}, Converting to gif, "
                f"It may take a while...")
            if not os.path.exists(stk_tmp_path):
                os.makedirs(stk_tmp_path)
            gif_file_path = f"{stk_tmp_path}/{message.sticker.file_unique_id}.gif"
            await tgs_convert(tgs_file_path, gif_file_path)
            logger.info(f"Converted sticker to gif, Uploading gif of {gif_file_path}.")
            await message.reply_text(f"Converted sticker to gif, Uploading .gif, It may take a while...")
            # zip the gif file
            gif_file_path_zip = f"{stk_tmp_path}/{message.sticker.set_name}_{message.sticker.file_unique_id}.zip"
            with zipfile.ZipFile(gif_file_path_zip, 'w') as z:
                z.write(gif_file_path, os.path.basename(gif_file_path))
            # upload the gif
            await message.reply_document(gif_file_path_zip,
                                         caption=f"{message.sticker.emoji}: Task Completed, Credits: "
                                                 f"@StoGifsBot.\n"
                                                 f"https://t.me/addstickers/{message.sticker.set_name}")
            logger.info(f"Uploaded gif of {gif_file_path}")

    except pyrogram.errors.exceptions.flood_420.FloodWait as e:
        logger.error(f"Error: {e.MESSAGE}")
        await message.reply_text(f"Error: {e.MESSAGE}")
    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()
        await message.reply_text(f"Error: {e}")
    finally:
        if stk_tmp_path is None:
            return
        try:
            shutil.rmtree(stk_tmp_path)
        except Exception as e:
            logger.error(f"Delete tmp_sticker_path:{stk_tmp_path} failed: {e}")
            traceback.print_exc()


app.run()
