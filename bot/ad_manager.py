"""Ad Manager module for selecting advertisements from a structured directory.

This module is responsible for finding ad campaigns in a directory structure
of <Advertiser>/<Product>, selecting one ad from each campaign, and preparing
a "block" of ads to be posted.
"""

import os
import random
import re
import secrets
from config import settings
from logger import log
import database as db

SUPPORTED_IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.gif']


def _obfuscate_urls_in_text(text: str) -> str:
    """
    Finds all URLs in a string, removes the protocol, replaces all structural
    characters for obfuscation, and wraps the result in bold tags.
    """
    url_pattern = r'https?://[^\s/$.?#].[^\s]*'

    def replacer(match):
        url = match.group(0)
        try:
            # Remove protocol (http://, https://)
            url_no_protocol = re.sub(r'https?://', '', url)
            
            # Chain replacements for all structural characters
            obfuscated_url = url_no_protocol.replace('.', ' (dot) ')
            obfuscated_url = obfuscated_url.replace('/', ' (slash) ')
            obfuscated_url = obfuscated_url.replace('?', ' (question) ')
            obfuscated_url = obfuscated_url.replace('=', ' (equals) ')
            obfuscated_url = obfuscated_url.replace('&', ' (and) ')
            obfuscated_url = obfuscated_url.replace('#', ' (hash) ')
            
            # Wrap the final result in bold tags
            return f"<b>{obfuscated_url}</b>"
        except Exception as e:
            log.warning(f"URL Obfuscation failed for '{url}': {e}. Returning original URL.")
            return url
    
    return re.sub(url_pattern, replacer, text)


def _find_campaign_paths() -> list[str]:
    """
    Finds all valid campaign directories within the main ads directory.
    A campaign directory is a leaf directory (contains no other directories).
    
    Returns:
        A list of absolute paths to campaign directories.
    """
    campaign_paths = []
    root_dir = settings.ads_directory
    if not os.path.isdir(root_dir):
        log.error(f"Ads directory '{root_dir}' not found.")
        return []

    log.debug(f"Scanning for campaign directories in '{root_dir}'...")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # A campaign directory is a leaf in the tree (has no subdirectories)
        # and contains at least one file.
        if not dirnames and filenames:
            campaign_paths.append(dirpath)
            log.debug(f"Found campaign directory: {dirpath}")
            
    log.info(f"Found {len(campaign_paths)} active ad campaigns.")
    return campaign_paths

def _get_ads_in_campaign(campaign_path: str) -> dict[str, dict]:
    """
    Scans a specific campaign directory and catalogues its available ads.

    An ad is defined by a .txt file. An associated image can have the same
    base filename with a supported image extension.

    Returns:
        A dictionary mapping the ad's base filename to its details.
    """
    ads_catalogue = {}
    log.debug(f"Scanning for ads in campaign '{campaign_path}'")
    for filename in os.listdir(campaign_path):
        filepath = os.path.join(campaign_path, filename)
        if not os.path.isfile(filepath):
            continue

        basename, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        if ext_lower == '.txt':
            if basename not in ads_catalogue:
                ads_catalogue[basename] = {'image_path': None}
            ads_catalogue[basename]['text_path'] = filepath
        elif ext_lower in SUPPORTED_IMAGE_EXTS:
            if basename not in ads_catalogue:
                ads_catalogue[basename] = {'text_path': None}
            ads_catalogue[basename]['image_path'] = filepath

    valid_ads = { name: paths for name, paths in ads_catalogue.items() if paths.get('text_path') }
    log.debug(f"Found {len(valid_ads)} valid ads in '{campaign_path}'.")
    return valid_ads


def get_specific_ad(campaign_dir: str, base_filename: str) -> list[dict] | None:
    """
    Finds a specific ad by its base filename within a given campaign directory.

    Args:
        campaign_dir: The absolute path to the specific campaign directory.
        base_filename: The base name of the ad files (without extension).

    Returns:
        A list containing a single dictionary for the found ad, or None.
    """
    log.info(f"Attempting to find specific ad '{base_filename}' in '{campaign_dir}'.")
    
    # Catalogue all ads in the directory to find the specific one
    all_ads = _get_ads_in_campaign(campaign_dir)
    ad_details = all_ads.get(base_filename)

    if not ad_details or not ad_details.get('text_path'):
        log.error(f"Ad with base filename '{base_filename}' not found or is invalid in '{campaign_dir}'.")
        return None

    log.info(f"Found specific ad '{base_filename}'.")
    try:
        with open(ad_details['text_path'], 'r', encoding='utf-8') as f:
            ad_text = f.read().strip()
    except IOError as e:
        log.error(f"Could not read ad text file {ad_details['text_path']}: {e}")
        return None

    # Stage 1: Obfuscate URLs
    ad_text = _obfuscate_urls_in_text(ad_text)

    # Stage 2: Append auth text and ad code
    full_text = ad_text
    if settings.auth_text:
        ad_code = secrets.token_hex(2).upper()
        augmented_disclaimer = f"{settings.auth_text} (Ad code: {ad_code})"
        full_text += f"\n\n{augmented_disclaimer}"

    # Return the ad in the same "block" format (a list with one item)
    ad_block = [{
        'text': full_text,
        'image_path': ad_details.get('image_path'),
        'filename': base_filename
    }]

    return ad_block



def select_ad_block() -> list[dict] | None:
    """
    Selects a block of ads, one from each campaign, avoiding recent duplicates.

    Returns:
        A list of ad dictionaries, or None if no ads could be selected.
    """
    log.info("Attempting to select an ad block to post.")
    campaign_paths = _find_campaign_paths()
    if not campaign_paths:
        log.warning("No ad campaigns found. Cannot select an ad block.")
        return None

    # Get recently posted ads to avoid duplicates
    avoid_reposting_within_hours = max(1, settings.time_based_frequency_hours // 2)
    recently_posted_files = db.get_recently_posted_ads(hours=avoid_reposting_within_hours)
    
    ad_block = []

    for campaign_path in campaign_paths:
        log.debug(f"Processing campaign: {campaign_path}")
        all_ads_in_campaign = _get_ads_in_campaign(campaign_path)
        if not all_ads_in_campaign:
            log.warning(f"No valid ads found in campaign directory '{campaign_path}', skipping.")
            continue

        available_ad_names = list(all_ads_in_campaign.keys())
        
        # Filter out recently posted ads for this campaign
        eligible_ad_names = [name for name in available_ad_names if name not in recently_posted_files]
        
        # If all ads in this campaign have been posted recently, fall back to the full list for this campaign
        if not eligible_ad_names:
            log.warning(f"All ads in campaign '{campaign_path}' have been posted recently. Choosing from the full list for this campaign.")
            eligible_ad_names = available_ad_names

        # Select one random ad from the eligible list for this campaign
        selected_ad_name = random.choice(eligible_ad_names)
        selected_ad_details = all_ads_in_campaign[selected_ad_name]
        log.info(f"Selected ad '{selected_ad_name}' from campaign '{campaign_path}'.")

        # Read the ad text
        try:
            with open(selected_ad_details['text_path'], 'r', encoding='utf-8') as f:
                ad_text = f.read().strip()
        except IOError as e:
            log.error(f"Could not read ad text file {selected_ad_details['text_path']}: {e}")
            continue

        # Stage 1: Obfuscate URLs
        ad_text = _obfuscate_urls_in_text(ad_text)

        # Stage 2: Append auth text and ad code
        full_text = ad_text
        if settings.auth_text:
            ad_code = secrets.token_hex(2).upper()
            augmented_disclaimer = f"{settings.auth_text} (Ad code: {ad_code})"
            full_text += f"\n\n{augmented_disclaimer}"

        ad_block.append({
            'text': full_text,
            'image_path': selected_ad_details.get('image_path'),
            'filename': selected_ad_name
        })

    if not ad_block:
        log.warning("Finished processing all campaigns, but no ads were selected for the block.")
        return None

    log.info(f"Ad block selected with {len(ad_block)} ads.")
    return ad_block