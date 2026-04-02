#!/bin/bash

# Prompt for repository URL
read -p "Enter repository URL (e.g., https://github.com/Affineindia/UnifiedView_ERYL-QUIN): " url

# Check if the URL is provided
if [ -z "$url" ]; then
    echo "Error: No repository URL provided."
    exit 1
fi

# Remove the protocol (https://) from the URL
base_repo_url=$(echo "$url" | sed 's|https://||')

# Prompt for username
read -p "Enter username: " username

# Prompt for Personal Access Token (hidden input)
read -s -p "Enter Personal Access Token: " password
echo # Move to a new line after hidden input

# Prompt for branch name
read -p "Enter branch name: " branchName

# Echo a message to show the cloning process has started
echo "Cloning repository $url from branch '$branchName'..."

# Construct the full URL including username and password for authentication
auth_url="https://$username:$password@$base_repo_url"

# Attempt to clone the repository using the provided credentials and branch
if ! git clone -b "$branchName" "$auth_url"; then
    # Display an error message if cloning fails
    echo "Error: Authentication failed, or branch '$branchName' not found."
    exit 1  # Exit the script with a non-zero status (indicating failure)
fi

# Display a success message if the clone is successful
echo "Repository cloned successfully."
