#!/bin/bash
set -x  # Enable debugging

ACTION="$1"

# Read service names from environment variables
SERVICE_NAME=${SERVICE_NAME:-"uniview-backend"}
SERVICE_NAME_1=${SERVICE_NAME_1:-"uniview-vector-queue"}
SERVICE_NAME_2=${SERVICE_NAME_2:-"uniview-graphrag-queue"}


# Paths to virtual environments
ENV_PATH_SERVICE_NAME="/home/env_backend/bin/activate"
ENV_PATH_SERVICE_NAME_1="/home/env_vector_queue/bin/activate"
ENV_PATH_SERVICE_NAME_2="/home/env_backend/bin/activate"


# Function to start the FastAPI Backend
start_backend() {
    echo "Starting the FastAPI Backend..."
    
    # Activate virtual environment for SERVICE_NAME
    if [ -f "$ENV_PATH_SERVICE_NAME" ]; then
        echo "Activating environment for $SERVICE_NAME..."
        . "$ENV_PATH_SERVICE_NAME"

	cd ..
	cd Backend
  
        pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 1728000 --reload --limit-max-requests 1000 --ssl-keyfile=/web_ssl/cert/generax.ai/privkey.pem --ssl-certfile=/web_ssl/cert/generax.ai/fullchain.pem --loop asyncio" --name "$SERVICE_NAME"
	deactivate

    else
        echo "Environment not found for $SERVICE_NAME at $ENV_PATH_SERVICE_NAME"
        exit 1
    fi

    # Activate virtual environment for SERVICE_NAME_1
    if [ -f "$ENV_PATH_SERVICE_NAME_1" ]; then
        echo "Activating environment for $SERVICE_NAME_1..."
        . "$ENV_PATH_SERVICE_NAME_1"

	cd ..
	cd Backend
        
        pm2 start "uvicorn queue_service_app:app --host 0.0.0.0 --port 8001 --workers 2 --timeout-keep-alive 1728000 --reload --limit-max-requests 1000 --ssl-keyfile=/web_ssl/cert/generax.ai/privkey.pem --ssl-certfile=/web_ssl/cert/generax.ai/fullchain.pem" --name "$SERVICE_NAME_1"
        deactivate
    else
        echo "Environment not found for $SERVICE_NAME_1 at $ENV_PATH_SERVICE_NAME_1"
        exit 1
    fi


        # Activate virtual environment for SERVICE_NAME_2
    if [ -f "$ENV_PATH_SERVICE_NAME_2" ]; then
        echo "Activating environment for $SERVICE_NAME_2..."
        . "$ENV_PATH_SERVICE_NAME_2"

	cd ..
	cd Backend
  
        pm2 start "uvicorn graphrag_queue_service_app:app --host 0.0.0.0 --port 8002 --workers 4 --timeout-keep-alive 1728000 --reload --limit-max-requests 1000 --ssl-keyfile=/web_ssl/cert/generax.ai/privkey.pem --ssl-certfile=/web_ssl/cert/generax.ai/fullchain.pem --loop asyncio" --name "$SERVICE_NAME_2"
	deactivate

    else
        echo "Environment not found for $SERVICE_NAME at $ENV_PATH_SERVICE_NAME"
        exit 1
    fi



    echo "FastAPI Backend started successfully..."
}

# Function to stop the FastAPI Backend
stop_backend() {
    echo "Stopping the FastAPI Backend..."
    pm2 stop "$SERVICE_NAME"
    pm2 stop "$SERVICE_NAME_1"
    pm2 stop "$SERVICE_NAME_2"
    pm2 delete "$SERVICE_NAME"
    pm2 delete "$SERVICE_NAME_1"
    pm2 delete "$SERVICE_NAME_2"
    pm2 save
    echo "FastAPI Backend stopped successfully..."
}

# Function to display help
display_help() {
    echo "Usage: ./script.sh [action]"
    echo "Available actions:"
    echo "  start - Start the FastAPI Backend"
    echo "  stop  - Stop the FastAPI Backend"
    echo "  help  - Display this help message"
}

# Main script logic
if [ "$ACTION" = "start" ]; then
    start_backend
elif [ "$ACTION" = "stop" ]; then
    stop_backend
elif [ "$ACTION" = "help" ]; then
    display_help
else
    echo "Invalid action provided. Please provide either 'start', 'stop', or 'help'."
    exit 1
fi
