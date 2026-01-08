"""
Manual Sync Runner

This script provides a command-line entry point to trigger the repository
synchronization process manually, without running the main bot application.
"""

import asyncio
from logger import log
from repo_syncer import sync_repositories

async def main():
    """
    Main function to run the synchronization.
    """
    log.info("====================================")
    log.info("  Manual Repository Sync Triggered  ")
    log.info("====================================")
    try:
        await sync_repositories()
        log.info("Manual sync completed successfully.")
    except Exception as e:
        log.critical(f"A fatal error occurred during the manual sync: {e}", exc_info=True)

if __name__ == "__main__":
    # Ensure the script can be run directly
    asyncio.run(main())
