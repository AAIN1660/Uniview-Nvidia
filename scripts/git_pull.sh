#!/bin/bash

# path set 
cd ..

# Ensure script is run from a git repository
if [ ! -d .git ]; then
  echo "Error: This is not a git repository!"
  exit 1
fi

# Stash current changes
echo "Stashing current changes..."
git stash > /dev/null 2>&1

# Read branch name
read -p "Enter branch name to pull from: " branchName

# Check if branch name is provided
if [ -z "$branchName" ]; then
  echo "Error: No branch name provided!"
  exit 1
fi

# Pull changes from the provided branch
echo "Pulling changes from $branchName branch..."

git pull origin "$branchName"
if [ $? -ne 0 ]; then
  echo "Error: Failed to pull changes from $branchName."
  exit 1
fi

# Apply stashed changes
echo "Applying stashed changes..."
git stash apply > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "No changes to apply from stash or stash application failed."
  exit 1
fi

echo "--------- Pull completed successfully ---------"
