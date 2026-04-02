#!/bin/bash

# path set 
cd ..

# Create virtual environment for backend
python3 -m venv env_backend

# Activate virtual environment
. ./env_backend/bin/activate 

# Set the working directory
cd Backend/ 

# Upgrade pip
pip install --upgrade pip

# Install dependencies from requirements.txt
pip install -r requirements.txt

echo "Pip dependencies for backend installed successfully."


# Create virtual environment for queue
python3 -m venv env_queue

# Activate virtual environment
. ./env_queue/bin/activate 

# Set the working directory
cd Backend/ 

# Upgrade pip
pip install --upgrade pip

# Install dependencies from requirements.txt
pip install -r queue_requirements.txt

echo "Pip dependencies for queue installed successfully."


# change path to scripts file location 
cd ../scripts/

# start the application to apply changes
sh fastapi.sh start
