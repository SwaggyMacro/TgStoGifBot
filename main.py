"""
Main entry point: initialize bot, register handlers, and start polling.
"""
from loguru import logger
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import load_config, get_proxy_url
from handlers import (
    start,
    help_command,
    about_command,
    sticker_to_gif,
    single_action_callback,
    single_format_callback,
    single_quality_callback,
    single_size_callback,
    single_fps_callback,
    set_sticker_set_flow,
    set_action_callback,
    set_format_callback,
    set_quality_callback,
    set_size_callback,
    set_fps_callback,
)


def main() -> None:
    """
    Initialize the Telegram bot application and register all handlers.
    """
    # Load configuration
    config = load_config("config.json")
    bot_token = config.get("bot_token")

    # Setup proxy if configured
    proxy_enabled = config.get("proxy", {}).get("status", False)
    if proxy_enabled:
        logger.info("Bot is running with proxy support.")
    else:
        logger.info("Bot is running without proxy.")

    # Build application
    if proxy_enabled:
        application = (Application.builder()
                       .token(bot_token)
                       .proxy(get_proxy_url(config.get("proxy", {})))
                       .connect_timeout(30)
                       .read_timeout(30)
                       .write_timeout(60)
                       .get_updates_proxy(get_proxy_url(config.get("proxy", {})))
                       .build())
    else:
        application = (Application.builder()
                       .token(bot_token)
                       .connect_timeout(30)
                       .read_timeout(30)
                       .write_timeout(60)
                       .build())

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("sets", set_sticker_set_flow))

    # Register message handler for stickers
    application.add_handler(MessageHandler(filters.Sticker.ALL, sticker_to_gif))

    # Register callback handlers (patterns simplified)
    application.add_handler(
        CallbackQueryHandler(single_action_callback, pattern=r"^single_action_.*$")
    )
    application.add_handler(
        CallbackQueryHandler(single_format_callback, pattern=r"^single_format_.*$")
    )
    application.add_handler(
        CallbackQueryHandler(single_quality_callback, pattern=r"^single_quality_.*$")
    )
    application.add_handler(
        CallbackQueryHandler(single_size_callback, pattern=r"^single_size_.*$")
    )
    application.add_handler(
        CallbackQueryHandler(single_fps_callback, pattern=r"^single_fps_.*$")
    )

    application.add_handler(
        CallbackQueryHandler(set_action_callback, pattern=r"^set_action_.*$")
    )
    application.add_handler(
        CallbackQueryHandler(set_format_callback, pattern=r"^set_format_.*$")
    )
    application.add_handler(
        CallbackQueryHandler(set_quality_callback, pattern=r"^set_quality_.*$")
    )
    application.add_handler(
        CallbackQueryHandler(set_size_callback, pattern=r"^set_size_.*$")
    )
    application.add_handler(
        CallbackQueryHandler(set_fps_callback, pattern=r"^set_fps_.*$")
    )

    logger.info("🚀 Starting bot...")
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()