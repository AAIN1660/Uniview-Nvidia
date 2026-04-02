#!/bin/bash

# Python Installation
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12


# Upgrade pip
pip install --upgrade pip

# pm2 installation
sudo apt install -y npm
sudo npm install -g pm2


# Npm Installationsudo apt update
sudo apt update
sudo apt install -y npm

# Node.js using NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash
nvm install stable
nvm use node stable

# Nginx installation
sudo apt install -y nginx
sudo service nginx restart

