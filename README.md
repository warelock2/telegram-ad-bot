# Telegram Ad Bot

A smart, configurable, and reliable Telegram bot for automatically posting advertisements to a public channel or group. The bot is designed to be run in Docker, ensuring easy setup and consistent operation.

## Features

- **Remote Content Management**: Ad content is sourced from external Git repositories, allowing for decoupled and version-controlled content management.
- **Activity-Based Posting**: Intelligently lurks and waits for the group to be active before posting, ensuring ads are seen by users, not a dead chat.
- **Campaign Management**: Organizes ads by `Product` or `Campaign` within each configured Git repository.
- **Block Posting**: Posts a "block" of ads at each interval—one randomly selected ad from each active campaign.
- **Configurable Frequency**: Set the minimum time interval between ad blocks (e.g., every 12 hours).
- **Randomization (Jitter)**: Adds a random time variation to the schedule to make posts feel less robotic.
- **Content Variety**: Avoids posting the same ad from a campaign too frequently.
- **Persistent State**: Remembers its last post time and ad history, even after restarts.
- **Flexible Ad Content**: Supports text-only ads and ads with both an image and text.
- **Dockerized**: Runs entirely within a Docker container for portability and ease of management.
- **Easy Setup**: Includes an interactive setup script to get you started quickly.
- **Dry Run Mode**: Run the bot in a test mode that logs what it would post without actually sending messages to Telegram.
- **On-Demand Posting**: A management command to force an immediate post of either a random ad block or a specific, targeted ad.

## Prerequisites

Before you begin, ensure you have the following installed:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Setup

### 1. Get the Bot Code
Clone this repository to a directory on your system.
```bash
git clone https://github.com/warelock/telegram-ad-bot.git
cd telegram-ad-bot
```

### 2. Create Your Telegram Bot
- Open Telegram and start a chat with [@BotFather](https://t.me/BotFather).
- Send the `/newbot` command and follow the instructions to choose a name and username for your bot.
- BotFather will provide you with a **Bot Token**. Copy this token.

### 3. **(MANDATORY)** Disable Bot Privacy Mode
The bot needs to see messages to check for group activity. You must disable privacy mode.
- In your chat with [@BotFather](https://t.me/BotFather), send the `/mybots` command.
- Select your bot from the list.
- Click on **"Bot Settings"** -> **"Group Privacy"**.
- Click the **"Turn off"** button. BotFather should confirm that privacy is now off for your bot.

*Why is this required? This allows the bot to receive all messages to check if a group is active. The bot's code is open source, and you can verify it only logs message timestamps, never the content.*

### 4. Get the Target Chat ID
- The bot is intended for **public** groups/channels. The Chat ID is the channel's username (e.g., `@mychannel`).
- Add your bot to the channel, promoting it to an administrator with permission to **post messages**.

### 5. Configure Ad Repositories
The bot now sources ad content from remote Git repositories. Each repository represents an "Advertiser". The folders at the root of the repository represent the "Products" or "Campaigns".

- To add a new advertiser, use the `manage.sh` script:
```bash
./manage.sh repo add <advertiser_name> <repository_url>
```
**Example:**
```bash
./manage.sh repo add zth_alliance https://github.com/warelock2/telegram-ad-content-piratechain-group.git
```
- The remote repository should be structured with product/campaign folders at its root. Inside these folders, place your ad files.
- An ad is defined by a text file (`.txt`).
- To add an image to an ad, create an image file (`.jpg`, `.jpeg`, `.png`, `.gif`) with the **exact same name** as the text file.

**Example Repository Structure:**
```
(root of git repository)
├── cipher_wallet/
│   ├── ad1.txt
│   └── ad1.jpg
└── zth_alliance_store/
    ├── ad2.txt
    └── ad3.txt
```

### 6. Run the Interactive Setup
Navigate to the project directory in your terminal and run the setup script to create your main `.env` configuration.
```bash
./setup.sh
```
This script will guide you through creating your `.env` file, asking for your `BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

## Usage
Use the `./manage.sh` script to control the bot and its content.

### Bot Control
- `start`: Build and start the bot.
- `stop`: Stop the bot.
- `restart`: Restart the bot.
- `logs`: View live logs.
- `status`: Show the status of the bot services.

### Content & Cache Management
- `repo list`: List the currently configured ad repositories.
- `repo add <name> <url>`: Add a new advertiser repository.
- `repo remove <name>`: Remove an advertiser and delete its cached content.
- `populate-cache`: Manually clone/pull all repositories into the local cache. Useful for testing without running the bot.
- `flush-cache`: Delete all content from the local ad cache. Use this to force a fresh clone of all repositories.
- `force-post [client] [product] [campaign_basename]`: Immediately trigger an ad post.
  - Run without arguments (`./manage.sh force-post`) to post a random ad block.
  - Provide a specific ad path (`./manage.sh force-post zth_alliance cipher_wallet ad1`) to post that single ad instantly.

## Configuration
All configuration is managed in the `.env` file.

| Variable                       | Description                                                               |
|--------------------------------|---------------------------------------------------------------------------|
| `BOT_TOKEN`                    | Your secret bot token from BotFather.                                     |
| `TELEGRAM_CHAT_ID`             | The channel/group to post in (e.g., `@mychannel`).                        |
| `ADS_DIRECTORY`                | The local directory used as a cache for ad campaigns. Defaults to `ads`.  |
| `AUTH_TEXT`                    | A "sponsored post" message to append to every ad. Leave blank to disable. |
| `TIME_BASED_FREQUENCY_HOURS`   | The base time interval between ad blocks, in hours.                       |
| `RANDOMIZATION_JITTER_MINUTES` | Random time in minutes to add/subtract from the frequency.                |
| `POST_SUCCESS_COOLDOWN_MINUTES`| The cooldown period (in minutes) after a successful post. Prevents spamming. |
| `ACTIVITY_CHECK_ENABLED`       | If `true`, enables the activity check feature.                            |
| `ACTIVITY_CHECK_MESSAGES`      | Minimum messages in the timeframe to be considered "active".              |
| `ACTIVITY_CHECK_TIMEFRAME_MINUTES`| The time window (in minutes) to check for messages.                    |
| `ACTIVITY_CHECK_RETRY_DELAY_MINUTES`| How long (in minutes) to wait before re-checking activity if the group is quiet. |
| `LOG_LEVEL`                    | Logging detail level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).               |
| `DRY_RUN`                      | If `true`, the bot logs posts instead of sending them.                    |
