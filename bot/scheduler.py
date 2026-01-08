"""
Core scheduling module for the Telegram Ad Bot.

This module contains the main asynchronous loop that determines when to post
an advertisement based on activity checks, a configurable frequency, and jitter.
"""

import asyncio
import datetime
import random
import os
from config import settings
from logger import log
import database as db
import ad_manager
from repo_syncer import sync_repositories
from telegram_client import TelegramClient

LAST_POST_KEY = "last_post_timestamp"


async def run_scheduler():
    """
    The main asynchronous scheduling loop.
    
    This function runs indefinitely, checking periodically if it's time to
    post a new ad block. A post is triggered only if both the activity
    check and the time-based frequency check pass.
    """
    log.info("Scheduler started.")
    client = TelegramClient(settings.bot_token)
    
    # Wait a bit on startup before the first check
    await asyncio.sleep(10)

    while True:
        try:
            now = datetime.datetime.utcnow()
            sleep_duration = settings.post_success_cooldown_minutes * 60 # Default sleep after post
            is_time_to_post = False
            next_post_time = None

            # 1. --- Activity Check ---
            if settings.activity_check_enabled:
                log.debug("Performing activity check...")
                recent_message_count = db.count_recent_messages(settings.activity_check_tframe_mins)
                if recent_message_count < settings.activity_check_messages:
                    log.info(f"Activity check failed. Found {recent_message_count} messages, need {settings.activity_check_messages}. Retrying in {settings.activity_check_retry_delay_mins} minutes.")
                    sleep_duration = settings.activity_check_retry_delay_mins * 60
                    await asyncio.sleep(sleep_duration)
                    continue
                log.debug("Activity check passed.")

            # 2. --- Time Check ---
            log.debug("Performing time check...")
            last_post_iso = db.get_state(LAST_POST_KEY)
            if not last_post_iso:
                log.info("No last post time found. Posting immediately.")
                is_time_to_post = True
            else:
                last_post_time = datetime.datetime.fromisoformat(last_post_iso)
                jitter = random.randint(-settings.randomization_jitter_minutes, settings.randomization_jitter_minutes)
                next_post_time = last_post_time + datetime.timedelta(hours=settings.time_based_frequency_hours, minutes=jitter)
                
                if now >= next_post_time:
                    is_time_to_post = True
                else:
                    # It's not time yet, sleep until the calculated next post time
                    is_time_to_post = False
                    sleep_duration = (next_post_time - now).total_seconds()

            if not is_time_to_post:
                sleep_duration = max(1, sleep_duration)
                if next_post_time:
                    log.info(f"Time check failed. Next post due around {next_post_time.strftime('%Y-%m-%d %H:%M:%S UTC')}. Sleeping until then.")
                else:
                    log.info(f"Time check failed. Sleeping for {sleep_duration / 60:.1f} minutes.")
                await asyncio.sleep(sleep_duration)
                continue
            
            # 3. --- Sync Repositories ---
            log.info("All checks passed. Syncing ad repositories before posting.")
            await sync_repositories()

            # 4. --- Post Ad Block ---
            log.info("Proceeding to post an ad block.")
            ad_block = ad_manager.select_ad_block()

            if ad_block:
                block_post_successful = True
                for i, ad in enumerate(ad_block):
                    log.debug(f"Posting ad {i+1}/{len(ad_block)} from block: {ad['filename']}")
                    post_successful = await client.post_ad(text=ad['text'], image_path=ad['image_path'])
                    
                    if post_successful:
                        db.record_posted_ad(ad['filename'])
                        # Brief pause between posts to not flood the chat
                        if i < len(ad_block) - 1:
                            await asyncio.sleep(2)
                    else:
                        log.error(f"Failed to post ad '{ad['filename']}'. Aborting this block.")
                        block_post_successful = False
                        break # Stop processing this block on the first failure
                
                if block_post_successful:
                    log.info(f"Successfully posted an ad block of {len(ad_block)} ads.")
                    db.set_state(LAST_POST_KEY, now.isoformat())
                else:
                    log.warning("Ad block posting failed. Will retry after a short delay.")
            else:
                log.warning("Could not select an ad block. Will check again later.")
            
            # After an attempt (successful or not), sleep for a default duration before next full check
            await asyncio.sleep(sleep_duration)

        except Exception as e:
            log.critical(f"An unexpected error occurred in the scheduler loop: {e}", exc_info=True)
            log.critical("Scheduler will restart after a 5-minute cooldown.")
            await asyncio.sleep(300)