pyinstaller --name commonBird `
    --add-data "common_bird_app.tcss:." `
    --add-data "jQuertAjax.js:." `
    --add-data "node_modules:node_modules" `
    --add-binary "$((Get-Command node.exe).Source):node.exe" `
    cli.py

# compress the build
Compress-Archive -Path "dist/commonBird" -DestinationPath "commonBird_win64.zip"