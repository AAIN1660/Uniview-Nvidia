#!/bin/bash

# path set 
cd ..

# Navigate to ui
cd Frontend/

# setting stable node version
nvm use node stable

# Ask if Node module to be reinstalled
read -p "Do you want to reinstall Node Modules (Y/N): " nodepermission

# Delete the existing node_modules if present
if [ "$nodepermission" = 'Y' ]; then
    if [ -d "node_modules" ]; then
        echo "Deleting node_modules folder..."
        sudo rm -rf node_modules
        echo "node_modules folder deleted."
    fi
    # Node Modules & packages installation
    npm install
fi

# Delete the exsisting build folder if present
if [ -d "dist" ]; then
    echo "Deleting build folder..."
    sudo rm -rf dist
    echo "build folder deleted."
fi

# Production build
npm run-script build:prod

# remove the exsisting build files present in nginx
sudo rm -rf /var/www/uniview/*

# Copy build files onto nginx folder for Quin
sudo cp -r ./dist/* /var/www/uniview/

# Restart Nginx service
sudo service nginx restart
