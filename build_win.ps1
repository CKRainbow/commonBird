pyinstaller --name commonBird `
    --add-data "common_bird_app.tcss:." `
    --add-data "jQuertAjax.js:." `
    --add-data "node_modules:node_modules" `
    --add-binary "$((Get-Command node.exe).Source):node.exe" `
    cli.py

Copy-Item -Path "README.md" -Destination "dist/commonBird"

# compress the build
Compress-Archive -Path "dist/commonBird" -DestinationPath "commonBird_win64.zip"