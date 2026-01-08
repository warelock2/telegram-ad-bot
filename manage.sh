#!/bin/bash
set -e

ENV_FILE=".env"
COMPOSE_FILE="docker-compose.yml"

# --- Helper Functions ---
function check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "\033[31mError: .env file not found.\033[0m"
        echo "Please run './setup.sh' first to generate the .env file."
        exit 1
    fi
}

function start_bot() {
    echo "Building and starting the bot in detached mode..."
    docker-compose -f "$COMPOSE_FILE" up --build -d
    echo -e "\033[32mBot started. Use './manage.sh status' to check and './manage.sh logs' to view logs.\033[0m"
}

function stop_bot() {
    echo "Stopping the bot and removing containers..."
    docker-compose -f "$COMPOSE_FILE" down
    echo -e "\033[32mBot stopped.\033[0m"
}

function restart_bot() {
    stop_bot
    start_bot
}

function show_logs() {
    echo "Attaching to logs. Press Ctrl+C to detach."
    docker-compose -f "$COMPOSE_FILE" logs -f bot
}

function show_status() {
    echo "Current status of bot services:"
    docker-compose -f "$COMPOSE_FILE" ps
}

function flush_cache() {
    echo "Flushing the ad content cache..."
    # Execute the find -delete command inside a Docker container to ensure proper permissions
    docker-compose -f "$COMPOSE_FILE" run --rm bot find /app/ads -mindepth 1 -not -name '.gitkeep' -delete
    echo -e "\033[32mCache flushed. Restart the bot ('./manage.sh restart') to re-populate from remotes.\033[0m"
}

function manage_repos() {
    SUB_COMMAND=$1
    CONF_DIR="conf"
    REPO_LIST_FILE="$CONF_DIR/repolist.txt"

    case "$SUB_COMMAND" in
        list)
            echo "Current ad repositories:"
            if [ -f "$REPO_LIST_FILE" ]; then
                cat "$REPO_LIST_FILE"
            else
                echo "No repositories configured. Use './manage.sh repo add <name> <url>'."
            fi
            ;;
        add)
            NAME=$2
            URL=$3
            if [ -z "$NAME" ] || [ -z "$URL" ]; then
                echo -e "\033[31mError: Missing arguments.\033[0m"
                echo "Usage: ./manage.sh repo add <name> <url>"
                exit 1
            fi
            
            # Ensure conf directory exists
            mkdir -p "$CONF_DIR"

            # Check if name already exists
            if [ -f "$REPO_LIST_FILE" ] && grep -q "^$NAME " "$REPO_LIST_FILE"; then
                echo -e "\033[31mError: A repository with the name '$NAME' already exists.\033[0m"
                exit 1
            fi
            echo "$NAME $URL" >> "$REPO_LIST_FILE"
            echo -e "\033[32mRepository '$NAME' added.\033[0m"
            ;;
        remove)
            NAME=$2
            if [ -z "$NAME" ]; then
                echo -e "\033[31mError: Missing argument.\033[0m"
                echo "Usage: ./manage.sh repo remove <name>"
                exit 1
            fi
            if [ ! -f "$REPO_LIST_FILE" ]; then
                echo -e "\033[31mError: repolist.txt not found in conf/. Nothing to remove.\033[0m"
                exit 1
            fi
            # Remove the line using sed. The -i flag edits in-place.
            sed -i "/^$NAME /d" "$REPO_LIST_FILE"
            # Also remove the cached directory inside a Docker container
            docker-compose -f "$COMPOSE_FILE" run --rm bot rm -rf "/app/ads/$NAME"
            echo -e "\033[32mRepository '$NAME' removed and cache cleared.\033[0m"
            ;;
        *)
            echo "Usage: ./manage.sh repo [list|add|remove]"
            ;;
    esac
}

function print_usage() {
    echo "Usage: ./manage.sh [command]"
    echo "Commands:"
    echo "  start                : Build and start the bot."
    echo "  stop                 : Stop the bot and remove containers."
    echo "  restart              : Stop and then restart the bot."
    echo "  logs                 : View live logs from the bot."
    echo "  status               : Show the status of the bot services."
    echo "  force-post [args...] : Trigger an ad post."
    echo "  flush-cache          : Deletes all local ad content to force a fresh clone."
    echo "  populate-cache       : Fetches remote ad content into the local cache."
    echo "  repo list            : List configured ad repositories."
    echo "  repo add <name> <url>: Add a new ad repository."
    echo "  repo remove <name>   : Remove an ad repository."
    echo
    echo "Example force-post:"
    echo "  ./manage.sh force-post zth_alliance cipher_wallet ad1"
}

function force_post() {
    echo "Directly triggering an ad post..."
    # Pass all arguments passed to this function to the python script
    docker-compose -f "$COMPOSE_FILE" run --rm bot python force_post.py "$@"
    echo -e "\033[32mDirect post command finished. Check logs for details.\033[0m"
    echo "You can monitor the output with './manage.sh logs'."
}

function populate_cache() {
    echo "Manually populating the ad cache from remote repositories..."
    docker-compose -f "$COMPOSE_FILE" run --rm bot python manual_sync.py
    echo -e "\033[32mCache population command finished. Check logs for details.\033[0m"
}

# --- Main Script ---
# The check_env function is not needed for repo management or flush-cache
if [[ "$1" != "repo" && "$1" != "flush-cache" && "$1" != "populate-cache" ]]; then
    check_env
fi

# Parse command
COMMAND=$1
if [ -z "$COMMAND" ]; then
    print_usage
    exit 1
fi

case "$COMMAND" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    force-post)
        shift # The first argument is 'force-post', we don't need it.
        force_post "$@" # Pass the rest of the arguments
        ;;
    repo)
        shift # The first argument is 'repo', we don't need it.
        manage_repos "$@" # Pass the rest of the arguments
        ;;
    flush-cache)
        flush_cache
        ;;
    populate-cache)
        populate_cache
        ;;
    *)
        echo -e "\033[31mError: Unknown command '$COMMAND'.\033[0m"
        print_usage
        exit 1
        ;;
esac

exit 0
