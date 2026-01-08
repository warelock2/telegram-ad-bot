"""
Repository Synchronization Module

This module handles the logic for fetching ad content from remote Git repositories,
turning a local 'ads' directory into a non-authoritative cache.
"""

import asyncio
import os
from logger import log

REPOLIST_PATH = "conf/repolist.txt"
ADS_DIR = "ads"

async def _run_command(command: str):
    """A wrapper to run a shell command asynchronously and log its output."""
    log.debug(f"Running command: {command}")
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        log.error(f"Command failed with exit code {process.returncode}: {command}")
        log.error(f"Stderr: {stderr.decode().strip()}")
        return False
    
    log.debug(f"Command successful: {command}")
    if stdout:
        log.debug(f"Stdout: {stdout.decode().strip()}")
    return True

async def sync_repositories():
    """
    Synchronizes ad content from remote Git repositories.
    
    Reads a list of repositories from repolist.txt. For each repo, it either
    clones it into the local 'ads' cache or pulls the latest changes if it
s    already exists.
    
    Handles the non-existence of repolist.txt gracefully.
    """
    log.info("Starting ad repository synchronization...")
    
    if not os.path.exists(REPOLIST_PATH):
        log.warning(f"'{REPOLIST_PATH}' not found. Skipping repository synchronization.")
        log.warning("Bot will use any existing content in the 'ads' directory.")
        return

    try:
        with open(REPOLIST_PATH, 'r') as f:
            repos = [line.strip().split() for line in f if line.strip()]
    except IOError as e:
        log.error(f"Could not read '{REPOLIST_PATH}': {e}. Skipping sync.")
        return

    if not os.path.exists(ADS_DIR):
        os.makedirs(ADS_DIR)

    sync_tasks = []
    for repo_data in repos:
        if len(repo_data) != 2:
            log.warning(f"Skipping malformed line in '{REPOLIST_PATH}': {' '.join(repo_data)}")
            continue
        
        name, url = repo_data
        target_dir = os.path.join(ADS_DIR, name)
        
        sync_tasks.append(_sync_single_repo(name, url, target_dir))

    await asyncio.gather(*sync_tasks)
    log.info("Ad repository synchronization finished.")

async def _sync_single_repo(name: str, url: str, target_dir: str):
    """Handles the clone or pull logic for a single repository."""
    if os.path.exists(target_dir) and os.path.isdir(target_dir):
        # Directory exists, check if it's a git repo
        if os.path.exists(os.path.join(target_dir, '.git')):
            log.info(f"Repository '{name}' exists, pulling latest changes...")
            command = f"git -C {target_dir} pull"
            await _run_command(command)
        else:
            # It's a directory but not a git repo, could be problematic
            log.warning(f"Directory '{target_dir}' exists but is not a Git repository. Re-cloning.")
            # Simple approach: remove and clone. A more advanced version might move it.
            # This is safer for a cache.
            await _run_command(f"rm -rf {target_dir}")
            log.info(f"Cloning new repository '{name}' from {url}...")
            command = f"git clone {url} {target_dir}"
            await _run_command(command)
    else:
        # Directory does not exist, clone it
        log.info(f"Cloning new repository '{name}' from {url}...")
        command = f"git clone {url} {target_dir}"
        await _run_command(command)
