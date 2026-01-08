"""
Main entry point for the Telegram Ad Bot application.

This script initializes the application, starts all background tasks (scheduler,
pruner), and runs the main Telegram bot listener.
"""

import asyncio
from logger import log
from config import settings, SettingsError
import database as db
from scheduler import run_scheduler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

async def post_init(application: Application) -> None:
    """
    Schedules background tasks after the application has been initialized.
    This is the recommended way to run background tasks with python-telegram-bot.
    """
    log.debug("post_init: Creating background tasks for scheduler and pruner.")
    # Store tasks in bot_data to access them in post_shutdown
    application.bot_data['scheduler_task'] = asyncio.create_task(run_scheduler())
    application.bot_data['pruner_task'] = asyncio.create_task(run_database_pruner())

async def post_shutdown(application: Application) -> None:
    """
    Cancels all background tasks during the shutdown process.
    """
    log.info("post_shutdown: Shutting down background tasks...")
    if 'scheduler_task' in application.bot_data:
        application.bot_data['scheduler_task'].cancel()
    if 'pruner_task' in application.bot_data:
        application.bot_data['pruner_task'].cancel()
    
    tasks = [task for key, task in application.bot_data.items() if key.endswith('_task')]
    await asyncio.gather(*tasks, return_exceptions=True)

async def run_database_pruner():
    """A background task to periodically clean up old message timestamps."""
    log.info("Database pruner task started.")
    while True:
        try:
            # Sleep for 24 hours
            await asyncio.sleep(24 * 3600)
            log.debug("Pruner waking up to clean old message logs.")
            db.prune_old_message_logs(hours=24)
        except asyncio.CancelledError:
            log.info("Database pruner task cancelled.")
            break
        except Exception as e:
            log.error(f"An error occurred in the database pruner: {e}", exc_info=True)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles messages in the target chat to log their timestamp for activity tracking.
    """
    log.debug(f"Received new message in target chat.")
    db.log_message_timestamp()

def main() -> None:
    """
    The main function that sets up and runs the entire application.
    """
    log.info("====================================")
    log.info("  Telegram Ad Bot Service Starting  ")
    log.info("====================================")
    
    log.info(f"Log Level: {settings.log_level}")
    log.info(f"Target Chat ID: {settings.telegram_chat_id}")
    log.info(f"Dry Run Mode: {'ENABLED' if settings.dry_run else 'DISABLED'}")

    # Initialize the database to ensure tables are created
    db.initialize_database()

    # Create the Telegram Application using the builder pattern
    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Create a filter for the specific chat we care about
    try:
        chat_id = int(settings.telegram_chat_id)
        chat_filter = filters.Chat(chat_id=chat_id)
        log.debug(f"Message handler configured for numeric chat_id: {chat_id}")
    except ValueError:
        username = settings.telegram_chat_id.lstrip('@')
        chat_filter = filters.Chat(username=username)
        log.debug(f"Message handler configured for username: @{username}")

    # Register the message handler with the chat filter
    application.add_handler(MessageHandler(chat_filter & filters.ALL, message_handler))

    # run_polling() is a blocking call that runs the bot until it's stopped.
    log.info("Starting bot listener...")
    application.run_polling()
    log.info("Bot service has shut down.")

if __name__ == "__main__":
    try:
        main()
    except SettingsError as e:
        log.critical(f"A configuration error prevented startup: {e}")
        log.critical("Please correct the .env file and restart the bot.")
    except (TelegramError, Exception) as e:
        log.critical(f"A fatal error occurred during bot startup: {e}", exc_info=True)
    except KeyboardInterrupt:
        log.info("Shutdown signal received (KeyboardInterrupt).")