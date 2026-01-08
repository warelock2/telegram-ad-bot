"""
Telegram Client module for interacting with the Telegram Bot API.

This module provides a simplified interface for sending messages and photos,
and includes robust error handling to manage different types of API errors.
It respects the DRY_RUN setting from the configuration.
"""

from telegram import Bot
from telegram.error import TelegramError, NetworkError, TimedOut, Forbidden, BadRequest
from config import settings
from logger import log


class TelegramClient:
    """A wrapper for the Telegram Bot API client."""

    def __init__(self, bot_token: str):
        """
        Initializes the Telegram Bot client.
        
        Args:
            bot_token: The secret API token for the bot.
        """
        if not bot_token:
            raise ValueError("Bot token cannot be empty.")
        self.bot = Bot(token=bot_token)
        log.info("Telegram client initialized.")

    async def post_ad(self, text: str, image_path: str = None) -> bool:
        """
        Posts an advertisement to the configured Telegram chat.

        If DRY_RUN is enabled, it logs the action instead of sending.
        Handles text-only posts and posts with an image and caption.

        Args:
            text: The text content of the ad.
            image_path: Optional path to an image file.

        Returns:
            True if the post was successful or in dry run mode, False otherwise.
        """
        log.info("Preparing to post ad...")
        
        if settings.dry_run:
            log.info("--- DRY RUN ENABLED ---")
            log.info(f"Would post to chat: {settings.telegram_chat_id}")
            if image_path:
                log.info(f"Would send photo: {image_path}")
            log.info(f"Text/Caption would be:\n{text}")
            log.info("--- END DRY RUN ---")
            return True

        try:
            if image_path:
                log.debug(f"Sending photo '{image_path}' with caption.")
                with open(image_path, 'rb') as photo_file:
                    await self.bot.send_photo(
                        chat_id=settings.telegram_chat_id,
                        photo=photo_file,
                        caption=text,
                        parse_mode='HTML'
                    )
            else:
                log.debug("Sending text-only message.")
                await self.bot.send_message(
                    chat_id=settings.telegram_chat_id,
                    text=text,
                    parse_mode='HTML'
                )
            log.info(f"Successfully posted ad to chat {settings.telegram_chat_id}.")
            return True
        except (TimedOut, NetworkError) as e:
            # Transient errors, worth retrying later
            log.warning(f"A transient network error occurred: {e}. The scheduler will try again later.")
            return False
        except Forbidden as e:
            # Fatal permission error
            log.critical(
                f"A fatal 'Forbidden' error occurred: {e}. The bot likely does not have "
                f"permission to post in the chat '{settings.telegram_chat_id}'. "
                f"Please make it an admin. The bot will stop."
            )
            raise e
        except BadRequest as e:
            # Can be a "chat not found" error or something else
            if 'chat not found' in str(e).lower():
                log.critical(
                    f"A fatal 'Chat Not Found' error occurred: {e}. The TELEGRAM_CHAT_ID "
                    f"'{settings.telegram_chat_id}' is likely incorrect. The bot will stop."
                )
                raise e # Re-raise to stop the application
            else:
                # Other bad requests (e.g., message too long)
                log.error(f"A bad request error occurred: {e}. The ad content may be invalid.")
                return False # Don't retry, content is likely the issue
        except TelegramError as e:
            # Catch any other Telegram-specific errors
            log.error(f"An unexpected Telegram error occurred: {e}")
            return False

# Since this class uses async methods, it's better to instantiate it where
# an asyncio event loop is running. We won't create a global instance here.
# Instead, the main.py will create an instance.
