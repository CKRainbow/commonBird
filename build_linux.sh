#!/bin/bash

latest_tag=$1
github_api_token=$2

echo "APP_VERSION=\"$latest_tag\"" >> src/utils/consts.py
echo "GITHUB_API_TOKEN=\"$github_api_token\"" >> src/utils/consts.py

# build
pyinstaller --name commonBird \
    --add-data "common_bird_app.tcss:." \
    --add-data "public_key.pem:." \
    --exclude-module pandas \
    --exclude-module numpy \
    --exclude-module textual-dev \
    --exclude-module pyinstaller \
    cli.py

npm i markdown-to-html-cli -g

markdown-to-html -i README.md -o dist/commonBird/README.html

python taxon_map_preview.py --map_file ch4_to_eb_taxon_map.json --output_path dist/commonBird/taxon_map_preview.html

cp -r res dist/commonBird/res
cp -r database dist/commonBird/database
cp README.md dist/commonBird
cp changelog.md dist/commonBird

# compress the build
cd dist
tar cvzf ../commonBird_linux_x64.tar.gz commonBird/
cd ..
