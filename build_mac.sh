#!/bin/bash

# build
pyinstaller --name commonBird \
    --add-data "common_bird_app.tcss:." \
    --add-data "jQuertAjax.js:." \
    --add-data "node_modules:node_modules" \
    --add-binary "$(which node):node" \
    cli.py

cp README.md dist/commonBird

# compress the build
tar cvzf commonBird_mac_x64.tar.gz dist/commonBird
