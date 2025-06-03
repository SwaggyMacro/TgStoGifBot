"""
Telegram bot command and callback handlers.
"""
import re
import traceback

from loguru import logger
from telegram import Update, Sticker, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from exporter import process_single_export, process_set_export, process_single_sticker, process_sticker_set

# Constants and options for buttons
FORMAT_OPTIONS = [
    ("gif",  "🖼️ GIF"),
    ("png",  "🌈 PNG"),
    ("webp", "🔄 WebP"),
    ("apng", "🎨 APNG"),
]
QUALITY_OPTIONS = [
    ("100", "🔧 Quality = 100%"),
    ("90",  "🔧 Quality = 90%"),
    ("70",  "🔧 Quality = 70%"),
    ("50",  "🔧 Quality = 50%"),
]
SIZE_OPTIONS = [
    ("64x64",   "📐 64×64"),
    ("128x128", "📏 128×128"),
    ("256x256", "📏 256×256"),
    ("512x512", "📐 512×512"),
]
FPS_OPTIONS = [12, 24, 30, 60, 90, 100]


def build_button_grid(options, prefix: str, columns: int = 2) -> InlineKeyboardMarkup:
    """
    Build an InlineKeyboardMarkup grid from a list of (value, label) pairs.

    :param options: List of tuples where the first element is suffix and second is label.
    :param prefix: Prefix for callback_data (e.g., 'set_format').
    :param columns: Number of buttons per row.
    :return: InlineKeyboardMarkup instance.
    """
    btns = []
    row = []
    for suffix, label in options:
        cb = f"{prefix}_{suffix}"
        row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == columns:
            btns.append(row)
            row = []
    if row:
        btns.append(row)
    btns.append([InlineKeyboardButton("❌ Cancel", callback_data=f"{prefix}_cancel")])
    return InlineKeyboardMarkup(btns)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command: send a welcome message.
    """
    welcome_text = (
        "👋 **Hello!**\n\n"
        "I can convert your animated stickers into various image formats. 🎉\n\n"
        "• Send me a sticker and I will guide you through format, quality, size.\n"
        "• Or use `/sets <link>` to convert an entire sticker set.\n"
        "• Only `animated stickers` are supported.\n\n"
        "🔗 *Source on* [GitHub](https://github.com/SwaggyMacro/TgStoGifBot)"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command: send usage instructions.
    """
    help_text = (
        "❓ **How to use me:**\n\n"
        "1. 📥 Send me an *animated sticker*, and I’ll ask you to pick:\n"
        "   • Step 1: *Format* (GIF, PNG, WebP, APNG)\n"
        "   • Step 2: *Quality* (100%, 90%, 70%, 50%)\n"
        "   • Step 3: *Size* (64×64, 128×128, 256×256, 512×512)\n\n"
        "2. 📦 Use `/sets` to convert a whole sticker set:\n"
        "   ```\n"
        "   /sets https://t.me/addstickers/GumLoveIs\n"
        "   ```\n"
        "   • After sending `/sets <link>`, I’ll guide you through the same steps.\n\n"
        "*Only animated stickers are supported.*"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /about command: send version and GitHub link.
    """
    about_text = (
        "ℹ️ **Stickers To Images Bot**\n\n"
        "`Version:` 1.0.0\n"
        "`GitHub:` [SwaggyMacro/TgStoGifBot](https://github.com/SwaggyMacro/TgStoGifBot)"
    )
    await update.message.reply_text(about_text, parse_mode=ParseMode.MARKDOWN)


async def sticker_to_gif(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming sticker: if animated, prompt for export or convert.
    """
    try:
        sticker: Sticker = update.message.sticker
        if not sticker.is_animated:
            await update.message.reply_text(
                "⚠️ Only `animated stickers` are supported.", parse_mode=ParseMode.MARKDOWN
            )
            return

        context.user_data["single_sticker_info"] = {
            "file_id": sticker.file_id,
            "file_unique_id": sticker.file_unique_id,
            "set_name": sticker.set_name or "no_set_name",
        }

        btns = [
            [
                InlineKeyboardButton("📁 Export .tgs", callback_data="single_action_export"),
                InlineKeyboardButton("🖼️ Convert", callback_data="single_action_convert"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="single_action_cancel")]
        ]
        keyboard = InlineKeyboardMarkup(btns)
        await update.message.reply_text(
            "❓ *Please Choose:*", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in sticker_to_gif: {e}")
        await update.message.reply_text(f"❌ *Error:* `{e}`", parse_mode=ParseMode.MARKDOWN)


async def single_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle user choice for single sticker: export or convert.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "single_action_cancel":
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend me a sticker again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.pop("single_sticker_info", None)
        return

    single_info = context.user_data.get("single_sticker_info")
    if not single_info:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send the sticker again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "single_action_export":
        await process_single_export(context.bot, single_info, query.message)
        return

    if data == "single_action_convert":
        keyboard = build_button_grid(FORMAT_OPTIONS, prefix="single_format", columns=2)
        await query.edit_message_text(
            "🔢 *Choose format* for your sticker:", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )


async def single_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle format selection for single sticker and prompt for quality.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.endswith("_cancel"):
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend me a sticker again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    match = re.match(r"single_format_(gif|png|webp|apng)", data)
    if not match:
        return
    chosen_format = match.group(1)

    single_info = context.user_data.get("single_sticker_info")
    if not single_info:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send the sticker again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    context.user_data["single_sticker_format"] = chosen_format
    keyboard = build_button_grid(QUALITY_OPTIONS, prefix="single_quality", columns=2)
    await query.edit_message_text(
        f"🎨 *Format = {chosen_format.upper()} selected.*\nNow choose *quality* for your sticker:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


async def single_quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle quality selection for single sticker and prompt for size.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.endswith("_cancel"):
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend me a sticker again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    match = re.match(r"single_quality_(\d+)", data)
    if not match:
        return
    quality = int(match.group(1))

    single_info = context.user_data.get("single_sticker_info")
    chosen_format = context.user_data.get("single_sticker_format", "gif")
    if not single_info:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send the sticker again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    context.user_data["single_sticker_quality"] = quality
    keyboard = build_button_grid(SIZE_OPTIONS, prefix="single_size", columns=2)
    await query.edit_message_text(
        f"🔧 *Quality = {quality}% selected.*\nNow choose *size* for your sticker:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


async def single_size_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle size selection for single sticker and prompt for FPS.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.endswith("_cancel"):
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend me a sticker again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    match = re.match(r"single_size_(\d+x\d+)", data)
    if not match:
        return
    size_str = match.group(1)
    width, height = map(int, size_str.split("x"))

    single_info = context.user_data.get("single_sticker_info")
    chosen_format = context.user_data.get("single_sticker_format", "gif")
    quality = context.user_data.get("single_sticker_quality", 100)
    if not single_info:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send the sticker again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    context.user_data["single_sticker_width"] = width
    context.user_data["single_sticker_height"] = height

    # Build FPS buttons (3 per row)
    btns, row = [], []
    for fps in FPS_OPTIONS:
        cb = f"single_fps_{fps}"
        label = f"⚡ {fps} fps"
        row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 3:
            btns.append(row)
            row = []
    if row:
        btns.append(row)
    btns.append([InlineKeyboardButton("❌ Cancel", callback_data="single_fps_cancel")])
    keyboard = InlineKeyboardMarkup(btns)

    await query.edit_message_text(
        f"🎬 *Size = {width}×{height} selected.*\nNow choose *frame rate* for your sticker:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


async def single_fps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle FPS selection for single sticker and perform conversion.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.endswith("_cancel"):
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend me a sticker again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    match = re.match(r"single_fps_(\d+)", data)
    if not match:
        return
    fps = int(match.group(1))

    single_info = context.user_data.get("single_sticker_info")
    chosen_format = context.user_data.get("single_sticker_format", "gif")
    quality = context.user_data.get("single_sticker_quality", 100)
    width = context.user_data.get("single_sticker_width")
    height = context.user_data.get("single_sticker_height")

    if not single_info or width is None or height is None:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send the sticker again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    # Clean up cached data
    context.user_data.clear()

    await process_single_sticker(
        bot=context.bot,
        single_info=single_info,
        chosen_format=chosen_format,
        quality=quality,
        width=width,
        height=height,
        fps=fps,
        feedback_msg=query.message,
    )

async def set_sticker_set_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /sets command: prompt user for export or convert on a sticker set.
    """
    try:
        text = update.message.text or ""
        match = re.search(r"t\.me/addstickers/([a-zA-Z0-9_]+)", text)
        if not match:
            keyboard = build_button_grid(FORMAT_OPTIONS, prefix="set_format", columns=2)
            await update.message.reply_text(
                "👉 Please send a link to a sticker set, e.g.:\n`/sets https://t.me/addstickers/GumLoveIs`\nFirst, choose *format*:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
            return

        sticker_set_name = match.group(1)
        context.user_data["sticker_set_name"] = sticker_set_name
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📁 Export .tgs", callback_data="set_action_export"),
                InlineKeyboardButton("🖼️ Convert", callback_data="set_action_convert"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="set_action_cancel")]
        ])
        await update.message.reply_text(
            f"❓ *Sticker Set:* `{sticker_set_name}`\nChoose an action:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in set_sticker_set_flow: {e}")
        traceback.print_exc()
        await update.message.reply_text(f"❌ *Error:* `{e}`", parse_mode=ParseMode.MARKDOWN)

async def set_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle user choice for sticker set: export or convert.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "set_action_cancel":
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend `/sets <link>` again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    sticker_set_name = context.user_data.get("sticker_set_name")
    if not sticker_set_name:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send `/sets <link>` again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "set_action_export":
        try:
            sticker_set = await context.bot.get_sticker_set(sticker_set_name)
            await process_set_export(
                bot=context.bot,
                sticker_set=sticker_set,
                sticker_set_name=sticker_set_name,
                feedback_msg=query.message,
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Failed to get sticker set `{sticker_set_name}`:\n`{e}`", parse_mode=ParseMode.MARKDOWN
            )
        return

    if data == "set_action_convert":
        keyboard = build_button_grid(FORMAT_OPTIONS, prefix="set_format", columns=2)
        await query.edit_message_text(
            f"🔢 *Choose format* for `{sticker_set_name}`:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

async def set_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle format selection for a sticker set and prompt for quality.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.endswith("_cancel"):
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend `/sets <link>` again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    match = re.match(r"set_format_(gif|png|webp|apng)", data)
    if not match:
        return
    chosen_format = match.group(1)

    sticker_set_name = context.user_data.get("sticker_set_name")
    if not sticker_set_name:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send `/sets <link>` again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    context.user_data["sticker_set_format"] = chosen_format
    keyboard = build_button_grid(QUALITY_OPTIONS, prefix="set_quality", columns=2)
    await query.edit_message_text(
        f"🎨 *Format = {chosen_format.upper()} selected.*\nNow choose *quality* for `{sticker_set_name}`:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )

async def set_quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle quality selection for a sticker set and prompt for size.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.endswith("_cancel"):
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend `/sets <link>` again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    match = re.match(r"set_quality_(\d+)", data)
    if not match:
        return
    quality = int(match.group(1))

    sticker_set_name = context.user_data.get("sticker_set_name")
    chosen_format = context.user_data.get("sticker_set_format", "gif")
    if not sticker_set_name:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send `/sets <link>` again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    context.user_data["sticker_set_quality"] = quality
    keyboard = build_button_grid(SIZE_OPTIONS, prefix="set_size", columns=2)
    await query.edit_message_text(
        f"🔧 *Quality = {quality}% selected.*\nNow choose *size* for `{sticker_set_name}`:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )

async def set_size_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle size selection for a sticker set and prompt for FPS.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.endswith("_cancel"):
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend `/sets <link>` again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    match = re.match(r"set_size_(\d+x\d+)", data)
    if not match:
        return
    size_str = match.group(1)
    width, height = map(int, size_str.split("x"))

    sticker_set_name = context.user_data.get("sticker_set_name")
    chosen_format = context.user_data.get("sticker_set_format", "gif")
    quality = context.user_data.get("sticker_set_quality", 100)
    if not sticker_set_name:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send `/sets <link>` again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    context.user_data["sticker_set_width"] = width
    context.user_data["sticker_set_height"] = height

    # Build FPS buttons (3 per row)
    btns, row = [], []
    for fps in FPS_OPTIONS:
        cb = f"set_fps_{fps}"
        label = f"⚡ {fps} fps"
        row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 3:
            btns.append(row)
            row = []
    if row:
        btns.append(row)
    btns.append([InlineKeyboardButton("❌ Cancel", callback_data="set_fps_cancel")])
    keyboard = InlineKeyboardMarkup(btns)

    await query.edit_message_text(
        f"🎬 *Size = {width}×{height} selected.*\nNow choose *frame rate* for `{sticker_set_name}`:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )

async def set_fps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle FPS selection for a sticker set and perform download/convert.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.endswith("_cancel"):
        await query.edit_message_text(
            "❌ *Operation canceled.*\nSend `/sets <link>` again any time.", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return

    match = re.match(r"set_fps_(\d+)", data)
    if not match:
        return
    fps = int(match.group(1))

    sticker_set_name = context.user_data.get("sticker_set_name")
    chosen_format = context.user_data.get("sticker_set_format", "gif")
    quality = context.user_data.get("sticker_set_quality", 100)
    width = context.user_data.get("sticker_set_width")
    height = context.user_data.get("sticker_set_height")

    if not sticker_set_name or width is None or height is None:
        await query.edit_message_text(
            "⚠️ Something went wrong. Please send `/sets <link>` again.", parse_mode=ParseMode.MARKDOWN
        )
        return

    # Clear context data
    context.user_data.clear()

    try:
        sticker_set = await context.bot.get_sticker_set(sticker_set_name)
        await process_sticker_set(
            bot=context.bot,
            sticker_set=sticker_set,
            sticker_set_name=sticker_set_name,
            chosen_format=chosen_format,
            quality=quality,
            width=width,
            height=height,
            fps=fps,
            feedback_msg=query.message,
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ Failed to get sticker set `{sticker_set_name}`:\n`{e}`", parse_mode=ParseMode.MARKDOWN
        )