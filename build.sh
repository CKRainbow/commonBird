#!/bin/bash

# downloaad node
wget https://nodejs.org/dist/v22.13.0/node-v22.13.0-linux-x64.tar.xz

# uncompress 
tar -xvf node-v22.13.0-linux-x64.tar.xz

# build
pyinstaller --name commonBird \
    --add-data "common_bird_app.tcss:." \
    --add-data "jQuertAjax.js:." \
    --add-data "node_modules:node_modules" \
    --add-binary "node-v22.13.0-linux-x64/bin/node:node" \
    cli.py

# compress the build
tar cvzf commonBird_linux_64.tar.gz dist/commonBird
