#!/bin/bash

# path set 
cd ..

# Activate virtual environment for backend application
. ./env_backend/bin/activate 

# Set the working directory
cd Backend/

# Upgrade pip
pip install --upgrade pip

# Install dependencies from requirements.txt
pip install -r requirements.txt



# Activate virtual environment for queue service application
. ./env_backend/bin/activate 

# Set the working directory
cd Backend/

# Upgrade pip
pip install --upgrade pip

# Install dependencies from requirements.txt
pip install -r queue_requirements.txt


# change path to scripts file location 
cd ../scripts/

# Stop the application 
sh fastapi.sh stop

# Restart the application to apply changes
sh fastapi.sh start



