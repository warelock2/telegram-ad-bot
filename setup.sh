#!/bin/bash
# Using set -e is disabled because we need to handle read's exit code on EOF
# set -e

ENV_FILE=".env"
SAMPLE_FILE="env-example.txt"

# --- Helper Functions ---
function check_command() {
    if ! command -v $1 &> /dev/null
    then
        echo -e "\033[31mError: $1 is not installed. Please install it to continue.\033[0m"
        exit 1
    fi
}

# --- Main Script ---
echo -e "\033[32m--- Telegram Ad Bot Setup ---\\033[0m"

# 1. Check for prerequisites
echo "Checking for prerequisites (docker, docker-compose)..."
check_command docker
check_command docker-compose
echo "All prerequisites are met."
echo ""

# 2. Ensure .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "No .env file found. Creating one from $SAMPLE_FILE..."
    cp "$SAMPLE_FILE" "$ENV_FILE"
fi

# 3. Source the .env file to get current values into the shell environment
# We add `|| true` in case the file is empty or has errors, to prevent exit
source "$ENV_FILE" || true

# 4. Build a list of variables to configure from the sample file
# This filters out empty lines and lines starting with #
VAR_LIST=$(grep -v '^\s*#' "$SAMPLE_FILE" | grep -v '^\s*$' | cut -d '=' -f 1)

echo "Please configure your bot. Press Enter to accept the current value in brackets."
echo ""

# 5. Loop through the variables and prompt the user
for VAR_NAME in $VAR_LIST; do
    # Use indirect expansion to get the current value of the variable from the environment
    CURRENT_VALUE="${!VAR_NAME}"
    
    # Prompt the user
    echo -n "$VAR_NAME [33m[$CURRENT_VALUE][0m: "
    
    # Read user input. `read` will return a non-zero exit code on EOF (Ctrl+D),
    # so we add `|| true` to prevent the script from exiting if the user does that.
    read USER_INPUT || true

    # If input is not empty, update the .env file
    if [ -n "$USER_INPUT" ]; then
        # Escape for sed: primarily backslashes, forward slashes, and ampersands
        NEW_VALUE_ESCAPED=$(echo "$USER_INPUT" | sed -e 's/\\/\\\\/g' -e 's/\//\\\//g' -e 's/&/\\&/g')
        
        # Use a different delimiter for sed to avoid conflicts with slashes in paths
        sed -i.bak "s|^$VAR_NAME=.*|$VAR_NAME=$NEW_VALUE_ESCAPED|" "$ENV_FILE"
        rm "${ENV_FILE}.bak" # Clean up the backup file created by sed -i
        
        # Re-source the file so the next prompt shows the updated value if it's referenced
        source "$ENV_FILE" || true
    fi
done

echo ""
echo -e "\033[32mConfiguration saved to .env file.\033[0m"
echo ""

# 6. Ask to start the bot
read -p "Do you want to build and start the bot now? (y/N) " START_NOW
if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    echo "Starting bot..."
    ./manage.sh start
else
    echo "You can start the bot later by running: ./manage.sh start"
fi

exit 0
