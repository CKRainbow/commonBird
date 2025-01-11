# Download node
Invoke-WebRequest -Uri "https://nodejs.org/dist/v22.13.0/node-v22.13.0-win-x64.zip" -OutFile "node-v22.13.0-win-x64.zip"

# Uncompress
Expand-Archive -Path "node-v22.13.0-win-x64.zip" -DestinationPath .

pyinstaller --name commonBird `
    --add-data "common_bird_app.tcss:." `
    --add-data "jQuertAjax.js:." `
    --add-data "node_modules:node_modules" `
    --add-binary "node-v22.13.0-win-x64/bin/node:node" `
    cli.py

# compress the build
Compress-Archive -Path "dist/commonBird" -DestinationPath "commonBird_win64.zip"