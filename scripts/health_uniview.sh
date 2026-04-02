#!/bin/bash

URL="$1"

# Make a GET request to the provided URL and extract the status_code using jq in one step
status_code=$(curl -s -X GET "$URL" -H 'accept: application/json' | jq -r '.status_code')

# Debugging: Print the extracted status code or a message if it's missing
echo "Extracted status_code: ${status_code:-No status code found for Eryl}"

# Check if status_code is empty or null
if [ -z "$status_code" ] || [ "$status_code" = "null" ]; then
    echo "No status code found. Running 'pm2 stop all'."
    sh fastapi.sh stop
    sleep 5
    sh fastapi.sh start
    echo "Script exited at: $(date +'%Y-%m-%d %H:%M:%S') after restarting the Eryl application."
else
    # Print the status code
    echo "Status Code: $status_code"
    echo "Script exited at: $(date +'%Y-%m-%d %H:%M:%S') due to helath check success for Eryl application."
fi
