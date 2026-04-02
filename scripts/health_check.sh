#!/bin/bash

# Function to display help message
display_help() {
    echo "Usage: ./script.sh <base_url> <port> <api>"
    echo "Parameters:"
    echo "  base_url - URL of the domain, e.g., https://uniview.generax.ai"
    echo "  port     - Backend port, e.g., 8000"
    echo "  api      - Health check API endpoint, e.g., health"
}

# Log the start time
echo "Script started at: $(date +'%Y-%m-%d %H:%M:%S')"

# Check if the number of arguments is 3 (excluding script name)
if [ "$#" -ne 3 ]; then
    display_help
    echo "Script exited at: $(date +'%Y-%m-%d %H:%M:%S') due to incorrect number of arguments."
    exit 1
fi

# Assign arguments to variables
base_url=$1
port=$2
api=$3


# Validate base_url using grep
if ! echo "$base_url" | grep -qE '^https?://'; then
    echo "Invalid base_url. It should start with 'http://' or 'https://'."
    display_help
    echo "Script exited at: $(date +'%Y-%m-%d %H:%M:%S') due to invalid base_url."
    exit 1
fi


# Check if the running script is already running
if pgrep -f "health_eryl.sh" > /dev/null; then
    echo "Script 'health_eryl.sh' is already running. Exiting."
    echo "Script exited at: $(date +'%Y-%m-%d %H:%M:%S')"
    exit 0
fi

# Construct the URL
URL="${base_url}:${port}/${api}"

# change to scripts
cd /home/azureuser/UnifiedView_ERYL-QUIN/scripts

# run health script file
sh health_uniview.sh $URL
