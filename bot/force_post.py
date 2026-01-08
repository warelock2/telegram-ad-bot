"""
Force Post Script

This script provides a direct, immediate mechanism to trigger an ad post.
It can operate in two modes:

1. Random Mode (no arguments): Selects a block of ads, one from each
   available campaign, and posts them.
2. Targeted Mode (with arguments): Posts one specific ad based on the
   provided path and basename.

This script does NOT update the 'last_post_timestamp' in the database,
ensuring that a forced post does not reset the main schedule.
"""

import asyncio
import sys
import os
from logger import log
from config import settings, SettingsError
import database as db
import ad_manager
from repo_syncer import sync_repositories
from telegram_client import TelegramClient
from telegram.error import TelegramError

async def force_post_logic(args: list[str]):
    """
    The core logic for selecting and posting an ad block immediately.
    
    Args:
        args: A list of command-line arguments passed to the script.
    """
    log.info("====================================")
    log.info("  Force Post Triggered Manually     ")
    log.info("====================================")
    log.info(f"Target Chat ID: {settings.telegram_chat_id}")
    log.info(f"Dry Run Mode: {'ENABLED' if settings.dry_run else 'DISABLED'}")

    # Initialize components and sync repositories
    db.initialize_database()
    await sync_repositories()
    client = TelegramClient(settings.bot_token)
    ad_block = None

    # --- Decide Mode: Random vs. Targeted ---
    if len(args) == 0:
        # 1a. Random Mode
        log.info("No specific ad requested. Selecting a random ad block.")
        ad_block = ad_manager.select_ad_block()
        if not ad_block:
            log.warning("Could not select a random ad block to post. No campaigns found.")
            return
    else:
        # 1b. Targeted Mode
        if len(args) != 3:
            log.critical("Invalid arguments. Usage: force-post <client> <product> <basename>")
            return
        
        client_arg, product_arg, basename_arg = args
        log.info(f"Specific ad requested: {client_arg}/{product_arg}/{basename_arg}")
        
        campaign_dir = os.path.join(settings.ads_directory, client_arg, product_arg)
        
        if not os.path.isdir(campaign_dir):
            log.critical(f"Validation failed: Campaign directory not found at '{campaign_dir}'")
            return
            
        ad_block = ad_manager.get_specific_ad(campaign_dir, basename_arg)
        if not ad_block:
            log.warning(f"Could not find the specified ad. Please check the path and basename.")
            return

    # 2. Post The Ad(s)
    log.info(f"Proceeding to post ad(s). Block size: {len(ad_block)}.")
    block_post_successful = True
    for i, ad in enumerate(ad_block):
        log.debug(f"Posting ad {i+1}/{len(ad_block)} from block: {ad['filename']}")
        post_successful = await client.post_ad(text=ad['text'], image_path=ad['image_path'])
        
        if post_successful:
            # Record that this specific ad was posted to avoid recent duplicates
            db.record_posted_ad(ad['filename'])
            # Brief pause between posts to not flood the chat
            if i < len(ad_block) - 1:
                await asyncio.sleep(2)
        else:
            log.error(f"Failed to post ad '{ad['filename']}'. Aborting this block.")
            block_post_successful = False
            break # Stop processing this block on the first failure

    if block_post_successful:
        log.info("Force post completed successfully.")
    else:
        log.warning("Force post failed because one or more ads in the block failed to send.")

async def main():
    try:
        # Pass all command-line arguments, excluding the script name itself
        await force_post_logic(sys.argv[1:])
    except SettingsError as e:
        log.critical(f"A configuration error prevented the force post: {e}")
    except (TelegramError, Exception) as e:
        log.critical(f"A fatal error occurred during the force post: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
