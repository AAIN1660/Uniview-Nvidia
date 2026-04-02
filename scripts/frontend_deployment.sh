#!/bin/bash

# path set 
cd ..

# Navigate to ui
cd Frontend/

# setting stable node version
nvm use node stable

# Node Modules & packages installation
npm install 

# Production build
npm run-script build:prod

# Copy build files onto nginx folder for Quin
sudo cp -r ./dist/* /var/www/uniview/

# 404 error fix
# Open default settings file with sudo privileges in ex editor
#sudo ex -s -c '51s/.*/try_files $uri \/index.html;/' -c 'x' /etc/nginx/sites-available/default

# Restart Nginx service
sudo service nginx restart
