#!/bin/bash

# build
pyinstaller --name commonBird \
    --add-data "common_bird_app.tcss:." \
    --add-data "jQuertAjax.js:." \
    --add-data "node_modules:node_modules" \
    --add-binary "$(which node):node" \
    cli.py

npm i markdown-to-html-cli -g

markdown-to-html -i README.md -o dis/commonBird/README.html

cp -r res dist/commonBird/res

# compress the build
tar cvzf commonBird_linux_x64.tar.gz dist/commonBird
